"""Pydantic schemas for admin reporting endpoints (004-admin-reporting).

Provides the response shapes for:
- EventStatItem: per-event stats row (total_registered, remaining_quota)
- EventStatsPage: paginated wrapper (fields named per contract: total/size/pages)
- ReportSummaryResponse: total active events count
"""

from __future__ import annotations

import math
from datetime import datetime

from pydantic import BaseModel, Field


class EventStatItem(BaseModel):
    """Statistics for a single active event."""

    id: int = Field(description="ID unik event.", examples=[1])
    title: str = Field(description="Nama event.", examples=["Workshop Python untuk Pemula"])
    date: datetime = Field(
        description="Waktu pelaksanaan event.",
        examples=["2026-06-15T09:00:00+07:00"],
    )
    quota: int = Field(description="Kuota maksimal peserta.", examples=[30])
    total_registered: int = Field(
        description="Jumlah peserta aktif (pendaftaran non-cancelled).",
        examples=[18],
    )
    remaining_quota: int = Field(
        description="Sisa kuota (quota − total_registered). Bisa negatif jika kuota dikurangi setelah pendaftaran.",
        examples=[12],
    )

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 1,
                "title": "Workshop Python untuk Pemula",
                "date": "2026-06-15T09:00:00+07:00",
                "quota": 30,
                "total_registered": 18,
                "remaining_quota": 12,
            }
        },
    }


class EventStatsPage(BaseModel):
    """Paginated response envelope for event statistics.

    Field names match the contract spec (total/size/pages) rather than
    the generic Page schema (total_items/page_size/total_pages).
    """

    items: list[EventStatItem] = Field(description="Daftar statistik event pada halaman ini.")
    total: int = Field(description="Total jumlah event aktif.", examples=[5])
    page: int = Field(description="Nomor halaman saat ini (mulai dari 1).", examples=[1])
    size: int = Field(description="Jumlah item per halaman.", examples=[20])
    pages: int = Field(description="Total jumlah halaman.", examples=[1])

    model_config = {
        "json_schema_extra": {
            "example": {
                "items": [
                    {
                        "id": 1,
                        "title": "Workshop Python untuk Pemula",
                        "date": "2026-06-15T09:00:00+07:00",
                        "quota": 30,
                        "total_registered": 18,
                        "remaining_quota": 12,
                    }
                ],
                "total": 5,
                "page": 1,
                "size": 20,
                "pages": 1,
            }
        }
    }

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

    total_active_events: int = Field(
        description="Jumlah event yang berstatus aktif dan tanggalnya di masa depan.",
        examples=[5],
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "total_active_events": 5,
            }
        }
    }
