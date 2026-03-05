# Data Model: 004-admin-reporting

**Phase**: 1 — Design  
**Date**: 2026-03-05  
**Source**: [spec.md](spec.md) §Key Entities + §Requirements + [research.md](research.md)

---

## 1. Domain Entities

### 1.1 Existing Entities Used (Read-Only)

This feature introduces **no new domain entities**. It is a read-only reporting layer over entities defined in previous features:

| Entity | Defined In | Fields Used |
|--------|-----------|-------------|
| `Event` | 002-event-management | `id`, `title`, `date`, `quota`, `status` |
| `EventRegistration` | 003-event-registration | `event_id`, `status` |
| `EventStatus` | 002-event-management | `ACTIVE` (`'active'`) |
| `RegistrationStatus` | 003-event-registration | `ACTIVE` (`'active'`) |

---

### 1.2 Query Result Shapes (Not Persisted)

These are **plain Python dataclasses** used to transfer aggregate query results from the infrastructure layer to the application layer. They are not ORM models and are not persisted.

#### EventStatRow

Represents one row returned from the per-event aggregate query.

| Field | Type | Source |
|-------|------|--------|
| `id` | `int` | `events.id` |
| `title` | `str` | `events.title` |
| `date` | `datetime` | `events.date` |
| `quota` | `int` | `events.quota` |
| `total_registered` | `int` | `COUNT(er.id) FILTER (WHERE er.status = 'active')` |
| `remaining_quota` | `int` | `quota - total_registered` (may be negative) |

```python
# src/infrastructure/repositories/reporting_repository.py
from dataclasses import dataclass
from datetime import datetime

@dataclass(frozen=True)
class EventStatRow:
    id:                int
    title:             str
    date:              datetime
    quota:             int
    total_registered:  int
    remaining_quota:   int
```

---

## 2. Aggregate Query

### 2.1 Per-Event Stats Query

Returns paginated list of active events with aggregated registration counts. "Active" is defined as: `status = 'active' AND date > NOW()` (consistent with FR-001, spec clarification, and 002 public listing filter).

```sql
-- Per-event stats (paginated)
SELECT
    e.id,
    e.title,
    e.date,
    e.quota,
    COUNT(er.id) FILTER (WHERE er.status = 'active')              AS total_registered,
    e.quota - COUNT(er.id) FILTER (WHERE er.status = 'active')    AS remaining_quota
FROM events e
LEFT JOIN event_registrations er ON er.event_id = e.id
WHERE e.status = 'active'
  AND e.date > NOW()
GROUP BY e.id
ORDER BY e.date ASC, e.id ASC
LIMIT :limit OFFSET :offset;

-- Total row count (for pagination metadata)
SELECT COUNT(*)
FROM events
WHERE status = 'active'
  AND date > NOW();
```

**SQLAlchemy 2.x ORM equivalent**:

```python
# src/infrastructure/repositories/reporting_repository.py
from datetime import datetime, timezone
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from src.infrastructure.db.models import Event, EventRegistration
from src.domain.models import EventStatus, RegistrationStatus

async def get_event_stats_page(
    session: AsyncSession,
    offset: int,
    limit: int,
) -> tuple[list[EventStatRow], int]:
    now = datetime.now(timezone.utc)

    active_reg_count = (
        func.count(EventRegistration.id)
        .filter(EventRegistration.status == RegistrationStatus.ACTIVE)
    )

    stats_query = (
        select(
            Event.id,
            Event.title,
            Event.date,
            Event.quota,
            active_reg_count.label("total_registered"),
            (Event.quota - active_reg_count).label("remaining_quota"),
        )
        .outerjoin(EventRegistration, EventRegistration.event_id == Event.id)
        .where(Event.status == EventStatus.ACTIVE, Event.date > now)
        .group_by(Event.id)
        .order_by(Event.date.asc(), Event.id.asc())
        .offset(offset)
        .limit(limit)
    )

    count_query = (
        select(func.count())
        .select_from(Event)
        .where(Event.status == EventStatus.ACTIVE, Event.date > now)
    )

    rows  = (await session.execute(stats_query)).all()
    total = (await session.execute(count_query)).scalar_one()

    return [
        EventStatRow(
            id=r.id,
            title=r.title,
            date=r.date,
            quota=r.quota,
            total_registered=r.total_registered,
            remaining_quota=r.remaining_quota,
        )
        for r in rows
    ], total
```

### 2.2 Summary Query

```sql
-- Total active events (scalar)
SELECT COUNT(*)
FROM events
WHERE status = 'active'
  AND date > NOW();
```

```python
async def get_total_active_events(session: AsyncSession) -> int:
    now = datetime.now(timezone.utc)
    result = await session.execute(
        select(func.count())
        .select_from(Event)
        .where(Event.status == EventStatus.ACTIVE, Event.date > now)
    )
    return result.scalar_one()
```

---

## 3. Index Analysis

No new indexes or migrations are needed. The required indexes exist from prior features:

| Index | Created In | Covers |
|-------|-----------|--------|
| `ix_events_status_date` | 002-event-management | `events(status, date)` — filters active + future events |
| `ix_event_registrations_event_active` | 003-event-registration | `event_registrations(event_id) WHERE status = 'active'` — partial index for conditional COUNT |
| `events.id` (PK) | 002-event-management | `GROUP BY e.id` |

With these indexes the aggregate query performs an index range scan on `events` for the active/future filter, then a partial index lookup on `event_registrations` per event. At 10,000 active events with max 100 rows returned per page, p95 ≤ 2 s is well within reach on PostgreSQL 15+.

---

## 4. API Response Models (Pydantic)

```python
# src/api/schemas/reports.py
from datetime import datetime
from pydantic import BaseModel, Field
from src.api.schemas.pagination import Page

class EventStatItem(BaseModel):
    id:                int
    title:             str
    date:              datetime
    quota:             int
    total_registered:  int      = Field(ge=0, description="Active registrations for this event")
    remaining_quota:   int      = Field(description="quota - total_registered; may be negative")

    model_config = {"from_attributes": True}

class ReportSummaryResponse(BaseModel):
    total_active_events: int = Field(ge=0)

# EventStatsPage is Page[EventStatItem] — reuses the generic Page[T] from pagination.py
EventStatsPage = Page[EventStatItem]
```

---

## 5. Validation Rules

| Rule | Source | Enforcement |
|------|--------|-------------|
| Only `role=admin` may access reporting endpoints | FR-004, US3 | `require_role(UserRole.ADMIN)` FastAPI dependency |
| `total_registered` counts only `status='active'` registrations | FR-006 | `COUNT FILTER (WHERE er.status = 'active')` in SQL |
| `remaining_quota` is raw (`quota - total_registered`), no clamp | FR-008 | Computed in SQL; `int` type in response, no `ge=0` constraint |
| "Active event" = `status='active' AND date > NOW()` | FR-001, FR-002, spec clarification | WHERE clause in both aggregate and summary queries |

---

## 6. Relationships (Reference)

```
User (001)
  └── role: UserRole  ──── enforces admin access to /admin/reports/...

Event (002)
  ├── id ──────────────── GROUP BY target in per-event stats query
  ├── status (EventStatus) ── WHERE status = 'active'
  ├── date ────────────── WHERE date > NOW()
  └── quota ───────────── used in remaining_quota calculation

EventRegistration (003)
  ├── event_id ────────── LEFT JOIN events.id
  └── status (RegistrationStatus) ── COUNT FILTER (WHERE status = 'active')
```
