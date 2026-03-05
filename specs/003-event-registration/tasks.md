# Tasks: 003-event-registration

**Input**: Design documents from `specs/003-event-registration/`
**Prerequisites**: plan.md ✅ · spec.md ✅ · research.md ✅ · data-model.md ✅ · contracts/ ✅

**Total tasks**: 28 (T001–T028)
**User story breakdown**: US1 → 7 tasks · US2 → 3 tasks · US3 → 7 tasks · Setup/Foundation → 7 tasks · Polish → 4 tasks

**Format**: `- [ ] [ID] [P?] [Story?] Description — file path`
- `[P]` = can run in parallel (different files, no blocking dependency)
- `[US1]`/`[US2]`/`[US3]` = user story label (story phases only)

---

## Phase 1: Setup

**Purpose**: Create test file stubs so parallel work can begin immediately.

- [ ] T001 Create empty test file stubs per plan.md: `tests/contract/test_registrations.py`, `tests/integration/test_registration_repository.py`, `tests/unit/test_registration_service.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core domain types, ORM extensions, migration, and router wiring that must be complete before any user story can be implemented. T002–T004 are independent and can be done in parallel; T005 depends on T002 and T004; T006 depends on T004 and T005; T007 depends on T003.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T002 [P] Extend `src/domain/models.py` — add `RegistrationStatus(str, enum.Enum)` with values `ACTIVE = "active"` and `CANCELLED = "cancelled"`
- [ ] T003 [P] Extend `src/domain/exceptions.py` — add `QuotaFullError(event_id)`, `DuplicateActiveRegistrationError(user_id, event_id)`, `NoActiveRegistrationError(user_id, event_id)`, `RegistrationDeadlinePassedError(event_id)` (exact signatures from data-model.md §5)
- [ ] T004 [P] Extend existing `Event` ORM class in `src/infrastructure/db/models.py` — add `current_participants: Mapped[int]` column (`Integer, NOT NULL, DEFAULT 0, server_default="0"`)
- [ ] T005 Add `EventRegistration` ORM model to `src/infrastructure/db/models.py` — fields: `id`, `user_id` (FK users.id), `event_id` (FK events.id), `status` (`SAEnum(RegistrationStatus)`), `registered_at` (`DateTime(timezone=True), server_default=func.now()`), `cancelled_at` (nullable), `event` relationship (`lazy="raise"`); `__table_args__`: partial unique index `uq_active_registration (user_id, event_id) WHERE status='active'`, covering index `ix_event_registrations_user_registered (user_id, registered_at)`, partial index `ix_event_registrations_event_active (event_id) WHERE status='active'`
- [ ] T006 Create Alembic migration `src/infrastructure/alembic/versions/yyyy_add_event_registrations_table.py`: (1) create `registrationstatus` enum type; (2) `ALTER TABLE events ADD COLUMN current_participants INTEGER NOT NULL DEFAULT 0` + two CHECK constraints (`chk_participants_not_negative`, `chk_participants_not_over_quota`); (3) create `event_registrations` table; (4) create all three indexes using `sa.text()` for the partial `WHERE` clauses; include correct `downgrade()` that reverses steps in reverse order
- [ ] T007 In `src/main.py` (or wherever 001/002 handlers live): register `registrations` router; add FastAPI exception handlers for `QuotaFullError` → 422 `QUOTA_FULL`, `DuplicateActiveRegistrationError` → 409 `DUPLICATE_REGISTRATION`, `NoActiveRegistrationError` → 404 `REGISTRATION_NOT_FOUND`, `RegistrationDeadlinePassedError` → 422 `REGISTRATION_DEADLINE_PASSED` — all using the inherited error envelope `{"error": {"code", "message", "httpStatus"}}`

**Checkpoint**: Migration runs cleanly (`alembic upgrade head`), `EventRegistration` is importable, all four new exception classes are importable, router prefix `/registrations` registered — user story phases may now proceed.

---

## Phase 3: User Story 1 — User mendaftar ke event publik (Priority: P1) 🎯 MVP

**Goal**: `POST /registrations/{event_id}` allows an authenticated user to register for a valid, open, non-duplicate event. Returns 201 `RegistrationResponse`. Counter atomically increments. Re-registration attempt for an already-active pair returns 409.

**Independent Test**: Obtain a user JWT. `POST /registrations/{event_id}` to a valid future event with quota → assert 201 + `RegistrationResponse` shape + `status="active"`. Immediately `POST` again to the same event → assert 409 `DUPLICATE_REGISTRATION`.

### Tests for User Story 1 ⚠️

> **Write these tests FIRST — they must FAIL before any implementation begins.**

- [ ] T008 [P] [US1] Write contract test: `POST /registrations/{event_id}` with valid user token → 201 + `RegistrationResponse` shape (`id`, `event_id`, `status`, `registered_at`); same request without token → 401 in `tests/contract/test_registrations.py`
- [ ] T009 [P] [US1] Write unit test for `registration_service.register()` happy path: mock event (active, future, quota available, no existing active reg), mock repository methods → assert `RegistrationResponse` returned and `current_participants` increment is called in `tests/unit/test_registration_service.py`
- [ ] T010 [P] [US1] Write integration test for `RegistrationRepository`: `create_registration()` persists a record with `status='active'`; atomic increment `events.current_participants` from 0 → 1; partial unique index blocks a second active row for the same `(user_id, event_id)` pair in `tests/integration/test_registration_repository.py`

### Implementation for User Story 1

- [ ] T011 [P] [US1] Implement `RegistrationResponse`, `EventSummary`, and `RegistrationWithEventResponse` Pydantic schemas (with `model_config = ConfigDict(from_attributes=True)`) in `src/api/schemas/registrations.py`
- [ ] T012 [US1] Implement `RegistrationRepository` in `src/infrastructure/repositories/registration_repository.py`: `get_active_registration(user_id, event_id) → EventRegistration | None`, `create_registration(user_id, event_id) → EventRegistration`, `atomic_increment_participants(event_id) → int | None` (`UPDATE events SET current_participants + 1 WHERE current_participants < quota RETURNING id`), `cancel_registration(user_id, event_id)` (sets `status=CANCELLED`, populates `cancelled_at`), `atomic_decrement_participants(event_id)` (`UPDATE events SET current_participants - 1 WHERE id = :id`), `get_my_registrations(user_id) → list[EventRegistration]` (with `selectinload(EventRegistration.event)`, ordered `registered_at DESC`)
- [ ] T013 [US1] Implement `registration_service.register()` use-case in `src/application/registration_service.py`: (1) load event via `_public_events_query().where(Event.id == event_id)`, raise `EventNotFoundError` if None; (2) check `registration_deadline < datetime.now(UTC)`, raise `RegistrationDeadlinePassedError`; (3) app-level pre-check for existing active registration, raise `DuplicateActiveRegistrationError`; (4) call `atomic_increment_participants`, raise `QuotaFullError` if no row returned; (5) call `create_registration` in same transaction; catch `IntegrityError` from `uq_active_registration` index → raise `DuplicateActiveRegistrationError` (narrow by index name)
- [ ] T014 [US1] Implement `POST /registrations/{event_id}` endpoint in `src/api/routers/registrations.py`: requires `Depends(get_current_user)`, receives `event_id: int` from path, calls `registration_service.register(session, current_user.id, event_id)`, returns 201 `RegistrationResponse`

**Checkpoint**: `POST /registrations/{event_id}` returns 201 for valid registrations with counter incremented. Duplicate active registration returns 409. No token returns 401. T008–T010 tests pass.

---

## Phase 4: User Story 2 — Sistem menolak pendaftaran yang tidak memenuhi syarat (Priority: P1)

**Goal**: All four rejection paths return exact HTTP status codes per FR-011 without side effects (counter unchanged, no record created). Concurrency test (SC-004) passes.

**Independent Test**: Seed: (1) non-existent event_id; (2) event with `registration_deadline` in the past; (3) event at full quota; (4) user already registered. `POST /registrations/{event_id}` to each → assert 404 / 422 / 422 / 409 respectively. Verify `events.current_participants` is unchanged after each rejection.

> **Note**: All guards are implemented as part of `registration_service.register()` in Phase 3. This phase is test-only — verifying each rejection path and the concurrent-quota guarantee.

### Tests for User Story 2 ⚠️

- [ ] T015 [P] [US2] Extend contract tests in `tests/contract/test_registrations.py`: 404 `EVENT_NOT_FOUND` (invalid/non-existent event_id), 422 `REGISTRATION_DEADLINE_PASSED` (event with past deadline), 422 `QUOTA_FULL` (quota=1 event already full), 409 `DUPLICATE_REGISTRATION` (user already has active reg) — verify error envelope `{"error": {"code", "message", "httpStatus"}}` on all cases
- [ ] T016 [P] [US2] Write unit tests for each rejection guard in `tests/unit/test_registration_service.py`: (1) `_public_events_query()` returns None → `EventNotFoundError` + 404 handler; (2) past `registration_deadline` → `RegistrationDeadlinePassedError` + 422 handler; (3) `atomic_increment_participants` returns None → `QuotaFullError` + 422 handler; (4) pre-check finds existing active row → `DuplicateActiveRegistrationError` + 409 handler — each as independent test case
- [ ] T017 [P] [US2] Write integration test for concurrent quota enforcement (SC-004) in `tests/integration/test_registration_repository.py`: `asyncio.gather` 5 concurrent `register()` calls from 5 different users to a `quota=1` event → assert exactly 1 returns `RegistrationResponse`; 4 raise `QuotaFullError`; `events.current_participants == 1` after all complete

**Checkpoint**: All 4 rejection paths tested against all status codes. Concurrent test confirms no overbooking possible (SC-004). T015–T017 tests pass.

---

## Phase 5: User Story 3 — User membatalkan pendaftaran dan melihat daftar pendaftarannya (Priority: P2)

**Goal**: `DELETE /registrations/{event_id}` soft-cancels the user's active registration (status → `cancelled`, counter decremented), returns 204. `GET /registrations/me` returns the user's full registration history (active + cancelled) as `list[RegistrationWithEventResponse]` ordered newest-first. Re-registration after cancellation creates a new `active` row.

**Independent Test**: (1) Register user to event → `DELETE /registrations/{event_id}` → 204. (2) Verify `GET /registrations/me` shows the record with `status="cancelled"` and `cancelled_at` populated. (3) `POST /registrations/{event_id}` again (quota available, deadline open) → 201 with a **new** registration `id`. (4) `GET /registrations/me` → two records for same event: one `cancelled`, one `active`.

### Tests for User Story 3 ⚠️

- [ ] T018 [P] [US3] Write contract tests for `DELETE /registrations/{event_id}` in `tests/contract/test_registrations.py`: 204 on valid cancel; 404 `REGISTRATION_NOT_FOUND` (no active reg exists); 422 `REGISTRATION_DEADLINE_PASSED` (deadline already passed for the event); 401 without token
- [ ] T019 [P] [US3] Write contract tests for `GET /registrations/me` in `tests/contract/test_registrations.py`: 200 with correct `list[RegistrationWithEventResponse]` shape (both active and cancelled items, `event` summary nested, `cancelled_at` nullable); 401 without token; empty list when user has no registrations; user A's token cannot see user B's registrations (different user → empty list)
- [ ] T020 [P] [US3] Write unit tests for `registration_service.cancel()` in `tests/unit/test_registration_service.py`: (1) no active registration → `NoActiveRegistrationError`; (2) past `registration_deadline` → `RegistrationDeadlinePassedError`; (3) valid cancel → `cancel_registration` + `atomic_decrement_participants` called; status returned is `cancelled`
- [ ] T021 [P] [US3] Write integration tests in `tests/integration/test_registration_repository.py`: `cancel_registration()` sets `status='cancelled'` and populates `cancelled_at`; `atomic_decrement_participants()` reduces `events.current_participants` by 1; after cancel, `uq_active_registration` partial index allows `create_registration()` again for same `(user_id, event_id)` — two rows exist (1 cancelled + 1 active)

### Implementation for User Story 3

- [ ] T022 [P] [US3] Implement `registration_service.cancel()` use-case in `src/application/registration_service.py`: (1) load active registration via `get_active_registration(user_id, event_id)`, raise `NoActiveRegistrationError` if None; (2) load event and check `registration_deadline < datetime.now(UTC)`, raise `RegistrationDeadlinePassedError`; (3) call `cancel_registration()` (sets `status=CANCELLED`, `cancelled_at=now()`) + `atomic_decrement_participants()` in same transaction
- [ ] T023 [P] [US3] Implement `registration_service.get_my_registrations()` use-case in `src/application/registration_service.py`: call `RegistrationRepository.get_my_registrations(user_id)` (uses `selectinload(EventRegistration.event)`, ordered `registered_at DESC`), return `list[RegistrationWithEventResponse]`
- [ ] T024 [US3] Implement `DELETE /registrations/{event_id}` endpoint (requires `Depends(get_current_user)`, calls `registration_service.cancel(session, current_user.id, event_id)`, returns 204 no content) and `GET /registrations/me` endpoint (requires `Depends(get_current_user)`, calls `registration_service.get_my_registrations(session, current_user.id)`, returns 200 `list[RegistrationWithEventResponse]`) in `src/api/routers/registrations.py`

**Checkpoint**: Cancel flow: counter decrements, record marked `cancelled`. Re-registration after cancel creates new `active` row (cancelled row stays, partial index allows it). `GET /registrations/me` returns only own records in `registered_at DESC` order. T018–T021 tests pass.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T025 [P] Run `mypy --strict` on all new/modified modules and fix any type errors: `src/domain/models.py`, `src/domain/exceptions.py`, `src/api/schemas/registrations.py`, `src/application/registration_service.py`, `src/infrastructure/repositories/registration_repository.py`, `src/api/routers/registrations.py`
- [ ] T026 [P] Verify FR-009 (participant list privacy) is not violated: confirm no endpoint in `src/api/routers/registrations.py` or `src/api/routers/events.py` returns a list of other users' registrations; add contract test asserting `GET /registrations/me` with user A token does not return user B's records in `tests/contract/test_registrations.py`
- [ ] T027 [P] Verify `registration_deadline` boundary edge case: add unit test in `tests/unit/test_registration_service.py` asserting that when `datetime.now(UTC) == registration_deadline` (mocked) the deadline check treats this as "passed" (`<` not `<=`), matching the boundary rule used by 002-event-management's public events filter and spec clarification
- [ ] T028 Run full test suite `pytest tests/` and confirm all 003-event-registration tests pass with no regressions in 001-authentication and 002-event-management tests

---

## Dependencies (Story Completion Order)

```
Phase 1 (Setup — T001)
    └─► Phase 2 (Foundational — T002–T007)
             ├─► Phase 3 (US1: Register — T008–T014)  ← MVP
             │       └─► Phase 4 (US2: Rejection tests — T015–T017)
             └─► Phase 5 (US3: Cancel + List — T018–T024)  [can start with Phase 3 complete]
                     └─► Phase 6 (Polish — T025–T028)
