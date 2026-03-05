# Implementation Plan: 002-event-management

**Branch**: `002-event-management` | **Date**: 2025 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/002-event-management/spec.md`

---

## Summary

Event management feature providing admin CRUD for public events and user-facing browsing with offset pagination. Admin operations (create/update/delete) are gated by RBAC from **001-authentication** (`require_role(UserRole.ADMIN)`). Deletion is a soft delete via a three-value status enum (`active`/`cancelled`/`deleted`). User listing filters to future, active events only; a `registration_closed` derived field is computed at serialization time.

**Stack**: Python 3.11 · FastAPI · SQLAlchemy 2.x async · Alembic 1.13 · Pydantic v2 · pydantic-settings · asyncpg (prod) / aiosqlite (dev+test)

---

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: FastAPI, SQLAlchemy 2.x async, Alembic 1.13, Pydantic v2 (with `AwareDatetime`, `computed_field`), pydantic-settings, asyncpg (prod), aiosqlite (dev/test)
**Storage**: PostgreSQL 15+ (prod); SQLite (dev/test via aiosqlite)
**Testing**: pytest + pytest-asyncio + httpx AsyncClient
**Target Platform**: Linux server
**Project Type**: web-service (HTTP API, REST)
**Performance Goals**: NFR-001/004 — 95% of requests respond within a few seconds at normal load (spec SC-004)
**Constraints**: Offset pagination max 100 per page; `registration_deadline ≤ date` enforced; status enum must align with spec vocabulary; future-only public listing
**Scale/Scope**: Depends on 001-authentication for RBAC; provides foundational data for 003-event-registration

---

## Constitution Check

*All gates checked. Implementation plan fully compliant.*

### Gate 1 — Stack Alignment ✅
Python 3.11+ · FastAPI · SQLAlchemy 2.x async · Alembic 1.13 · Pydantic v2 · pydantic-settings.
All libraries are mainstream, actively maintained, and consistent with 001-authentication. No new technology introduced beyond Pydantic v2 `AwareDatetime` and `computed_field` (both stable in Pydantic 2.x). No unjustified deviation.

### Gate 2 — Clean Architecture ✅
Layer boundaries maintained and consistent with 001-authentication:
- **API layer** (`src/api/routers/events.py`, `src/api/schemas/events.py`, `src/api/schemas/pagination.py`): FastAPI route handlers, Pydantic request/response models, `Depends(pagination_params)`. No business logic.
- **Application/Service layer** (`src/application/event_service.py`): Use-case orchestration, `_public_events_query()` helper, `registration_deadline ≤ date` enforcement, status transitions. Depends on domain + repository interfaces only.
- **Domain layer** (`src/domain/models.py`, `src/domain/exceptions.py`): `EventStatus` enum, domain exceptions (`EventNotFoundError`, `QuotaBelowParticipantsError`, `EventDateInPastError`). No framework imports.
- **Infrastructure layer** (`src/infrastructure/db/models.py`, `src/infrastructure/repositories/event_repository.py`): SQLAlchemy ORM `Event` model, Alembic migration, async repository. Depends inward toward domain only.

Dependency direction: API → Application → Domain ← Infrastructure (inward-only).

### Gate 3 — Testing Strategy ✅
Each user story has a defined test path:
- **US1 (admin create)**: Contract test (`POST /admin/events` 201/400/422/401/403), unit test (`EventCreate` validation: deadline > date raises `ValidationError`), integration test (repo `create_event` persists and returns correct ORM object)
- **US2 (admin update/delete)**: Contract test (`PUT /admin/events/{id}` 200/404, `DELETE /admin/events/{id}` 204/404), unit test (quota below participants → `QuotaBelowParticipantsError`), integration test (delete sets status to DELETED, event no longer appears in public query)
- **US3 (user browse)**: Contract test (`GET /events` 200 with correct `Page[EventResponse]` shape, `GET /events/{id}` 200/404), unit test (`registration_closed` computed field True/False, `_public_events_query()` excludes non-active/past events), integration test (pagination math, ordering `date ASC, title ASC`)

Tests are non-negotiable deliverables tracked in tasks.md.

### Gate 4 — Simplicity & Observability ✅
No additional services or infrastructure beyond the existing 001-authentication foundation. Single project structure. Observability via FastAPI default exception handlers + structured logging (same pattern as 001-authentication). `_public_events_query()` helper eliminates scattered filter duplication. No additional complexity entries needed.

---

## Project Structure

### Documentation (this feature)

```text
specs/002-event-management/
├── plan.md              # This file
├── research.md          # Phase 0 output (all 6 topics resolved)
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   ├── openapi.yaml     # Phase 1 output
│   └── error-envelope.md
└── tasks.md             # Phase 2 output (/speckit.tasks — not created by /speckit.plan)
```

### Source Code (repository root)

Extends the 001-authentication single-project layout. Adds the following files:

```text
src/
├── api/
│   ├── routers/
│   │   ├── auth.py           # (existing — 001)
│   │   └── events.py         # NEW — admin + public event endpoints
│   ├── schemas/
│   │   ├── auth.py           # (existing — 001)
│   │   ├── events.py         # NEW — EventCreate, EventUpdate, EventResponse
│   │   └── pagination.py     # NEW — Page[T] generic + pagination_params Depends
│   └── dependencies/
│       ├── auth.py           # (existing — 001: get_current_user, require_role)
│       └── pagination.py     # NEW — pagination_params dependency
├── application/
│   ├── auth_service.py       # (existing — 001)
│   └── event_service.py      # NEW — CRUD use-cases, _public_events_query()
├── domain/
│   ├── models.py             # EXTEND — add EventStatus enum
│   └── exceptions.py         # EXTEND — add EventNotFoundError, QuotaBelowParticipantsError, EventDateInPastError
└── infrastructure/
    ├── db/
    │   ├── base.py           # (existing)
    │   └── models.py         # EXTEND — add Event ORM model with composite index
    ├── repositories/
    │   ├── user_repository.py          # (existing — 001)
    │   └── event_repository.py         # NEW — async CRUD repository
    └── alembic/
        └── versions/
            └── xxxx_add_events_table.py  # NEW — migration with CONCURRENTLY indexes

tests/
├── contract/
│   ├── test_auth.py                # (existing — 001)
│   ├── test_events_admin.py        # NEW — admin CRUD contract tests
│   └── test_events_public.py       # NEW — public browse/detail contract tests
├── integration/
│   ├── test_user_repository.py     # (existing — 001)
│   └── test_event_repository.py    # NEW — repository + pagination integration tests
└── unit/
    ├── test_auth_service.py        # (existing — 001)
    ├── test_event_service.py       # NEW — service logic unit tests
    └── test_event_schemas.py       # NEW — Pydantic schema validation unit tests
```

**Structure Decision**: Single project (Option 1). Extends 001-authentication codebase. No separate service or sub-package needed — event management is a domain module within the same FastAPI application.

---

## Complexity Tracking

> No constitution violations. Table omitted per instructions.
