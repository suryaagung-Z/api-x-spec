"""Unit tests for ReportingService (T006).

Tests cover:
- EventStatRow → EventStatItem field mapping correctness
- Pagination math: pages = ceil(total / size)
- Empty result returns empty items list with pages=0
"""

from __future__ import annotations

import math
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.api.schemas.reports import EventStatsPage, ReportSummaryResponse
from src.application.reporting_service import ReportingService
from src.infrastructure.repositories.reporting_repository import EventStatRow

pytestmark = pytest.mark.asyncio

_FUTURE_DATE = datetime(2027, 6, 15, 9, 0, 0, tzinfo=UTC)


def _make_service() -> tuple[ReportingService, AsyncMock]:
    """Return (service, mock_repo) with mock injected into the service."""
    session = MagicMock()
    service = ReportingService(session)
    mock_repo = AsyncMock()
    service._repo = mock_repo  # noqa: SLF001 — test-only injection
    return service, mock_repo


def _row(
    id: int,
    quota: int = 100,
    registered: int = 0,
    title: str | None = None,
) -> EventStatRow:
    return EventStatRow(
        id=id,
        title=title or f"Event {id}",
        date=_FUTURE_DATE,
        quota=quota,
        total_registered=registered,
        remaining_quota=quota - registered,
    )


# ---------------------------------------------------------------------------
# Mapping — EventStatRow → EventStatItem
# ---------------------------------------------------------------------------


async def test_row_to_item_all_fields_mapped():
    """All EventStatRow fields appear correctly in the resulting EventStatItem."""
    service, mock_repo = _make_service()
    row = _row(42, quota=100, registered=87, title="Tech Conference 2026")
    mock_repo.get_event_stats_page.return_value = ([row], 1)

    result = await service.get_event_stats(page=1, size=20)

    assert len(result.items) == 1
    item = result.items[0]
    assert item.id == 42
    assert item.title == "Tech Conference 2026"
    assert item.date == _FUTURE_DATE
    assert item.quota == 100
    assert item.total_registered == 87
    assert item.remaining_quota == 13


async def test_negative_remaining_quota_preserved():
    """remaining_quota is passed through as-is even when negative (FR-008)."""
    service, mock_repo = _make_service()
    row = _row(1, quota=5, registered=7)  # remaining = -2
    mock_repo.get_event_stats_page.return_value = ([row], 1)

    result = await service.get_event_stats(page=1, size=20)

    assert result.items[0].remaining_quota == -2


# ---------------------------------------------------------------------------
# Pagination math
# ---------------------------------------------------------------------------


async def test_pagination_meta_page_and_size():
    """Result carries back the page and size values passed in."""
    service, mock_repo = _make_service()
    mock_repo.get_event_stats_page.return_value = ([_row(1)], 47)

    result = await service.get_event_stats(page=3, size=20)

    assert result.page == 3
    assert result.size == 20


async def test_pagination_total_and_pages():
    """total and pages are derived from the repository total, not len(items)."""
    service, mock_repo = _make_service()
    mock_repo.get_event_stats_page.return_value = ([_row(i) for i in range(1, 8)], 47)

    result = await service.get_event_stats(page=3, size=20)

    assert result.total == 47
    assert result.pages == math.ceil(47 / 20)  # == 3


async def test_pagination_pages_rounds_up():
    """ceil(total / size) — 21 items / 20 per page = 2 pages."""
    service, mock_repo = _make_service()
    mock_repo.get_event_stats_page.return_value = ([_row(1)], 21)

    result = await service.get_event_stats(page=1, size=20)

    assert result.pages == 2


async def test_offset_calculation_forwarded_to_repo():
    """Service computes offset = (page - 1) * size and forwards to repository."""
    service, mock_repo = _make_service()
    mock_repo.get_event_stats_page.return_value = ([], 0)

    await service.get_event_stats(page=4, size=10)

    mock_repo.get_event_stats_page.assert_called_once_with(offset=30, limit=10)


# ---------------------------------------------------------------------------
# Edge case — empty result
# ---------------------------------------------------------------------------


async def test_empty_result_returns_empty_items_and_zero_pages():
    """Zero rows: items=[], total=0, pages=0."""
    service, mock_repo = _make_service()
    mock_repo.get_event_stats_page.return_value = ([], 0)

    result = await service.get_event_stats(page=1, size=20)

    assert isinstance(result, EventStatsPage)
    assert result.items == []
    assert result.total == 0
    assert result.pages == 0


# ---------------------------------------------------------------------------
# get_summary
# ---------------------------------------------------------------------------


async def test_get_summary_returns_correct_count():
    """get_summary delegates to repo and wraps result."""
    service, mock_repo = _make_service()
    mock_repo.get_total_active_events.return_value = 13

    result = await service.get_summary()

    assert isinstance(result, ReportSummaryResponse)
    assert result.total_active_events == 13
    mock_repo.get_total_active_events.assert_called_once()


async def test_get_summary_zero_when_no_active_events():
    """get_summary returns 0 when repository returns 0."""
    service, mock_repo = _make_service()
    mock_repo.get_total_active_events.return_value = 0

    result = await service.get_summary()

    assert result.total_active_events == 0
