# Tasks: Authentication and Authorization

**Input**: Design documents from `specs/001-authentication/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅, quickstart.md ✅

**Tests**: REQUIRED per project constitution — every user story that introduces behavior MUST
have automated tests. Tests are written FIRST and must fail before implementation begins
(red-green-refactor).

**Organization**: Tasks are grouped by user story to enable independent implementation and
testing. US1 and US2 are both P1; US3 is P2.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependency on incomplete tasks)
- **[Story]**: Maps task to a specific user story (US1, US2, US3)
- Exact file paths are included in every task description

---

## Phase 1: Setup

**Purpose**: Initialize project skeleton, toolchain, and configuration files.

- [X] T001 Create full directory structure per plan.md (`src/api/routers/`, `src/api/schemas/`, `src/api/dependencies/`, `src/application/`, `src/domain/`, `src/infrastructure/db/`, `src/infrastructure/repositories/`, `src/infrastructure/auth/`, `tests/unit/`, `tests/integration/`, `tests/contract/`, `alembic/`)
- [X] T002 Initialize `pyproject.toml` with all dependencies: `fastapi`, `uvicorn[standard]`, `sqlalchemy[asyncio]`, `alembic`, `PyJWT`, `bcrypt`, `pydantic-settings`, `aiosqlite`, `asyncpg`; dev deps: `pytest`, `pytest-asyncio`, `httpx`, `black`, `ruff`, `mypy`, `pytest-benchmark`, `locust` (last two required by T041 for SC-001/SC-005 performance verification)
- [X] T003 [P] Create `.env.example` with `JWT_SECRET_KEY`, `JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60`, `DATABASE_URL=sqlite+aiosqlite:///./dev.db` (do NOT include `JWT_ALGORITHM` — the algorithm is hardcoded to `HS256` in code and MUST NOT be configurable via env var)
- [X] T004 [P] Configure `black`, `ruff`, and `mypy` tool sections in `pyproject.toml`; implement shared async pytest fixtures in `tests/conftest.py`: async `test_client` fixture (in-memory `aiosqlite` DB, creates all tables, tears down after test), `create_user(client, *, name, email, password, role)` async helper (calls `POST /auth/register` then sets role directly via DB for admin), `user_auth_headers(client)` and `admin_auth_headers(client)` fixtures that register+login a `user`-role and `admin`-role user respectively and return `{"Authorization": "Bearer <token>"}` dicts — required by T017, T025, and T033

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be
implemented. Establishes domain models, infrastructure adapters, DB schema, and
app wiring that all three stories depend on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T005 Implement `User` dataclass and `UserRole` enum (`user`, `admin`) in `src/domain/models.py` with fields: `id`, `name`, `email`, `hashed_password`, `role`, `created_at` (note: `is_active` is out of scope for this feature — omit)
- [X] T006 [P] Implement domain exceptions in `src/domain/exceptions.py`: `EmailAlreadyExistsError`, `InvalidCredentialsError`, `UserNotFoundError`
- [X] T007 [P] Implement password utilities in `src/infrastructure/auth/password.py`: `hash_password()` (bcrypt 5.x, `rounds=12`) and `verify_password()` with dummy-hash timing-safe path for unknown users
- [X] T008 [P] Implement JWT utilities in `src/infrastructure/auth/jwt.py`: `create_access_token(sub, role)` (hardcode `algorithm="HS256"` directly in code — NOT read from `Settings` or any env var; claims `sub`/`role`/`iat`/`exp`; expiry from `settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES`) and `decode_token(token)` enforcing `algorithms=["HS256"]` as an explicit allowlist (rejects `alg=none` and any other algorithm)
- [X] T009 Implement SQLAlchemy 2.x ORM `User` model in `src/infrastructure/db/models.py` with all columns, `CHECK` constraint on `role`, `UNIQUE` on `email`; inherits from `DeclarativeBase` with `AsyncAttrs`; add `__table_args__` with `Index("ix_users_email_lower", func.lower(User.email), unique=True)` for case-insensitive email uniqueness enforcement at DB layer (matches data-model.md functional index)
- [X] T010 Implement async DB session factory in `src/infrastructure/db/session.py`: `create_async_engine`, `async_sessionmaker(expire_on_commit=False)`, `get_db()` dependency with commit/rollback lifecycle
- [X] T011 Configure Alembic for async SQLAlchemy in `alembic/env.py` using `run_sync` pattern; set `target_metadata` to ORM `Base.metadata`
- [X] T012 Generate initial Alembic migration for `users` table in `alembic/versions/` via `alembic revision --autogenerate -m "create_users_table"`; verify generated SQL matches `data-model.md` schema
- [X] T013 Implement `UserRepository` in `src/infrastructure/repositories/user_repository.py`: `get_by_email(email)` (normalize input with `email.lower()` before querying to support case-insensitive login lookups), `get_by_id(user_id)`, `create(name, email, hashed_password, role)`, `get_all()` (returns `list[User]`, used by `GET /admin/users`) using `AsyncSession`
- [X] T014 [P] Implement Pydantic v2 API schemas in `src/api/schemas/auth.py`: `RegisterRequest` (name, email `EmailStr`, password min=8 max=72), `LoginRequest`, `TokenResponse`, `UserRead` (with `ConfigDict(from_attributes=True)`)
- [X] T015 [P] Implement error envelope schemas in `src/api/schemas/errors.py`: `ErrorDetail` (code, message, httpStatus) and `ErrorEnvelope`; matches `contracts/error-envelope.md`
- [X] T016 Implement FastAPI app factory in `src/main.py`: create `app`, load `pydantic-settings` `Settings`, register domain exception handlers: `EmailAlreadyExistsError` → 409 `ErrorEnvelope`; `InvalidCredentialsError` → 401 `ErrorEnvelope` with `headers={"WWW-Authenticate": "Bearer"}`; `UserNotFoundError` → 401 `ErrorEnvelope` with `headers={"WWW-Authenticate": "Bearer"}`; register `@app.exception_handler(RequestValidationError)` → 422 `ErrorEnvelope(code="VALIDATION_ERROR", httpStatus=422)` (satisfies FR-011 for all error paths including Pydantic validation failures); include routers placeholder

