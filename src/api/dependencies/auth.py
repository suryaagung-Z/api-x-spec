"""FastAPI authentication and authorization dependencies."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas.errors import ErrorDetail, ErrorEnvelope
from src.domain.models import User
from src.infrastructure.auth.jwt import decode_token
from src.infrastructure.db.session import get_db
from src.infrastructure.repositories.user_repository import UserRepository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Validate Bearer JWT and return the corresponding domain User.

    Raises HTTP 401 for any failure: invalid/expired token, tampered signature,
    or user no longer found.
    """
    credentials_exc = HTTPException(
        status_code=401,
        detail=ErrorEnvelope(
            error=ErrorDetail(
                code="UNAUTHORIZED",
                message="Could not validate credentials.",
                httpStatus=401,
            )
        ).model_dump(),
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        if not isinstance(user_id, str):
            raise credentials_exc
    except jwt.PyJWTError:
        raise credentials_exc from None

    repo = UserRepository(session)
    user = await repo.get_by_id(user_id)
    if user is None:
        raise credentials_exc
    return user


def require_role(required_role: str) -> Callable[..., Awaitable[User]]:
    """Dependency factory that enforces role-based access control.

    Returns a dependency function that sub-depends on ``get_current_user`` and
    raises HTTP 403 when the authenticated user's role does not match.
    """

    async def role_checker(
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        if current_user.role.value != required_role:
            raise HTTPException(
                status_code=403,
                detail=ErrorEnvelope(
                    error=ErrorDetail(
                        code="FORBIDDEN",
                        message="Insufficient permissions.",
                        httpStatus=403,
                    )
                ).model_dump(),
            )
        return current_user

    return role_checker
