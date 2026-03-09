"""Admin router: admin-only endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies.auth import require_role
from src.api.schemas.auth import UserRead
from src.infrastructure.db.session import get_db
from src.infrastructure.repositories.user_repository import UserRepository

router = APIRouter(dependencies=[Depends(require_role("admin"))])


@router.get("/users", response_model=list[UserRead])
async def list_users(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[UserRead]:
    repo = UserRepository(session)
    users = await repo.get_all()
    return [UserRead.model_validate(u) for u in users]