```

**US1 and US3 ordering**: US3 depends on the `RegistrationRepository` (T012) and `registration_service.register()` (T013) from US1, since cancel() semantics require an active registration to exist. Begin Phase 5 only after Phase 3 is complete.

**US2 ordering**: All US2 tasks (T015–T017) are pure tests that exercise the guards already implemented in US1 (T013). They can be written concurrently with Phase 5 since they do not block US3 implementation.

---

## Parallel Execution Examples

### Phase 2 — can parallelize T002, T003, T004 immediately

| Worker A | Worker B | Worker C |
|----------|----------|----------|
| T002 (RegistrationStatus enum) | T003 (domain exceptions) | T004 (current_participants column) |
| → T005 (EventRegistration ORM — needs T002 + T004) | → T007 (exception handlers — needs T003) | |
| → T006 (migration — needs T004 + T005) | | |

### Phase 3 — tests can be written in parallel with schemas

| Worker A | Worker B |
|----------|----------|
| T008 (contract test stub) | T011 (Pydantic schemas) |
| T009 (unit test stub) | T012 (repository methods) |
| T010 (integration test stub) | → T013 (service — needs T012) |
| | → T014 (endpoint — needs T013) |

### Phase 5 — cancel and list use-cases are independent

| Worker A | Worker B |
|----------|----------|
| T018 (contract: DELETE tests) | T019 (contract: GET /me tests) |
| T020 (unit: cancel() guards) | T021 (integration: soft-delete + re-reg) |
| T022 (cancel() use-case) | T023 (get_my_registrations() use-case) |
| → T024 (endpoints — needs T022 + T023) | |

---

## Implementation Strategy

**MVP scope**: Complete Phases 1–4 (T001–T017). This delivers a fully working registration endpoint with all acceptance criteria for the two P1 user stories (US1 + US2) and the SC-004 concurrency guarantee validated by automated tests.

**Increment 2**: Complete Phase 5 (T018–T024) to deliver cancellation, re-registration, and personal registration list (US3, P2).

**Done**: Complete Phase 6 (T025–T028) for type safety, privacy verification, edge-case coverage, and no-regression confirmation.
