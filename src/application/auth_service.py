"""Application-layer use cases: register and login (no HTTP imports)."""
from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.exceptions import EmailAlreadyExistsError, InvalidCredentialsError
from src.domain.models import User
from src.infrastructure.auth.jwt import create_access_token
from src.infrastructure.auth.password import hash_password, verify_password
from src.infrastructure.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)


async def register(
    name: str,
    email: str,
    password: str,
    session: AsyncSession,
) -> User:
    """Register a new user account.

    Normalises email to lowercase, checks uniqueness, hashes the password,
    and persists the new user.  Raises ``EmailAlreadyExistsError`` on conflict.
    """
    email = email.lower()
    repo = UserRepository(session)
    existing = await repo.get_by_email(email)
    if existing:
        logger.info("Registration failed — email already in use: %s", email)
        raise EmailAlreadyExistsError(email)

    hashed = hash_password(password)
    user = await repo.create(name=name, email=email, hashed_password=hashed)
    logger.info("User registered: id=%s email=%s", user.id, user.email)
    return user


async def login(
    email: str,
    password: str,
    session: AsyncSession,
) -> str:
    """Authenticate a user and return a signed JWT access token.

    Normalises email to lowercase before lookup.  Raises
    ``InvalidCredentialsError`` for any mismatch (email or password) without
    revealing which.
    """
    email = email.lower()
    repo = UserRepository(session)
    user = await repo.get_by_email(email)

    # verify_password handles the timing-safe dummy path when user is None
    hashed = user.hashed_password if user else None
    if not verify_password(password, hashed):
        logger.info("Login failed for: %s", email)
        raise InvalidCredentialsError()

    token = create_access_token(sub=user.id, role=user.role.value)  # type: ignore[union-attr]
    logger.info("Login success: id=%s", user.id)  # type: ignore[union-attr]
    return token
