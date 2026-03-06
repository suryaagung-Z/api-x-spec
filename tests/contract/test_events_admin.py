"""Contract tests for admin event endpoints (T008 + T016)."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

# ---------------------------------------------------------------------------
# Shared test data
# ---------------------------------------------------------------------------

_NOW = datetime.now(tz=UTC)
_FUTURE_DATE = (_NOW + timedelta(days=30)).isoformat()
_FUTURE_DEADLINE = (_NOW + timedelta(days=20)).isoformat()
_PAST_DATE = (_NOW - timedelta(days=1)).isoformat()
_PAST_DEADLINE = (_NOW - timedelta(days=2)).isoformat()

_VALID_EVENT = {
    "title": "Admin Test Event",
    "description": "Created in contract tests",
    "date": _FUTURE_DATE,
    "registration_deadline": _FUTURE_DEADLINE,
    "quota": 50,
}


async def _create_event(client: AsyncClient, headers: dict, **overrides) -> dict:
    body = {**_VALID_EVENT, **overrides}
    r = await client.post("/admin/events", json=body, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


# ===========================================================================
# T008: POST /admin/events
# ===========================================================================


async def test_admin_create_event_201(
    test_client: AsyncClient, admin_auth_headers: dict
):
    r = await test_client.post(
        "/admin/events", json=_VALID_EVENT, headers=admin_auth_headers
    )
    assert r.status_code == 201
    body = r.json()
    assert body["title"] == _VALID_EVENT["title"]
    assert body["quota"] == _VALID_EVENT["quota"]
    assert "id" in body
    assert "registration_closed" in body


async def test_admin_create_event_response_shape(
    test_client: AsyncClient, admin_auth_headers: dict
):
    r = await test_client.post(
        "/admin/events", json=_VALID_EVENT, headers=admin_auth_headers
    )
    assert r.status_code == 201
    body = r.json()
    required_fields = {
        "id", "title", "description", "date", "registration_deadline",
        "quota", "status", "created_at", "registration_closed"
    }
    assert required_fields.issubset(body.keys())


async def test_admin_create_event_422_deadline_after_date(
    test_client: AsyncClient, admin_auth_headers: dict
):
    """deadline > date must return 422."""
    bad_body = {
        **_VALID_EVENT,
        "date": _FUTURE_DEADLINE,          # earlier
        "registration_deadline": _FUTURE_DATE,  # later → invalid
    }
    r = await test_client.post(
        "/admin/events", json=bad_body, headers=admin_auth_headers
    )
    assert r.status_code == 422


async def test_admin_create_event_201_past_deadline_future_date(
    test_client: AsyncClient, admin_auth_headers: dict
):
    """A past registration_deadline with a future event date is valid
    (registration closed early).
    """
    body = {
        **_VALID_EVENT,
        "date": _FUTURE_DATE,
        "registration_deadline": _PAST_DEADLINE,
    }
    r = await test_client.post(
        "/admin/events", json=body, headers=admin_auth_headers
    )
    assert r.status_code == 201


async def test_admin_create_event_422_past_event_date(
    test_client: AsyncClient, admin_auth_headers: dict
):
    """event date explicitly in the past → 422."""
    bad_body = {
        **_VALID_EVENT,
        "date": _PAST_DATE,
        "registration_deadline": _PAST_DEADLINE,
    }
    r = await test_client.post(
        "/admin/events", json=bad_body, headers=admin_auth_headers
    )
    assert r.status_code == 422


async def test_admin_create_event_422_missing_title(
    test_client: AsyncClient, admin_auth_headers: dict
):
    bad_body = {k: v for k, v in _VALID_EVENT.items() if k != "title"}
    r = await test_client.post(
        "/admin/events", json=bad_body, headers=admin_auth_headers
    )
    assert r.status_code == 422


async def test_admin_create_event_422_naive_datetime(
    test_client: AsyncClient, admin_auth_headers: dict
):
    """Naive (non-timezone-aware) datetime must be rejected."""
    bad_body = {
        **_VALID_EVENT,
        "date": "2099-12-31T23:59:59",  # no timezone offset
    }
    r = await test_client.post(
        "/admin/events", json=bad_body, headers=admin_auth_headers
    )
    assert r.status_code == 422


async def test_admin_create_event_401_no_token(test_client: AsyncClient):
    r = await test_client.post("/admin/events", json=_VALID_EVENT)
    assert r.status_code == 401


async def test_admin_create_event_403_regular_user(
    test_client: AsyncClient, user_auth_headers: dict
):
    r = await test_client.post(
        "/admin/events", json=_VALID_EVENT, headers=user_auth_headers
    )
    assert r.status_code == 403
    body = r.json()
    # Envelope check: must have error.code
    assert "error" in body
    assert body["error"]["httpStatus"] == 403


# ===========================================================================
# T016: GET /admin/events/{id}
# ===========================================================================


async def test_admin_get_event_200(
    test_client: AsyncClient, admin_auth_headers: dict
):
    event = await _create_event(test_client, admin_auth_headers)
    r = await test_client.get(
        f"/admin/events/{event['id']}", headers=admin_auth_headers
    )
    assert r.status_code == 200
    assert r.json()["id"] == event["id"]


async def test_admin_get_event_404(
    test_client: AsyncClient, admin_auth_headers: dict
):
    r = await test_client.get("/admin/events/999999", headers=admin_auth_headers)
    assert r.status_code == 404
    body = r.json()
    assert "error" in body
    assert body["error"]["httpStatus"] == 404


async def test_admin_get_event_401(test_client: AsyncClient):
    r = await test_client.get("/admin/events/1")
    assert r.status_code == 401


async def test_admin_get_event_403_regular_user(
    test_client: AsyncClient, user_auth_headers: dict
):
    r = await test_client.get("/admin/events/1", headers=user_auth_headers)
    assert r.status_code == 403


# ===========================================================================
# T016: PUT /admin/events/{id}
# ===========================================================================


async def test_admin_update_event_200(
    test_client: AsyncClient, admin_auth_headers: dict
):
    event = await _create_event(test_client, admin_auth_headers)
    r = await test_client.put(
        f"/admin/events/{event['id']}",
        json={"title": "Updated Title"},
        headers=admin_auth_headers,
    )
    assert r.status_code == 200
    assert r.json()["title"] == "Updated Title"


async def test_admin_update_event_404(
    test_client: AsyncClient, admin_auth_headers: dict
):
    r = await test_client.put(
        "/admin/events/999999",
        json={"title": "Ghost"},
        headers=admin_auth_headers,
    )
    assert r.status_code == 404


async def test_admin_update_event_422_deadline_after_date(
    test_client: AsyncClient, admin_auth_headers: dict
):
    """PUT: partial update where resulting deadline > date → 422."""
    event = await _create_event(test_client, admin_auth_headers)
    # Move date to just after current deadline but supply a new deadline later
    further_future = (_NOW + timedelta(days=100)).isoformat()
    r = await test_client.put(
        f"/admin/events/{event['id']}",
        json={"registration_deadline": further_future},
        headers=admin_auth_headers,
    )
    assert r.status_code == 422


async def test_admin_update_event_401(test_client: AsyncClient):
    r = await test_client.put("/admin/events/1", json={"title": "x"})
    assert r.status_code == 401


async def test_admin_update_event_403_regular_user(
    test_client: AsyncClient, user_auth_headers: dict
):
    r = await test_client.put(
        "/admin/events/1", json={"title": "x"}, headers=user_auth_headers
    )
    assert r.status_code == 403


# ===========================================================================
# T016: DELETE /admin/events/{id}
# ===========================================================================


async def test_admin_delete_event_204(
    test_client: AsyncClient, admin_auth_headers: dict
):
    event = await _create_event(test_client, admin_auth_headers)
    r = await test_client.delete(
        f"/admin/events/{event['id']}", headers=admin_auth_headers
    )
    assert r.status_code == 204


async def test_admin_delete_event_404(
    test_client: AsyncClient, admin_auth_headers: dict
):
    r = await test_client.delete("/admin/events/999999", headers=admin_auth_headers)
    assert r.status_code == 404


async def test_admin_delete_event_already_deleted_404(
    test_client: AsyncClient, admin_auth_headers: dict
):
    """Deleting an already-deleted event must return 404."""
    event = await _create_event(test_client, admin_auth_headers)
    await test_client.delete(
        f"/admin/events/{event['id']}", headers=admin_auth_headers
    )
    r = await test_client.delete(
        f"/admin/events/{event['id']}", headers=admin_auth_headers
    )
    assert r.status_code == 404


async def test_admin_delete_event_401(test_client: AsyncClient):
    r = await test_client.delete("/admin/events/1")
    assert r.status_code == 401


async def test_admin_delete_event_403_regular_user(
    test_client: AsyncClient, user_auth_headers: dict
):
    r = await test_client.delete("/admin/events/1", headers=user_auth_headers)
    assert r.status_code == 403
