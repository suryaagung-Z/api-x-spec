"""Application-layer use cases for event registration (no HTTP imports)."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas.registrations import (
    RegistrationResponse,
    RegistrationWithEventResponse,
)
from src.application.event_service import get_public_event
from src.domain.exceptions import (
    DuplicateActiveRegistrationError,
    EventNotFoundError,
    NoActiveRegistrationError,
    QuotaFullError,
    RegistrationDeadlinePassedError,
)
from src.infrastructure.repositories.registration_repository import (
    RegistrationRepository,
)

logger = logging.getLogger(__name__)


async def register(
    session: AsyncSession, user_id: str, event_id: int
) -> RegistrationResponse:
    """Register user for an event.

    Guards (evaluated in order):
    1. Event exists and is ACTIVE → raises EventNotFoundError (404)
    2. registration_deadline not passed → raises RegistrationDeadlinePassedError (422)
    3. No existing ACTIVE registration → raises DuplicateActiveRegistrationError (409)
    4. current_participants < quota → raises QuotaFullError (422)
    """
    # 1. Check event exists and is ACTIVE
    # raises EventNotFoundError if not found
    event = await get_public_event(event_id, session)

    # 2. Check registration deadline
    now = datetime.now(tz=UTC)
    deadline = event.registration_deadline
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=UTC)
    if now >= deadline:
        raise RegistrationDeadlinePassedError(event_id)

    repo = RegistrationRepository(session)

    # 3. Pre-check for existing active registration (app-level guard)
    existing = await repo.get_active_registration(user_id, event_id)
    if existing is not None:
        raise DuplicateActiveRegistrationError(user_id, event_id)

    # 4. Atomic quota increment — returns None if quota exhausted
    event_id_returned = await repo.atomic_increment_participants(event_id)
    if event_id_returned is None:
        raise QuotaFullError(event_id)

    # 5. Create registration (catch DB-level duplicate from partial unique index)
    try:
        orm = await repo.create_registration(user_id, event_id)
    except IntegrityError as exc:
        # Unique index violation: concurrent duplicate registration
        await session.rollback()
        raise DuplicateActiveRegistrationError(user_id, event_id) from exc

    await session.commit()
    logger.info(
        "User %s registered for event %s (reg_id=%s)", user_id, event_id, orm.id
    )
    return RegistrationResponse.model_validate(orm)


async def cancel(session: AsyncSession, user_id: str, event_id: int) -> None:
    """Cancel a user's active registration for an event.

    Guards (evaluated in order):
    1. Active registration exists → raises NoActiveRegistrationError (404)
    2. Event still exists and is ACTIVE → raises EventNotFoundError (404)
    3. registration_deadline not passed → raises RegistrationDeadlinePassedError (422)
    """
    repo = RegistrationRepository(session)

    # 1. Check active registration exists
    existing = await repo.get_active_registration(user_id, event_id)
    if existing is None:
        raise NoActiveRegistrationError(user_id, event_id)

    # 2. Check event still accessible
    try:
        event = await get_public_event(event_id, session)
    except EventNotFoundError:
        raise

    # 3. Check registration deadline
    now = datetime.now(tz=UTC)
    deadline = event.registration_deadline
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=UTC)
    if now >= deadline:
        raise RegistrationDeadlinePassedError(event_id)

    # Cancel and decrement counter
    await repo.cancel_registration(user_id, event_id)
    await repo.atomic_decrement_participants(event_id)
    await session.commit()
    logger.info("User %s cancelled registration for event %s", user_id, event_id)


async def get_my_registrations(
    session: AsyncSession, user_id: str
) -> list[RegistrationWithEventResponse]:
    """Return all registrations for the current user, ordered newest first."""
    repo = RegistrationRepository(session)
    orms = await repo.get_my_registrations(user_id)
    return [RegistrationWithEventResponse.model_validate(o) for o in orms]
