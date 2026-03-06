"""Domain exceptions for the authentication feature."""
from __future__ import annotations


class DomainError(Exception):
    """Base class for domain errors."""


class EmailAlreadyExistsError(DomainError):
    """Raised when attempting to register with an already-registered email."""


class InvalidCredentialsError(DomainError):
    """Raised on login when email or password is incorrect."""


class UserNotFoundError(DomainError):
    """Raised when a JWT subject references a user that no longer exists."""


# ---------------------------------------------------------------------------
# Event management exceptions (002-event-management)
# ---------------------------------------------------------------------------


class EventNotFoundError(DomainError):
    """Raised when an event cannot be found by ID or is not publicly accessible."""

    def __init__(self, event_id: int) -> None:
        self.event_id = event_id
        super().__init__(f"Event {event_id} not found")


class QuotaBelowParticipantsError(DomainError):
    """Raised when an update would set quota below the current participant count."""

    def __init__(
        self, event_id: int, requested_quota: int, participant_count: int
    ) -> None:
        self.event_id = event_id
        self.requested_quota = requested_quota
        self.participant_count = participant_count
        super().__init__(
            f"Cannot set quota to {requested_quota}; "
            f"event {event_id} already has {participant_count} participants"
        )


class EventDateInPastError(DomainError):
    """Raised when an event date is set in the past on create (business rule)."""

    def __init__(self, event_id: int | None = None) -> None:
        super().__init__("Event date must be in the future")


# ---------------------------------------------------------------------------
# Event registration exceptions (003-event-registration)
# ---------------------------------------------------------------------------


class QuotaFullError(DomainError):
    """Raised when an event has no remaining quota."""

    def __init__(self, event_id: int) -> None:
        self.event_id = event_id
        super().__init__(f"Event {event_id} is fully booked")


class DuplicateActiveRegistrationError(DomainError):
    """Raised when a user attempts to register again for an already-registered event."""

    def __init__(self, user_id: str, event_id: int) -> None:
        self.user_id = user_id
        self.event_id = event_id
        super().__init__(
            f"User already has an active registration for event {event_id}"
        )


class NoActiveRegistrationError(DomainError):
    """Raised when a cancellation is attempted but no active registration exists."""

    def __init__(self, user_id: str, event_id: int) -> None:
        self.user_id = user_id
        self.event_id = event_id
        super().__init__(f"No active registration found for event {event_id}")


class RegistrationDeadlinePassedError(DomainError):
    """Raised when registration or cancellation is attempted after the deadline."""

    def __init__(self, event_id: int) -> None:
        self.event_id = event_id
        super().__init__(f"Registration deadline for event {event_id} has passed")
