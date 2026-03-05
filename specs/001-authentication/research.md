# Research: Authentication and Authorization (001-authentication)

**Phase**: 0 — Research  
**Date**: 2026-03-05  
**Status**: Complete — all NEEDS CLARIFICATION resolved

---

## 1. JWT Library

**Decision**: `PyJWT` 2.11.0  
**Rationale**: Actively maintained (latest release Jan 2026), Auth0-backed, zero mandatory
dependencies for HS256, and the library FastAPI's official tutorial explicitly recommends
(switched from `python-jose`). Clean single-purpose API.  
**Alternatives considered**:
- `python-jose` 3.5.0 — older FastAPI docs used this; slower release cadence, known CVEs
  in its `native-python` crypto backend, requires choosing a crypto backend at install time.
- `joserfc` — modern RFC-compliant but very young ecosystem, limited FastAPI examples.
- `authlib` — full OAuth/OIDC stack; too heavy for basic JWT signing.

**Key patterns**:
- Encode: `jwt.encode(payload, SECRET_KEY, algorithm="HS256")` with `sub`, `role`, `iat`, `exp`.
- Decode: `jwt.decode(token, SECRET_KEY, algorithms=["HS256"], options={"require": ["sub","exp","iat"]})` —
  always pass `algorithms` as a list (prevents algorithm-confusion attacks).
- Expiry validation is automatic — `jwt.ExpiredSignatureError` (subclass of `InvalidTokenError`)
  is raised when `exp` is past.
- Use `datetime.now(timezone.utc)` exclusively; `datetime.utcnow()` is deprecated.

---

## 2. Password Hashing

**Decision**: `bcrypt` 5.0.0 (PyCA, Rust-backed)  
**Rationale**: Maintained (Sep 2025 release), Rust backend is fast and memory-safe,
no dependency on `passlib`. `passlib[bcrypt]` has been unmaintained since 2020 and emits
`AttributeError` on bcrypt 4.x+ due to removed `__about__`.  
**Alternatives considered**:
- `passlib[bcrypt]` 1.7.4 — `CryptContext` migration pattern is useful but the library is
  unmaintained; breaks silently on newer bcrypt versions.
- `argon2-cffi` (Argon2) — stronger algorithm but spec explicitly requires bcrypt.

**Key patterns**:
- Hash: `bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()`
- Verify: `bcrypt.checkpw(plain.encode(), hashed.encode())`
- Cost factor: **rounds=12** (~250ms on modern hardware; OWASP recommends ≥100ms).
- Enforce max 72-byte password at API layer — bcrypt 5.x raises `ValueError` beyond that.
- Timing-safe enumeration defense: always verify against a dummy hash when user not found.

---

## 3. Role-Based Access Control (RBAC)

The idiomatic FastAPI pattern is a **dependency factory** — a function that accepts a role
argument and returns a `Callable` that FastAPI can inject. The returned callable itself
depends on `get_current_user`, forming a sub-dependency chain.

```python
# app/dependencies/auth.py

from typing import Annotated
from fastapi import Depends, HTTPException, status
from app.domain.models import User

def require_role(required_role: str):
    """Factory: returns a FastAPI dependency that enforces a specific role."""
    def role_checker(
        current_user: Annotated[User, Depends(get_current_user)]
    ) -> User:
        if current_user.role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": {
                        "code": "FORBIDDEN",
                        "message": "Insufficient permissions",
                        "httpStatus": 403,
                    }
                },
            )
        return current_user
    return role_checker

# Usage in router:
@router.get("/admin/users")
async def list_users(
    _: Annotated[User, Depends(require_role("admin"))]
):
    ...
```

For multiple allowed roles, extend to `require_any_role(*roles)`:

```python
def require_any_role(*allowed_roles: str):
    def role_checker(
        current_user: Annotated[User, Depends(get_current_user)]
    ) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(status_code=403, ...)
        return current_user
    return role_checker
```

---

### Carrying Role in JWT Claims

### JWT Payload Structure

Per the spec clarification (2026-03-05), the token **must** carry `sub`, `role`, `iat`, `exp`
with HS256 signing. The `role` field is a **private claim** (not reserved by RFC 7519).

```python
# Token payload at issuance (login):
{
    "sub": "usr_01HXYZ...",   # unique user identifier (UUID or ULID)
    "role": "admin",           # "user" | "admin"
    "iat": 1741132800,         # issued-at (UTC epoch)
    "exp": 1741136400          # expiry = iat + 3600 (60 min per spec)
}

# Python – building the token:
def create_access_token(subject: str, role: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
```

