"""Integration tests for RegistrationRepository (T010, T017, T021)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.domain.models import EventStatus, RegistrationStatus
from src.infrastructure.db.models import Base
from src.infrastructure.db.models import Event as OrmEvent
from src.infrastructure.db.models import EventRegistration as OrmRegistration
from src.infrastructure.repositories.registration_repository import (
    RegistrationRepository,
)

pytestmark = pytest.mark.asyncio

TEST_URL = "sqlite+aiosqlite:///:memory:"

_engine = create_async_engine(
    TEST_URL,
    connect_args={"check_same_thread": False},
)
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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _make_event(
    session: AsyncSession,
    *,
    title: str = "Test Event",
    quota: int = 100,
    days_ahead: int = 30,
    deadline_days: int = 20,
) -> OrmEvent:
    """Insert an Event row and flush — returns the ORM instance."""
    orm = OrmEvent(
        title=title,
        description="test",
        date=_future(days_ahead),
        registration_deadline=_future(deadline_days),
        quota=quota,
        status=EventStatus.ACTIVE,
        current_participants=0,
    )
    session.add(orm)
    await session.flush()
    await session.refresh(orm)
    return orm


# ---------------------------------------------------------------------------
# T010: create_registration / atomic_increment_participants
# ---------------------------------------------------------------------------


async def test_create_registration_persists_as_active():
    """create_registration inserts a row with status=ACTIVE."""
    async with _SessionLocal() as session:
        event = await _make_event(session)
        repo = RegistrationRepository(session)
        reg = await repo.create_registration("user-001", event.id)
        await session.commit()

        assert reg.id is not None
        assert reg.event_id == event.id
        assert reg.user_id == "user-001"
        assert reg.status == RegistrationStatus.ACTIVE
        assert reg.registered_at is not None


async def test_atomic_increment_updates_counter():
    """atomic_increment_participants updates current_participants 0 → 1."""
    async with _SessionLocal() as session:
        event = await _make_event(session, quota=10)
        await session.commit()

        repo = RegistrationRepository(session)
        result = await repo.atomic_increment_participants(event.id)
        await session.commit()

        assert result == event.id

        # Reload
        await session.refresh(event)
        assert event.current_participants == 1


async def test_atomic_increment_returns_none_when_full():
    """atomic_increment_participants returns None when quota is reached."""
    async with _SessionLocal() as session:
        event = await _make_event(session, quota=1)
        repo = RegistrationRepository(session)
        # Fill quota
        r1 = await repo.atomic_increment_participants(event.id)
        assert r1 is not None
        # Now full
        r2 = await repo.atomic_increment_participants(event.id)
        assert r2 is None


async def test_partial_unique_index_blocks_duplicate_active():
    """Partial unique index prevents two ACTIVE rows for the same (user, event)."""
    async with _SessionLocal() as session:
        event = await _make_event(session)
        repo = RegistrationRepository(session)
        await repo.create_registration("user-dup", event.id)
        await session.flush()

        # Second active insert should violate the partial unique index
        with pytest.raises((IntegrityError, Exception)):
            await repo.create_registration("user-dup", event.id)
            await session.flush()


async def test_get_active_registration_returns_none_when_absent():
    async with _SessionLocal() as session:
        event = await _make_event(session)
        repo = RegistrationRepository(session)
        result = await repo.get_active_registration("no-such-user", event.id)
        assert result is None


async def test_get_active_registration_returns_registration():
    async with _SessionLocal() as session:
        event = await _make_event(session)
        repo = RegistrationRepository(session)
        await repo.create_registration("user-abc", event.id)
        await session.flush()

        reg = await repo.get_active_registration("user-abc", event.id)
        assert reg is not None
        assert reg.user_id == "user-abc"


# ---------------------------------------------------------------------------
# T017: Quota enforcement under concurrent-like conditions
# ---------------------------------------------------------------------------


async def test_quota_enforcement_sequential_fills_then_rejects():
    """SC-004 (sequential simulation): quota=1 event fills on first attempt,
    rejects second.

    True SQL concurrency requires a multi-connection DB (e.g. PostgreSQL).
    With aiosqlite in-memory (single-connection), we verify the atomic UPDATE guard
    works correctly in sequential fill → reject behaviour.
    """
    async with _SessionLocal() as session:
        event = await _make_event(session, quota=1)
        await session.commit()
        event_id = event.id

    results: list[bool] = []
    for i in range(5):
        async with _SessionLocal() as session:
            repo = RegistrationRepository(session)
            result = await repo.atomic_increment_participants(event_id)
            if result is None:
                results.append(False)
            else:
                # Insert row without refresh
                from src.infrastructure.db.models import EventRegistration as OrmReg

                orm = OrmReg(
                    user_id=f"quota-user-{i}",
                    event_id=event_id,
                    status=RegistrationStatus.ACTIVE,
                    registered_at=datetime.now(tz=UTC),
                )
                session.add(orm)
                await session.flush()
                await session.commit()
                results.append(True)

    successes = sum(1 for r in results if r)
    assert successes == 1, f"Expected exactly 1 success, got {successes}"

    async with _SessionLocal() as verify_session:
        from sqlalchemy import select

        row = await verify_session.execute(
            select(OrmEvent).where(OrmEvent.id == event_id)
        )
        ev = row.scalar_one()
        assert ev.current_participants == 1


# ---------------------------------------------------------------------------
# T021: cancel_registration / atomic_decrement_participants / re-registration
# ---------------------------------------------------------------------------


async def test_cancel_sets_cancelled_at():
    """cancel_registration sets status=CANCELLED and populates cancelled_at."""
    async with _SessionLocal() as session:
        event = await _make_event(session)
        repo = RegistrationRepository(session)
        await repo.create_registration("user-cancel", event.id)
        await session.flush()

        await repo.cancel_registration("user-cancel", event.id)
        await session.flush()

        result = await session.execute(
            __import__("sqlalchemy", fromlist=["select"])
            .select(OrmRegistration)
            .where(OrmRegistration.user_id == "user-cancel")
            .where(OrmRegistration.event_id == event.id)
        )
        reg = result.scalar_one()
        assert reg.status == RegistrationStatus.CANCELLED
        assert reg.cancelled_at is not None


async def test_cancel_decrements_participants():
    """atomic_decrement_participants brings current_participants back to 0."""
    async with _SessionLocal() as session:
        event = await _make_event(session, quota=5)
        repo = RegistrationRepository(session)
        await repo.atomic_increment_participants(event.id)
        await session.flush()

        await session.refresh(event)
        assert event.current_participants == 1

        await repo.atomic_decrement_participants(event.id)
        await session.flush()

        await session.refresh(event)
        assert event.current_participants == 0


async def test_cancel_does_not_decrement_below_zero():
    """atomic_decrement_participants does nothing if counter is already 0."""
    async with _SessionLocal() as session:
        event = await _make_event(session, quota=5)
        repo = RegistrationRepository(session)

        # Decrement when already at 0
        await repo.atomic_decrement_participants(event.id)
        await session.flush()

        await session.refresh(event)
        assert event.current_participants == 0


async def test_reregistration_after_cancel_creates_new_row():
    """Re-registration after cancel: two rows in DB — 1 cancelled, 1 active."""
    async with _SessionLocal() as session:
        event = await _make_event(session, quota=5)
        await session.commit()

    # Register
    async with _SessionLocal() as session:
        repo = RegistrationRepository(session)
        await repo.atomic_increment_participants(event.id)
        await repo.create_registration("user-rereg", event.id)
        await session.commit()

    # Cancel
    async with _SessionLocal() as session:
        repo = RegistrationRepository(session)
        await repo.cancel_registration("user-rereg", event.id)
        await repo.atomic_decrement_participants(event.id)
        await session.commit()

    # Re-register
    async with _SessionLocal() as session:
        repo = RegistrationRepository(session)
        await repo.atomic_increment_participants(event.id)
        await repo.create_registration("user-rereg", event.id)
        await session.commit()

    # Verify two rows: 1 cancelled + 1 active
    from sqlalchemy import select as sa_select

    async with _SessionLocal() as session:
        result = await session.execute(
            sa_select(OrmRegistration)
            .where(OrmRegistration.user_id == "user-rereg")
            .where(OrmRegistration.event_id == event.id)
        )
        rows = list(result.scalars().all())
        assert len(rows) == 2
        statuses = {r.status for r in rows}
        assert statuses == {RegistrationStatus.ACTIVE, RegistrationStatus.CANCELLED}


async def test_get_my_registrations_returns_all_statuses():
    """get_my_registrations returns both active and cancelled rows."""
    async with _SessionLocal() as session:
        event1 = await _make_event(session, title="Ev1")
        event2 = await _make_event(session, title="Ev2")
        repo = RegistrationRepository(session)

        # Register for event1 (stays active)
        await repo.atomic_increment_participants(event1.id)
        await repo.create_registration("user-list", event1.id)

        # Register + cancel event2
        await repo.atomic_increment_participants(event2.id)
        await repo.create_registration("user-list", event2.id)
        await repo.cancel_registration("user-list", event2.id)

        await session.commit()

    async with _SessionLocal() as session:
        repo = RegistrationRepository(session)
        regs = await repo.get_my_registrations("user-list")
        assert len(regs) == 2
        statuses = {r.status for r in regs}
        assert statuses == {RegistrationStatus.ACTIVE, RegistrationStatus.CANCELLED}


async def test_get_my_registrations_empty_for_unknown_user():
    async with _SessionLocal() as session:
        repo = RegistrationRepository(session)
        regs = await repo.get_my_registrations("ghost-user")
        assert regs == []