**Checkpoint**: Foundation ready — domain, infra, DB schema, app wiring all in place. User story implementation can now begin.

---

## Phase 3: User Story 1 — Registrasi User Baru (Priority: P1) 🎯 MVP

**Goal**: Users can register a new account with name, email, and password. Passwords are
stored as bcrypt hashes. Duplicate email registrations are rejected with a clear JSON error.

**Independent Test**: Register with a new email (→ 201, password stored as bcrypt hash),
then register again with the same email (→ 409 `EMAIL_ALREADY_EXISTS` JSON error envelope).

### Tests for User Story 1 (REQUIRED) ⚠️

> **Write these tests FIRST — they MUST FAIL before any implementation below**

- [X] T017 [P] [US1] Write contract tests for `POST /auth/register` in `tests/contract/test_register.py`: success 201 returns `UserRead` with no `password` field and no `is_active` field; duplicate email returns 409 `ErrorEnvelope` with `code="EMAIL_ALREADY_EXISTS"`; re-registration with the same email in a different case (e.g., `User@Example.com` after registering `user@example.com`) also returns 409 (verifies case-insensitive uniqueness from C3); password of 7 characters returns 422 `ErrorEnvelope` with `code="VALIDATION_ERROR"` (FR-013 lower boundary); password of 73 characters returns 422 `ErrorEnvelope` with `code="VALIDATION_ERROR"` (FR-013 upper boundary)
- [X] T018 [P] [US1] Write integration tests for `UserRepository` in `tests/integration/test_user_repository.py`: `create()` persists user and stores email as lowercase; `get_by_email()` returns user or None; `get_by_email()` with mixed-case email finds the same user (case-insensitive lookup); second `create()` with same email raises `EmailAlreadyExistsError`; `create()` with same email in different case (e.g., `User@Example.com`) also raises `EmailAlreadyExistsError` (case-insensitive enforcement — C3)
- [X] T019 [P] [US1] Write unit tests for `hash_password` / `verify_password` in `tests/unit/test_password.py`: hash differs from plain text; verify returns True for correct password, False for wrong; verify does not raise for unknown user (timing-safe dummy path)

### Implementation for User Story 1

- [X] T020 [US1] Implement `register(name, email, password)` use case in `src/application/auth_service.py`: normalize email to lowercase (`email = email.lower()`) before uniqueness check and persistence (application-layer enforcement of case-insensitive uniqueness per data-model.md); check uniqueness via `UserRepository.get_by_email()`; raise `EmailAlreadyExistsError` on conflict; hash password via `hash_password()`; persist via `UserRepository.create()`; return domain `User`
- [X] T021 [P] [US1] Write unit tests for `auth_service.register()` in `tests/unit/test_auth_service.py`: successful registration; raises `EmailAlreadyExistsError` on duplicate email; password is hashed not stored plain
- [X] T022 [US1] Implement `POST /auth/register` endpoint in `src/api/routers/auth.py`: call `auth_service.register()`, respond 201 `UserRead`; mount router on app in `src/main.py`
- [X] T023 [US1] Verify `EmailAlreadyExistsError` → 409 exception handler in `src/main.py` returns `ErrorEnvelope` with `code="EMAIL_ALREADY_EXISTS"` and `httpStatus=409`; confirm 422 Pydantic validation errors also use `ErrorEnvelope` shape

