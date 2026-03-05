# Implementation Plan: 004-admin-reporting

**Branch**: `004-admin-reporting` | **Date**: 2026-03-05 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/004-admin-reporting/spec.md`

---

## Summary

Admin reporting feature providing two read-only endpoints — a paginated per-event statistics list and a total active events summary — accessible exclusively to users with role `admin`. Statistics (`total_registered`, `remaining_quota`) are computed at query time via SQL aggregation over existing `events` and `event_registrations` tables. No new database tables or migrations are required.

**Stack**: Python 3.11 · FastAPI · SQLAlchemy 2.x async · Pydantic v2 · pydantic-settings · asyncpg (prod) / aiosqlite (dev+test)

**Key design decisions** (full rationale in [research.md](research.md)):
1. **Single LEFT JOIN + `COUNT FILTER`** query for per-event stats eliminates N+1 (R-001).
2. **"Active event"** = `status = 'active' AND date > NOW()` — consistent with 002 public listing (R-002).
3. **Existing 002/003 indexes** are sufficient to satisfy p95 ≤ 2 s at 10,000 active events (R-006).
4. **No new ORM models or Alembic migrations** — purely read-only over existing schema (R-007).

---

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: FastAPI, SQLAlchemy 2.x async, Pydantic v2, pydantic-settings, asyncpg (prod), aiosqlite (dev/test)  
**Storage**: PostgreSQL 15+ (prod); SQLite (dev/test via aiosqlite)  
**Testing**: pytest + pytest-asyncio + httpx AsyncClient  
**Target Platform**: Linux server  
**Project Type**: web-service (HTTP API, REST)  
**Performance Goals**: SC-002 — p95 ≤ 2 s with up to 10,000 active events and proportional registrations at normal load  
**Constraints**: Admin-only access (`require_role(UserRole.ADMIN)`); no N+1 queries; `remaining_quota` displayed as-is including negative values; no Alembic migration  
**Scale/Scope**: Depends on 001-authentication (JWT, role enforcement), 002-event-management (Event entity, `EventStatus`), 003-event-registration (EventRegistration entity, `RegistrationStatus`, partial index on `event_registrations`)

---

## Constitution Check

*All gates checked post-design. Implementation plan fully compliant.*

### Gate 1 — Stack Alignment ✅
Python 3.11+ · FastAPI · SQLAlchemy 2.x async · Pydantic v2 · pydantic-settings. No new libraries introduced. All choices are mainstream and actively maintained, identical to the 001/002/003 stack.

### Gate 2 — Clean Architecture ✅
Layer boundaries consistent with 001, 002, and 003:
- **API layer** (`src/api/routers/reports.py`, `src/api/schemas/reports.py`): FastAPI route handlers, Pydantic response schemas (`EventStatItem`, `EventStatsPage`, `ReportSummaryResponse`). No business logic.
- **Application/Service layer** (`src/application/reporting_service.py`): `get_event_stats(page, size)` and `get_summary()` use-cases. Delegates DB access to repository. No framework imports beyond dependency injection.
- **Domain layer**: No new domain entities. Uses existing `EventStatus` and `RegistrationStatus` enums from `src/domain/models.py`.
- **Infrastructure layer** (`src/infrastructure/repositories/reporting_repository.py`): `ReportingRepository` with `get_event_stats_page(offset, limit) → list[EventStatRow]` and `get_total_active_events() → int`. Encapsulates the aggregate SQL query. No business logic.

Dependency direction: API → Application → Domain ← Infrastructure (inward-only). No circular dependencies.

### Gate 3 — Testing Strategy ✅
Each user story has a defined test path:
- **US1 (per-event stats)**:
  - Contract test (`GET /admin/reports/events/stats` returns 200 with `Page[EventStatItem]` shape, correct `total_registered` and `remaining_quota`)
  - Unit test (service correctly maps `EventStatRow` → `EventStatItem`, pagination math)
  - Integration test (aggregate query returns correct counts with mix of active/cancelled registrations; event with zero registrations shows `total_registered=0, remaining_quota=quota`)
- **US2 (summary)**:
  - Contract test (`GET /admin/reports/events/summary` returns `{ total_active_events: N }`)
  - Integration test (only counts events with `status='active' AND date > NOW()`; past/inactive events excluded; returns 0 when none active)
- **US3 (admin-only access)**:
  - Contract test (`401` when no token; `403` when `role=user` token; `200` when `role=admin` token)
  - No unit test needed — auth enforcement is delegated to `require_role` (already tested in 001)
- **Negative `remaining_quota`** (edge case — FR-008):
  - Integration test: event with `quota=5, total_registered=7` → `remaining_quota=-2`

Tests are non-negotiable deliverables tracked in tasks.md.

### Gate 4 — Simplicity & Observability ✅
No additional services, processes, or new database tables. Single project extension adding four files. Aggregate SQL query is a proven PostgreSQL pattern with no extra dependencies. FastAPI exception handlers propagate `UNAUTHORIZED`/`FORBIDDEN` from 001 error envelope. No new error codes are introduced. Logging follows the 001/002/003 pattern. Complexity tracking table is not required.

---

## Project Structure

### Documentation (this feature)

```text
specs/004-admin-reporting/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   ├── openapi.yaml     # Phase 1 output
│   └── error-envelope.md
└── tasks.md             # Phase 2 output (/speckit.tasks — not created by /speckit.plan)
```

### Source Code (repository root)

Extends the 001 + 002 + 003 single-project layout. No new migrations. Adds the following files:

```text
src/
├── api/
│   ├── routers/
│   │   ├── auth.py              # (existing — 001)
│   │   ├── events.py            # (existing — 002)
│   │   ├── registrations.py     # (existing — 003)
│   │   └── reports.py          # NEW — GET /admin/reports/events/stats, GET /admin/reports/events/summary
│   └── schemas/
│       ├── auth.py              # (existing — 001)
│       ├── events.py            # (existing — 002)
│       ├── pagination.py        # (existing — 002, reused)
│       ├── registrations.py     # (existing — 003)
│       └── reports.py          # NEW — EventStatItem, EventStatsPage, ReportSummaryResponse
├── application/
│   ├── auth_service.py          # (existing — 001)
│   ├── event_service.py         # (existing — 002)
│   ├── registration_service.py  # (existing — 003)
│   └── reporting_service.py    # NEW — get_event_stats, get_summary use-cases
├── domain/
│   ├── models.py                # (existing — no changes; EventStatus + RegistrationStatus reused)
│   └── exceptions.py            # (existing — no changes; no new domain exceptions)
└── infrastructure/
    ├── db/
    │   └── models.py            # (existing — no changes; Event + EventRegistration reused)
    ├── repositories/
    │   ├── user_repository.py           # (existing — 001)
    │   ├── event_repository.py          # (existing — 002)
    │   ├── registration_repository.py   # (existing — 003)
    │   └── reporting_repository.py     # NEW — aggregate query: get_event_stats_page, get_total_active_events
    └── alembic/
        └── versions/
            # No new migration for this feature

tests/
├── contract/
│   ├── test_auth.py                     # (existing — 001)
│   ├── test_events_admin.py             # (existing — 002)
│   ├── test_events_public.py            # (existing — 002)
│   ├── test_registrations.py            # (existing — 003)
│   └── test_reports.py                 # NEW — contract tests for both reporting endpoints
├── integration/
│   ├── test_event_repository.py         # (existing — 002)
│   ├── test_registration_repository.py  # (existing — 003)
│   └── test_reporting_repository.py    # NEW — aggregate query correctness, edge cases
└── unit/
    ├── test_auth_service.py             # (existing — 001)
    ├── test_event_service.py            # (existing — 002)
    ├── test_registration_service.py     # (existing — 003)
    └── test_reporting_service.py       # NEW — pagination math, row mapping, zero-count edge case
```

**Structure Decision**: Single project extension (Option 1). No frontend, no separate service. All four new files follow the same layered structure as 001/002/003.