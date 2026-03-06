"""Async repository for Event CRUD operations."""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.models import EventStatus
from src.infrastructure.db.models import Event as OrmEvent


class EventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # Shared: base query for public (ACTIVE, future) events
    # ------------------------------------------------------------------
    def _public_base_query(self) -> Select[tuple[OrmEvent]]:
        now = datetime.now(tz=UTC)
        return (
            select(OrmEvent)
            .where(OrmEvent.status == EventStatus.ACTIVE)
            .where(OrmEvent.date > now)
        )

    # ------------------------------------------------------------------
    # US1: Create
    # ------------------------------------------------------------------
    async def create(
        self,
        *,
        title: str,
        description: str,
        date: datetime,
        registration_deadline: datetime,
        quota: int,
    ) -> OrmEvent:
        orm = OrmEvent(
            title=title,
            description=description,
            date=date,
            registration_deadline=registration_deadline,
            quota=quota,
            status=EventStatus.ACTIVE,
            created_at=datetime.now(tz=UTC),
            updated_at=datetime.now(tz=UTC),
        )
        self._session.add(orm)
        await self._session.flush()
        await self._session.refresh(orm)
        return orm

    # ------------------------------------------------------------------
    # US2: Admin read / update / soft-delete (no status filter)
    # ------------------------------------------------------------------
    async def get_by_id_admin(self, event_id: int) -> OrmEvent | None:
        result = await self._session.execute(
            select(OrmEvent).where(OrmEvent.id == event_id)
        )
        return result.scalar_one_or_none()

    async def update(self, orm: OrmEvent, changes: dict[str, object]) -> OrmEvent:
        for key, value in changes.items():
            setattr(orm, key, value)
        orm.updated_at = datetime.now(tz=UTC)
        await self._session.flush()
        await self._session.refresh(orm)
        return orm

    async def soft_delete(self, orm: OrmEvent) -> None:
        orm.status = EventStatus.DELETED
        orm.updated_at = datetime.now(tz=UTC)
        await self._session.flush()

    # ------------------------------------------------------------------
    # US3: Public listing (ACTIVE + future only)
    # ------------------------------------------------------------------
    async def count_public(self) -> int:
        base = self._public_base_query()
        count_stmt = select(func.count()).select_from(base.order_by(None).subquery())
        result = await self._session.execute(count_stmt)
        return int(result.scalar_one())

    async def list_public(self, *, offset: int, limit: int) -> list[OrmEvent]:
        stmt = (
            self._public_base_query()
            .order_by(OrmEvent.date.asc(), OrmEvent.title.asc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_public_by_id(self, event_id: int) -> OrmEvent | None:
        result = await self._session.execute(
            select(OrmEvent)
            .where(OrmEvent.id == event_id)
            .where(OrmEvent.status == EventStatus.ACTIVE)
        )
        return result.scalar_one_or_none()
