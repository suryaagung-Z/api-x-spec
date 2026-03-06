# Implementation Plan: Authentication and Authorization

**Branch**: `001-authentication` | **Date**: 2026-03-05 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `/specs/001-authentication/spec.md`

## Summary

Implement a JWT-based authentication and role-based authorization system for the API-X
backend. Users can register (bcrypt-hashed passwords), log in to receive a signed
HS256 JWT (60-minute default expiry), and access protected endpoints by sending
`Authorization: Bearer <token>`. Two roles are supported (`user`, `admin`);
admin-only endpoints reject `user`-role tokens with HTTP 403. All auth and error
responses use a consistent JSON envelope `{"error": {"code", "message", "httpStatus"}}`.

Tech stack: Python 3.11 · FastAPI · SQLAlchemy 2.x async · Alembic · PyJWT 2.x · bcrypt 5.x.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: FastAPI, PyJWT 2.11, bcrypt 5.0, SQLAlchemy 2.0 async,
  Alembic 1.13, pydantic-settings, asyncpg (prod), aiosqlite (dev/test)  
**Storage**: PostgreSQL 15+ (production) / SQLite (development & test)  
**Testing**: pytest, pytest-asyncio, httpx (AsyncClient)  
**Target Platform**: Linux server  
**Project Type**: web-service (REST API)  
**Performance Goals**: ≥95% of register+login flows complete in <5 s under normal load (SC-001)  
**Constraints**: <200ms p95 for token validation (→ SC-005 in spec.md); bcrypt hashing ~250ms (rounds=12) is acceptable on the login path  
**Scale/Scope**: Initial; scales to support growing user base with PostgreSQL in prod
**Code Quality Tooling**: Black (formatter) + Ruff (linter) + mypy --strict; both MUST be applied to all new modules. CI gate: `black --check src/ tests/` and `ruff check src/ tests/`. Configured in `pyproject.toml` (T004). Satisfies constitution §Technology "MUST be documented in the plan or project README" requirement.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Check | Status | Notes |
|---|---|---|
| **Stack alignment** | ✅ PASS | Python 3.11 + FastAPI — matches constitution default; PyJWT, bcrypt, SQLAlchemy are mainstream, actively maintained |
| **Clean architecture** | ✅ PASS | Boundaries defined (see Project Structure): API layer → application services → domain → infrastructure. Domain has no HTTP/framework imports |
| **Testing strategy** | ✅ PASS | Every user story has contract tests (httpx) + unit tests for domain/service logic + integration tests for repository; tests are non-negotiable |
| **Simplicity & observability** | ✅ PASS | Single project, no extra services; structured logging via Python `logging`; no extra abstraction layers beyond the standard clean-arch split |

**No violations** — no Complexity Tracking entries required.

## Phases Overview

| Phase | Name | Purpose |
|---|---|---|
| Phase 1 | Setup | Initialize project skeleton, toolchain, and configuration files |
| Phase 2 | Foundational | Domain models, infra adapters, DB schema, app wiring — **blocks all user stories** |
| Phase 3 | User Story 1 (P1) | Registration with bcrypt password storage and email uniqueness enforcement |
| Phase 4 | User Story 2 (P1) | Login, JWT issuance, and protected endpoint access (`GET /auth/me`) |
| Phase 5 | User Story 3 (P2) | Admin RBAC — role-gated endpoint enforcement (`GET /admin/users`) |
| Phase 6 | Polish | Observability, security hardening, and performance verification |

See `tasks.md` for detailed task breakdown and dependency order.

## Project Structure

### Documentation (this feature)

```text
specs/001-authentication/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── openapi.yaml
│   └── error-envelope.md
└── tasks.md             # Phase 2 output (/speckit.tasks — NOT created here)
```

### Source Code (repository root)

```text
src/
├── api/
│   ├── routers/
│   │   ├── auth.py          # POST /auth/register, POST /auth/login, GET /auth/me
│   │   └── admin.py         # GET /admin/users (admin-only router)
│   ├── schemas/
│   │   ├── auth.py          # RegisterRequest, LoginRequest, TokenResponse, UserRead
│   │   └── errors.py        # ErrorDetail, ErrorEnvelope (Pydantic)
│   └── dependencies/
│       └── auth.py          # get_current_user(), require_role(role)
├── application/
│   └── auth_service.py      # register(), login() use cases (no HTTP)
├── domain/
│   ├── models.py            # User dataclass/entity, UserRole enum
│   └── exceptions.py        # DomainError, EmailAlreadyExistsError, ...
└── infrastructure/
    ├── db/
    │   ├── session.py       # engine, AsyncSessionLocal, get_db dependency
    │   └── models.py        # SQLAlchemy ORM User model
    ├── repositories/
    │   └── user_repository.py  # UserRepository (get_by_email, create, ...)
    └── auth/
        ├── jwt.py           # create_access_token(), decode_token()
        └── password.py      # hash_password(), verify_password()

tests/
├── unit/
│   ├── test_auth_service.py
│   ├── test_jwt.py
│   └── test_password.py
├── integration/
│   └── test_user_repository.py
└── contract/
    ├── test_register.py
    ├── test_login.py
    ├── test_protected.py
    └── test_admin.py

alembic/
├── env.py
└── versions/

pyproject.toml      # dependencies, black/ruff/mypy config
.env.example        # JWT_SECRET_KEY, DATABASE_URL, JWT_ACCESS_TOKEN_EXPIRE_MINUTES
```

**Structure Decision**: Single project layout (Option 1) — clean-arch split within `src/`.
No separate services or packages needed for a self-contained auth module.

**Composition Root**: `src/main.py` — FastAPI app factory, `Settings` injection via `pydantic-settings`, domain exception handler registration (`EmailAlreadyExistsError` → 409, `InvalidCredentialsError` → 401, `UserNotFoundError` → 401, `RequestValidationError` → 422), and router mounting (`/auth`, `/admin`). All dependency wiring flows outward from this module.

## Complexity Tracking

> No violations — table not required.
