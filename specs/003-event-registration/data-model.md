# Data Model: 003-event-registration

---

## 1. Domain Entities

### 1.1 RegistrationStatus Enum

```python
# src/domain/models.py (addition)
import enum

class RegistrationStatus(str, enum.Enum):
    ACTIVE    = "active"
    CANCELLED = "cancelled"
```

Maps directly to spec vocabulary: `aktif` → `ACTIVE`, `dibatalkan` → `CANCELLED`. Records are **never hard-deleted** (FR-008, FR-010).

---

### 1.2 EventRegistration Entity

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `id` | `int` | PK, auto-increment | Surrogate key |
| `user_id` | `int` | NOT NULL, FK → `users.id` | The registering user |
| `event_id` | `int` | NOT NULL, FK → `events.id` | Target event |
| `status` | `RegistrationStatus` | NOT NULL, default `active` | Soft-delete flag |
| `registered_at` | `datetime (TIMESTAMPTZ)` | NOT NULL, server_default NOW() | When registration was created |
| `cancelled_at` | `datetime (TIMESTAMPTZ)` | NULL | Populated when status changes to `cancelled` |

**Uniqueness constraint**: Only one `ACTIVE` registration is allowed per `(user_id, event_id)`.
Enforced by partial unique index `uq_active_registration` on `(user_id, event_id) WHERE status = 'active'`.
A `CANCELLED` row does **not** block a new `ACTIVE` row for the same pair (FR-005).

---

### 1.3 Event Entity — Addition from 003

The `Event` table (defined in 002-event-management) gains one column in this feature:

| Column added | Type | Default | Constraint | Notes |
|-------------|------|---------|------------|-------|
| `current_participants` | `int` | `0` | NOT NULL, ≥ 0, ≤ quota | Denormalized counter; incremented on registration, decremented on cancellation |

The counter is updated atomically in the same database transaction as the registration/cancellation insert/update, using PostgreSQL row-level locking semantics of the UPDATE statement.

---

## 2. SQLAlchemy ORM Model

### 2.1 EventRegistration ORM

```python
# src/infrastructure/db/models.py (addition)
from datetime import datetime
from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Index, Integer, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.domain.models import RegistrationStatus

class EventRegistration(Base):
    __tablename__ = "event_registrations"

    id:            Mapped[int]                = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id:       Mapped[int]                = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    event_id:      Mapped[int]                = mapped_column(Integer, ForeignKey("events.id"), nullable=False)
    status:        Mapped[RegistrationStatus] = mapped_column(
                       SAEnum(RegistrationStatus, name="registrationstatus"),
                       nullable=False,
                       default=RegistrationStatus.ACTIVE,
                   )
    registered_at: Mapped[datetime] = mapped_column(
                       DateTime(timezone=True),
                       nullable=False,
                       server_default=func.now(),
                   )
    cancelled_at:  Mapped[datetime | None] = mapped_column(
                       DateTime(timezone=True),
                       nullable=True,
                       default=None,
                   )

    # Relationship — loaded explicitly with selectinload; lazy="raise" catches accidental access
    event: Mapped["Event"] = relationship("Event", lazy="raise")

    __table_args__ = (
        # Hard guarantee: only one ACTIVE registration per (user, event)
        # Cancelled rows do not participate in this constraint
        Index(
            "uq_active_registration",
            "user_id",
            "event_id",
            unique=True,
            postgresql_where="status = 'active'",
        ),
        # Covers WHERE user_id = ? ORDER BY registered_at DESC (GET /registrations/me)
        Index("ix_event_registrations_user_registered", "user_id", "registered_at"),
        # Covers WHERE event_id = ? AND status = 'active' (participant count queries, if needed)
        Index(
            "ix_event_registrations_event_active",
            "event_id",
            postgresql_where="status = 'active'",
        ),
    )
```

### 2.2 Event ORM — `current_participants` column addition

```python
# src/infrastructure/db/models.py — add to existing Event class:
current_participants: Mapped[int] = mapped_column(
    Integer, nullable=False, default=0, server_default="0"
)
```

---

## 3. SQL Schema (reference)

