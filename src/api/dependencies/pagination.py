"""FastAPI dependency for offset pagination query parameters."""
from __future__ import annotations

from dataclasses import dataclass

from fastapi import Query


@dataclass
class PaginationParams:
    page: int
    page_size: int


async def pagination_params(
    page: int = Query(default=1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(
        default=20, ge=1, le=100, description="Items per page (max 100)"
    ),
) -> PaginationParams:
    return PaginationParams(page=page, page_size=page_size)
