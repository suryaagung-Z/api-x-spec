# Tasks: 002-event-management

**Input**: Design documents from `specs/002-event-management/`
**Prerequisites**: plan.md ✅ · spec.md ✅ · research.md ✅ · data-model.md ✅ · contracts/ ✅

**Total tasks**: 31 (T001–T031)
**User story breakdown**: US1 → 8 tasks (T007–T014) · US2 → 5 tasks (T015–T019) · US3 → 6 tasks (T020–T025) · Setup/Foundation → 6 tasks (T001–T006) · Polish → 6 tasks (T026–T031)

**Format**: `- [ ] [ID] [P?] [Story?] Description — file path`
- `[P]` = can run in parallel (different files, no blocking dependency)
- `[US1]`/`[US2]`/`[US3]` = user story label (story phases only)

---

## Phase 1: Setup

**Purpose**: Create directory/file stubs for the new modules so parallel work can begin immediately.

- [ ] T001 Create new feature directories per plan.md structure: `src/api/schemas/`, `src/api/dependencies/`, `src/application/`, `src/infrastructure/repositories/`, `tests/contract/`, `tests/integration/`, `tests/unit/`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that must be complete before any user story can be implemented. These touch shared files and must be done sequentially relative to each other.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T002 [P] Add `EventStatus` enum (`ACTIVE`, `DELETED`) to `src/domain/models.py`
- [ ] T003 [P] Add domain exceptions `EventNotFoundError`, `QuotaBelowParticipantsError`, `EventDateInPastError` to `src/domain/exceptions.py`
- [ ] T004 Add `Event` ORM model with `DateTime(timezone=True)` columns, `SAEnum(EventStatus)`, and `__table_args__` composite index `ix_events_date_title` + `ix_events_registration_deadline` to `src/infrastructure/db/models.py`
- [ ] T005 Create Alembic migration for `events` table and `eventstatus` enum; create both indexes using `op.execute("CREATE INDEX CONCURRENTLY ...")` inside `op.get_context().autocommit_block()` (not `create_index(postgresql_concurrently=True)` which fails inside a transaction) in `src/infrastructure/alembic/versions/xxxx_add_events_table.py`
- [ ] T006 Register events router prefix `/admin/events` and `/events` in the FastAPI application entry point (e.g., `src/main.py` or `src/app.py`)

**Checkpoint**: `Event` ORM model importable, migration runs cleanly, router prefix registered — user story phases may now proceed.

---

## Phase 3: User Story 1 — Admin membuat event publik baru (Priority: P1) 🎯 MVP

**Goal**: Admin can `POST /admin/events` with all required fields. Created event is stored with status `ACTIVE` and appears in the public listing (covered by US3). Response includes `registration_closed` derived flag.

**Independent Test**: Call `POST /admin/events` with a valid admin JWT and valid body → assert 201 + `EventResponse` shape. Call `GET /events` with a user token → assert the new event appears. Call `POST /admin/events` with `registration_deadline > date` → assert 422.

### Tests for User Story 1 ⚠️

- [ ] T007 [P] [US1] Write unit tests for: (1) `EventCreate.validate_deadline_before_date` model_validator (deadline > date → `ValidationError`, deadline == date → valid) in `tests/unit/test_event_schemas.py`; (2) `create_event` service raises `EventDateInPastError` when `date` is in the past — FR-013 service-level guard (mirrors T015 pattern for `QuotaBelowParticipantsError`) in `tests/unit/test_event_service.py`
- [ ] T008 [P] [US1] Write contract tests for `POST /admin/events`: 201 with valid body, 422 for deadline > date, 422 for `date` in past (FR-013), 422 for missing fields, 422 for naive datetime, 401 without token, 403 with non-admin token in `tests/contract/test_events_admin.py`

### Implementation for User Story 1

- [ ] T009 [P] [US1] Implement `Page[T]` generic model with `@computed_field total_pages` in `src/api/schemas/pagination.py` and `pagination_params` FastAPI dependency (`page`, `page_size` with `ge=1`, `le=100`) in `src/api/dependencies/pagination.py`
- [ ] T010 [US1] Implement `EventCreate` (with `AwareDatetime`, `model_validator` for deadline ≤ date), `EventUpdate` (all fields `Optional`), and `EventResponse` (with `@computed_field registration_closed`) Pydantic schemas in `src/api/schemas/events.py`
- [ ] T011 [US1] Implement `EventRepository.create` method (persists `Event` ORM, returns ORM object after `flush`) in `src/infrastructure/repositories/event_repository.py`
- [ ] T012 [US1] Implement `_public_events_query()` helper and `create_event` use-case (normalize datetimes to UTC, raise `EventDateInPastError` if `date` is in the past per FR-013, call `EventRepository.create`) in `src/application/event_service.py`
- [ ] T013 [US1] Implement `POST /admin/events` endpoint (depends on `require_role(UserRole.ADMIN)` from 001-auth, calls `event_service.create_event`, returns 201) in `src/api/routers/events.py`
- [ ] T014 [US1] Register FastAPI exception handlers for `EventNotFoundError` → 404, `QuotaBelowParticipantsError` → 409, `EventDateInPastError` → 422 using the error envelope `{"error": {"code", "message", "httpStatus"}}` format in `src/main.py` (or wherever auth exception handlers live)

