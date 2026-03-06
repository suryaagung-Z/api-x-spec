# Implementation Plan: 003-event-registration

**Branch**: `003-event-registration` | **Date**: 2026-03-05 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/003-event-registration/spec.md`

---

## Summary

Event registration feature that allows authenticated users to register for public events and cancel their registrations. Enforces quota, deadline, and duplicate-prevention rules with correctness under concurrent requests. Provides a "my registrations" list endpoint. All state transitions are soft-delete (no hard deletes).

**Stack**: Python 3.11 · FastAPI · SQLAlchemy 2.x async · Alembic 1.13 · Pydantic v2 · pydantic-settings · asyncpg (prod) / aiosqlite (dev+test)

**Key concerns**:
1. **Concurrency safety**: denormalized `current_participants` counter on `Event` with atomic `UPDATE … WHERE current_participants < quota RETURNING id` prevents overbooking structurally.
2. **Re-registration after cancellation**: partial unique index on `(user_id, event_id) WHERE status = 'active'` allows cancelled users to re-register — no `cancelled` row blocks a new `active` row.

---

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: FastAPI, SQLAlchemy 2.x async, Alembic 1.13, Pydantic v2, pydantic-settings, asyncpg (prod), aiosqlite (dev/test)
**Storage**: PostgreSQL 15+ (prod); SQLite (dev/test via aiosqlite)
**Testing**: pytest + pytest-asyncio + httpx AsyncClient
**Target Platform**: Linux server
**Project Type**: web-service (HTTP API, REST)
**Performance Goals**: SC-004 — no overbooking under parallel registrations; individual registration/cancellation request **p95 < 300ms** at expected concurrent load (non-blocking aspiration; no load test required for MVP, but implementation MUST NOT introduce unnecessary blocking I/O)
**Constraints**: Quota never exceeded (even under concurrency); `registration_deadline` enforced for both registration and cancellation; soft delete only; user can only see own registrations
**Scale/Scope**: Depends on 001-authentication (user identity, JWT) and 002-event-management (Event entity, EventStatus, EventNotFoundError)
**Cross-Feature Schema Impact**: This feature adds `current_participants` (INTEGER, NOT NULL DEFAULT 0) to the `events` table originally defined in 002-event-management. This is a backward-compatible additive change; no 002 behavior is removed or altered. The column is introduced by migration T006 (`yyyy_add_event_registrations_table.py`) with a safe DEFAULT so existing rows are not broken.

---

## Constitution Check

*All gates checked. Implementation plan fully compliant.*

### Gate 1 — Stack Alignment ✅
Python 3.11+ · FastAPI · SQLAlchemy 2.x async · Alembic 1.13 · Pydantic v2 · pydantic-settings.
No new libraries introduced. All choices are mainstream and actively maintained. asyncpg concurrency behavior (row-level locking via atomic UPDATE) is well-documented and widely used.
**Formatter**: black · **Linter**: ruff (extends the 001/002 toolchain; formatting and lint enforcement is tracked in T029).

### Gate 2 — Clean Architecture ✅
Layer boundaries consistent with 001 and 002:
- **API layer** (`src/api/routers/registrations.py`, `src/api/schemas/registrations.py`): FastAPI route handlers, Pydantic request/response schemas. No business logic.
- **Application/Service layer** (`src/application/registration_service.py`): `register`, `cancel`, `get_my_registrations` use-cases. All quota/deadline/duplicate guards live here. Depends only on domain + repository.
- **Domain layer** (`src/domain/models.py` extend, `src/domain/exceptions.py` extend): `RegistrationStatus` enum, new domain exceptions. No framework imports.
- **Infrastructure layer** (`src/infrastructure/db/models.py` extend, `src/infrastructure/repositories/registration_repository.py`): `EventRegistration` ORM model with partial unique index, Alembic migrations (add `current_participants` to `events`, add `event_registrations` table).

Dependency direction: API → Application → Domain ← Infrastructure (inward-only).

### Gate 3 — Testing Strategy ✅
Each user story has a defined test path:
- **US1 (register)**: Contract test (`POST /registrations/{event_id}` all status codes), unit test (deadline/quota/duplicate logic), integration test (counter increments, partial unique index behaviour)
- **US2 (rejection scenarios)**: Contract test (event not found 404, deadline passed 422, quota full 422, duplicate 409), unit test for each rejection path in service layer
- **US3 (cancel + re-register)**: Contract test (`DELETE /registrations/{event_id}`, `GET /registrations/me`), unit test (cancel guard: no active reg, deadline check), integration test (counter decrements, re-registration creates new row)
- **Concurrent test** (SC-004): asyncio gather N concurrent register requests to quota=1 event — assert exactly 1 success, N-1 get 422, `current_participants == 1`

Tests are non-negotiable deliverables tracked in tasks.md.

### Gate 4 — Simplicity & Observability ✅
No additional services or processes. Single project extension. Complexity introduced (atomic UPDATE, partial unique index) is proven PostgreSQL pattern with zero extra dependencies. FastAPI exception handlers map all domain exceptions to error envelope. Logging follows 001/002 pattern. No new technology beyond existing stack.

---

## Project Structure

### Documentation (this feature)

```text
specs/003-event-registration/
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

