"""Unit tests for event Pydantic schemas."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from src.api.schemas.events import EventCreate, EventResponse
from src.domain.models import EventStatus

FUTURE = datetime.now(tz=UTC) + timedelta(days=30)
PAST = datetime.now(tz=UTC) - timedelta(days=1)


def _make_event_create(**overrides) -> dict:
    base = {
        "title": "Test Event",
        "description": "A test event",
        "date": (FUTURE + timedelta(days=5)).isoformat(),
        "registration_deadline": FUTURE.isoformat(),
        "quota": 100,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# EventCreate.validate_deadline_before_date
# ---------------------------------------------------------------------------


def test_event_create_valid():
    e = EventCreate(**{
        **_make_event_create(),
        "date": FUTURE + timedelta(days=5),
        "registration_deadline": FUTURE,
    })
    assert e.quota == 100


def test_event_create_deadline_after_date_raises_validation_error():
    """registration_deadline > date must raise ValidationError."""
    with pytest.raises(ValidationError):
        EventCreate(
            title="Bad Event",
            description="desc",
            date=FUTURE,
            registration_deadline=FUTURE + timedelta(days=1),  # deadline AFTER date
            quota=10,
        )


def test_event_create_deadline_equal_to_date_is_valid():
    """registration_deadline == date is allowed."""
    e = EventCreate(
        title="Same Day",
        description="desc",
        date=FUTURE,
        registration_deadline=FUTURE,
        quota=10,
    )
    assert e.registration_deadline == e.date


def test_event_create_naive_datetime_raises():
    """Naive datetimes (no timezone) must be rejected."""
    naive_dt = datetime(2030, 1, 1, 12, 0, 0)  # no tzinfo
    with pytest.raises(ValidationError):
        EventCreate(
            title="Naive",
            description="desc",
            date=naive_dt,
            registration_deadline=naive_dt,
            quota=10,
        )


# ---------------------------------------------------------------------------
# EventResponse.registration_closed computed field
# ---------------------------------------------------------------------------


def _make_event_response(registration_deadline: datetime) -> EventResponse:
    return EventResponse(
        id=1,
        title="Test",
        description="desc",
        date=FUTURE + timedelta(days=5),
        registration_deadline=registration_deadline,
        quota=50,
        status=EventStatus.ACTIVE,
        created_at=datetime.now(tz=UTC),
    )


def test_registration_closed_is_true_when_deadline_in_past():
    event = _make_event_response(
        registration_deadline=datetime.now(tz=UTC) - timedelta(hours=1)
    )
    assert event.registration_closed is True


def test_registration_closed_is_false_when_deadline_in_future():
    event = _make_event_response(
        registration_deadline=datetime.now(tz=UTC) + timedelta(days=10)
    )
    assert event.registration_closed is False