**Checkpoint**: `POST /admin/events` returns 201 with correct `EventResponse`. Validation errors return 422. Auth errors return 401/403. All T007–T008 tests pass.

---

## Phase 4: User Story 2 — Admin mengelola event yang sudah memiliki peserta (Priority: P1)

**Goal**: Admin can `GET /admin/events/{id}` (any status), `PUT /admin/events/{id}` (partial update, quota ≥ participants enforced), and `DELETE /admin/events/{id}` (soft delete → status `DELETED`, 204). All endpoints require ADMIN role.

**Independent Test**: Create an event (US1). Then: (1) `GET /admin/events/{id}` → assert 200. (2) `PUT /admin/events/{id}` with valid changes → assert 200 + updated fields. (3) `PUT` with quota below current participants (simulate by setting a stub participant count or reaching into the DB) → assert 409. (4) `DELETE /admin/events/{id}` → assert 204. (5) `GET /admin/events/{id}` after delete → assert event status is `deleted`. (6) `GET /events/{id}` after delete → assert 404 (deleted events hidden from public).

### Tests for User Story 2 ⚠️

- [ ] T015 [P] [US2] Write unit tests for `update_event` quota-protection logic: quota update below participant count → raises `QuotaBelowParticipantsError`; quota update ≥ participant count → succeeds in `tests/unit/test_event_service.py`
- [ ] T016 [P] [US2] Write contract tests for `GET /admin/events/{id}` (200/404/401/403), `PUT /admin/events/{id}` (200/404/409/422/401/403), `DELETE /admin/events/{id}` (204/404/401/403) in `tests/contract/test_events_admin.py`

### Implementation for User Story 2

- [ ] T017 [P] [US2] Implement `EventRepository.get_by_id_admin` (no status filter), `update` (apply partial dict, `flush`), and `soft_delete` (set `status = EventStatus.DELETED`, `flush`) methods in `src/infrastructure/repositories/event_repository.py`
- [ ] T018 [US2] Implement `get_event_admin`, `update_event` (load event, merge update fields, cross-validate deadline ≤ date using stored values for missing partial fields, check quota ≥ participant count), and `delete_event` (soft delete) use-cases in `src/application/event_service.py`
- [ ] T019 [US2] Implement `GET /admin/events/{id}`, `PUT /admin/events/{id}`, and `DELETE /admin/events/{id}` endpoints (all require `require_role(UserRole.ADMIN)`) in `src/api/routers/events.py`

**Checkpoint**: All admin CRUD endpoints functional (201/200/204). Quota protection returns 409. Soft delete hides event from public. All T015–T016 tests pass.

---

## Phase 5: User Story 3 — User menelusuri dan melihat daftar event publik (Priority: P2)

**Goal**: `GET /events` returns paginated, future-only, active events ordered `date ASC, title ASC`. Response is `Page[EventResponse]` with `total_items`, `total_pages`, `registration_closed` on each item. `GET /events/{id}` returns a single active event or 404. No authentication required.

**Independent Test**: Seed events (past, active future, deleted). Call `GET /events?page=1&page_size=2` → assert only future+active events appear, shape is `Page[EventResponse]`, `total_pages` is correct. Advance to page 2 → assert no duplication/gap. Call `GET /events/{id}` for active event → 200. Call for deleted event → 404.

### Tests for User Story 3 ⚠️

- [ ] T020 [P] [US3] Write unit tests for `_public_events_query()` (excludes `DELETED` and past events) and `EventResponse.registration_closed` computed field (`deadline` in past → `True`, `deadline` in future → `False`) in `tests/unit/test_event_service.py` and `tests/unit/test_event_schemas.py`
- [ ] T021 [P] [US3] Write contract tests for `GET /events` (200 with correct `Page[EventResponse]` shape, future-only filter, `registration_closed` present, 422 for invalid `page_size`), `GET /events?page=999` (200 with empty `items`), and `GET /events/{id}` (200 / 404 for deleted or non-existent) in `tests/contract/test_events_public.py`
- [ ] T022 [P] [US3] Write integration tests for repository public listing: ordering by `date ASC, title ASC`, past events excluded, DELETED events excluded, pagination offset math (page 2 returns correct slice), `count_public` matches `len(all_public_events)` in `tests/integration/test_event_repository.py`

### Implementation for User Story 3

