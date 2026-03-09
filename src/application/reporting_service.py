"""Application-layer use cases for admin reporting (no HTTP imports).

Delegates all database access to ReportingRepository; no business logic
beyond data mapping and pagination math.
"""

from __future__ import annotations

import logging
import math

from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas.reports import EventStatItem, EventStatsPage, ReportSummaryResponse
from src.infrastructure.repositories.reporting_repository import ReportingRepository

logger = logging.getLogger(__name__)


class ReportingService:
    """Use-case façade for admin reporting endpoints."""

    def __init__(self, session: AsyncSession) -> None:
        self._repo = ReportingRepository(session)

    async def get_event_stats(self, page: int, size: int) -> EventStatsPage:
        """Return paginated per-event participant statistics.

        Converts EventStatRow list → EventStatItem list and computes
        pagination metadata (pages = ceil(total / size)).
        """
        offset = (page - 1) * size
        rows, total = await self._repo.get_event_stats_page(offset=offset, limit=size)

        items = [
            EventStatItem(
                id=row.id,
                title=row.title,
                date=row.date,
                quota=row.quota,
                total_registered=row.total_registered,
                remaining_quota=row.remaining_quota,
            )
            for row in rows
        ]

        pages = math.ceil(total / size) if size > 0 else 0
        logger.debug(
            "get_event_stats page=%d size=%d total=%d pages=%d",
            page,
            size,
            total,
            pages,
        )
        return EventStatsPage(
            items=items, total=total, page=page, size=size, pages=pages
        )

    async def get_summary(self) -> ReportSummaryResponse:
        """Return total count of currently active events."""
        count = await self._repo.get_total_active_events()
        logger.debug("get_summary total_active_events=%d", count)
        return ReportSummaryResponse(total_active_events=count)