### Extracting Role in `get_current_user`

```python
# app/dependencies/auth.py

from typing import Annotated
import jwt
from jwt.exceptions import InvalidTokenError
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from app.domain.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

class TokenData(BaseModel):
    sub: str
    role: str

async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)]
) -> User:
    """
    Layer: Application boundary / FastAPI dependency.
    Validates the JWT and returns a domain User object.
    Raises 401 on any token problem.
    """
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={
            "error": {
                "code": "UNAUTHORIZED",
                "message": "Could not validate credentials",
                "httpStatus": 401,
            }
        },
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=["HS256"],
        )
        token_data = TokenData(sub=payload["sub"], role=payload["role"])
    except (InvalidTokenError, KeyError, ValidationError):
        raise credentials_exc

    user = await user_repository.get_by_id(token_data.sub)
    if user is None:
        raise credentials_exc
    return user
```

**Key point**: `role` is trusted from the JWT claim — the DB lookup is only to confirm the
user still exists (not revoked). Do not re-fetch the role from the DB on every request
unless you need real-time role revocation (expensive); embed it in the token with an
appropriate short expiry (60 min as specified).

---

### Admin-Only Routes vs General Protected Routes

Use a two-tier dependency chain. Both tiers live in `app/dependencies/auth.py`:

```
get_current_user          → validates token integrity → 401 on failure
    └── require_role(...)     → checks role claim     → 403 on failure
```

### General Protected Route (any authenticated user)

```python
@router.get("/auth/me")
async def get_profile(
    current_user: Annotated[User, Depends(get_current_user)]
):
    return current_user
```

### Admin-Only Route

```python
@router.get("/admin/users")
async def list_all_users(
    _: Annotated[User, Depends(require_role("admin"))]
):
    ...
```

### Protecting an Entire Router with `dependencies=`

```python
# app/routers/admin.py
from fastapi import APIRouter, Depends
from app.dependencies.auth import require_role

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(require_role("admin"))],  # applies to ALL routes
)

@router.get("/users")
async def list_users(): ...

@router.delete("/users/{user_id}")
async def delete_user(user_id: str): ...
```

This is the preferred pattern when an entire router is admin-only: declare the guard
once on the router, not on each endpoint.

---

### 401 vs 403 Semantics

| Situation | Status | Code string | `WWW-Authenticate` header |
|---|---|---|---|
| Missing `Authorization` header | **401** | `UNAUTHORIZED` | `Bearer` (required by RFC 6750) |
| Malformed / tampered token | **401** | `UNAUTHORIZED` | `Bearer` |
| Expired token (`exp` in past) | **401** | `UNAUTHORIZED` | `Bearer` |
| Valid token, wrong role | **403** | `FORBIDDEN` | not required |

This matches the spec clarification: *"Login salah, request tanpa token, token invalid atau
kedaluwarsa → 401; akses endpoint admin-only oleh user ber-role `user` → 403."*

### FastAPI's OAuth2 Scope System vs Custom RBAC

FastAPI's built-in `Security()` + `SecurityScopes` raises **401** even for insufficient
scopes (following the OAuth2 spec, which conflates authn and authz at this level).
**For explicit role-based 403 responses, do not use `SecurityScopes`** — use the
`require_role()` factory above, which explicitly raises `HTTP_403_FORBIDDEN`.

```python
# 401 path (in get_current_user — token problems):
raise HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    headers={"WWW-Authenticate": "Bearer"},   # REQUIRED per RFC 6750
    detail={"error": {"code": "UNAUTHORIZED", ...}},
)

# 403 path (in require_role — authorization failure):
raise HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,    # no WWW-Authenticate header
    detail={"error": {"code": "FORBIDDEN", ...}},
)
```

---

### Clean Architecture Placement

### Layer Map