- [ ] T023 [P] [US3] Implement `EventRepository.list_public` (two-query pattern: `count_stmt = select(func.count()).select_from(base.order_by(None).subquery())`; `data_stmt` with `.offset().limit()`) and `EventRepository.get_public_by_id` in `src/infrastructure/repositories/event_repository.py`
- [ ] T024 [US3] Implement `list_public_events` use-case (calls repository, assembles `Page[EventResponse]`) and `get_public_event` use-case (raises `EventNotFoundError` if None) in `src/application/event_service.py`
- [ ] T025 [US3] Implement `GET /events` (uses `Depends(pagination_params)`, returns `Page[EventResponse]`, no auth required) and `GET /events/{id}` (returns `EventResponse`, no auth required, 404 on missing/DELETED) in `src/api/routers/events.py`

**Checkpoint**: Full public browse flow works. Pagination consistent across pages. Past and DELETED events invisible to public. `registration_closed` flag correct. All T020–T022 tests pass.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T026 [P] Run `black --check` and `ruff check` on all new modules; run `mypy --strict` on (`src/api/schemas/events.py`, `src/api/schemas/pagination.py`, `src/api/dependencies/pagination.py`, `src/application/event_service.py`, `src/infrastructure/repositories/event_repository.py`); fix all formatting, linting, and type errors
- [ ] T027 [P] Verify FR-009 edge case: seed an event with `registration_deadline` in the past but `date` in the future → assert `GET /events` includes it and `registration_closed == true` — add or extend `tests/unit/test_event_schemas.py`
- [ ] T028 [P] Verify extreme pagination edge case: `GET /events?page=9999` → 200 with `items: []`, `total_pages` correct, no 500 — add assertion to `tests/contract/test_events_public.py`
- [ ] T029 [P] Verify `EventUpdate` partial-update cross-validation: only `date` supplied → service loads stored `registration_deadline` and checks deadline ≤ new date; only `registration_deadline` supplied → service loads stored `date` and checks — add unit test to `tests/unit/test_event_service.py`
- [ ] T030 Run full test suite (`pytest tests/`) and confirm all 002-event-management tests pass with no regressions in 001-authentication tests
- [ ] T031 [P] Add a performance benchmark for `GET /events` with a representative seeded dataset (hundreds of active events) asserting p95 < 1000 ms (NFR-001 / SC-004) in `tests/integration/test_event_performance.py` using `pytest-benchmark` or equivalent

---

## Dependencies (Story Completion Order)

```
Phase 1 (Setup)
    └─► Phase 2 (Foundational — Event ORM, exceptions, migration, router registration)
            ├─► Phase 3 (US1 — POST /admin/events) ← MVP delivery point
            │       └─► Phase 4 (US2 — PUT/DELETE /admin/events/{id})  ← depends on US1 router stub
            │               └─► Phase 5 (US3 — GET /events, GET /events/{id})  ← independent of US2, but shares router
            │                       └─► Phase 6 (Polish)
            └─► Phase 5 can also start after Phase 2 + US1 schemas are done
```

> US2 and US3 share `src/api/routers/events.py` and `src/application/event_service.py`.
> Implement in order to avoid merge conflicts on those files.

---

## Parallel Execution Opportunities

### Within Phase 2 (after T001)
- T002 ‖ T003 (different files: `models.py` vs `exceptions.py`)
- T004 → T005 (Alembic migration depends on ORM model being finalized)

### Within Phase 3 (US1, after Phase 2)
- T007 ‖ T008 (both write new test files — no shared state)
- T009 ‖ T007 ‖ T008 (pagination schemas/deps are independent of test files)
- T010 → T011 → T012 → T013 (sequential: schema → repo → service → router)

### Within Phase 4 (US2, after T013)
- T015 ‖ T016 ‖ T017 (unit test, contract test, and repository methods are all independent files)
- T018 → T019 (service use-cases before router endpoints)

### Within Phase 5 (US3, after Phase 2 + T010 done)
- T020 ‖ T021 ‖ T022 ‖ T023 (unit tests, contract tests, integration tests, repository methods all in different files)
- T024 → T025 (service → router)

### Within Phase 6
- T026 ‖ T027 ‖ T028 ‖ T029 ‖ T031 (all independent — different files/assertions)

---

## Implementation Strategy

**MVP** = Phase 1 + Phase 2 + Phase 3 (T001–T014)
After T014, `POST /admin/events` is fully functional and admin can create events.
This is the minimum viable increment — unblocks all downstream features (003-event-registration, reporting).

**Increment 2** = Phase 4 (T015–T019) — admin update/delete
**Increment 3** = Phase 5 (T020–T025) — public browse/pagination
**Increment 4** = Phase 6 (T026–T031) — polish, formatter/linter/mypy, edge case coverage, performance benchmark

Each increment is independently deployable and testable.