**Checkpoint**: `POST /auth/register` fully functional — new email creates account, duplicate returns 409, all T017–T019 tests pass.

---

## Phase 4: User Story 2 — Login dan Akses Endpoint Terproteksi (Priority: P1)

**Goal**: Registered users can log in with email/password and receive a JWT access token.
Protected endpoints accept the token via `Authorization: Bearer <token>`; requests without
a valid token are rejected with 401 and a consistent JSON error.

**Independent Test**: Register a user → login → receive JWT → `GET /auth/me` with token succeeds (200) → `GET /auth/me` without token or with tampered/expired token returns 401 `ErrorEnvelope`.

### Tests for User Story 2 (REQUIRED) ⚠️

> **Write these tests FIRST — they MUST FAIL before any implementation below**

- [X] T024 [P] [US2] Write contract tests for `POST /auth/login` in `tests/contract/test_login.py`: correct credentials return 200 `TokenResponse` with `token_type="bearer"`; wrong password returns 401 `UNAUTHORIZED` with `WWW-Authenticate: Bearer` response header (per FR-006 and openapi.yaml); unknown email returns 401 with same message and same `WWW-Authenticate: Bearer` header (no enumeration)
- [X] T025 [P] [US2] Write contract tests for `GET /auth/me` in `tests/contract/test_protected.py`: valid token returns 200 `UserRead`; missing `Authorization` header returns 401; malformed token returns 401; expired token (manipulated `exp`) returns 401; all 401 responses include `WWW-Authenticate: Bearer` header
- [X] T026 [P] [US2] Write unit tests for JWT utilities in `tests/unit/test_jwt.py`: `create_access_token` encodes `sub`, `role`, `iat`, `exp`; `decode_token` returns payload; expired token raises; tampered signature raises; `alg=none` rejected

### Implementation for User Story 2

- [X] T027 [US2] Implement `login(email, password)` use case in `src/application/auth_service.py`: normalize input email with `email = email.lower()` before calling `UserRepository.get_by_email()` (ensures mixed-case logins match stored lowercase emails — C6); run `verify_password` (including dummy-hash path for unknown email), raise `InvalidCredentialsError` on any mismatch, call `create_access_token(sub=user.id, role=user.role)` and return token string
- [X] T028 [P] (after T021) [US2] Write unit tests for `auth_service.login()` in `tests/unit/test_auth_service.py`: successful login returns token string; wrong password raises `InvalidCredentialsError`; unknown email raises `InvalidCredentialsError` (same exception — no enumeration)
- [X] T029 [US2] Implement `get_current_user()` async dependency in `src/api/dependencies/auth.py`: extract Bearer token via `OAuth2PasswordBearer`, call `decode_token()`, look up user via `UserRepository.get_by_id()`, raise `HTTPException(401, headers={"WWW-Authenticate": "Bearer"})` on any failure (invalid token, expired, tampered, user not found)
- [X] T030 [US2] Implement `POST /auth/login` endpoint in `src/api/routers/auth.py`: call `auth_service.login()`, return `TokenResponse`
- [X] T031 [US2] Implement `GET /auth/me` endpoint in `src/api/routers/auth.py` with `Depends(get_current_user)`, return `UserRead`
- [X] T032 [US2] Verify `InvalidCredentialsError` and `UserNotFoundError` → 401 handlers in `src/main.py` return `ErrorEnvelope` with `code="UNAUTHORIZED"` and `httpStatus=401`; confirm all 401 responses (including login path) include `WWW-Authenticate: Bearer` response header per FR-006; confirm generic message that does not reveal email vs. password distinction

**Checkpoint**: Login and protected endpoint fully functional — JWT issued on login, `GET /auth/me` accepts/rejects tokens correctly, all T024–T026 tests pass.

---

## Phase 5: User Story 3 — Akses Endpoint Khusus Admin (Priority: P2)