```
┌─────────────────────────────────────────────────────┐
│  API Layer (routers/)                               │
│  • Declare which dependency each endpoint needs     │
│  • No auth logic here; only Depends(require_role()) │
├─────────────────────────────────────────────────────┤
│  Dependency / Application Boundary (dependencies/)  │ ← role checking lives HERE
│  • get_current_user() — token validation → User     │
│  • require_role()     — role check → 403 or pass    │
│  • These are HTTP/FastAPI concepts; only this layer │
│    knows about Request, HTTPException, Bearer       │
├─────────────────────────────────────────────────────┤
│  Application Services (services/)                   │
│  • Receive a User object as a plain Python arg      │
│  • May assert on user.role for business logic,      │
│    but raise a domain exception, NOT HTTPException  │
│  • e.g., EventService.cancel(event, actor: User)    │
├─────────────────────────────────────────────────────┤
│  Domain (domain/)                                   │
│  • User, Role, etc. are plain Pydantic/dataclass    │
│  • Role is a domain concept (UserRole enum)         │
│  • Zero knowledge of HTTP, JWT, FastAPI             │
├─────────────────────────────────────────────────────┤
│  Infrastructure (infrastructure/)                   │
│  • JWT encode/decode (security.py)                  │
│  • Password hashing (bcrypt via pwdlib)             │
│  • DB queries for user lookup                       │
└─────────────────────────────────────────────────────┘
```

### Specific Placement Rules

| Concern | Lives in | Rationale |
|---|---|---|
| JWT encode/decode, secret key | `app/core/security.py` or `app/infrastructure/auth/jwt.py` | Pure crypto/infra, no HTTP knowledge |
| Token extraction from `Authorization` header | `OAuth2PasswordBearer` (FastAPI built-in) | Framework-provided |
| `get_current_user()` — token validation → domain User | `app/dependencies/auth.py` | Application boundary; maps infra token to domain object |
| `require_role()` — role enforcement → 403 | `app/dependencies/auth.py` | HTTP-level guard; belongs with other HTTP dependencies |
| Business logic requiring role checks | `app/services/` | Domain-level, using domain exceptions |
| `UserRole` enum (`user`, `admin`) | `app/domain/models.py` | Domain concept |

### Domain Exception vs HTTPException Pattern

When services need to enforce authorization semantics (e.g. ownership checks), they
raise a domain exception that an exception handler translates — **not** `HTTPException`
directly:

```python
# domain/exceptions.py
class PermissionDeniedError(Exception): ...

# services/event_service.py
def cancel_event(event: Event, actor: User):
    if event.organizer_id != actor.id and actor.role != UserRole.ADMIN:
        raise PermissionDeniedError("Only the organizer or an admin can cancel")
    ...

# main.py / exception handlers
@app.exception_handler(PermissionDeniedError)
async def permission_denied_handler(request, exc):
    return JSONResponse(status_code=403, content={"error": {"code": "FORBIDDEN", ...}})
```

This keeps services testable without HTTP context.

---

## Recommended Dependency Structure (Summary)

```python
# Dependency tree for admin-only endpoint:

require_role("admin")
    └── get_current_user(token: str = Depends(oauth2_scheme))
            └── jwt.decode(token)          # infrastructure
            └── user_repo.get_by_id(sub)   # infrastructure

# For general authenticated endpoint:
get_current_user(token)     → 401 if token invalid
# (no role check)

# For admin-only endpoint or router:
require_role("admin")       → depends on get_current_user
                             → 403 if role != "admin"
```

---

## Libraries to Consider

| Library | Purpose | Recommendation |
|---|---|---|
| **`PyJWT`** (`pip install pyjwt`) | JWT encode/decode | **Use this** — actively maintained, official FastAPI docs recommendation (2025+) |
| **`pwdlib[argon2]`** | Password hashing | **Use this** — new recommended replacement over `passlib` in FastAPI docs |
| `passlib[bcrypt]` | Password hashing (legacy) | Still works; use if spec mandates bcrypt explicitly (spec says bcrypt, so use `passlib[bcrypt]`) |
| `python-jose` | JWT alternative | Avoid — less maintained, known CVEs in older versions |
| **`fastapi-users`** | Full authn/authz library | Optional — opinionated, good for fast setup, but adds abstraction overhead |
| `casbin` | Policy-based RBAC | Consider if role hierarchy or resource-scoped permissions are needed later; overkill for two-role system |

### Decision for This Project

Given the spec (two roles: `user` / `admin`, HS256, bcrypt, 60-min expiry):

- **`PyJWT`** for token operations
- **`passlib[bcrypt]`** for password hashing (spec explicitly states bcrypt)
- No external RBAC library needed — the `require_role()` factory pattern is sufficient
- No `fastapi-users` — adds coupling for minor convenience

---

## Key Decision Points for `plan.md`

1. **JWT role claim** — embed `role` directly in token payload; no DB lookup for role on
   each request. Acceptable given 60-min expiry and the absence of a real-time revocation
   requirement in the spec.

