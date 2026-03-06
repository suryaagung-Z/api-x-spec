"""Shared async pytest fixtures for all test suites."""
from __future__ import annotations

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.infrastructure.db.models import Base

# ---------------------------------------------------------------------------
# In-memory SQLite engine for tests (never touches dev.db)
# ---------------------------------------------------------------------------
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

_test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)
_TestSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    _test_engine, expire_on_commit=False
)


@pytest_asyncio.fixture()
async def test_client():
    """Async httpx client wired to the FastAPI app with an in-memory DB."""
    # Late import to avoid circular imports and allow engine override
    import src.infrastructure.db.session as db_session_module
    from src.main import app

    # Patch the session factory used by get_db()
    original_factory = db_session_module.AsyncSessionLocal
    db_session_module.AsyncSessionLocal = _TestSessionLocal  # type: ignore[assignment]

    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    db_session_module.AsyncSessionLocal = original_factory  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Helper: create a user via the API (and optionally promote to admin via DB)
# ---------------------------------------------------------------------------
async def create_user(
    client: AsyncClient,
    *,
    name: str,
    email: str,
    password: str,
    role: str = "user",
) -> dict:
    """Register a user through POST /auth/register and return the UserRead dict.

    For admin role, updates the role directly in the DB after registration
    (admin creation via API is out of scope for this feature).
    """
    response = await client.post(
        "/auth/register",
        json={"name": name, "email": email, "password": password},
    )
    assert response.status_code == 201, response.text
    user_data: dict = response.json()

    if role == "admin":
        # Promote to admin directly via DB
        from sqlalchemy import update

        from src.infrastructure.db.models import User as OrmUser

        async with _TestSessionLocal() as session:
            await session.execute(
                update(OrmUser)
                .where(OrmUser.email == email.lower())
                .values(role="admin")
            )
            await session.commit()

        user_data["role"] = "admin"

    return user_data


async def _get_token(client: AsyncClient, email: str, password: str) -> str:
    response = await client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200, response.text
    return str(response.json()["access_token"])


@pytest_asyncio.fixture()
async def user_auth_headers(test_client: AsyncClient) -> dict:
    """Register + login a regular user, return Authorization headers."""
    await create_user(
        test_client,
        name="Test User",
        email="user@test.com",
        password="userP@ss123",
        role="user",
    )
    token = await _get_token(test_client, "user@test.com", "userP@ss123")
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture()
async def admin_auth_headers(test_client: AsyncClient) -> dict:
    """Register + login an admin user, return Authorization headers."""
    await create_user(
        test_client,
        name="Test Admin",
        email="admin@test.com",
        password="adminP@ss123",
        role="admin",
    )
    token = await _get_token(test_client, "admin@test.com", "adminP@ss123")
    return {"Authorization": f"Bearer {token}"}
