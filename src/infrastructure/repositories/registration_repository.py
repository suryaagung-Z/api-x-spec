"""Async repository for EventRegistration CRUD operations."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy import update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.domain.models import RegistrationStatus
from src.infrastructure.db.models import Event as OrmEvent
from src.infrastructure.db.models import EventRegistration as OrmRegistration


class RegistrationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # US1: Register
    # ------------------------------------------------------------------

    async def get_active_registration(
        self, user_id: str, event_id: int
    ) -> OrmRegistration | None:
        """Return the ACTIVE registration for (user, event) or None."""
        result = await self._session.execute(
            select(OrmRegistration)
            .where(OrmRegistration.user_id == user_id)
            .where(OrmRegistration.event_id == event_id)
            .where(OrmRegistration.status == RegistrationStatus.ACTIVE)
        )
        return result.scalar_one_or_none()

    async def atomic_increment_participants(self, event_id: int) -> int | None:
        """Atomically increment current_participants if quota not reached.

        Returns the event ID on success, None if quota is full.
        """
        stmt = (
            sa_update(OrmEvent)
            .where(OrmEvent.id == event_id)
            .where(OrmEvent.current_participants < OrmEvent.quota)
            .values(current_participants=OrmEvent.current_participants + 1)
            .returning(OrmEvent.id)
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return row

    async def create_registration(self, user_id: str, event_id: int) -> OrmRegistration:
        """Insert a new ACTIVE registration row and return it."""
        orm = OrmRegistration(
            user_id=user_id,
            event_id=event_id,
            status=RegistrationStatus.ACTIVE,
            registered_at=datetime.now(tz=UTC),
        )
        self._session.add(orm)
        await self._session.flush()
        await self._session.refresh(orm)
        return orm

    # ------------------------------------------------------------------
    # US2/US3: Cancel
    # ------------------------------------------------------------------

    async def cancel_registration(self, user_id: str, event_id: int) -> None:
        """Soft-cancel: set status=CANCELLED and populate cancelled_at."""
        stmt = (
            sa_update(OrmRegistration)
            .where(OrmRegistration.user_id == user_id)
            .where(OrmRegistration.event_id == event_id)
            .where(OrmRegistration.status == RegistrationStatus.ACTIVE)
            .values(
                status=RegistrationStatus.CANCELLED,
                cancelled_at=datetime.now(tz=UTC),
            )
        )
        await self._session.execute(stmt)
        await self._session.flush()

    async def atomic_decrement_participants(self, event_id: int) -> None:
        """Atomically decrement current_participants (guard: >= 0)."""
        stmt = (
            sa_update(OrmEvent)
            .where(OrmEvent.id == event_id)
            .where(OrmEvent.current_participants > 0)
            .values(current_participants=OrmEvent.current_participants - 1)
        )
        await self._session.execute(stmt)
        await self._session.flush()

    # ------------------------------------------------------------------
    # US3: List my registrations
    # ------------------------------------------------------------------

    async def get_my_registrations(self, user_id: str) -> list[OrmRegistration]:
        """Return all registrations for a user, newest first, with event loaded."""
        result = await self._session.execute(
            select(OrmRegistration)
            .where(OrmRegistration.user_id == user_id)
            .options(selectinload(OrmRegistration.event))
            .order_by(OrmRegistration.registered_at.desc())
        )
        return list(result.scalars().all())
