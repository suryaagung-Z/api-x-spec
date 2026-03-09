"""Integration tests for ReportingRepository (T005, T012).

Tests cover:
- get_event_stats_page: active/cancelled registration counts, zero-registration
  events, negative remaining_quota, exclusion of past/inactive events.
- get_total_active_events: correct filtering, zero result.
- NFR-001: SQL statement count assertions via before_cursor_execute event hook.

Note on FK enforcement: aiosqlite (SQLite) does not enable foreign key
constraints by default, so User rows are not required for test registrations.

Note on concurrent status changes (F6 edge case): read-time consistency is
guaranteed by the database's default transaction isolation level. Each call
sees a snapshot of committed data at the time of statement execution.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from sqlalchemy import event as sa_event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.domain.models import EventStatus, RegistrationStatus
from src.infrastructure.db.models import Base
from src.infrastructure.db.models import Event as OrmEvent
from src.infrastructure.db.models import EventRegistration as OrmRegistration
from src.infrastructure.repositories.reporting_repository import ReportingRepository

pytestmark = pytest.mark.asyncio

TEST_URL = "sqlite+aiosqlite:///:memory:"

_engine = create_async_engine(TEST_URL, connect_args={"check_same_thread": False})
_SessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    _engine, expire_on_commit=False
)

_NOW = datetime.now(tz=UTC)


@pytest_asyncio.fixture(autouse=True)
async def _setup_db():
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


def _future(days: int = 30) -> datetime:
    return _NOW + timedelta(days=days)


def _past(days: int = 1) -> datetime:
    return _NOW - timedelta(days=days)


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------


async def _make_event(
    session: AsyncSession,
    *,
    title: str = "Test Event",
    quota: int = 100,
    days_ahead: int = 30,
    status: EventStatus = EventStatus.ACTIVE,
) -> OrmEvent:
    """Insert an Event row, flush, and return the ORM instance."""
    orm = OrmEvent(
        title=title,
        description="test",
        date=_future(days_ahead),
        registration_deadline=_future(max(days_ahead - 3, 1)),
        quota=quota,
        status=status,
        current_participants=0,
    )
    session.add(orm)
    await session.flush()
    await session.refresh(orm)
    return orm


async def _make_past_event(
    session: AsyncSession,
    *,
    title: str = "Past Event",
) -> OrmEvent:
    """Insert a past active event (date in the past)."""
    # registration_deadline must be <= date; both in the past
    past_date = _past(2)
    past_deadline = _past(7)
    orm = OrmEvent(
        title=title,
        description="past",
        date=past_date,
        registration_deadline=past_deadline,
        quota=50,
        status=EventStatus.ACTIVE,
        current_participants=0,
    )
    session.add(orm)
    await session.flush()
    await session.refresh(orm)
    return orm


async def _make_registration(
    session: AsyncSession,
    event_id: int,
    user_id: str,
    status: RegistrationStatus = RegistrationStatus.ACTIVE,
) -> OrmRegistration:
    """Insert an EventRegistration row and flush."""
    orm = OrmRegistration(
        event_id=event_id,
        user_id=user_id,
        status=status,
        registered_at=_NOW,
    )
    session.add(orm)
    await session.flush()
    return orm


# ---------------------------------------------------------------------------
# SQL statement counter helper
# ---------------------------------------------------------------------------


class _SQLCounter:
    """Counts before_cursor_execute events on a sync engine."""

    def __init__(self) -> None:
        self.count = 0

    def __call__(self, conn, cursor, statement, parameters, context, executemany):
        self.count += 1


# ---------------------------------------------------------------------------
# T005: get_event_stats_page
# ---------------------------------------------------------------------------


async def test_stats_active_registrations_counted():
    """Events with active registrations report correct total_registered."""
    async with _SessionLocal() as session:
        event = await _make_event(session, quota=10)
        await _make_registration(session, event.id, "user-001")
        await _make_registration(session, event.id, "user-002")
        await session.commit()

    async with _SessionLocal() as session:
        repo = ReportingRepository(session)
        rows, total = await repo.get_event_stats_page(offset=0, limit=20)

    assert total == 1
    assert len(rows) == 1
    row = rows[0]
    assert row.id == event.id
    assert row.total_registered == 2
    assert row.remaining_quota == 8  # 10 - 2


async def test_stats_cancelled_registrations_not_counted():
    """Cancelled registrations do NOT contribute to total_registered."""
    async with _SessionLocal() as session:
        event = await _make_event(session, quota=10)
        # 2 active, 1 cancelled (different users to avoid unique-index conflict)
        await _make_registration(session, event.id, "user-001")
        await _make_registration(session, event.id, "user-002")
        await _make_registration(
            session, event.id, "user-003", RegistrationStatus.CANCELLED
        )
        await session.commit()

    async with _SessionLocal() as session:
        repo = ReportingRepository(session)
        rows, _ = await repo.get_event_stats_page(offset=0, limit=20)

    assert rows[0].total_registered == 2
    assert rows[0].remaining_quota == 8


async def test_stats_zero_registrations():
    """Event with no registrations: total_registered=0, remaining_quota=quota."""
    async with _SessionLocal() as session:
        event = await _make_event(session, quota=50)
        await session.commit()

    async with _SessionLocal() as session:
        repo = ReportingRepository(session)
        rows, total = await repo.get_event_stats_page(offset=0, limit=20)

    assert total == 1
    assert rows[0].total_registered == 0
    assert rows[0].remaining_quota == 50


async def test_stats_negative_remaining_quota():
    """Event with more registrations than quota returns negative remaining_quota."""
    async with _SessionLocal() as session:
        event = await _make_event(session, quota=2)
        # Insert 4 registrations for different users (exceeds quota=2)
        await _make_registration(session, event.id, "user-001")
        await _make_registration(session, event.id, "user-002")
        await _make_registration(session, event.id, "user-003")
        await _make_registration(session, event.id, "user-004")
        await session.commit()

    async with _SessionLocal() as session:
        repo = ReportingRepository(session)
        rows, _ = await repo.get_event_stats_page(offset=0, limit=20)

    assert rows[0].total_registered == 4
    assert rows[0].remaining_quota == -2  # quota=2, registered=4 → 2-4=-2


async def test_stats_past_active_events_excluded():
    """Events with status='active' but date <= NOW() are excluded."""
    async with _SessionLocal() as session:
        await _make_past_event(session)
        await session.commit()

    async with _SessionLocal() as session:
        repo = ReportingRepository(session)
        rows, total = await repo.get_event_stats_page(offset=0, limit=20)

    assert total == 0
    assert rows == []


async def test_stats_inactive_events_excluded():
    """Events with status='deleted' (inactive) are excluded regardless of date."""
    async with _SessionLocal() as session:
        await _make_event(session, status=EventStatus.DELETED)
        await session.commit()

    async with _SessionLocal() as session:
        repo = ReportingRepository(session)
        rows, total = await repo.get_event_stats_page(offset=0, limit=20)

    assert total == 0
    assert rows == []


async def test_stats_pagination_total_reflects_all_not_just_page():
    """total count returned equals ALL active events, not just the page."""
    async with _SessionLocal() as session:
        for i in range(5):
            await _make_event(session, title=f"Event {i}", days_ahead=30 + i)
        await session.commit()

    async with _SessionLocal() as session:
        repo = ReportingRepository(session)
        rows, total = await repo.get_event_stats_page(offset=0, limit=2)

    assert total == 5
    assert len(rows) == 2  # only 2 returned per LIMIT


async def test_stats_ordered_by_date_then_id():
    """Results are ordered by date ASC, then id ASC for same-date events."""
    async with _SessionLocal() as session:
        e1 = await _make_event(session, title="Later", days_ahead=60)
        e2 = await _make_event(session, title="Sooner", days_ahead=30)
        await session.commit()

    async with _SessionLocal() as session:
        repo = ReportingRepository(session)
        rows, _ = await repo.get_event_stats_page(offset=0, limit=20)

    assert rows[0].id == e2.id  # sooner date first
    assert rows[1].id == e1.id


async def test_stats_nfr001_sql_statement_count():
    """NFR-001: get_event_stats_page issues exactly 2 SQL statements per call
    (one aggregate stats query + one pagination count query).
    This is O(1) statements regardless of N events — no N+1 pattern.
    """
    async with _SessionLocal() as session:
        await _make_event(session)
        await session.commit()

    counter = _SQLCounter()
    sa_event.listen(_engine.sync_engine, "before_cursor_execute", counter)
    try:
        async with _SessionLocal() as session:
            repo = ReportingRepository(session)
            counter.count = 0  # reset after setup
            await repo.get_event_stats_page(offset=0, limit=20)
    finally:
        sa_event.remove(_engine.sync_engine, "before_cursor_execute", counter)

    assert (
        counter.count == 2
    ), f"Expected 2 SQL statements (stats + count), got {counter.count}"


# ---------------------------------------------------------------------------
# T012: get_total_active_events
# ---------------------------------------------------------------------------


async def test_total_active_counts_only_active_future():
    """Only events with status='active' AND date > NOW() are counted."""
    async with _SessionLocal() as session:
        await _make_event(session, title="Active Future 1")
        await _make_event(session, title="Active Future 2")
        await _make_event(session, status=EventStatus.DELETED)  # excluded
        await _make_past_event(session)  # active but past — excluded
        await session.commit()

    async with _SessionLocal() as session:
        repo = ReportingRepository(session)
        count = await repo.get_total_active_events()

    assert count == 2


async def test_total_active_excludes_past_active_events():
    """Past events with status='active' are NOT counted."""
    async with _SessionLocal() as session:
        await _make_past_event(session)
        await session.commit()

    async with _SessionLocal() as session:
        repo = ReportingRepository(session)
        count = await repo.get_total_active_events()

    assert count == 0


async def test_total_active_excludes_inactive_events():
    """Events with status='deleted' are excluded."""
    async with _SessionLocal() as session:
        await _make_event(session, status=EventStatus.DELETED)
        await session.commit()

    async with _SessionLocal() as session:
        repo = ReportingRepository(session)
        count = await repo.get_total_active_events()

    assert count == 0


async def test_total_active_returns_zero_when_none():
    """Returns 0 when no active future events exist."""
    async with _SessionLocal() as session:
        repo = ReportingRepository(session)
        count = await repo.get_total_active_events()

    assert count == 0


async def test_total_active_nfr001_sql_statement_count():
    """NFR-001: get_total_active_events issues exactly 1 SQL statement per call.
    Read-time consistency for concurrent status changes is guaranteed by the
    database's default transaction isolation level (F6 edge case).
    """
    async with _SessionLocal() as session:
        await _make_event(session)
        await session.commit()

    counter = _SQLCounter()
    sa_event.listen(_engine.sync_engine, "before_cursor_execute", counter)
    try:
        async with _SessionLocal() as session:
            repo = ReportingRepository(session)
            counter.count = 0
            await repo.get_total_active_events()
    finally:
        sa_event.remove(_engine.sync_engine, "before_cursor_execute", counter)

    assert counter.count == 1, f"Expected exactly 1 SQL statement, got {counter.count}"