Extends the 001 + 002 single-project layout. Adds / extends the following files:

```text
src/
├── api/
│   ├── routers/
│   │   ├── auth.py              # (existing — 001)
│   │   ├── events.py            # (existing — 002)
│   │   └── registrations.py    # NEW — POST/DELETE /registrations/{event_id}, GET /registrations/me
│   └── schemas/
│       ├── auth.py              # (existing — 001)
│       ├── events.py            # (existing — 002)
│       ├── pagination.py        # (existing — 002)
│       └── registrations.py    # NEW — RegisterResponse, RegistrationWithEventResponse, EventSummary
├── application/
│   ├── auth_service.py          # (existing — 001)
│   ├── event_service.py         # (existing — 002)
│   └── registration_service.py # NEW — register, cancel, get_my_registrations use-cases
├── domain/
│   ├── models.py                # EXTEND — add RegistrationStatus enum
│   └── exceptions.py            # EXTEND — add QuotaFullError, DuplicateActiveRegistrationError, NoActiveRegistrationError, RegistrationDeadlinePassedError
└── infrastructure/
    ├── db/
    │   └── models.py            # EXTEND — add EventRegistration ORM model; add current_participants to Event
    ├── repositories/
    │   ├── user_repository.py           # (existing — 001)
    │   ├── event_repository.py          # (existing — 002)
    │   └── registration_repository.py  # NEW — async repository for EventRegistration
    └── alembic/
        └── versions/
            ├── xxxx_add_events_table.py               # (existing — 002)
            └── yyyy_add_event_registrations_table.py  # NEW — event_registrations table + current_participants column on events

tests/
├── contract/
│   ├── test_auth.py                     # (existing — 001)
│   ├── test_events_admin.py             # (existing — 002)
│   ├── test_events_public.py            # (existing — 002)
│   └── test_registrations.py           # NEW — all registration endpoint contract tests
├── integration/
│   ├── test_user_repository.py          # (existing — 001)
│   ├── test_event_repository.py         # (existing — 002)
│   └── test_registration_repository.py # NEW — repo integration tests
└── unit/
    ├── test_auth_service.py             # (existing — 001)
    ├── test_event_service.py            # (existing — 002)
    ├── test_event_schemas.py            # (existing — 002)
    └── test_registration_service.py    # NEW — service unit tests (guards, status transitions)
```

**Structure Decision**: Single project (Option 1). Extends 001 + 002 codebase. No new service or sub-package. Event registration is a domain module within the same FastAPI application.

---

## Complexity Tracking

> No constitution violations. Table omitted per instructions.
