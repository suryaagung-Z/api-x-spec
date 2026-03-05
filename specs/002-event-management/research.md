# Research: 002-event-management

All NEEDS CLARIFICATION items resolved. Decisions finalized for Phase 1 design.

---

## 1. Pagination Pattern

**Decision**: Two-query pattern with `Page[T]` generic Pydantic model and FastAPI `Depends` parameter injection.

**Pattern**:
```python
# schemas/pagination.py
import math
from typing import Generic, TypeVar
from pydantic import BaseModel, computed_field

T = TypeVar("T")

class Page(BaseModel, Generic[T]):
    items: list[T]
    total_items: int
    page: int
    page_size: int

    @computed_field
    @property
    def total_pages(self) -> int:
        if self.page_size == 0:
            return 0
        return math.ceil(self.total_items / self.page_size)
```

```python
# api/dependencies/pagination.py
from typing import Annotated
from fastapi import Query

def pagination_params(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> tuple[int, int]:
    return page, page_size
```

```python
# Count query — strip ORDER BY before subquerying
from sqlalchemy import select, func

base_stmt = select(Event).where(...).order_by(Event.date.asc(), Event.title.asc())

count_stmt = select(func.count()).select_from(base_stmt.order_by(None).subquery())
total_items = await session.scalar(count_stmt)

data_stmt = base_stmt.offset((page - 1) * page_size).limit(page_size)
items = (await session.scalars(data_stmt)).all()
```

**Key constraint**: Do NOT use `asyncio.gather` on a single `AsyncSession`. SQLAlchemy `AsyncSession` is **not** safe for concurrent operations on the same session. Run count query first, then data query sequentially.

**Edge cases**:
- `page > total_pages` → return empty `items` list (not 404/error)
- `page_size` validated to `ge=1, le=100` via FastAPI `Query` → automatic 422 on invalid input
- `MAX_PAGE_SIZE = 100` constant enforced at dependency level

**Rationale**: Two-query is the standard approach for offset pagination with accurate total counts. Cursor-based pagination was considered but rejected — spec explicitly requires `page`/`page_size` params and `total_items`/`total_pages` in response. Keyset/cursor pagination does not expose total counts naturally.

**Alternatives considered**:
- `asyncio.gather(count, data)` — rejected (single AsyncSession not concurrent-safe per SQLAlchemy docs)
- Subquery in single query — rejected (more complex, less readable, same round-trip cost)
- Cursor-based pagination — rejected (spec requires offset-style params and total_pages)

---

## 2. Database Index Strategy

**Decision**: Composite B-tree index on `(date, title)` for public listing; separate B-tree on `(registration_deadline)` for registration feature.

**Index definitions** (in SQLAlchemy ORM):
```python
from sqlalchemy import Index

class Event(Base):
    __tablename__ = "events"
    # ... columns ...

    __table_args__ = (
        Index("ix_events_date_title", "date", "title"),
        Index("ix_events_registration_deadline", "registration_deadline"),
    )
```

**In Alembic migration**:
```python
op.create_index(
    "ix_events_date_title",
    "events",
    ["date", "title"],
    postgresql_concurrently=True,  # avoid table lock in production
)
op.create_index(
    "ix_events_registration_deadline",
    "events",
    ["registration_deadline"],
    postgresql_concurrently=True,
)
```

Note: `postgresql_concurrently=True` requires the migration to run outside a transaction block. Add `op.execute("COMMIT")` before `CREATE INDEX CONCURRENTLY` in Alembic, or configure the migration to use `non_transactional=True`.

**Why `(date, title)` composite** (not `(status, date, title)`):
- Public listing applies `WHERE date >= now()` + `ORDER BY date ASC, title ASC` — the composite covers both the range scan and eliminates the sort node (index-only traversal)
- Status filter is extremely low-cardinality (3 values) — PostgreSQL query planner often skips low-cardinality leading columns in composites; having `status` first can hurt the index for range queries on `date`
- Admin queries that need all statuses still benefit from the `(date, title)` index for sorting

**`registration_deadline` index**: Required for feature 003 — querying events where registration is still open. Created now to avoid a later migration that locks the table.

**Alternatives considered**:
- Partial index `WHERE status = 'active' AND date >= now()` — rejected (`NOW()` is `STABLE`, not `IMMUTABLE`; PostgreSQL rejects it in index predicates)
- BRIN index on `date` — rejected (BRIN is only efficient for physically ordered append-only data; events can be inserted with any date; ORDER BY needs B-tree for correct ordering)
- GIN index — not applicable (no full-text or JSONB columns now)

---

## 3. Event Deletion / Status Strategy

**Decision**: Status enum `EventStatus` (active / cancelled / deleted) with `_public_events_query()` helper as single source of truth for public visibility filtering.

**Rationale**: Directly matches spec vocabulary (`aktif/non-aktif/dihapus`). Spec Key Entities already prescribes a `status` field. Preserves FK integrity for feature 003 (registration records remain valid). Single `DELETE` endpoint → status flip to `DELETED`, no cascade, no cleanup required.

