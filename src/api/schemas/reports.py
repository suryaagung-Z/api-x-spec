"""Pydantic schemas for admin reporting endpoints (004-admin-reporting).

Provides the response shapes for:
- EventStatItem: per-event stats row (total_registered, remaining_quota)
- EventStatsPage: paginated wrapper (fields named per contract: total/size/pages)
- ReportSummaryResponse: total active events count
"""

from __future__ import annotations

import math
from datetime import datetime

from pydantic import BaseModel


class EventStatItem(BaseModel):
    """Statistics for a single active event."""

    id: int
    title: str
    date: datetime
    quota: int
    total_registered: int
    # FR-008: remaining_quota may be negative; no ge=0 constraint.
    remaining_quota: int

    model_config = {"from_attributes": True}


class EventStatsPage(BaseModel):
    """Paginated response envelope for event statistics.

    Field names match the contract spec (total/size/pages) rather than
    the generic Page schema (total_items/page_size/total_pages).
    """

    items: list[EventStatItem]
    total: int
    page: int
    size: int
    pages: int

    @classmethod
    def build(
        cls,
        items: list[EventStatItem],
        total: int,
        page: int,
        size: int,
    ) -> EventStatsPage:
        pages = math.ceil(total / size) if size > 0 else 0
        return cls(items=items, total=total, page=page, size=size, pages=pages)


class ReportSummaryResponse(BaseModel):
    """Summary count of currently active events."""

    total_active_events: int
