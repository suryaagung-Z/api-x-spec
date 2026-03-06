"""Integration tests for UserRepository against a real in-memory SQLite DB."""
from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.domain.exceptions import EmailAlreadyExistsError
from src.infrastructure.db.models import Base
from src.infrastructure.repositories.user_repository import UserRepository

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture()
async def repo_session():
    engine = create_async_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
    factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
        engine, expire_on_commit=False
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with factory() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.mark.asyncio
async def test_create_persists_user_with_lowercase_email(repo_session: AsyncSession):
    repo = UserRepository(repo_session)
    user = await repo.create("Test", "Test@Example.COM", "hashed")
    assert user.email == "test@example.com"
    assert user.id is not None


@pytest.mark.asyncio
async def test_get_by_email_returns_user(repo_session: AsyncSession):
    repo = UserRepository(repo_session)
    await repo.create("Alice", "alice@repo.com", "hashed")
    found = await repo.get_by_email("alice@repo.com")
    assert found is not None
    assert found.email == "alice@repo.com"


@pytest.mark.asyncio
async def test_get_by_email_returns_none_for_unknown(repo_session: AsyncSession):
    repo = UserRepository(repo_session)
    assert await repo.get_by_email("unknown@repo.com") is None


@pytest.mark.asyncio
async def test_get_by_email_case_insensitive(repo_session: AsyncSession):
    """Mixed-case lookup finds the user stored as lowercase."""
    repo = UserRepository(repo_session)
    await repo.create("Bob", "bob@repo.com", "hashed")
    found = await repo.get_by_email("BOB@REPO.COM")
    assert found is not None
    assert found.email == "bob@repo.com"


@pytest.mark.asyncio
async def test_create_duplicate_email_raises(repo_session: AsyncSession):
    repo = UserRepository(repo_session)
    await repo.create("Carol", "carol@repo.com", "hashed")
    with pytest.raises(EmailAlreadyExistsError):
        await repo.create("Carol2", "carol@repo.com", "hashed2")


@pytest.mark.asyncio
async def test_create_duplicate_email_different_case_raises(repo_session: AsyncSession):
    """Case-insensitive email uniqueness enforcement: C3."""
    repo = UserRepository(repo_session)
    await repo.create("Dave", "dave@repo.com", "hashed")
    with pytest.raises(EmailAlreadyExistsError):
        await repo.create("Dave2", "Dave@Repo.Com", "hashed2")