```python
import enum
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

class EventStatus(str, enum.Enum):
    ACTIVE    = "active"
    CANCELLED = "cancelled"
    DELETED   = "deleted"

class Event(Base):
    # ...
    status: Mapped[EventStatus] = mapped_column(
        SAEnum(EventStatus, name="eventstatus"),
        nullable=False,
        default=EventStatus.ACTIVE,
    )
```

```python
# services/event_service.py
from datetime import datetime, timezone

def _public_events_query():
    """Single source of truth for public event visibility. Always used for user-facing reads."""
    return (
        select(Event)
        .where(Event.status == EventStatus.ACTIVE)
        .where(Event.date >= func.now())
    )

async def admin_delete_event(session: AsyncSession, event_id: int) -> None:
    event = await session.get(Event, event_id)  # admin sees all statuses
    if event is None:
        raise EventNotFoundError(event_id)
    event.status = EventStatus.DELETED
    await session.flush()
```

**`with_loader_criteria` for relationship loads** (feature 003 readiness):
```python
from sqlalchemy.orm import with_loader_criteria

stmt = (
    select(EventRegistration)
    .where(EventRegistration.user_id == user_id)
    .options(
        with_loader_criteria(Event, Event.status == EventStatus.ACTIVE, include_aliases=True)
    )
)
```
> Note: `with_loader_criteria` applies to ORM relationship loads (lazy/selectin/joined), not to explicit `.join()` calls. Add explicit `.where(Event.status == EventStatus.ACTIVE)` for explicit joins.

**Alternatives considered**:
- Hard delete + CASCADE — rejected (destroys registration records; violates spec 003 FR-008)
- Hard delete + RESTRICT — rejected (requires multi-step deletion; violates spec 002 FR-005)
- Boolean `is_deleted` / `deleted_at` — rejected (cannot express `cancelled` state; spec explicitly names 3 states)
- Soft-delete plugins (`sqlalchemy-easy-softdelete`) — rejected (overkill; imposes `deleted_at` pattern; magic filtering; wrong semantics for 3-value enum)

---

## 4. Datetime / Timezone Handling

**Decision**: `TIMESTAMPTZ` everywhere in PostgreSQL (`DateTime(timezone=True)` in SQLAlchemy). `AwareDatetime` (Pydantic v2) for input schemas. `func.now()` for SQL comparisons. `datetime.now(timezone.utc)` for Python-side comparisons. Normalize to UTC before storage.

**SQLAlchemy ORM column type**:
```python
from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime

class Event(Base):
    date:                  Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    registration_deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at:            Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:            Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
```

**Pydantic input schema**:
```python
from pydantic import AwareDatetime, model_validator
from typing import Self

class EventCreate(BaseModel):
    title:                 str
    description:           str
    date:                  AwareDatetime   # rejects naive datetimes — 422 if naive
    registration_deadline: AwareDatetime
    quota:                 int

    @model_validator(mode="after")
    def validate_deadline_before_date(self) -> Self:
        if self.registration_deadline > self.date:
            raise ValueError("registration_deadline must be ≤ date")
        return self
```

**Service layer normalization** (normalize to UTC before persisting):
```python
from datetime import timezone

def _normalize_utc(dt: datetime) -> datetime:
    return dt.astimezone(timezone.utc)
```

**SQL filter for future events**:
```python
# Use func.now() in SQL expressions — evaluated DB-side, timezone-aware
.where(Event.date >= func.now())
```

**Python-side comparison** (e.g., `registration_closed` computed field):
```python
from datetime import datetime, timezone
return self.registration_deadline < datetime.now(timezone.utc)
```

**NEVER use**:
- `datetime.utcnow()` — deprecated in Python 3.12, always naive
- `datetime.now()` — naive (no timezone), incorrect for comparisons
- `datetime.utcnow().replace(tzinfo=timezone.utc)` — use `datetime.now(timezone.utc)` directly

**Rationale**: `TIMESTAMPTZ` in PostgreSQL stores internally as UTC and auto-converts on read to the session timezone. `AwareDatetime` enforces that clients always send timezone-aware datetimes, preventing silent incorrect UTC interpretation of naive datetimes.

**Alternatives considered**:
- `TIMESTAMP` (without timezone) — rejected (silent data loss; no timezone offset stored; ambiguous interpretation)
- Store all timestamps as Unix epoch integers — rejected (poor readability; Pydantic/SQLAlchemy have native datetime support)
- `pytz` for timezone conversion — not needed; Python 3.11 `zoneinfo` + `datetime.now(timezone.utc)` pattern is sufficient

---

## 5. `registration_closed` Computed Field

**Decision**: `@computed_field @property` on Pydantic v2 response model. Evaluated Python-side at serialization time.

```python
from pydantic import BaseModel, computed_field, ConfigDict
from datetime import datetime, timezone

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
        return self.registration_deadline < datetime.now(timezone.utc)
```

