"""Contract tests for event registration endpoints (T008, T015, T018, T019)."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from httpx import AsyncClient

from tests.conftest import _get_token, create_user

pytestmark = pytest.mark.asyncio

_NOW = datetime.now(tz=UTC)
_FUTURE_DATE = (_NOW + timedelta(days=30)).isoformat()
_FUTURE_DEADLINE = (_NOW + timedelta(days=20)).isoformat()
_PAST_DEADLINE = (_NOW - timedelta(hours=1)).isoformat()


# ---------------------------------------------------------------------------
# This module-level fixture provides BOTH admin and user headers from a SINGLE
# test_client instance, preventing pytest-asyncio from creating separate
# fixture runner scopes for each auth header fixture.
# Tests destructure the returned tuple: (admin_headers, user_headers)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture()
async def auth_headers(test_client: AsyncClient) -> tuple[dict, dict]:
    """Return (admin_auth_headers, user_auth_headers) both from same test_client."""
    await create_user(
        test_client,
        name="Test Admin",
        email="admin@test.com",
        password="adminP@ss123",
        role="admin",
    )
    await create_user(
        test_client,
        name="Test User",
        email="user@test.com",
        password="userP@ss123",
        role="user",
    )
    admin_token = await _get_token(test_client, "admin@test.com", "adminP@ss123")
    user_token = await _get_token(test_client, "user@test.com", "userP@ss123")
    return (
        {"Authorization": f"Bearer {admin_token}"},
        {"Authorization": f"Bearer {user_token}"},
    )


_VALID_EVENT = {
    "title": "Registration Test Event",
    "description": "For registration tests",
    "date": _FUTURE_DATE,
    "registration_deadline": _FUTURE_DEADLINE,
    "quota": 50,
}

_PAST_DEADLINE_EVENT = {
    "title": "Late Signup Event",
    "description": "Deadline already passed",
    "date": _FUTURE_DATE,
    "registration_deadline": _PAST_DEADLINE,
    "quota": 100,
}


async def _create_event(client: AsyncClient, headers: dict, **overrides) -> dict:
    body = {**_VALID_EVENT, **overrides}
    r = await client.post("/admin/events", json=body, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


# ---------------------------------------------------------------------------
# T008: POST /registrations/{event_id} — US1 happy path
# ---------------------------------------------------------------------------


async def test_register_201_valid(
    test_client: AsyncClient,
    auth_headers: tuple[dict, dict],
):
    admin_h, user_h = auth_headers
    event = await _create_event(test_client, admin_h)
    r = await test_client.post(f"/registrations/{event['id']}", headers=user_h)
    assert r.status_code == 201
    body = r.json()
    assert body["event_id"] == event["id"]
    assert body["status"] == "active"
    assert "id" in body
    assert "registered_at" in body


async def test_register_response_shape(
    test_client: AsyncClient,
    auth_headers: tuple[dict, dict],
):
    admin_h, user_h = auth_headers
    event = await _create_event(test_client, admin_h)
    r = await test_client.post(f"/registrations/{event['id']}", headers=user_h)
    body = r.json()
    assert set(body.keys()) >= {"id", "event_id", "status", "registered_at"}


async def test_register_401_no_token(
    test_client: AsyncClient,
    auth_headers: tuple[dict, dict],
):
    admin_h, _ = auth_headers
    event = await _create_event(test_client, admin_h)
    r = await test_client.post(f"/registrations/{event['id']}")
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# T015: POST /registrations/{event_id} — US2 rejection paths
# ---------------------------------------------------------------------------


async def test_register_404_nonexistent_event(
    test_client: AsyncClient,
    auth_headers: tuple[dict, dict],
):
    _, user_h = auth_headers
    r = await test_client.post("/registrations/999999", headers=user_h)
    assert r.status_code == 404
    body = r.json()
    assert "error" in body
    assert body["error"]["code"] == "EVENT_NOT_FOUND"
    assert body["error"]["httpStatus"] == 404


async def test_register_422_deadline_passed(
    test_client: AsyncClient,
    auth_headers: tuple[dict, dict],
):
    admin_h, user_h = auth_headers
    event = await _create_event(test_client, admin_h, **_PAST_DEADLINE_EVENT)
    r = await test_client.post(f"/registrations/{event['id']}", headers=user_h)
    assert r.status_code == 422
    body = r.json()
    assert body["error"]["code"] == "REGISTRATION_DEADLINE_PASSED"


async def test_register_422_quota_full(
    test_client: AsyncClient,
    auth_headers: tuple[dict, dict],
):
    """Quota=1 event: second user gets 422 QUOTA_FULL."""
    admin_h, user_h = auth_headers
    event = await _create_event(test_client, admin_h, title="Quota Full Test", quota=1)

    # Register first user (fills quota)
    r1 = await test_client.post(f"/registrations/{event['id']}", headers=user_h)
    assert r1.status_code == 201

    # Register second user
    await create_user(
        test_client,
        name="Second User",
        email="second@test.com",
        password="second@ss123",
    )
    token2 = await _get_token(test_client, "second@test.com", "second@ss123")
    r2 = await test_client.post(
        f"/registrations/{event['id']}", headers={"Authorization": f"Bearer {token2}"}
    )
    assert r2.status_code == 422
    assert r2.json()["error"]["code"] == "QUOTA_FULL"


async def test_register_409_duplicate(
    test_client: AsyncClient,
    auth_headers: tuple[dict, dict],
):
    admin_h, user_h = auth_headers
    event = await _create_event(test_client, admin_h)
    await test_client.post(f"/registrations/{event['id']}", headers=user_h)
    r = await test_client.post(f"/registrations/{event['id']}", headers=user_h)
    assert r.status_code == 409
    body = r.json()
    assert body["error"]["code"] == "DUPLICATE_REGISTRATION"
    assert body["error"]["httpStatus"] == 409


async def test_register_error_envelope_shape(
    test_client: AsyncClient,
    auth_headers: tuple[dict, dict],
):
    """All error responses must have {error: {code, message, httpStatus}}."""
    _, user_h = auth_headers
    r = await test_client.post("/registrations/999999", headers=user_h)
    body = r.json()
    assert "error" in body
    err = body["error"]
    assert "code" in err
    assert "message" in err
    assert "httpStatus" in err


# ---------------------------------------------------------------------------
# T018: DELETE /registrations/{event_id} — cancel
# ---------------------------------------------------------------------------


async def test_cancel_204_valid(
    test_client: AsyncClient,
    auth_headers: tuple[dict, dict],
):
    admin_h, user_h = auth_headers
    event = await _create_event(test_client, admin_h)
    await test_client.post(f"/registrations/{event['id']}", headers=user_h)
    r = await test_client.delete(f"/registrations/{event['id']}", headers=user_h)
    assert r.status_code == 204


async def test_cancel_401_no_token(
    test_client: AsyncClient,
    auth_headers: tuple[dict, dict],
):
    admin_h, user_h = auth_headers
    event = await _create_event(test_client, admin_h)
    await test_client.post(f"/registrations/{event['id']}", headers=user_h)
    r = await test_client.delete(f"/registrations/{event['id']}")
    assert r.status_code == 401


async def test_cancel_404_no_active_registration(
    test_client: AsyncClient,
    auth_headers: tuple[dict, dict],
):
    """Cancel without prior registration → 404 REGISTRATION_NOT_FOUND."""
    admin_h, user_h = auth_headers
    event = await _create_event(test_client, admin_h)
    r = await test_client.delete(f"/registrations/{event['id']}", headers=user_h)
    assert r.status_code == 404
    body = r.json()
    assert body["error"]["code"] == "REGISTRATION_NOT_FOUND"


async def test_cancel_422_deadline_passed(
    test_client: AsyncClient,
    auth_headers: tuple[dict, dict],
):
    """Cancel after deadline passes → 422 REGISTRATION_DEADLINE_PASSED.

    We insert the registration directly via DB since the API correctly blocks
    registrations for past-deadline events.
    """
    from src.domain.models import RegistrationStatus
    from src.infrastructure.db.models import EventRegistration as OrmReg
    from tests.conftest import _TestSessionLocal

    admin_h, user_h = auth_headers
    past_event = await _create_event(test_client, admin_h, **_PAST_DEADLINE_EVENT)

    r_me = await test_client.get("/auth/me", headers=user_h)
    user_id = r_me.json()["id"]

    async with _TestSessionLocal() as session:
        orm = OrmReg(
            user_id=user_id,
            event_id=past_event["id"],
            status=RegistrationStatus.ACTIVE,
            registered_at=datetime.now(tz=UTC),
        )
        session.add(orm)
        await session.commit()

    r = await test_client.delete(f"/registrations/{past_event['id']}", headers=user_h)
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "REGISTRATION_DEADLINE_PASSED"


async def test_cancel_cross_user_returns_404(
    test_client: AsyncClient,
    auth_headers: tuple[dict, dict],
):
    """User A cannot cancel user B's registration — returns 404 (not 403)."""
    admin_h, user_h = auth_headers
    event = await _create_event(test_client, admin_h)
    await test_client.post(f"/registrations/{event['id']}", headers=user_h)

    # User B tries to cancel
    await create_user(
        test_client, name="User B", email="userb@test.com", password="userB@ss123"
    )
    token_b = await _get_token(test_client, "userb@test.com", "userB@ss123")
    r = await test_client.delete(
        f"/registrations/{event['id']}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "REGISTRATION_NOT_FOUND"


# ---------------------------------------------------------------------------
# T019: GET /registrations/me
# ---------------------------------------------------------------------------


async def test_get_my_registrations_200(
    test_client: AsyncClient,
    auth_headers: tuple[dict, dict],
):
    admin_h, user_h = auth_headers
    event = await _create_event(test_client, admin_h)
    await test_client.post(f"/registrations/{event['id']}", headers=user_h)
    r = await test_client.get("/registrations/me", headers=user_h)
    assert r.status_code == 200
    items = r.json()
    assert isinstance(items, list)
    assert len(items) >= 1


async def test_get_my_registrations_shape(
    test_client: AsyncClient,
    auth_headers: tuple[dict, dict],
):
    admin_h, user_h = auth_headers
    event = await _create_event(test_client, admin_h)
    await test_client.post(f"/registrations/{event['id']}", headers=user_h)
    r = await test_client.get("/registrations/me", headers=user_h)
    items = r.json()
    item = items[0]
    assert {"id", "event_id", "status", "registered_at", "event"}.issubset(item.keys())
    assert "cancelled_at" in item
    event_summary = item["event"]
    assert {"id", "title", "date", "registration_deadline", "status"}.issubset(
        event_summary.keys()
    )


async def test_get_my_registrations_includes_cancelled(
    test_client: AsyncClient,
    auth_headers: tuple[dict, dict],
):
    """After cancel, entry has status=cancelled."""
    admin_h, user_h = auth_headers
    event = await _create_event(test_client, admin_h)
    await test_client.post(f"/registrations/{event['id']}", headers=user_h)
    await test_client.delete(f"/registrations/{event['id']}", headers=user_h)
    r = await test_client.get("/registrations/me", headers=user_h)
    statuses = [i["status"] for i in r.json()]
    assert "cancelled" in statuses


async def test_get_my_registrations_empty_for_new_user(
    test_client: AsyncClient,
    auth_headers: tuple[dict, dict],
):
    """User with no registrations returns empty list."""
    _, user_h = auth_headers
    r = await test_client.get("/registrations/me", headers=user_h)
    assert r.status_code == 200
    assert r.json() == []


async def test_get_my_registrations_401_no_token(test_client: AsyncClient):
    r = await test_client.get("/registrations/me")
    assert r.status_code == 401


async def test_get_my_registrations_user_isolation(
    test_client: AsyncClient,
    auth_headers: tuple[dict, dict],
):
    """User A's token cannot see user B's registrations — returns only own records."""
    admin_h, user_h = auth_headers
    event = await _create_event(test_client, admin_h)
    await test_client.post(f"/registrations/{event['id']}", headers=user_h)

    # User B (no registrations)
    await create_user(
        test_client,
        name="Isolated User",
        email="isolated@test.com",
        password="iso@ss123",
    )
    token_iso = await _get_token(test_client, "isolated@test.com", "iso@ss123")
    r = await test_client.get(
        "/registrations/me", headers={"Authorization": f"Bearer {token_iso}"}
    )
    assert r.status_code == 200
    assert r.json() == []


async def test_re_registration_after_cancel(
    test_client: AsyncClient,
    auth_headers: tuple[dict, dict],
):
    """Re-registration after cancellation creates a new active record."""
    admin_h, user_h = auth_headers
    event = await _create_event(test_client, admin_h)
    r1 = await test_client.post(f"/registrations/{event['id']}", headers=user_h)
    first_id = r1.json()["id"]

    await test_client.delete(f"/registrations/{event['id']}", headers=user_h)
    r2 = await test_client.post(f"/registrations/{event['id']}", headers=user_h)
    assert r2.status_code == 201
    assert r2.json()["id"] != first_id

    r_me = await test_client.get("/registrations/me", headers=user_h)
    event_regs = [reg for reg in r_me.json() if reg["event_id"] == event["id"]]
    statuses = {reg["status"] for reg in event_regs}
    assert statuses == {"active", "cancelled"}
