# api-x-spec Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-03-05

## Active Technologies
- Python 3.11+ + FastAPI, SQLAlchemy 2.x async, Alembic 1.13, Pydantic v2 (with `AwareDatetime`, `computed_field`), pydantic-settings, asyncpg (prod), aiosqlite (dev/test) (002-event-management)
- PostgreSQL 15+ (prod); SQLite (dev/test via aiosqlite) (002-event-management)
- Python 3.11+ + FastAPI, SQLAlchemy 2.x async, Alembic 1.13, Pydantic v2, pydantic-settings, asyncpg (prod), aiosqlite (dev/test) (003-event-registration)
- Python 3.11+ + FastAPI, SQLAlchemy 2.x async, Pydantic v2, pydantic-settings, asyncpg (prod), aiosqlite (dev/test) (004-admin-reporting)
- Python 3.11+ + FastAPI ≥0.111.0, Pydantic v2 Field annotations, OpenAPI 3.1.0 (005-swagger-api-docs)

- Python 3.11+ + FastAPI, PyJWT 2.11, bcrypt 5.0, SQLAlchemy 2.0 async, (001-authentication)

## Project Structure

```text
backend/
frontend/
tests/
```

## Commands

cd src; pytest; ruff check .

## Code Style

Python 3.11+: Follow standard conventions

## Recent Changes
- 005-swagger-api-docs: Added Python 3.11+ + FastAPI ≥0.111.0, Pydantic v2 Field annotations, OpenAPI 3.1.0
- 004-admin-reporting: Added Python 3.11+ + FastAPI, SQLAlchemy 2.x async, Pydantic v2, pydantic-settings, asyncpg (prod), aiosqlite (dev/test)
- 003-event-registration: Added Python 3.11+ + FastAPI, SQLAlchemy 2.x async, Alembic 1.13, Pydantic v2, pydantic-settings, asyncpg (prod), aiosqlite (dev/test)


<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
