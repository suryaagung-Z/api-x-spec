"""Integration tests for EventRepository (T022)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.domain.models import EventStatus
from src.infrastructure.db.models import Base
from src.infrastructure.repositories.event_repository import EventRepository

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


async def _make_event(
    session: AsyncSession,
    *,
    title: str = "Test",
    days: int = 30,
    deadline_days: int = 20,
    quota: int = 100,
):
    repo = EventRepository(session)
    orm = await repo.create(
        title=title,
        description="desc",
        date=_future(days),
        registration_deadline=_future(deadline_days),
        quota=quota,
    )
    await session.commit()
    return orm


# ---------------------------------------------------------------------------
# create / get_by_id_admin
# ---------------------------------------------------------------------------


async def test_create_and_get_by_id_admin():
    async with _SessionLocal() as session:
        orm = await _make_event(session, title="Alpha")
        assert orm.id is not None
        assert orm.title == "Alpha"
        assert orm.status == EventStatus.ACTIVE

        repo = EventRepository(session)
        fetched = await repo.get_by_id_admin(orm.id)
        assert fetched is not None
        assert fetched.title == "Alpha"


async def test_get_by_id_admin_returns_none_for_missing():
    async with _SessionLocal() as session:
        repo = EventRepository(session)
        assert await repo.get_by_id_admin(999_999) is None


# ---------------------------------------------------------------------------
# soft_delete
# ---------------------------------------------------------------------------


async def test_soft_delete_marks_as_deleted():
    async with _SessionLocal() as session:
        orm = await _make_event(session)
        repo = EventRepository(session)
        await repo.soft_delete(orm)
        assert orm.status == EventStatus.DELETED


async def test_get_by_id_admin_still_returns_deleted_event():
    """Admin endpoint may still read deleted events (for audit);
    service layer filters.
    """
    async with _SessionLocal() as session:
        orm = await _make_event(session)
        event_id = orm.id
        repo = EventRepository(session)
        await repo.soft_delete(orm)
        await session.commit()

    async with _SessionLocal() as session:
        repo = EventRepository(session)
        fetched = await repo.get_by_id_admin(event_id)
        assert fetched is not None
        assert fetched.status == EventStatus.DELETED


# ---------------------------------------------------------------------------
# count_public / list_public — filtering
# ---------------------------------------------------------------------------


async def test_count_public_excludes_deleted():
    async with _SessionLocal() as session:
        await _make_event(session, title="Active", days=30)
        deleted = await _make_event(session, title="Deleted", days=31)
        repo = EventRepository(session)
        await repo.soft_delete(deleted)
        await session.commit()
        count = await repo.count_public()
        assert count == 1


async def test_count_public_excludes_past_events():
    """Events whose date < now should not be counted."""
    async with _SessionLocal() as session:
        # We can't insert a past event through normal create since service blocks it,
        # but we can insert directly via ORM
        from src.infrastructure.db.models import Event as OrmEvent

        past_event = OrmEvent(
            title="Past",
            description="gone",
            date=_NOW - timedelta(days=1),
            registration_deadline=_NOW - timedelta(days=2),
            quota=10,
            status=EventStatus.ACTIVE,
        )
        session.add(past_event)
        await session.commit()

        repo = EventRepository(session)
        count = await repo.count_public()
        assert count == 0


async def test_list_public_ordering_date_asc_title_asc():
    """Events must be returned ordered by date ASC, then title ASC."""
    async with _SessionLocal() as session:
        # Insert three events with ascending dates
        await _make_event(session, title="C Event", days=50, deadline_days=40)
        await _make_event(session, title="A Event", days=30, deadline_days=20)
        await _make_event(session, title="B Event", days=40, deadline_days=30)

        repo = EventRepository(session)
        events = await repo.list_public(offset=0, limit=10)
        titles = [e.title for e in events]
        assert titles == ["A Event", "B Event", "C Event"]


async def test_list_public_same_date_title_asc():
    """Events on same date must be sorted alphabetically by title."""
    async with _SessionLocal() as session:
        same_date = _future(30)
        from src.infrastructure.db.models import Event as OrmEvent

        for title in ("Z Event", "A Event", "M Event"):
            session.add(
                OrmEvent(
                    title=title,
                    description="d",
                    date=same_date,
                    registration_deadline=_future(20),
                    quota=10,
                    status=EventStatus.ACTIVE,
                )
            )
        await session.commit()

        repo = EventRepository(session)
        events = await repo.list_public(offset=0, limit=10)
        titles = [e.title for e in events]
        assert titles == ["A Event", "M Event", "Z Event"]


async def test_list_public_pagination_offset():
    """Offset/limit pagination must work consistently with ordering."""
    async with _SessionLocal() as session:
        for i in range(1, 6):
            await _make_event(
                session, title=f"Event {i:02d}", days=i + 10, deadline_days=i + 5
            )

        repo = EventRepository(session)
        page1 = await repo.list_public(offset=0, limit=2)
        page2 = await repo.list_public(offset=2, limit=2)
        page3 = await repo.list_public(offset=4, limit=2)

        assert len(page1) == 2
        assert len(page2) == 2
        assert len(page3) == 1

        all_ids = [e.id for e in page1] + [e.id for e in page2] + [e.id for e in page3]
        assert len(all_ids) == len(set(all_ids)), "Duplicate events across pages!"


async def test_count_public_matches_list_public():
    async with _SessionLocal() as session:
        for i in range(3):
            await _make_event(
                session, title=f"Event {i}", days=i + 10, deadline_days=i + 5
            )

        repo = EventRepository(session)
        count = await repo.count_public()
        events = await repo.list_public(offset=0, limit=100)
        assert count == len(events)


async def test_get_public_by_id_returns_none_for_deleted():
    async with _SessionLocal() as session:
        orm = await _make_event(session, title="Will Be Deleted")
        event_id = orm.id
        repo = EventRepository(session)
        await repo.soft_delete(orm)
        await session.commit()
        result = await repo.get_public_by_id(event_id)
        assert result is None


async def test_get_public_by_id_returns_none_for_missing():
    async with _SessionLocal() as session:
        repo = EventRepository(session)
        assert await repo.get_public_by_id(999_999) is None


async def test_get_public_by_id_returns_event():
    async with _SessionLocal() as session:
        orm = await _make_event(session, title="Fetchable")
        repo = EventRepository(session)
        result = await repo.get_public_by_id(orm.id)
        assert result is not None
        assert result.title == "Fetchable"