2. **`require_role()` factory** — single dependency file `src/api/dependencies/auth.py` exports
   both `get_current_user` and `require_role`. All routers import from here.

3. **Router-level guard** — admin router uses `dependencies=[Depends(require_role("admin"))]`
   to avoid per-endpoint repetition.

4. **401 carries `WWW-Authenticate: Bearer`** — required by RFC 6750 §3;
   must set `headers={"WWW-Authenticate": "Bearer"}` explicitly.

5. **Consistent error envelope** — both 401 and 403 use
   `{"error": {"code": str, "message": str, "httpStatus": int}}` per spec clarification.

---

## 4. Storage & ORM

**Decision**: SQLAlchemy 2.x async + Alembic + PostgreSQL (prod) / SQLite (dev)  
**Rationale**: SQLAlchemy 2.x async is the community standard for FastAPI; Alembic is the
canonical migration tool; SQLite via `aiosqlite` for zero-setup dev, PostgreSQL via
`asyncpg` for production.  
**Alternatives considered**:
- Tortoise ORM — async-native but smaller ecosystem.
- SQLModel — wraps SQLAlchemy + Pydantic; still maturing.
- `encode/databases` — raw async queries, no ORM; too low-level.

**Library versions**:

| Library | Version |
|---|---|
| `sqlalchemy[asyncio]` | `>=2.0.48` |
| `asyncpg` (prod) | `>=0.29` |
| `aiosqlite` (dev/test) | `>=0.20` |
| `alembic` | `>=1.13` |

**Key patterns**:
- `AsyncSession` per request via `get_db()` dependency — never shared across tasks.
- `expire_on_commit=False` on `async_sessionmaker` — mandatory; prevents lazy-load errors post-commit.
- Lazy loading disabled — use `selectinload()` or `joinedload()` explicitly.
- Repository pattern: `UserRepository(session)` encapsulates all user queries.
- SQLAlchemy ORM models (`src/infrastructure/`) and Pydantic schemas (`src/api/schemas/` or
  `src/application/dtos/`) are kept as **separate classes**.
- Pydantic v2: `model_config = ConfigDict(from_attributes=True)` (replaces `orm_mode=True`).

---

## 5. FastAPI & Runtime

**Decision**: FastAPI (latest stable), Python 3.11+, Pydantic v2  
**Rationale**: Directly specified by the project constitution as default stack.

**Error envelope** (per spec FR-011 / clarification):
```json
{
  "error": {
    "code": "EMAIL_ALREADY_EXISTS",
    "message": "An account with this email already exists.",
    "httpStatus": 409
  }
}
```
Implement via a custom exception class + FastAPI `exception_handler`. All
`HTTPException`-derived errors from auth dependencies must also use this envelope.

---

## 6. Configuration & Secrets

**Decision**: `pydantic-settings` `BaseSettings` loaded from environment variables  
**Rationale**: Constitution mandates env-var-based config; `pydantic-settings` is the
idiomatic FastAPI approach with full type hints and validation.

| Variable | Description | Default |
|---|---|---|
| `JWT_SECRET_KEY` | HS256 signing secret (≥32 bytes) | — (required) |
| `JWT_ALGORITHM` | Signing algorithm | `HS256` |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | Token expiry in minutes | `60` |
| `DATABASE_URL` | Async SQLAlchemy URL | `sqlite+aiosqlite:///./dev.db` |

---

## 7. Testing Stack

**Decision**: `pytest` + `httpx` (async) + `pytest-asyncio`  
**Rationale**: Constitution mandates `pytest`. `httpx` with `AsyncClient` is the FastAPI
recommended async test client. `pytest-asyncio` enables `async def` test functions.

**Test DB**: SQLite in-memory (`sqlite+aiosqlite:///:memory:`) per test session via
`override_get_db` fixture.

| Test type | Tool | Location |
|---|---|---|
| Unit (domain, services) | `pytest` + `unittest.mock` | `tests/unit/` |
| Integration (DB + repository) | `pytest` + `pytest-asyncio` | `tests/integration/` |
| Contract (HTTP API endpoints) | `pytest` + `httpx.AsyncClient` | `tests/contract/` |

---

## 8. Code Quality

**Decision**: `black` (formatter) + `ruff` (linter) + `mypy` (type checker)  
**Rationale**: Constitution mandates an auto-formatter and linter; `black`+`ruff` is the
current FastAPI/Python community standard. `mypy` enforces type-hints compliance.

