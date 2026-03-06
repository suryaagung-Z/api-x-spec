# Tasks: Admin Reporting

**Input**: Design documents from `/specs/004-admin-reporting/`
**Prerequisites**: plan.md ✅ · spec.md ✅ · research.md ✅ · data-model.md ✅ · contracts/ ✅

**Tests**: Tests are **required** for every user story per plan.md Gate 3 ("Tests are non-negotiable deliverables tracked in tasks.md").

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies within the phase)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Exact file paths included in every description

---

## Phase 1: Setup (Router Registration)

**Purpose**: Wire the new reports router into the existing application — required before any endpoint is reachable.

- [ ] T001 Register `reports` router in `src/main.py` by adding `app.include_router(reports.router)` alongside the existing auth/events/registrations routers

**Checkpoint**: `GET /admin/reports/events/stats` returns 404 (route exists but handlers not yet implemented) — confirms registration is wired correctly.

---

## Phase 2: Foundational (Shared Data Shapes)

**Purpose**: Establish the data transfer objects shared across all user story implementations. Must be complete before any service or repository work begins.

**⚠️ CRITICAL**: Phases 3 and 4 depend on these types existing.

- [ ] T002 [P] Create `EventStatRow` frozen dataclass (id, title, date, quota, total_registered, remaining_quota) in `src/infrastructure/repositories/reporting_repository.py`
- [ ] T003 [P] Create Pydantic schemas `EventStatItem`, `EventStatsPage`, and `ReportSummaryResponse` in `src/api/schemas/reports.py` — `EventStatsPage` reuses `Page[EventStatItem]` from `src/api/schemas/pagination.py`; `remaining_quota` has no `ge` constraint (FR-008)

**Checkpoint**: `from src.infrastructure.repositories.reporting_repository import EventStatRow` and `from src.api.schemas.reports import EventStatItem, EventStatsPage, ReportSummaryResponse` import without error.

---

## Phase 3: User Story 1 — Per-Event Participant Statistics (Priority: P1) 🎯 MVP

**Goal**: Admin can call `GET /admin/reports/events/stats?page=1&size=20` and receive a paginated `EventStatsPage` with `total_registered` and `remaining_quota` per active event.

**Independent Test**: Seed several active future events with varying registration counts, call the endpoint with an admin token, and verify each item's `total_registered` equals the count of active (non-cancelled) registrations and `remaining_quota = quota − total_registered` (including negative values).

### Tests for User Story 1 (REQUIRED) ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T004 [P] [US1] Contract test — `GET /admin/reports/events/stats` returns 200 with correct `EventStatsPage` shape (items array, total, page, size, pages fields; `total_registered` and `remaining_quota` values match seeded data) in `tests/contract/test_reports.py`
- [ ] T005 [P] [US1] Integration test — `ReportingRepository.get_event_stats_page()`: active events with mixed active/cancelled registrations return correct counts; event with zero registrations returns `total_registered=0, remaining_quota=quota`; event with more registrations than quota returns negative `remaining_quota`; past and inactive events are excluded; assert exactly one SQL statement is issued per call using a SQLAlchemy `before_cursor_execute` event hook (NFR-001); add a comment noting that read-time consistency for concurrent status changes is guaranteed by the database's default transaction isolation level (F6 edge case) in `tests/integration/test_reporting_repository.py`
- [ ] T006 [P] [US1] Unit test — `ReportingService.get_event_stats()`: `EventStatRow` → `EventStatItem` mapping is correct; pagination math (`pages = ceil(total / size)`) is correct; empty result returns empty items list in `tests/unit/test_reporting_service.py`

### Tests for User Story 3 — Admin-Only Access (Priority: P1) ⚠️

> US3 access control applies to all reporting endpoints. Stats-endpoint assertions are written here (Phase 3) before the router is implemented; summary-endpoint assertions are added in Phase 4 (T007b) once T010 creates the router module.

- [ ] T007 [US3] Contract test — unauthenticated request to `GET /admin/reports/events/stats` returns 401 `UNAUTHORIZED`; request with `role=user` token returns 403 `FORBIDDEN`; request with `role=admin` token returns 200 in `tests/contract/test_reports.py`

### Implementation for User Story 1

- [ ] T008 [US1] Implement `ReportingRepository.get_event_stats_page(offset, limit) → tuple[list[EventStatRow], int]` — single LEFT JOIN + `COUNT(er.id) FILTER (WHERE er.status = 'active')` query with `WHERE e.status='active' AND e.date > now` filter, `GROUP BY e.id ORDER BY e.date ASC, e.id ASC`, plus separate scalar count query for pagination total in `src/infrastructure/repositories/reporting_repository.py`
- [ ] T009 [US1] Implement `ReportingService.get_event_stats(page, size) → EventStatsPage` — converts `EventStatRow` list to `EventStatItem` list, computes `pages = ceil(total / size)`, injects `ReportingRepository` via dependency injection in `src/application/reporting_service.py`

