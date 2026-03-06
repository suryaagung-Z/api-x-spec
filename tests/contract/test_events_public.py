"""Contract tests for public event endpoints (T021 + T028)."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

_NOW = datetime.now(tz=UTC)
_FUTURE_DATE = (_NOW + timedelta(days=30)).isoformat()
_FUTURE_DEADLINE = (_NOW + timedelta(days=20)).isoformat()


_VALID_EVENT = {
    "title": "Public Test Event",
    "description": "Visible to all",
    "date": _FUTURE_DATE,
    "registration_deadline": _FUTURE_DEADLINE,
    "quota": 100,
}


async def _create_event(client: AsyncClient, headers: dict, **overrides) -> dict:
    body = {**_VALID_EVENT, **overrides}
    r = await client.post("/admin/events", json=body, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


# ===========================================================================
# T021: GET /events — list public events
# ===========================================================================


async def test_public_list_events_200(
    test_client: AsyncClient, admin_auth_headers: dict
):
    await _create_event(test_client, admin_auth_headers)
    r = await test_client.get("/events")
    assert r.status_code == 200
    body = r.json()
    assert "items" in body
    assert "total_items" in body
    assert "page" in body
    assert "page_size" in body
    assert "total_pages" in body


async def test_public_list_events_items_have_registration_closed(
    test_client: AsyncClient, admin_auth_headers: dict
):
    await _create_event(test_client, admin_auth_headers)
    r = await test_client.get("/events")
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) >= 1
    assert "registration_closed" in items[0]


async def test_public_list_events_only_future_events(
    test_client: AsyncClient, admin_auth_headers: dict
):
    """Only events with date > now should appear in the public list."""
    # Create a valid future event
    await _create_event(test_client, admin_auth_headers)
    # The public list should only contain future events; past events shouldn't appear
    r = await test_client.get("/events")
    assert r.status_code == 200
    items = r.json()["items"]
    for item in items:
        event_date = datetime.fromisoformat(item["date"])
        if event_date.tzinfo is None:
            event_date = event_date.replace(tzinfo=UTC)
        assert event_date > _NOW, f"Past event leaked into public list: {item}"


async def test_public_list_events_deleted_excluded(
    test_client: AsyncClient, admin_auth_headers: dict
):
    """Deleted events must not appear in the public list."""
    event = await _create_event(test_client, admin_auth_headers, title="To Be Deleted")
    await test_client.delete(
        f"/admin/events/{event['id']}", headers=admin_auth_headers
    )
    r = await test_client.get("/events")
    assert r.status_code == 200
    ids = [item["id"] for item in r.json()["items"]]
    assert event["id"] not in ids


async def test_public_list_events_pagination_defaults(
    test_client: AsyncClient, admin_auth_headers: dict
):
    r = await test_client.get("/events")
    assert r.status_code == 200
    body = r.json()
    assert body["page"] == 1
    assert body["page_size"] == 20


async def test_public_list_events_pagination_params(
    test_client: AsyncClient, admin_auth_headers: dict
):
    for i in range(5):
        await _create_event(test_client, admin_auth_headers, title=f"Event {i}")
    r = await test_client.get("/events?page=1&page_size=2")
    assert r.status_code == 200
    body = r.json()
    assert len(body["items"]) <= 2
    assert body["page_size"] == 2


async def test_public_list_events_422_invalid_page_size(test_client: AsyncClient):
    """page_size=0 or >100 must return 422."""
    assert (await test_client.get("/events?page_size=0")).status_code == 422
    assert (await test_client.get("/events?page_size=101")).status_code == 422


async def test_public_list_events_422_invalid_page(test_client: AsyncClient):
    """page=0 must return 422."""
    assert (await test_client.get("/events?page=0")).status_code == 422


# T028: high page number returns empty items, not 404
async def test_public_list_events_high_page_returns_empty(
    test_client: AsyncClient, admin_auth_headers: dict
):
    await _create_event(test_client, admin_auth_headers)
    r = await test_client.get("/events?page=9999")
    assert r.status_code == 200
    body = r.json()
    assert body["items"] == []
    assert body["page"] == 9999


# ===========================================================================
# T021: GET /events/{id} — public event detail
# ===========================================================================


async def test_public_get_event_200(
    test_client: AsyncClient, admin_auth_headers: dict
):
    event = await _create_event(test_client, admin_auth_headers)
    r = await test_client.get(f"/events/{event['id']}")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == event["id"]
    assert "registration_closed" in body


async def test_public_get_event_404_nonexistent(test_client: AsyncClient):
    r = await test_client.get("/events/999999")
    assert r.status_code == 404
    body = r.json()
    assert "error" in body
    assert body["error"]["httpStatus"] == 404


async def test_public_get_event_404_deleted(
    test_client: AsyncClient, admin_auth_headers: dict
):
    """A deleted event must not be accessible via the public endpoint."""
    event = await _create_event(test_client, admin_auth_headers)
    await test_client.delete(
        f"/admin/events/{event['id']}", headers=admin_auth_headers
    )
    r = await test_client.get(f"/events/{event['id']}")
    assert r.status_code == 404


# T027: event with past deadline but future date → in public list,
# registration_closed=True
async def test_public_event_past_deadline_future_date_registration_closed(
    test_client: AsyncClient, admin_auth_headers: dict
):
    """An event with registration_deadline in the past but date in the future
    should appear in the public list with registration_closed=True."""
    past_deadline = (_NOW - timedelta(hours=1)).isoformat()
    future_date = (_NOW + timedelta(days=60)).isoformat()
    event = await _create_event(
        test_client,
        admin_auth_headers,
        date=future_date,
        registration_deadline=past_deadline,
    )
    r = await test_client.get(f"/events/{event['id']}")
    assert r.status_code == 200
    assert r.json()["registration_closed"] is True


async def test_public_list_includes_event_with_past_deadline(
    test_client: AsyncClient, admin_auth_headers: dict
):
    """Same scenario as above but via the list endpoint."""
    past_deadline = (_NOW - timedelta(hours=1)).isoformat()
    future_date = (_NOW + timedelta(days=60)).isoformat()
    event = await _create_event(
        test_client,
        admin_auth_headers,
        title="Registration Closed Event",
        date=future_date,
        registration_deadline=past_deadline,
    )
    r = await test_client.get("/events")
    assert r.status_code == 200
    ids = [item["id"] for item in r.json()["items"]]
    assert event["id"] in ids
