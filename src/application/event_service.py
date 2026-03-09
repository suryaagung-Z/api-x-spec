"""Application-layer use cases for event management (no HTTP imports)."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas.events import EventCreate, EventResponse, EventUpdate
from src.api.schemas.pagination import Page
from src.domain.exceptions import (
    EventDateInPastError,
    EventNotFoundError,
    QuotaBelowParticipantsError,
)
from src.infrastructure.repositories.event_repository import EventRepository

logger = logging.getLogger(__name__)


def _to_utc(dt: datetime) -> datetime:
    """Normalize a datetime to UTC.

    Naive datetimes are assumed to be UTC (as stored by SQLite).
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


# ---------------------------------------------------------------------------
# US1: Create
# ---------------------------------------------------------------------------


async def create_event(body: EventCreate, session: AsyncSession) -> EventResponse:
    now = datetime.now(tz=UTC)
    date_utc = _to_utc(body.date)

    if date_utc <= now:
        raise EventDateInPastError()

    deadline_utc = _to_utc(body.registration_deadline)
    repo = EventRepository(session)
    orm = await repo.create(
        title=body.title,
        description=body.description,
        date=date_utc,
        registration_deadline=deadline_utc,
        quota=body.quota,
    )
    logger.info("Event created: id=%s title=%r", orm.id, orm.title)
    return EventResponse.model_validate(orm)


# ---------------------------------------------------------------------------
# US2: Admin read / update / delete
# ---------------------------------------------------------------------------


async def get_event_admin(event_id: int, session: AsyncSession) -> EventResponse:
    repo = EventRepository(session)
    orm = await repo.get_by_id_admin(event_id)
    if orm is None:
        raise EventNotFoundError(event_id)
    return EventResponse.model_validate(orm)


async def update_event(
    event_id: int, body: EventUpdate, session: AsyncSession
) -> EventResponse:
    repo = EventRepository(session)
    orm = await repo.get_by_id_admin(event_id)
    if orm is None:
        raise EventNotFoundError(event_id)

    # Resolve effective date and deadline (partial update: merge with stored)
    new_date = _to_utc(body.date) if body.date is not None else _to_utc(orm.date)
    new_deadline = (
        _to_utc(body.registration_deadline)
        if body.registration_deadline is not None
        else _to_utc(orm.registration_deadline)
    )

    # Cross-validate deadline ≤ date using merged values
    if new_deadline > new_date:
        from fastapi import HTTPException

        from src.api.schemas.errors import ErrorDetail, ErrorEnvelope

        raise HTTPException(
            status_code=422,
            detail=ErrorEnvelope(
                error=ErrorDetail(
                    code="VALIDATION_ERROR",
                    message="registration_deadline must be on or before the event date",
                    httpStatus=422,
                )
            ).model_dump(),
        )

    # Quota protection: treat 0 as "no registrations for now"
    participant_count = 0  # replaced by feature 003
    new_quota = body.quota if body.quota is not None else orm.quota
    if new_quota < participant_count:
        raise QuotaBelowParticipantsError(event_id, new_quota, participant_count)

    changes: dict[str, object] = {}
    if body.title is not None:
        changes["title"] = body.title
    if body.description is not None:
        changes["description"] = body.description
    if body.date is not None:
        changes["date"] = new_date
    if body.registration_deadline is not None:
        changes["registration_deadline"] = new_deadline
    if body.quota is not None:
        changes["quota"] = body.quota

    orm = await repo.update(orm, changes)
    logger.info("Event updated: id=%s", event_id)
    return EventResponse.model_validate(orm)


async def delete_event(event_id: int, session: AsyncSession) -> None:
    repo = EventRepository(session)
    orm = await repo.get_by_id_admin(event_id)
    if orm is None:
        raise EventNotFoundError(event_id)
    from src.domain.models import EventStatus

    if orm.status == EventStatus.DELETED:
        raise EventNotFoundError(event_id)
    await repo.soft_delete(orm)
    logger.info("Event soft-deleted: id=%s", event_id)


# ---------------------------------------------------------------------------
# US3: Public listing and detail
# ---------------------------------------------------------------------------


async def list_public_events(
    session: AsyncSession, *, page: int, page_size: int
) -> Page[EventResponse]:
    repo = EventRepository(session)
    total = await repo.count_public()
    offset = (page - 1) * page_size
    items = await repo.list_public(offset=offset, limit=page_size)
    return Page[EventResponse](
        items=[EventResponse.model_validate(o) for o in items],
        total_items=total,
        page=page,
        page_size=page_size,
    )


async def get_public_event(event_id: int, session: AsyncSession) -> EventResponse:
    repo = EventRepository(session)
    orm = await repo.get_public_by_id(event_id)
    if orm is None:
        raise EventNotFoundError(event_id)
    return EventResponse.model_validate(orm)
