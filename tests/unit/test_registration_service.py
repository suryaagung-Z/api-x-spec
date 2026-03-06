"""Unit tests for registration_service use cases (T009, T016, T020, T027)."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.application.registration_service import cancel, register
from src.domain.exceptions import (
    DuplicateActiveRegistrationError,
    EventNotFoundError,
    NoActiveRegistrationError,
    QuotaFullError,
    RegistrationDeadlinePassedError,
)

pytestmark = pytest.mark.asyncio

_NOW = datetime.now(tz=UTC)
_FUTURE = _NOW + timedelta(days=30)
_FUTURE_DEADLINE = _NOW + timedelta(days=20)
_PAST_DEADLINE = _NOW - timedelta(hours=1)

USER_ID = "user-uuid-1234"
EVENT_ID = 42


def _make_event_response(*, deadline: datetime = _FUTURE_DEADLINE):
    """Create a mock EventResponse-like object."""
    ev = MagicMock()
    ev.id = EVENT_ID
    ev.registration_deadline = deadline
    return ev


# ---------------------------------------------------------------------------
# T009 / T016: register() use-case guards
# ---------------------------------------------------------------------------


async def test_register_raises_event_not_found():
    """Guard 1: event not found → EventNotFoundError."""
    session = AsyncMock()
    with patch(
        "src.application.registration_service.get_public_event",
        side_effect=EventNotFoundError(EVENT_ID),
    ):
        with pytest.raises(EventNotFoundError):
            from src.application.registration_service import register

            await register(session, USER_ID, EVENT_ID)


async def test_register_raises_deadline_passed():
    """Guard 2: registration_deadline in past → RegistrationDeadlinePassedError."""
    session = AsyncMock()
    with patch(
        "src.application.registration_service.get_public_event",
        return_value=_make_event_response(deadline=_PAST_DEADLINE),
    ):
        with pytest.raises(RegistrationDeadlinePassedError):
            from src.application.registration_service import register

            await register(session, USER_ID, EVENT_ID)


async def test_register_raises_duplicate_registration():
    """Guard 3: existing active registration → DuplicateActiveRegistrationError."""
    session = AsyncMock()
    with patch(
        "src.application.registration_service.get_public_event",
        return_value=_make_event_response(),
    ):
        with patch(
            "src.application.registration_service.RegistrationRepository"
        ) as MockRepo:
            repo = MockRepo.return_value
            repo.get_active_registration = AsyncMock(
                return_value=MagicMock()  # existing registration
            )

            with pytest.raises(DuplicateActiveRegistrationError):
                from src.application.registration_service import register

                await register(session, USER_ID, EVENT_ID)


async def test_register_raises_quota_full():
    """Guard 4: atomic_increment returns None → QuotaFullError."""
    session = AsyncMock()
    with patch(
        "src.application.registration_service.get_public_event",
        return_value=_make_event_response(),
    ):
        with patch(
            "src.application.registration_service.RegistrationRepository"
        ) as MockRepo:
            repo = MockRepo.return_value
            repo.get_active_registration = AsyncMock(return_value=None)
            repo.atomic_increment_participants = AsyncMock(return_value=None)

            with pytest.raises(QuotaFullError):
                from src.application.registration_service import register

                await register(session, USER_ID, EVENT_ID)


async def test_register_happy_path():
    """All guards pass → RegistrationResponse returned."""
    session = AsyncMock()
    orm = MagicMock()
    orm.id = 1
    orm.event_id = EVENT_ID
    orm.status = "active"
    orm.registered_at = _NOW

    with patch(
        "src.application.registration_service.get_public_event",
        return_value=_make_event_response(),
    ):
        with patch(
            "src.application.registration_service.RegistrationRepository"
        ) as MockRepo:
            repo = MockRepo.return_value
            repo.get_active_registration = AsyncMock(return_value=None)
            repo.atomic_increment_participants = AsyncMock(return_value=EVENT_ID)
            repo.create_registration = AsyncMock(return_value=orm)

            from src.api.schemas.registrations import RegistrationResponse
            from src.application.registration_service import register

            with patch(
                "src.api.schemas.registrations.RegistrationResponse.model_validate"
            ) as mock_validate:
                mock_validate.return_value = RegistrationResponse(
                    id=1, event_id=EVENT_ID, status="active", registered_at=_NOW
                )
                result = await register(session, USER_ID, EVENT_ID)

            assert result.event_id == EVENT_ID
            assert result.status.value == "active"


# ---------------------------------------------------------------------------
# T020: cancel() use-case guards
# ---------------------------------------------------------------------------


async def test_cancel_raises_no_active_registration():
    """Guard 1: no active registration → NoActiveRegistrationError."""
    session = AsyncMock()
    with patch(
        "src.application.registration_service.RegistrationRepository"
    ) as MockRepo:
        repo = MockRepo.return_value
        repo.get_active_registration = AsyncMock(return_value=None)

        with pytest.raises(NoActiveRegistrationError):
            from src.application.registration_service import cancel

            await cancel(session, USER_ID, EVENT_ID)


async def test_cancel_raises_event_not_found():
    """Guard 2: active registration exists but event not found → EventNotFoundError."""
    session = AsyncMock()
    with patch(
        "src.application.registration_service.RegistrationRepository"
    ) as MockRepo:
        repo = MockRepo.return_value
        repo.get_active_registration = AsyncMock(return_value=MagicMock())

        with patch(
            "src.application.registration_service.get_public_event",
            side_effect=EventNotFoundError(EVENT_ID),
        ):
            with pytest.raises(EventNotFoundError):
                from src.application.registration_service import cancel

                await cancel(session, USER_ID, EVENT_ID)


async def test_cancel_raises_deadline_passed():
    """Guard 3: registration_deadline already passed
    → RegistrationDeadlinePassedError.
    """
    session = AsyncMock()
    with patch(
        "src.application.registration_service.RegistrationRepository"
    ) as MockRepo:
        repo = MockRepo.return_value
        repo.get_active_registration = AsyncMock(return_value=MagicMock())

        with patch(
            "src.application.registration_service.get_public_event",
            return_value=_make_event_response(deadline=_PAST_DEADLINE),
        ):
            with pytest.raises(RegistrationDeadlinePassedError):
                from src.application.registration_service import cancel

                await cancel(session, USER_ID, EVENT_ID)


async def test_cancel_happy_path_calls_cancel_and_decrement():
    """Valid cancel: cancel_registration + atomic_decrement called."""
    session = AsyncMock()
    with patch(
        "src.application.registration_service.RegistrationRepository"
    ) as MockRepo:
        repo = MockRepo.return_value
        repo.get_active_registration = AsyncMock(return_value=MagicMock())
        repo.cancel_registration = AsyncMock()
        repo.atomic_decrement_participants = AsyncMock()

        with patch(
            "src.application.registration_service.get_public_event",
            return_value=_make_event_response(),
        ):
            from src.application.registration_service import cancel

            await cancel(session, USER_ID, EVENT_ID)

        repo.cancel_registration.assert_called_once_with(USER_ID, EVENT_ID)
        repo.atomic_decrement_participants.assert_called_once_with(EVENT_ID)


# ---------------------------------------------------------------------------
# T027: Boundary edge case — deadline at exact moment
# ---------------------------------------------------------------------------


async def test_register_deadline_at_exact_moment_raises():
    """Guard: when now == registration_deadline, request is rejected
    (closed boundary).
    """
    exact_now = datetime.now(tz=UTC)
    session = AsyncMock()
    with patch(
        "src.application.registration_service.get_public_event",
        return_value=_make_event_response(deadline=exact_now),
    ):
        with patch("src.application.registration_service.datetime") as mock_dt:
            mock_dt.now.return_value = exact_now

            with pytest.raises(RegistrationDeadlinePassedError):
                await register(session, USER_ID, EVENT_ID)


async def test_cancel_deadline_at_exact_moment_raises():
    """Cancel guard: closed boundary — exact deadline moment is rejected."""
    exact_now = datetime.now(tz=UTC)
    session = AsyncMock()
    with patch(
        "src.application.registration_service.RegistrationRepository"
    ) as MockRepo:
        repo = MockRepo.return_value
        repo.get_active_registration = AsyncMock(return_value=MagicMock())

        with patch(
            "src.application.registration_service.get_public_event",
            return_value=_make_event_response(deadline=exact_now),
        ):
            with patch("src.application.registration_service.datetime") as mock_dt:
                mock_dt.now.return_value = exact_now

                with pytest.raises(RegistrationDeadlinePassedError):
                    await cancel(session, USER_ID, EVENT_ID)
