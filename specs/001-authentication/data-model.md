# Data Model: Authentication and Authorization (001-authentication)

**Phase**: 1 — Design  
**Date**: 2026-03-05  
**Source**: [spec.md](spec.md) §Key Entities + §Requirements

---

## Entities

### User

Represents an individual account that can authenticate and be authorized.

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID / ULID (string PK) | NOT NULL, PK, unique | Generated on creation; used as JWT `sub` claim |
| `name` | string | NOT NULL, max 255 | Display name provided at registration |
| `email` | string | NOT NULL, unique, max 255 | Case-insensitive unique index; used as login identifier |
| `hashed_password` | string | NOT NULL | bcrypt hash (rounds=12); NEVER plain text |
| `role` | enum(`user`, `admin`) | NOT NULL, default `user` | Determines access level |
| `is_active` | boolean | NOT NULL, default `true` | Reserved for future deactivation logic |
| `created_at` | datetime (UTC) | NOT NULL, server default | Audit timestamp |

**Validation rules**:
- `email` — valid email address format; must be unique across all users (case-insensitive).
- `password` (input, not stored) — min 8 chars, max 72 chars (bcrypt 72-byte limit).
- `name` — non-empty, max 255 characters.
- `role` — must be one of `user` | `admin`; default on registration is `user`.

**State transitions**:
```
[new] → is_active=true (on registration)
      → is_active=false (future: deactivation — out of scope for this feature)
```

**SQLAlchemy ORM model location**: `src/infrastructure/db/models.py`  
**Domain entity location**: `src/domain/models.py` (plain Python dataclass or Pydantic model)

---

### UserRole (Enum)

Value object representing the permission tier of a User.

| Value | Description |
|---|---|
| `user` | Standard authenticated user; can access general protected endpoints |
| `admin` | Elevated role; can access admin-only endpoints in addition to user endpoints |

**Location**: `src/domain/models.py`

---

### AuthToken (JWT — not persisted)

Represents the JWT access token issued at login. Not stored in the database; stateless.

| Claim | Type | Description |
|---|---|---|
| `sub` | string | Unique user identifier (`User.id`); RFC 7519 Subject |
| `role` | string (`user`\|`admin`) | User's role encoded at time of issuance |
| `iat` | integer (epoch seconds, UTC) | Issued-at timestamp; RFC 7519 |
| `exp` | integer (epoch seconds, UTC) | Expiry timestamp = `iat` + 3600 seconds (default 60 min) |

**Signing**: HS256 with `JWT_SECRET_KEY` (env var, ≥32 bytes).  
**Transmission**: HTTP header `Authorization: Bearer <token>`.  
**Expiry**: 60 minutes default; configurable via `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` env var.  
**Not stored**: No token table or blacklist in this specification (re-login required after expiry).

---

## Relationships

```
User ──< (no FK relationships in this feature scope)
```

`User` is the only persisted entity for this feature. `Role` is an enum field on `User`, not
a separate table. `AuthToken` is ephemeral (stateless JWT).

---

## Database Schema (SQL — PostgreSQL dialect)

```sql
CREATE TABLE users (
    id          VARCHAR(36)  PRIMARY KEY,                  -- UUID v4 or ULID
    name        VARCHAR(255) NOT NULL,
    email       VARCHAR(255) NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    role        VARCHAR(10)  NOT NULL DEFAULT 'user'
                    CHECK (role IN ('user', 'admin')),
    is_active   BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX ix_users_email_lower ON users (LOWER(email));
```

> **Note**: The case-insensitive email uniqueness is enforced at application layer
> (`email.lower()` before storage) and at DB layer via the functional index.

---

## Pydantic Schemas (API layer — `src/api/schemas/`)

### Input schemas

```python
class RegisterRequest(BaseModel):
    name: str                   # min_length=1, max_length=255
    email: EmailStr             # validated email format
    password: str               # min_length=8, max_length=72

class LoginRequest(BaseModel):
    email: EmailStr
    password: str               # min_length=1 (no length hint to attacker)
```

### Output schemas

```python
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    email: str
    role: str
    is_active: bool
    created_at: datetime
```

### Error schema

```python
class ErrorDetail(BaseModel):
    code: str           # e.g. "EMAIL_ALREADY_EXISTS"
    message: str        # human-readable
    httpStatus: int     # mirrors HTTP status code

class ErrorEnvelope(BaseModel):
    error: ErrorDetail
```

---

## Domain Exceptions (`src/domain/exceptions.py`)

| Exception | When raised | HTTP mapping |
|---|---|---|
| `EmailAlreadyExistsError` | Registration with duplicate email | 409 Conflict |
| `InvalidCredentialsError` | Wrong email or password on login | 401 Unauthorized |
| `UserNotFoundError` | Token sub refers to deleted user | 401 Unauthorized |

Exception-to-HTTP mapping is handled in `src/api/` via FastAPI exception handlers,
**never inside domain or service code**.

---

## Error Code Reference

| `code` string | `httpStatus` | Trigger |
|---|---|---|
| `EMAIL_ALREADY_EXISTS` | 409 | Registration with already-registered email |
| `UNAUTHORIZED` | 401 | Missing/invalid/expired/tampered JWT; wrong login credentials |
| `FORBIDDEN` | 403 | Valid JWT but insufficient role for endpoint |
| `VALIDATION_ERROR` | 422 | Pydantic input validation failure |