**Why Pydantic `@computed_field`** (not DB-generated column or hybrid_property):
- Works with `ConfigDict(from_attributes=True)` — maps directly from SQLAlchemy ORM objects
- Unit-testable without DB — just construct a `EventResponse` with a deadline in the past/future
- Async-safe — no additional DB round-trip needed
- Correct: `registration_closed` is a derived business-logic value, not a stored value
- `@computed_field` is included in `model.model_dump()` and JSON serialization automatically

**PostgreSQL generated column — rejected**:
```sql
-- This would fail:
registration_closed BOOLEAN GENERATED ALWAYS AS (registration_deadline < NOW()) STORED
-- ERROR: generation expression is not immutable — NOW() is STABLE, not IMMUTABLE
```
PostgreSQL generated columns require the expression to be `IMMUTABLE`. `NOW()` is `STABLE` (varies per transaction), so it cannot be used in a generated column.

**SQLAlchemy `hybrid_property` with `.expression`** — considered but deferred:
```python
from sqlalchemy.ext.hybrid import hybrid_property

class Event(Base):
    @hybrid_property
    def registration_closed(self) -> bool:
        return self.registration_deadline < datetime.now(timezone.utc)

    @registration_closed.expression
    def registration_closed(cls):
        return cls.registration_deadline < func.now()
```
This would allow `WHERE Event.registration_closed == True` in SQL queries. Not needed for current spec (FR filtering is by `date >= now()`, not `registration_closed`). **Upgrade path**: if feature 003 needs `WHERE registration_closed = true` filtering, promote to `hybrid_property`.

**Alternatives considered**:
- PostgreSQL generated column — rejected (NOW() not IMMUTABLE in generated column expressions)
- SQLAlchemy `hybrid_property` — deferred (current spec doesn't require SQL-side filtering on this field)
- Computed in repository/service layer and passed separately — rejected (more plumbing; Pydantic computed_field is cleaner and co-located with the schema)

---

## 6. Runtime / Framework

**Decision**: Same stack as 001-authentication (no new technology introduced).

| Component | Choice | Version |
|-----------|--------|---------|
| Language | Python | 3.11+ |
| HTTP framework | FastAPI | latest stable |
| ORM | SQLAlchemy async | 2.x |
| Migration | Alembic | 1.13+ |
| Validation | Pydantic v2 | 2.x (with `AwareDatetime`, `computed_field`) |
| DB (prod) | PostgreSQL | 15+ via asyncpg |
| DB (dev/test) | SQLite | via aiosqlite |
| Testing | pytest + pytest-asyncio + httpx | latest stable |
| Code quality | black + ruff + mypy | latest stable |
| Config | pydantic-settings BaseSettings | 2.x |

**Dependency on 001-authentication**: `require_role(UserRole.ADMIN)` FastAPI dependency gates all admin event endpoints. No new auth primitives needed.

---

## 7. Testing Strategy

**Decision**: Same pattern as 001-authentication — contract tests first, then integration, then unit for business logic.

| Test type | What it covers | Location |
|-----------|---------------|----------|
| Contract (httpx AsyncClient) | All 6 endpoints, status codes, response schema, pagination shape | `tests/contract/test_events_admin.py`, `test_events_public.py` |
| Integration (real DB) | Repository queries, index usage, status filtering, pagination offset math | `tests/integration/test_event_repository.py` |
| Unit (no DB/network) | `EventCreate` model_validator (deadline > date → error), `registration_closed` computed field, `_public_events_query()` helper | `tests/unit/test_event_schemas.py`, `test_event_service.py` |

**Key unit test cases**:
- `EventCreate` with `registration_deadline > date` → `ValidationError`
- `EventResponse` with past `registration_deadline` → `registration_closed == True`
- `EventResponse` with future `registration_deadline` → `registration_closed == False`
- `_public_events_query()` excludes `CANCELLED` and `DELETED` events
- `_public_events_query()` excludes past events (`date < now`)

---

## 8. Summary of All Decisions

| Topic | Decision |
|-------|----------|
| Pagination | Two-query (count + data), `Page[T]` generic, FastAPI `Depends`, strip `ORDER BY` in count subquery, sequential (not concurrent) on single AsyncSession |
| DB indexes | Composite B-tree `(date, title)` + separate `(registration_deadline)`, `postgresql_concurrently=True` in Alembic, NO partial index, NO BRIN |
| Deletion | Status enum `EventStatus` (active/cancelled/deleted), `_public_events_query()` helper, `with_loader_criteria` for relationship loads, no soft-delete plugins |
| Datetime | `TIMESTAMPTZ` + `DateTime(timezone=True)`, `AwareDatetime` for inputs, `func.now()` in SQL, `datetime.now(timezone.utc)` in Python, normalize to UTC before storage |
| `registration_closed` | Pydantic `@computed_field @property` on response model, Python-side evaluation, no DB generated column, hybrid_property deferred |
| Runtime | Python 3.11 · FastAPI · SQLAlchemy 2.x async · Alembic 1.13 · Pydantic v2 · pydantic-settings (identical to 001-authentication) |
