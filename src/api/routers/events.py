"""Event router: admin CRUD and public browse endpoints."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies.auth import require_role
from src.api.dependencies.pagination import PaginationParams, pagination_params
from src.api.schemas.events import EventCreate, EventResponse, EventUpdate
from src.api.schemas.pagination import Page
from src.application import event_service
from src.infrastructure.db.session import get_db

# ---------------------------------------------------------------------------
# Admin router — all endpoints require ADMIN role
# ---------------------------------------------------------------------------
admin_router = APIRouter(
    prefix="/admin/events",
    tags=["admin-events"],
    dependencies=[Depends(require_role("admin"))],
)


@admin_router.post(
    "", response_model=EventResponse, status_code=status.HTTP_201_CREATED
)
async def create_event(
    body: EventCreate,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> EventResponse:
    return await event_service.create_event(body, session)


@admin_router.get("/{event_id}", response_model=EventResponse)
async def get_event_admin(
    event_id: int,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> EventResponse:
    return await event_service.get_event_admin(event_id, session)


@admin_router.put("/{event_id}", response_model=EventResponse)
async def update_event(
    event_id: int,
    body: EventUpdate,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> EventResponse:
    return await event_service.update_event(event_id, body, session)


@admin_router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    event_id: int,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    await event_service.delete_event(event_id, session)


# ---------------------------------------------------------------------------
# Public router — no authentication required
# ---------------------------------------------------------------------------
public_router = APIRouter(prefix="/events", tags=["events"])


@public_router.get("", response_model=Page[EventResponse])
async def list_events(
    session: Annotated[AsyncSession, Depends(get_db)],
    pagination: Annotated[PaginationParams, Depends(pagination_params)],
) -> Page[EventResponse]:
    return await event_service.list_public_events(
        session, page=pagination.page, page_size=pagination.page_size
    )


@public_router.get("/{event_id}", response_model=EventResponse)
async def get_event(
    event_id: int,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> EventResponse:
    return await event_service.get_public_event(event_id, session)
