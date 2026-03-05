# Data Model: 002-event-management

---

## 1. Domain Entities

### 1.1 EventStatus Enum

```python
# src/domain/models.py
import enum

class EventStatus(str, enum.Enum):
    ACTIVE    = "active"
    CANCELLED = "cancelled"
    DELETED   = "deleted"
```

Maps directly to spec vocabulary: `aktif` → `ACTIVE`, `non-aktif` → `CANCELLED`, `dihapus` → `DELETED`.

---

### 1.2 Event Entity

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `id` | `int` | PK, auto-increment | Surrogate key |
| `title` | `str` | NOT NULL, max 255 | Event title |
| `description` | `str` | NOT NULL | Full description, no length limit |
| `date` | `datetime (TIMESTAMPTZ)` | NOT NULL | Event date/time; must be future on create |
| `registration_deadline` | `datetime (TIMESTAMPTZ)` | NOT NULL | Must be ≤ `date` (FR-012) |
| `quota` | `int` | NOT NULL, ≥ 1 | Max participants; on update ≥ current participant count |
| `status` | `EventStatus` | NOT NULL, default `active` | Three-value enum for soft-delete |
| `created_at` | `datetime (TIMESTAMPTZ)` | NOT NULL, server_default NOW() | Audit field |
| `updated_at` | `datetime (TIMESTAMPTZ)` | NOT NULL, server_default NOW(), onupdate NOW() | Audit field |

**Derived field** (not stored):
| Field | Type | Computed from | Notes |
|-------|------|---------------|-------|
| `registration_closed` | `bool` | `registration_deadline < datetime.now(UTC)` | Pydantic `@computed_field` on response schema |

---

### 1.3 EventRegistration (Reference — owned by 003-event-registration)

Not defined in this feature. Referenced here for FK context only.

| Field | Type | Notes |
|-------|------|-------|
| `event_id` | `int` | FK → `events.id` (NOT CASCADE DELETE — event uses soft delete) |
| `user_id` | `int` | FK → `users.id` |

---

## 2. SQLAlchemy ORM Model

```python
# src/infrastructure/db/models.py (additions)
from datetime import datetime
from sqlalchemy import DateTime, Enum as SAEnum, Index, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from src.domain.models import EventStatus

class Event(Base):
    __tablename__ = "events"

    id:                    Mapped[int]         = mapped_column(Integer, primary_key=True, autoincrement=True)
    title:                 Mapped[str]         = mapped_column(String(255), nullable=False)
    description:           Mapped[str]         = mapped_column(Text, nullable=False)
    date:                  Mapped[datetime]    = mapped_column(DateTime(timezone=True), nullable=False)
    registration_deadline: Mapped[datetime]    = mapped_column(DateTime(timezone=True), nullable=False)
    quota:                 Mapped[int]         = mapped_column(Integer, nullable=False)
    status:                Mapped[EventStatus] = mapped_column(
                               SAEnum(EventStatus, name="eventstatus"),
                               nullable=False,
                               default=EventStatus.ACTIVE,
                           )
    created_at:            Mapped[datetime]    = mapped_column(
                               DateTime(timezone=True),
                               nullable=False,
                               server_default=func.now(),
                           )
    updated_at:            Mapped[datetime]    = mapped_column(
                               DateTime(timezone=True),
                               nullable=False,
                               server_default=func.now(),
                               onupdate=func.now(),
                           )

    __table_args__ = (
        Index("ix_events_date_title", "date", "title"),
        Index("ix_events_registration_deadline", "registration_deadline"),
    )
```

---

## 3. SQL Schema (reference)

```sql
CREATE TYPE eventstatus AS ENUM ('active', 'cancelled', 'deleted');

CREATE TABLE events (
    id                    SERIAL PRIMARY KEY,
    title                 VARCHAR(255)  NOT NULL,
    description           TEXT          NOT NULL,
    date                  TIMESTAMPTZ   NOT NULL,
    registration_deadline TIMESTAMPTZ   NOT NULL,
    quota                 INTEGER       NOT NULL,
    status                eventstatus   NOT NULL DEFAULT 'active',
    created_at            TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at            TIMESTAMPTZ   NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_quota_positive        CHECK (quota >= 1),
    CONSTRAINT chk_deadline_before_date  CHECK (registration_deadline <= date)
);

-- Primary public listing index: covers WHERE date >= X ORDER BY date, title
CREATE INDEX CONCURRENTLY ix_events_date_title
    ON events (date ASC, title ASC);

-- For feature 003 registration deadline queries
CREATE INDEX CONCURRENTLY ix_events_registration_deadline
    ON events (registration_deadline);
```

> **Note**: The `CHECK (registration_deadline <= date)` DB constraint is a safety net. The primary enforcement is in the Pydantic `model_validator` at the API layer (returns 422 with a clear message before reaching the DB).

---

## 4. Pydantic Schemas

### 4.1 EventCreate

