"""Contract tests for admin reporting endpoints (T004, T007, T011, T007b).

Tests cover:
- T004: GET /admin/reports/events/stats — correct EventStatsPage shape and
  values matching seeded data (total_registered, remaining_quota).
- T007: Admin-only access for stats endpoint (401, 403, 200).
- T011: GET /admin/reports/events/summary — correct ReportSummaryResponse shape;
  returns 0 when no active events.
- T007b: Admin-only access for summary endpoint (401, 403, 200).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from httpx import AsyncClient

from src.domain.models import EventStatus, RegistrationStatus
from src.infrastructure.db.models import Event as OrmEvent
from src.infrastructure.db.models import EventRegistration as OrmRegistration
from src.infrastructure.db.models import User as OrmUser
from tests.conftest import _get_token, _TestSessionLocal, create_user

pytestmark = pytest.mark.asyncio

_NOW = datetime.now(tz=UTC)


# ---------------------------------------------------------------------------
# Auth fixture
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture()
async def auth_headers(test_client: AsyncClient) -> tuple[dict, dict]:
    """Return (admin_headers, user_headers) both created on the same test_client."""
    await create_user(
        test_client,
        name="Report Admin",
        email="radmin@test.com",
        password="adminP@ss123",
        role="admin",
    )
    await create_user(
        test_client,
        name="Report User",
        email="ruser@test.com",
        password="userP@ss123",
        role="user",
    )
    admin_token = await _get_token(test_client, "radmin@test.com", "adminP@ss123")
    user_token = await _get_token(test_client, "ruser@test.com", "userP@ss123")
    return (
        {"Authorization": f"Bearer {admin_token}"},
        {"Authorization": f"Bearer {user_token}"},
    )


# ---------------------------------------------------------------------------
# Seed helpers (direct DB, uses same in-memory engine as test_client)
# ---------------------------------------------------------------------------


async def _seed_event(
    *,
    title: str = "Report Test Event",
    quota: int = 100,
    days_ahead: int = 30,
    status: EventStatus = EventStatus.ACTIVE,
) -> OrmEvent:
    """Insert an event directly and return the flushed ORM instance."""
    async with _TestSessionLocal() as session:
        orm = OrmEvent(
            title=title,
            description="for reporting tests",
            date=_NOW + timedelta(days=days_ahead),
            registration_deadline=_NOW + timedelta(days=max(days_ahead - 3, 1)),
            quota=quota,
            status=status,
            current_participants=0,
        )
        session.add(orm)
        await session.flush()
        await session.refresh(orm)
        await session.commit()
        return orm


async def _seed_user(user_id: str, email: str) -> None:
    """Insert a minimal User row for FK-compliant registrations."""
    from src.infrastructure.auth.password import hash_password

    async with _TestSessionLocal() as session:
        user = OrmUser(
            id=user_id,
            name=f"User {user_id}",
            email=email,
            hashed_password=hash_password("P@ssw0rd!"),
            role="user",
        )
        session.add(user)
        try:
            await session.commit()
        except Exception:
            await session.rollback()


async def _seed_registration(
    event_id: int,
    user_id: str,
    status: RegistrationStatus = RegistrationStatus.ACTIVE,
) -> None:
    """Insert an EventRegistration row for the given event+user."""
    async with _TestSessionLocal() as session:
        reg = OrmRegistration(
            event_id=event_id,
            user_id=user_id,
            status=status,
            registered_at=_NOW,
        )
        session.add(reg)
        await session.commit()


# ---------------------------------------------------------------------------
# T004: GET /admin/reports/events/stats — shape and correctness
# ---------------------------------------------------------------------------


async def test_stats_200_response_shape(
    test_client: AsyncClient,
    auth_headers: tuple[dict, dict],
):
    """Response body contains all required EventStatsPage fields."""
    admin_h, _ = auth_headers
    r = await test_client.get("/admin/reports/events/stats", headers=admin_h)
    assert r.status_code == 200
    body = r.json()
    assert "items" in body
    assert "total" in body
    assert "page" in body
    assert "size" in body
    assert "pages" in body
    assert isinstance(body["items"], list)
    assert isinstance(body["total"], int)
    assert isinstance(body["page"], int)
    assert isinstance(body["size"], int)
    assert isinstance(body["pages"], int)


async def test_stats_items_have_correct_fields(
    test_client: AsyncClient,
    auth_headers: tuple[dict, dict],
):
    """Each item in the response has all EventStatItem fields."""
    admin_h, _ = auth_headers
    await _seed_event(title="Shape Check Event", quota=50)

    r = await test_client.get("/admin/reports/events/stats", headers=admin_h)
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) >= 1
    item = items[0]
    for field in (
        "id",
        "title",
        "date",
        "quota",
        "total_registered",
        "remaining_quota",
    ):
        assert field in item, f"Missing field: {field}"


async def test_stats_total_registered_matches_active_registrations(
    test_client: AsyncClient,
    auth_headers: tuple[dict, dict],
):
    """total_registered equals count of active registrations for the event."""
    admin_h, _ = auth_headers
    event = await _seed_event(title="Reg Count Event", quota=20)
    # Seed users and registrations via the DB (FK-compliant)
    await _seed_user("stat-user-1", "suser1@test.com")
    await _seed_user("stat-user-2", "suser2@test.com")
    await _seed_user("stat-user-3", "suser3@test.com")
    await _seed_registration(event.id, "stat-user-1")
    await _seed_registration(event.id, "stat-user-2")
    await _seed_registration(event.id, "stat-user-3")

    r = await test_client.get(
        "/admin/reports/events/stats?page=1&size=100", headers=admin_h
    )
    assert r.status_code == 200
    match = next(i for i in r.json()["items"] if i["id"] == event.id)
    assert match["total_registered"] == 3
    assert match["remaining_quota"] == 17  # 20 - 3


async def test_stats_cancelled_registrations_excluded_from_count(
    test_client: AsyncClient,
    auth_headers: tuple[dict, dict],
):
    """Cancelled registrations do NOT appear in total_registered."""
    admin_h, _ = auth_headers
    event = await _seed_event(title="Cancelled Reg Event", quota=10)
    await _seed_user("cstat-u1", "csu1@test.com")
    await _seed_user("cstat-u2", "csu2@test.com")
    await _seed_registration(event.id, "cstat-u1")
    await _seed_registration(event.id, "cstat-u2", RegistrationStatus.CANCELLED)

    r = await test_client.get(
        "/admin/reports/events/stats?page=1&size=100", headers=admin_h
    )
    assert r.status_code == 200
    match = next(i for i in r.json()["items"] if i["id"] == event.id)
    assert match["total_registered"] == 1
    assert match["remaining_quota"] == 9  # 10 - 1


async def test_stats_pagination_defaults(
    test_client: AsyncClient,
    auth_headers: tuple[dict, dict],
):
    """Default pagination: page=1, size=20."""
    admin_h, _ = auth_headers
    r = await test_client.get("/admin/reports/events/stats", headers=admin_h)
    assert r.status_code == 200
    body = r.json()
    assert body["page"] == 1
    assert body["size"] == 20


# ---------------------------------------------------------------------------
# T007: Admin-only access — stats endpoint
# ---------------------------------------------------------------------------


async def test_stats_401_unauthenticated(test_client: AsyncClient):
    """Missing token → 401 (FastAPI OAuth2 built-in, no custom error envelope)."""
    r = await test_client.get("/admin/reports/events/stats")
    assert r.status_code == 401


async def test_stats_403_user_role(
    test_client: AsyncClient,
    auth_headers: tuple[dict, dict],
):
    """role=user token → 403 FORBIDDEN."""
    _, user_h = auth_headers
    r = await test_client.get("/admin/reports/events/stats", headers=user_h)
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "FORBIDDEN"


async def test_stats_200_admin_role(
    test_client: AsyncClient,
    auth_headers: tuple[dict, dict],
):
    """role=admin token → 200 OK."""
    admin_h, _ = auth_headers
    r = await test_client.get("/admin/reports/events/stats", headers=admin_h)
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# T011: GET /admin/reports/events/summary — shape and correctness
# ---------------------------------------------------------------------------


async def test_summary_200_response_shape(
    test_client: AsyncClient,
    auth_headers: tuple[dict, dict],
):
    """Response body contains total_active_events integer."""
    admin_h, _ = auth_headers
    r = await test_client.get("/admin/reports/events/summary", headers=admin_h)
    assert r.status_code == 200
    body = r.json()
    assert "total_active_events" in body
    assert isinstance(body["total_active_events"], int)


async def test_summary_reflects_active_events(
    test_client: AsyncClient,
    auth_headers: tuple[dict, dict],
):
    """total_active_events count increases when active future events are seeded."""
    admin_h, _ = auth_headers
    # Baseline
    r0 = await test_client.get("/admin/reports/events/summary", headers=admin_h)
    baseline = r0.json()["total_active_events"]

    await _seed_event(title="Summary Event A")
    await _seed_event(title="Summary Event B")

    r = await test_client.get("/admin/reports/events/summary", headers=admin_h)
    assert r.status_code == 200
    assert r.json()["total_active_events"] == baseline + 2


async def test_summary_zero_when_no_active_events(
    test_client: AsyncClient,
    auth_headers: tuple[dict, dict],
):
    """Returns total_active_events=0 (not an error) when no active events exist.

    This test relies on the isolated in-memory DB having no events at start.
    """
    admin_h, _ = auth_headers
    # No events seeded — fresh in-memory DB per test_client fixture
    r = await test_client.get("/admin/reports/events/summary", headers=admin_h)
    assert r.status_code == 200
    assert r.json()["total_active_events"] == 0


# ---------------------------------------------------------------------------
# T007b: Admin-only access — summary endpoint
# ---------------------------------------------------------------------------


async def test_summary_401_unauthenticated(test_client: AsyncClient):
    """Missing token → 401 (FastAPI OAuth2 built-in, no custom error envelope)."""
    r = await test_client.get("/admin/reports/events/summary")
    assert r.status_code == 401


async def test_summary_403_user_role(
    test_client: AsyncClient,
    auth_headers: tuple[dict, dict],
):
    """role=user token → 403 FORBIDDEN."""
    _, user_h = auth_headers
    r = await test_client.get("/admin/reports/events/summary", headers=user_h)
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "FORBIDDEN"


async def test_summary_200_admin_role(
    test_client: AsyncClient,
    auth_headers: tuple[dict, dict],
):
    """role=admin token → 200 OK."""
    admin_h, _ = auth_headers
    r = await test_client.get("/admin/reports/events/summary", headers=admin_h)
    assert r.status_code == 200