```sql
-- New type
CREATE TYPE registrationstatus AS ENUM ('active', 'cancelled');

-- New column on existing events table (003 migration)
ALTER TABLE events
    ADD COLUMN current_participants INTEGER NOT NULL DEFAULT 0;

ALTER TABLE events
    ADD CONSTRAINT chk_participants_not_negative
    CHECK (current_participants >= 0);

ALTER TABLE events
    ADD CONSTRAINT chk_participants_not_over_quota
    CHECK (current_participants <= quota);

-- New table
CREATE TABLE event_registrations (
    id             SERIAL      PRIMARY KEY,
    user_id        INTEGER     NOT NULL REFERENCES users(id),
    event_id       INTEGER     NOT NULL REFERENCES events(id),
    status         registrationstatus NOT NULL DEFAULT 'active',
    registered_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    cancelled_at   TIMESTAMPTZ
);

-- Uniqueness: one active registration per (user, event); cancelled rows excluded
CREATE UNIQUE INDEX uq_active_registration
    ON event_registrations (user_id, event_id)
    WHERE status = 'active';

-- Covers GET /registrations/me query pattern
CREATE INDEX ix_event_registrations_user_registered
    ON event_registrations (user_id, registered_at DESC);

-- Covers quota/participant count queries per event (active only)
CREATE INDEX ix_event_registrations_event_active
    ON event_registrations (event_id)
    WHERE status = 'active';
```

---

## 4. Pydantic Schemas

### 4.1 RegisterRequest

```python
# src/api/schemas/registrations.py
from pydantic import BaseModel

class RegisterRequest(BaseModel):
    """Request body is empty — event_id comes from path parameter."""
    pass
```

> Note: Registration takes `event_id` as a **path parameter**, not a body field: `POST /registrations/{event_id}`. No request body schema needed beyond what FastAPI extracts from the path.

### 4.2 RegistrationResponse (simple, post-register)

```python
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from src.domain.models import RegistrationStatus

class RegistrationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:            int
    event_id:      int
    status:        RegistrationStatus
    registered_at: datetime
```

### 4.3 EventSummary (nested in list response)

```python
from src.domain.models import EventStatus

class EventSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:                    int
    title:                 str
    date:                  datetime
    registration_deadline: datetime
    status:                EventStatus  # allows user to see if event was cancelled
```

### 4.4 RegistrationWithEventResponse (GET /registrations/me)

```python
class RegistrationWithEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:            int
    event_id:      int
    status:        RegistrationStatus
    registered_at: datetime
    cancelled_at:  datetime | None
    event:         EventSummary
```

---

## 5. Domain Exceptions

```python
# src/domain/exceptions.py (additions)

class QuotaFullError(Exception):
    """Raised when event quota is reached and no more registrations can be accepted."""
    def __init__(self, event_id: int) -> None:
        self.event_id = event_id
        super().__init__(f"Event {event_id} is fully booked")

class DuplicateActiveRegistrationError(Exception):
    """Raised when user already has an active registration for this event."""
    def __init__(self, user_id: int, event_id: int) -> None:
        self.user_id = user_id
        self.event_id = event_id
        super().__init__(f"User {user_id} already has an active registration for event {event_id}")

class NoActiveRegistrationError(Exception):
    """Raised when attempting to cancel a registration that does not exist or is already cancelled."""
    def __init__(self, user_id: int, event_id: int) -> None:
        self.user_id = user_id
        self.event_id = event_id
        super().__init__(f"No active registration found for user {user_id} on event {event_id}")

class RegistrationDeadlinePassedError(Exception):
    """Raised when registration_deadline has already passed (for both registration and cancellation)."""
    def __init__(self, event_id: int) -> None:
        self.event_id = event_id
        super().__init__(f"Registration deadline for event {event_id} has passed")
```

### Exception → HTTP Status Mapping

