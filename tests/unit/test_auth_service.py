"""Unit tests for auth_service register() and login() use cases."""
from __future__ import annotations

from datetime import UTC
from unittest.mock import AsyncMock, patch

import pytest

from src.domain.exceptions import EmailAlreadyExistsError, InvalidCredentialsError
from src.domain.models import User, UserRole

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user(**overrides) -> User:
    from datetime import datetime

    defaults = dict(
        id="test-id-001",
        name="Test User",
        email="test@example.com",
        hashed_password="$2b$12$fakehash",
        role=UserRole.user,
        created_at=datetime.now(tz=UTC),
    )
    defaults.update(overrides)
    return User(**defaults)


# ---------------------------------------------------------------------------
# register() tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_register_success():
    session = AsyncMock()
    expected_user = _make_user()

    with (
        patch(
            "src.application.auth_service.UserRepository"
        ) as MockRepo,
        patch(
            "src.application.auth_service.hash_password",
            return_value="$2b$12$fakehash",
        ),
    ):
        mock_repo = MockRepo.return_value
        mock_repo.get_by_email = AsyncMock(return_value=None)
        mock_repo.create = AsyncMock(return_value=expected_user)

        from src.application.auth_service import register

        user = await register("Test User", "test@example.com", "password123", session)

    assert user.email == "test@example.com"
    mock_repo.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_register_raises_on_duplicate_email():
    session = AsyncMock()
    existing = _make_user()

    with patch("src.application.auth_service.UserRepository") as MockRepo:
        mock_repo = MockRepo.return_value
        mock_repo.get_by_email = AsyncMock(return_value=existing)

        from src.application.auth_service import register

        with pytest.raises(EmailAlreadyExistsError):
            await register("Test", "test@example.com", "password123", session)


@pytest.mark.asyncio
async def test_register_password_is_hashed_not_plain():
    session = AsyncMock()
    plain = "plaintext-password!"

    with (
        patch("src.application.auth_service.UserRepository") as MockRepo,
        patch(
            "src.application.auth_service.hash_password",
            return_value="$2b$12$fakehash",
        ) as mock_hash,
    ):
        mock_repo = MockRepo.return_value
        mock_repo.get_by_email = AsyncMock(return_value=None)
        mock_repo.create = AsyncMock(return_value=_make_user())

        from src.application.auth_service import register

        await register("Test", "test@example.com", plain, session)

    mock_hash.assert_called_once_with(plain)
    # Ensure create was called with the hash, not the plain password
    call_kwargs = mock_repo.create.call_args
    assert plain not in str(call_kwargs)


# ---------------------------------------------------------------------------
# login() tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_login_success_returns_token():
    session = AsyncMock()
    user = _make_user()

    with (
        patch("src.application.auth_service.UserRepository") as MockRepo,
        patch(
            "src.application.auth_service.verify_password",
            return_value=True,
        ),
        patch(
            "src.application.auth_service.create_access_token",
            return_value="fake.jwt.token",
        ),
    ):
        mock_repo = MockRepo.return_value
        mock_repo.get_by_email = AsyncMock(return_value=user)

        from src.application.auth_service import login

        token = await login("test@example.com", "password123", session)

    assert token == "fake.jwt.token"


@pytest.mark.asyncio
async def test_login_wrong_password_raises_invalid_credentials():
    session = AsyncMock()
    user = _make_user()

    with (
        patch("src.application.auth_service.UserRepository") as MockRepo,
        patch(
            "src.application.auth_service.verify_password",
            return_value=False,
        ),
    ):
        mock_repo = MockRepo.return_value
        mock_repo.get_by_email = AsyncMock(return_value=user)

        from src.application.auth_service import login

        with pytest.raises(InvalidCredentialsError):
            await login("test@example.com", "wrong-password", session)


@pytest.mark.asyncio
async def test_login_unknown_email_raises_invalid_credentials():
    """Unknown email raises same InvalidCredentialsError — no enumeration."""
    session = AsyncMock()

    with (
        patch("src.application.auth_service.UserRepository") as MockRepo,
        patch(
            "src.application.auth_service.verify_password",
            return_value=False,
        ),
    ):
        mock_repo = MockRepo.return_value
        mock_repo.get_by_email = AsyncMock(return_value=None)

        from src.application.auth_service import login

        with pytest.raises(InvalidCredentialsError):
            await login("nobody@example.com", "password123", session)
