"""Async repository for read-only admin reporting aggregate queries.

No ORM models or Alembic migrations are added — this is a purely read-only
layer over the existing `events` and `event_registrations` tables.

Aggregate pattern:
  Single LEFT JOIN + COUNT(er.id) FILTER (WHERE er.status = 'active') query
  avoids N+1 queries (NFR-001). A separate scalar COUNT query provides the
  pagination total.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.models import EventStatus, RegistrationStatus
from src.infrastructure.db.models import Event as OrmEvent
from src.infrastructure.db.models import EventRegistration as OrmRegistration


@dataclass(frozen=True)
class EventStatRow:
    """One row returned from the per-event aggregate query (not persisted).

    remaining_quota = quota - total_registered; may be negative (FR-008).
    """

    id: int
    title: str
    date: datetime
    quota: int
    total_registered: int
    remaining_quota: int


class ReportingRepository:
    """Read-only repository for admin reporting queries."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_event_stats_page(
        self,
        offset: int,
        limit: int,
    ) -> tuple[list[EventStatRow], int]:
        """Return paginated per-event statistics and total active-event count.

        Issues exactly two SQL statements:
          1. Aggregate stats query (LEFT JOIN + COUNT FILTER) with LIMIT/OFFSET
          2. Scalar COUNT query for pagination total

        The aggregate query runs in O(1) statements regardless of the number
        of active events, satisfying NFR-001 (no N+1 queries).

        "Active event" predicate: status = 'active' AND date > NOW()
        (consistent with FR-001 and the 002 public listing filter).
        """
        now = datetime.now(UTC)

        # COUNT of active (non-cancelled) registrations per event
        active_reg_count = func.count(OrmRegistration.id).filter(
            OrmRegistration.status == RegistrationStatus.ACTIVE
        )

        stats_query = (
            select(
                OrmEvent.id,
                OrmEvent.title,
                OrmEvent.date,
                OrmEvent.quota,
                active_reg_count.label("total_registered"),
                (OrmEvent.quota - active_reg_count).label("remaining_quota"),
            )
            .outerjoin(OrmRegistration, OrmRegistration.event_id == OrmEvent.id)
            .where(OrmEvent.status == EventStatus.ACTIVE, OrmEvent.date > now)
            .group_by(OrmEvent.id)
            .order_by(OrmEvent.date.asc(), OrmEvent.id.asc())
            .offset(offset)
            .limit(limit)
        )

        count_query = (
            select(func.count())
            .select_from(OrmEvent)
            .where(OrmEvent.status == EventStatus.ACTIVE, OrmEvent.date > now)
        )

        rows = (await self._session.execute(stats_query)).all()
        total = (await self._session.execute(count_query)).scalar_one()

        return (
            [
                EventStatRow(
                    id=r.id,
                    title=r.title,
                    date=r.date,
                    quota=r.quota,
                    total_registered=r.total_registered,
                    remaining_quota=r.remaining_quota,
                )
                for r in rows
            ],
            total,
        )

    async def get_total_active_events(self) -> int:
        """Return count of events with status='active' AND date > NOW().

        Issues exactly one SQL statement (NFR-001).
        Read-time consistency for concurrent status changes is guaranteed
        by the database's default transaction isolation level (F6 edge case).
        """
        now = datetime.now(UTC)
        result = await self._session.execute(
            select(func.count())
            .select_from(OrmEvent)
            .where(OrmEvent.status == EventStatus.ACTIVE, OrmEvent.date > now)
        )
        return result.scalar_one()