**Goal**: Endpoints restricted to the `admin` role reject `user`-role tokens with HTTP 403
(`FORBIDDEN`) while accepting `admin`-role tokens. Role information is encoded in the JWT
claim at login and verified per-request without a DB round-trip.

**Independent Test**: Create an admin-role user (direct DB seed or test fixture) and a
user-role user → login both → `GET /admin/users` with admin token returns 200 → with user
token returns 403 `FORBIDDEN` → without token returns 401 `UNAUTHORIZED`.

### Tests for User Story 3 (REQUIRED) ⚠️

> **Write these tests FIRST — they MUST FAIL before any implementation below**

- [X] T033 [P] [US3] Write contract tests for `GET /admin/users` in `tests/contract/test_admin.py`: admin JWT returns 200 list; user-role JWT returns 403 `ErrorEnvelope` with `code="FORBIDDEN"` and no `WWW-Authenticate` header; missing token returns 401 with `WWW-Authenticate: Bearer`

### Implementation for User Story 3

- [X] T034 [US3] Implement `require_role(required_role: str)` dependency factory in `src/api/dependencies/auth.py`: sub-depends on `get_current_user()`, raises `HTTPException(403, ErrorEnvelope)` with `code="FORBIDDEN"` and `httpStatus=403` when `user.role != required_role` (no `WWW-Authenticate` header on 403)
- [X] T035 [US3] Implement `GET /admin/users` admin-only router in `src/api/routers/admin.py` with `dependencies=[Depends(require_role("admin"))]` at router level, returning list of all users as `list[UserRead]` via `UserRepository`
- [X] T036 [US3] Register admin router in `src/main.py` with prefix `/admin` and tag `admin`

**Checkpoint**: All three user stories independently functional — US1 (register), US2 (login + protected), US3 (admin RBAC). All T033 tests pass.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Observability, security hardening, and final validation across all stories.

- [X] T037 [P] Add structured logging via Python `logging` to `src/application/auth_service.py` (register success/failure, login success/failure) and `src/api/routers/auth.py` (request-level info); ensure no sensitive data (passwords, tokens) appears in logs
- [X] T038 [P] Run full test suite (`pytest --cov=src --cov-report=term-missing`) and fix any regressions; confirm all unit, integration, and contract tests for US1, US2, US3 pass
- [X] T039 Validate `quickstart.md` smoke-test sequence end-to-end: `POST /auth/register` → `POST /auth/login` → `GET /auth/me` → `GET /admin/users` (403 then 200 with admin token); confirm `.env.example` and `alembic upgrade head` instructions work from a clean checkout
- [X] T040 [P] Create `scripts/seed_admin.py`: a standalone script that provisions an initial `admin`-role user via `UserRepository` (reads credentials from env vars `SEED_ADMIN_EMAIL` / `SEED_ADMIN_PASSWORD`; idempotent — skips if email already exists); append `SEED_ADMIN_EMAIL` and `SEED_ADMIN_PASSWORD` placeholder entries to `.env.example`; add a "Seeding the admin account" section to `quickstart.md` documenting usage
- [X] T041 [P] Verify SC-001 and SC-005 performance thresholds (deferred to post-MVP — MUST run before production release): (0) create `locustfile.py` in the repo root with a Locust `HttpUser` class and a `TaskSet` that executes `POST /auth/register` → `POST /auth/login` per simulated user (generate a unique email per user via `uuid.uuid4()` to avoid duplicate-email conflicts; required by step 2); (1) **SC-005** — run `pytest --benchmark-only -k test_get_me_valid_token` (requires `pytest-benchmark` from T002 dev deps); assert p95 latency for JWT validation on `GET /auth/me` is < 200ms; record result in `quickstart.md`; (2) **SC-001** — run `locust -f locustfile.py --headless -u 50 -r 20 --run-time 60s` using the `TaskSet` from step 0; assert ≥ 95% of requests complete in < 5s; record result in `quickstart.md`; (3) add a `## Performance Verification` section to `quickstart.md` documenting both commands, thresholds, and a `TODO: run before production release` callout

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: Requires Phase 1 complete. **BLOCKS all user stories.**
- **US1 (Phase 3)**: Requires Phase 2 complete. No dependency on US2 or US3.
- **US2 (Phase 4)**: Requires Phase 2 complete + T029 (`get_current_user`) is a pre-requisite for US3. US2 can start in parallel with US1. **Note**: T028 extends `tests/unit/test_auth_service.py` created by T021 (Phase 3) — T028 MUST NOT be started before T021 is complete, even when US1 and US2 are worked in parallel by separate developers.
- **US3 (Phase 5)**: Requires Phase 2 complete + T029 (`get_current_user`) from US2.
- **Polish (Phase 6)**: Requires all desired user stories complete.

