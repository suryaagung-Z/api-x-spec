# Developer Quickstart: Authentication and Authorization (001-authentication)

**Feature branch**: `001-authentication`  
**Stack**: Python 3.11 · FastAPI · SQLAlchemy 2.x async · PyJWT · bcrypt

---

## Prerequisites

- Python 3.11+
- Git

---

## 1. Clone & Create Virtual Environment

```bash
git clone <repo-url>
cd <repo>
git checkout 001-authentication

python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate
```

---

## 2. Install Dependencies

```bash
pip install -e ".[dev]"
# or, without pyproject.toml extras:
pip install fastapi uvicorn[standard] sqlalchemy[asyncio] alembic \
            PyJWT bcrypt pydantic-settings aiosqlite asyncpg
pip install pytest pytest-asyncio httpx black ruff mypy
```

---

## 3. Configure Environment

Copy `.env.example` to `.env` and fill in the required values:

```bash
cp .env.example .env
```

**.env.example contents**:
```dotenv
# Required — generate a strong secret: openssl rand -hex 32
JWT_SECRET_KEY=replace-me-with-a-real-secret-at-least-32-chars

# Optional overrides (these are the defaults)
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60

# SQLite (dev default) — swap for prod PostgreSQL URL
DATABASE_URL=sqlite+aiosqlite:///./dev.db
# DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/authdb
```

> **Security**: Never commit a real `JWT_SECRET_KEY` to version control.

---

## 4. Apply Database Migrations

```bash
# First run — creates dev.db (SQLite) or applies to configured PostgreSQL
alembic upgrade head
```

---

## 5. Run the Development Server

```bash
uvicorn src.main:app --reload --port 8000
```

Interactive API docs available at:
- Swagger UI: <http://localhost:8000/docs>
- ReDoc: <http://localhost:8000/redoc>

---

## 6. Smoke Test the API

### Register a user

```bash
curl -s -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"name": "Alice", "email": "alice@example.com", "password": "s3cur3P@ssword!"}' \
  | python -m json.tool
```

Expected: `201 Created` with `UserRead` JSON.

### Login and capture token

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "alice@example.com", "password": "s3cur3P@ssword!"}' \
  | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

echo "Token: $TOKEN"
```

### Access protected endpoint

```bash
curl -s http://localhost:8000/auth/me \
  -H "Authorization: Bearer $TOKEN" \
  | python -m json.tool
```

Expected: `200 OK` with `UserRead` JSON.

### Attempt admin endpoint as regular user (expect 403)

```bash
curl -s http://localhost:8000/admin/users \
  -H "Authorization: Bearer $TOKEN"
```

Expected: `403 Forbidden` with `{"error": {"code": "FORBIDDEN", ...}}`.

---

## 7. Run Tests

```bash
# All tests
pytest

# By type
pytest tests/unit/
pytest tests/integration/
pytest tests/contract/

# With coverage
pytest --cov=src --cov-report=term-missing
```

---

## 8. Code Quality Checks

```bash
# Format
black src/ tests/

# Lint
ruff check src/ tests/

# Type check
mypy src/
```

---

## 9. Project Structure Overview

```text
src/
├── main.py              # FastAPI app factory, exception handlers, router registration
├── api/
│   ├── routers/
│   │   ├── auth.py      # POST /auth/register, POST /auth/login, GET /auth/me
│   │   └── admin.py     # GET /admin/users (admin-only)
│   ├── schemas/
│   │   ├── auth.py      # RegisterRequest, LoginRequest, TokenResponse, UserRead
│   │   └── errors.py    # ErrorDetail, ErrorEnvelope
│   └── dependencies/
│       └── auth.py      # get_current_user(), require_role(role)
├── application/
│   └── auth_service.py  # register(), login() use cases (pure Python, no HTTP)
├── domain/
│   ├── models.py        # User entity, UserRole enum
│   └── exceptions.py    # Domain exceptions (EmailAlreadyExistsError, etc.)
└── infrastructure/
    ├── db/
    │   ├── session.py   # AsyncEngine, AsyncSessionLocal, get_db dependency
    │   └── models.py    # SQLAlchemy ORM User model
    ├── repositories/
    │   └── user_repository.py
    └── auth/
        ├── jwt.py       # create_access_token(), decode_token()
        └── password.py  # hash_password(), verify_password()

tests/
├── unit/            # Domain logic, service, JWT, password utils
├── integration/     # Repository + real SQLite DB
└── contract/        # Full HTTP flows via httpx.AsyncClient

alembic/             # DB migrations
.env.example         # Environment variable template
pyproject.toml       # Dependencies, tool config (black, ruff, mypy)
```

---

## 10. Key Architectural Notes

- **Error envelope**: All errors return `{"error": {"code", "message", "httpStatus"}}` — see [contracts/error-envelope.md](contracts/error-envelope.md).
- **JWT claims**: `sub` (user id), `role`, `iat`, `exp`; signed with HS256.
- **Role checking**: `get_current_user` → 401 on bad token; `require_role("admin")` → 403 on wrong role.
- **No tokens stored**: JWTs are stateless; there is no token blacklist in v1.
- **Password limit**: Passwords are capped at 72 characters (bcrypt limit); the API validates and rejects longer inputs.
- **Email uniqueness**: Stored as lowercase; unique index enforced at both app and DB layer.