### Implementation for User Story 3

- [ ] T010 [US3] Implement `GET /admin/reports/events/stats` route handler with `Depends(require_role(UserRole.ADMIN))` and `Depends(pagination_params)` in `src/api/routers/reports.py`; create the router module with `APIRouter(prefix="/admin/reports", tags=["Admin Reporting"])`

**Checkpoint**: `GET /admin/reports/events/stats?page=1&size=20` with an admin token returns paginated stats; same URL with a user token returns 403; without a token returns 401. `pytest tests/contract/test_reports.py tests/integration/test_reporting_repository.py tests/unit/test_reporting_service.py` all pass for US1 and stats-endpoint US3 tests. *(Summary-endpoint access control is verified in Phase 4 — T007b.)*

---

## Phase 4: User Story 2 — Total Active Events Summary (Priority: P2)

**Goal**: Admin can call `GET /admin/reports/events/summary` and receive `{ "total_active_events": N }` reflecting only events with `status='active' AND date > NOW()`.

**Independent Test**: Seed events with varying statuses (active-future, active-past, inactive) and verify the summary count matches only the active-future subset; verify zero is returned correctly when none qualify.

### Tests for User Story 2 (REQUIRED) ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T011 [P] [US2] Contract test — `GET /admin/reports/events/summary` returns 200 with `{ "total_active_events": N }` shape; returns `total_active_events=0` (not an error) when no active events exist in `tests/contract/test_reports.py`
- [ ] T012 [P] [US2] Integration test — `ReportingRepository.get_total_active_events()`: counts only `status='active' AND date > NOW()` events; past events with `status='active'` are excluded; events with `status='inactive'` are excluded; returns 0 when none qualify; assert exactly one SQL statement is issued per call (NFR-001); document that per-query isolation covers the concurrent status-change edge case (F6) in `tests/integration/test_reporting_repository.py`

### Tests for User Story 3 — Summary Endpoint Access Control ⚠️

> US3 access control also applies to the summary endpoint. Written here (Phase 4) once the router module exists from T010.

- [ ] T007b [US3] Contract test — unauthenticated request to `GET /admin/reports/events/summary` returns 401 `UNAUTHORIZED`; request with `role=user` token returns 403 `FORBIDDEN`; request with `role=admin` token returns 200 in `tests/contract/test_reports.py`

### Implementation for User Story 2

- [ ] T013 [US2] Implement `ReportingRepository.get_total_active_events() → int` — `SELECT COUNT(*) FROM events WHERE status='active' AND date > NOW()` scalar query in `src/infrastructure/repositories/reporting_repository.py`
- [ ] T014 [US2] Implement `ReportingService.get_summary() → ReportSummaryResponse` — delegates to `ReportingRepository.get_total_active_events()` and returns `ReportSummaryResponse(total_active_events=count)` in `src/application/reporting_service.py`
- [ ] T015 [US2] Implement `GET /admin/reports/events/summary` route handler with `Depends(require_role(UserRole.ADMIN))` in `src/api/routers/reports.py`

**Checkpoint**: `GET /admin/reports/events/summary` with an admin token returns `{ "total_active_events": N }`; 403 with a user token; 401 without token. `pytest tests/contract/test_reports.py tests/integration/test_reporting_repository.py` pass for US2 and summary-endpoint US3 tests (T007b). All four new files are now complete.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Final hardening, documentation, and full-suite validation across all user stories.

- [ ] T016 [P] Add module-level docstrings and inline comments to all four new files (`src/api/schemas/reports.py`, `src/api/routers/reports.py`, `src/application/reporting_service.py`, `src/infrastructure/repositories/reporting_repository.py`) explaining the `COUNT FILTER` pattern and the active-event predicate
- [ ] T017 [P] Run full pytest suite (`pytest tests/`) and confirm SC-001 (all stat values match seeded data) and SC-003 (100% of non-admin access attempts rejected) pass; fix any failures
- [ ] T018 [P] Run the quickstart.md smoke tests — execute all five curl examples (4a–4e) against a running `uvicorn src.main:app --reload` instance and verify every response matches the expected shape defined in `specs/004-admin-reporting/quickstart.md`
- [ ] T019 [P] Performance benchmark — seed the test database with 10,000 active future events and proportional event registrations; execute `GET /admin/reports/events/stats?page=1&size=20` and `GET /admin/reports/events/summary` repeatedly; assert p95 wall-clock latency ≤ 2 s per endpoint (SC-002); capture `EXPLAIN ANALYZE` output for the aggregate query and assert it contains a `HashAggregate` or `GroupAggregate` node to confirm aggregation occurs at the storage layer (NFR-002); use `pytest-benchmark` or a timing-loop with `statistics.quantiles` in `tests/integration/test_reporting_repository.py`

