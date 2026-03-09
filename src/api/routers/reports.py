"""Admin reporting router: read-only stats endpoints (admin-only).

All routes require role=admin via the router-level dependency.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies.auth import require_role
from src.api.dependencies.pagination import PaginationParams, pagination_params
from src.api.schemas.reports import EventStatsPage, ReportSummaryResponse
from src.application.reporting_service import ReportingService
from src.infrastructure.db.session import get_db

router = APIRouter(
    prefix="/admin/reports",
    tags=["Admin Reporting"],
    dependencies=[Depends(require_role("admin"))],
)


@router.get("/events/stats", response_model=EventStatsPage)
async def get_event_stats(
    pagination: Annotated[PaginationParams, Depends(pagination_params)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> EventStatsPage:
    """Paginated per-event participant statistics.

    Returns total_registered (active non-cancelled registrations) and
    remaining_quota (quota − total_registered; may be negative per FR-008)
    for every active future event, ordered by date ASC then id ASC.
    """
    service = ReportingService(session)
    return await service.get_event_stats(
        page=pagination.page, size=pagination.page_size
    )


@router.get("/events/summary", response_model=ReportSummaryResponse)
async def get_event_summary(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ReportSummaryResponse:
    """Total count of currently active future events.

    "Active" is defined as status='active' AND date > NOW().
    """
    service = ReportingService(session)
    return await service.get_summary()