| Domain Exception | HTTP Status | Error Code | FR reference |
|-----------------|-------------|------------|--------------|
| `EventNotFoundError` (from 002) | 404 Not Found | `EVENT_NOT_FOUND` | FR-002, FR-011 |
| `RegistrationDeadlinePassedError` | 422 Unprocessable | `REGISTRATION_DEADLINE_PASSED` | FR-003, FR-007, FR-011 |
| `QuotaFullError` | 422 Unprocessable | `QUOTA_FULL` | FR-004, FR-011 |
| `DuplicateActiveRegistrationError` | 409 Conflict | `DUPLICATE_REGISTRATION` | FR-005, FR-011 |
| `NoActiveRegistrationError` | 404 Not Found | `REGISTRATION_NOT_FOUND` | FR-011 |

---

## 6. Registration State Transitions

```text
                ┌────────────────────────────────────────┐
                │           EventRegistration            │
                │                                        │
    register()  │  ┌──────────┐    cancel()  ┌──────────┐│
   ────────────►│  │  ACTIVE  │ ────────────►│CANCELLED ││
                │  └──────────┘              └──────────┘│
                │       ▲                         │      │
                │       │   register() (re-reg)   │      │
                │       │   new ACTIVE row        │      │
                │       └─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─┘      │
                └────────────────────────────────────────┘
```

- **ACTIVE** → register at any point (while deadline not passed, quota not full)
- **ACTIVE** → **CANCELLED** via `cancel()` (while deadline not passed)
- **CANCELLED** → new **ACTIVE** row created via `register()` (previous cancelled row stays)
- No transitions after deadline has passed
- Records are never deleted

---

## 7. Service Layer — Key Logic

### register() — full guard sequence

```python
async def register(session: AsyncSession, user_id: int, event_id: int) -> EventRegistration:
    # 1. Event exists and is public (ACTIVE + future date)
    event = await session.scalar(_public_events_query().where(Event.id == event_id))
    if event is None:
        raise EventNotFoundError(event_id)

    # 2. Registration deadline not passed
    if event.registration_deadline < datetime.now(timezone.utc):
        raise RegistrationDeadlinePassedError(event_id)

    # 3. App-level duplicate check (fast path before DB write)
    existing = await session.scalar(
        select(EventRegistration).where(
            EventRegistration.user_id == user_id,
            EventRegistration.event_id == event_id,
            EventRegistration.status == RegistrationStatus.ACTIVE,
        )
    )
    if existing is not None:
        raise DuplicateActiveRegistrationError(user_id, event_id)

    # 4. Atomic quota increment (0 rows returned → quota full)
    result = await session.execute(
        update(Event)
        .where(Event.id == event_id)
        .where(Event.current_participants < Event.quota)
        .values(current_participants=Event.current_participants + 1)
        .returning(Event.id)
    )
    if result.first() is None:
        raise QuotaFullError(event_id)

    # 5. Insert registration (partial unique index guards concurrent duplicate race)
    registration = EventRegistration(user_id=user_id, event_id=event_id)
    session.add(registration)
    try:
        await session.flush()
    except IntegrityError as exc:
        if (
            isinstance(exc.__cause__, asyncpg.exceptions.UniqueViolationError)
            and "uq_active_registration" in str(exc.__cause__)
        ):
            raise DuplicateActiveRegistrationError(user_id, event_id)
        raise

    return registration
```

### cancel() — guard sequence

```python
async def cancel(session: AsyncSession, user_id: int, event_id: int) -> None:
    # 1. Find active registration
    registration = await session.scalar(
        select(EventRegistration).where(
            EventRegistration.user_id == user_id,
            EventRegistration.event_id == event_id,
            EventRegistration.status == RegistrationStatus.ACTIVE,
        )
    )
    if registration is None:
        raise NoActiveRegistrationError(user_id, event_id)

    # 2. Check deadline (cancellation also blocked after deadline — spec clarification)
    event = await session.get(Event, event_id)
    if event.registration_deadline < datetime.now(timezone.utc):
        raise RegistrationDeadlinePassedError(event_id)

    # 3. Soft delete
    registration.status = RegistrationStatus.CANCELLED
    registration.cancelled_at = datetime.now(timezone.utc)

    # 4. Decrement counter
    await session.execute(
        update(Event)
        .where(Event.id == event_id)
        .values(current_participants=Event.current_participants - 1)
    )
    await session.flush()
```
