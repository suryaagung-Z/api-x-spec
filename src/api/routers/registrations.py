"""FastAPI router for event registration endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies.auth import get_current_user
from src.api.schemas.registrations import (
    RegistrationResponse,
    RegistrationWithEventResponse,
)
from src.application import registration_service
from src.domain.models import User
from src.infrastructure.db.session import get_db

router = APIRouter(prefix="/registrations", tags=["registrations"])


@router.post(
    "/{event_id}",
    status_code=status.HTTP_201_CREATED,
    response_model=RegistrationResponse,
)
async def register_for_event(
    event_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> RegistrationResponse:
    return await registration_service.register(session, current_user.id, event_id)


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_registration(
    event_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    await registration_service.cancel(session, current_user.id, event_id)


@router.get("/me", response_model=list[RegistrationWithEventResponse])
async def get_my_registrations(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[RegistrationWithEventResponse]:
    return await registration_service.get_my_registrations(session, current_user.id)