### User Story Dependencies

| Story | Can start after | Depends on from other stories |
|---|---|---|
| **US1 (P1)** | Phase 2 complete | None |
| **US2 (P1)** | Phase 2 complete | None (but T022 enables register-then-login in contract tests) |
| **US3 (P2)** | Phase 2 complete | T029 `get_current_user()` from US2 |

### Within Each User Story

1. Tests FIRST — must FAIL before implementation
2. Models / domain → services (application) → endpoints (API)
3. Verify tests pass after implementation — commit

### Parallel Opportunities Per Phase

**Phase 1**: T003, T004 in parallel (after T001, T002)

**Phase 2**:
- T006, T007, T008 in parallel (after T005)
- T009 after T005; T010 after T009; T011, T012, T013 after T010
- T014, T015 independently in parallel at any time; T016 after T014, T015, T013

**Phase 3 (US1)**:
- T017, T018, T019 all in parallel (different test files)
- T021 in parallel with T020 (different files)

**Phase 4 (US2)**:
- T024, T025, T026 all in parallel (different test files)
- T028 in parallel with T027 (different files)

**Phase 5 (US3)**:
- T033 in parallel with T034 (test vs. implementation)

**Phase 6**: T037, T038 in parallel

---

## Parallel Example: US1

```
# Tests — all in parallel:
T017  tests/contract/test_register.py
T018  tests/integration/test_user_repository.py
T019  tests/unit/test_password.py

# Then implementation — T020 first, T021 in parallel with T020, T022 after T020:
T020  src/application/auth_service.py::register()
T021  tests/unit/test_auth_service.py (register cases)   ← parallel with T020

# Then endpoint + wiring:
T022  src/api/routers/auth.py::POST /auth/register
T023  src/main.py exception handler verification
```

## Parallel Example: US2

```
# Tests — all in parallel:
T024  tests/contract/test_login.py
T025  tests/contract/test_protected.py
T026  tests/unit/test_jwt.py

# Then implementation:
T027  src/application/auth_service.py::login()
T028  tests/unit/test_auth_service.py (login cases)      ← parallel with T027

# Then dependency + endpoints:
T029  src/api/dependencies/auth.py::get_current_user()
T030  src/api/routers/auth.py::POST /auth/login
T031  src/api/routers/auth.py::GET /auth/me
T032  src/main.py exception handler verification
```

---

## Implementation Strategy

### MVP First (US1 Only — Minimal Viable Registration)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (**non-negotiable gate**)
3. Complete Phase 3: User Story 1 (register)
4. **STOP AND VALIDATE**: Run T017–T019 tests, curl `POST /auth/register`
5. Deploy/demo if ready

### Incremental Delivery

1. **Setup + Foundational** → project running, DB migrated, app boots
2. **+ US1** → Registration works → independently testable → demo
3. **+ US2** → Login + JWT + protected endpoint → independently testable → demo
4. **+ US3** → Admin RBAC → independently testable → demo
5. **+ Polish** → Logging, coverage, quickstart validated → release-ready

### Parallel Team Strategy (2 developers)

After Foundational phase completes:
- **Dev A**: US1 (T017–T023)
- **Dev B**: US2 infrastructure (T026 JWT tests, T027 login service, T029 get_current_user)
- Once US2's T029 merges: Dev A or B starts US3

---

## Task Summary

| Phase | Tasks | Count |
|---|---|---|
| Phase 1: Setup | T001–T004 | 4 |
| Phase 2: Foundational | T005–T016 | 12 |
| Phase 3: US1 Registration (P1) | T017–T023 | 7 |
| Phase 4: US2 Login + Protected (P1) | T024–T032 | 9 |
| Phase 5: US3 Admin RBAC (P2) | T033–T036 | 4 |
| Phase 6: Polish | T037–T041 | 5 |
| **Total** | | **41** |

| User Story | Test tasks | Impl tasks | Parallel [P] tasks |
|---|---|---|---|
| US1 | T017, T018, T019, T021 (4) | T020, T022, T023 (3) | T017, T018, T019, T021 |
| US2 | T024, T025, T026, T028 (4) | T027, T029, T030, T031, T032 (5) | T024, T025, T026, T028 |
| US3 | T033 (1) | T034, T035, T036 (3) | T033 |

**Suggested MVP scope**: Phase 1 + Phase 2 + Phase 3 (US1 only) — 23 tasks