```python
# src/api/schemas/events.py
from pydantic import AwareDatetime, BaseModel, Field, model_validator
from typing import Self

class EventCreate(BaseModel):
    title:                 str           = Field(..., min_length=1, max_length=255)
    description:           str           = Field(..., min_length=1)
    date:                  AwareDatetime  # rejects naive datetime → 422
    registration_deadline: AwareDatetime
    quota:                 int           = Field(..., ge=1)

    @model_validator(mode="after")
    def validate_deadline_before_date(self) -> Self:
        if self.registration_deadline > self.date:
            raise ValueError(
                "registration_deadline must be on or before the event date"
            )
        return self
```

### 4.2 EventUpdate

```python
from pydantic import AwareDatetime, BaseModel, Field, model_validator
from typing import Self

class EventUpdate(BaseModel):
    title:                 str | None           = Field(None, min_length=1, max_length=255)
    description:           str | None           = Field(None, min_length=1)
    date:                  AwareDatetime | None = None
    registration_deadline: AwareDatetime | None = None
    quota:                 int | None           = Field(None, ge=1)

    @model_validator(mode="after")
    def validate_deadline_before_date(self) -> Self:
        if self.registration_deadline is not None and self.date is not None:
            if self.registration_deadline > self.date:
                raise ValueError(
                    "registration_deadline must be on or before the event date"
                )
        return self
```

> **Service layer responsibility**: When only one of `date`/`registration_deadline` is provided in the update, the service must load the current event and cross-check with the stored value before persisting.

### 4.3 EventResponse

```python
from datetime import datetime, timezone
from pydantic import BaseModel, ConfigDict, computed_field
from src.domain.models import EventStatus

class EventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:                    int
    title:                 str
    description:           str
    date:                  datetime
    registration_deadline: datetime
    quota:                 int
    status:                EventStatus
    created_at:            datetime

    @computed_field
    @property
    def registration_closed(self) -> bool:
        """True if registration_deadline is in the past relative to UTC now."""
        return self.registration_deadline < datetime.now(timezone.utc)
```

> `registration_closed` is included automatically in `model.model_dump()` and JSON serialization. No additional serialization configuration needed.

### 4.4 Page[EventResponse] (pagination wrapper)

```python
# src/api/schemas/pagination.py
import math
from typing import Generic, TypeVar
from pydantic import BaseModel, computed_field

T = TypeVar("T")

class Page(BaseModel, Generic[T]):
    items:       list[T]
    total_items: int
    page:        int
    page_size:   int

    @computed_field
    @property
    def total_pages(self) -> int:
        if self.page_size == 0:
            return 0
        return math.ceil(self.total_items / self.page_size)
```

Usage: `Page[EventResponse]` — resolved automatically by FastAPI/Pydantic for `response_model`.

---

## 5. Domain Exceptions

All exceptions defined in `src/domain/exceptions.py`. No framework imports.

```python
# src/domain/exceptions.py (additions)

class EventNotFoundError(Exception):
    """Raised when an event cannot be found (by ID) or is not publicly accessible."""
    def __init__(self, event_id: int) -> None:
        self.event_id = event_id
        super().__init__(f"Event {event_id} not found")

class QuotaBelowParticipantsError(Exception):
    """Raised when an update would set quota below the current participant count."""
    def __init__(self, event_id: int, requested_quota: int, participant_count: int) -> None:
        self.event_id = event_id
        self.requested_quota = requested_quota
        self.participant_count = participant_count
        super().__init__(
            f"Cannot set quota to {requested_quota}; event {event_id} already has {participant_count} participants"
        )

class EventDateInPastError(Exception):
    """Raised when an event date is set in the past on create (business rule, not Pydantic validation)."""
    def __init__(self, event_id: int | None = None) -> None:
        super().__init__("Event date must be in the future")
```

### Exception → HTTP Status Mapping

| Domain Exception | HTTP Status | Error Code |
|-----------------|-------------|------------|
| `EventNotFoundError` | 404 Not Found | `EVENT_NOT_FOUND` |
| `QuotaBelowParticipantsError` | 409 Conflict | `QUOTA_BELOW_PARTICIPANTS` |
| `EventDateInPastError` | 422 Unprocessable Entity | `INVALID_DATE_RANGE` |
| `EventCreate`/`EventUpdate` ValidationError (Pydantic) | 422 Unprocessable Entity | `VALIDATION_ERROR` |

---

## 6. State Transitions

```text
                  ┌──────────┐
       (create)   │          │
   ──────────────►│  ACTIVE  │
                  │          │
                  └─────┬────┘
                        │ admin cancel
                        ▼
                  ┌──────────┐
                  │CANCELLED │
                  └─────┬────┘
                        │
          admin delete   │   admin delete
        (from any state) ▼
                  ┌──────────┐
                  │ DELETED  │
                  └──────────┘
```

- Only `ACTIVE` events appear in public listing / detail endpoints
- `CANCELLED` events are visible to admin (omitted from public)
- `DELETED` events are invisible everywhere (treated as non-existent for users and for feature 003 registration)
- Transitions are one-directional: `DELETED` cannot be restored (by current spec — service can be extended if needed)
