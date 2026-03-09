"""Auth router: register, login, and current-user endpoints."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies.auth import get_current_user
from src.api.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserRead,
)
from src.application import auth_service
from src.domain.models import User
from src.infrastructure.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> UserRead:
    user = await auth_service.register(
        name=body.name,
        email=body.email,
        password=body.password,
        session=session,
    )
    logger.info("POST /auth/register success: id=%s", user.id)
    return UserRead.model_validate(user)


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    token = await auth_service.login(
        email=body.email,
        password=body.password,
        session=session,
    )
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserRead)
async def me(current_user: Annotated[User, Depends(get_current_user)]) -> UserRead:
    return UserRead.model_validate(current_user)