**Checkpoint**: All 20 tasks complete. `pytest` green (including benchmark thresholds). Quickstart smoke tests pass. Feature branch ready for review.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 — BLOCKS Phases 3 and 4
- **Phase 3 (US1 + US3, P1)**: Depends on Phase 2 — implements the per-event stats endpoint with access control
- **Phase 4 (US2, P2)**: Depends on Phase 2 — can start immediately after Phase 2; Phase 3 not required but its router module must exist for `T015` to extend it (start Phase 4 after T010 completes)
- **Phase 5 (Polish)**: Depends on Phases 3 and 4 being complete

### User Story Dependencies

- **US1 (P1)**: Depends on Foundational (T002, T003) — no dependency on US2 or US3
- **US3 (P1)**: Depends on US1 implementation (T008–T009) — access control is added to the same router module
- **US2 (P2)**: Depends on Foundational (T002, T003) and the router module created in T010 — independent of US1 business logic

### Within Each Phase

- Tests MUST be written before implementation (fail first)
- T002 and T003 are parallel (different files)
- T004, T005, T006 are parallel (different files)
- T007 must follow T004 (same file: `tests/contract/test_reports.py`)
- T008 → T009 → T010 are sequential (each depends on the previous layer)
- T011 and T012 are parallel (different files)
- T007b must follow T011 (same file: `tests/contract/test_reports.py`, Phase 4)
- T013 → T014 → T015 are sequential
- T016 and T017 are parallel (different files / pure read operations)
- T018 must follow T017 (requires all tests passing before smoke tests)
- T019 must follow T017 (benchmark requires implementation complete; can run in parallel with T018)

---

## Parallel Execution Examples

### Phase 2 — Foundational

```
# Both can start simultaneously (different files):
T002  Create EventStatRow dataclass in src/infrastructure/repositories/reporting_repository.py
T003  Create Pydantic schemas in src/api/schemas/reports.py
```

### Phase 3 — US1 + US3 Tests

```
# Three test files can be written simultaneously:
T004  Contract tests in tests/contract/test_reports.py
T005  Integration tests in tests/integration/test_reporting_repository.py
T006  Unit tests in tests/unit/test_reporting_service.py

# Then sequentially extend test_reports.py (stats endpoint only):
T007  Stats-endpoint access-control contract tests in tests/contract/test_reports.py
```

### Phase 4 — US2 Tests

```
# Both test files can start simultaneously:
T011  Contract tests (summary endpoint) in tests/contract/test_reports.py
T012  Integration tests (get_total_active_events) in tests/integration/test_reporting_repository.py

# Then sequentially extend test_reports.py:
T007b  Summary-endpoint access-control contract tests in tests/contract/test_reports.py
```

---

## Implementation Strategy

### MVP First (User Story 1 + Access Control Only)

1. Complete Phase 1: Setup (T001)
2. Complete Phase 2: Foundational (T002–T003 in parallel)
3. Write US1/US3 stats-endpoint tests (T004–T006 in parallel, then T007)
4. Implement US1 stack: T008 → T009 → T010
5. **STOP and VALIDATE**: Run `pytest tests/contract/test_reports.py tests/integration/test_reporting_repository.py tests/unit/test_reporting_service.py`
6. Deploy/demo — admin can view per-event stats, access control enforced

### Incremental Delivery

1. **MVP**: Setup + Foundational + Phase 3 → `GET /admin/reports/events/stats` fully functional with admin guard
2. **Increment 2**: Phase 4 → `GET /admin/reports/events/summary` added
3. **Final**: Phase 5 → full polish, smoke tests, all SC criteria verified

### Single-Developer Sequence

```
T001 → T002 + T003 (parallel) →
T004 + T005 + T006 (parallel) → T007 →
T008 → T009 → T010 →
[Validate US1/US3 stats independently] →
T011 + T012 (parallel) → T007b →
T013 → T014 → T015 →
[Validate US2 independently] →
T016 + T017 (parallel) → T018 + T019 (parallel)
```

---

## Notes

- **No migrations**: This feature is read-only. `alembic current` must show the 003 head before running the app.
- **No new libraries**: All dependencies (FastAPI, SQLAlchemy 2.x async, Pydantic v2, asyncpg/aiosqlite) are already installed.
- **`remaining_quota` may be negative** — `EventStatItem.remaining_quota` intentionally has no `ge=0` constraint (FR-008).
- **Active-event predicate**: `status = 'active' AND date > NOW()` — consistent with 002 public listing (R-002). Use `datetime.now(timezone.utc)` in Python for the `now` binding.
- **Existing indexes** (`ix_events_status_date`, `ix_event_registrations_event_active`) from 002/003 are sufficient — no new indexes needed (R-006).
- `[P]` tasks = different files, no dependencies within the phase
- `[Story]` label maps each task to a specific user story for traceability
- Commit after each checkpoint or logical group
