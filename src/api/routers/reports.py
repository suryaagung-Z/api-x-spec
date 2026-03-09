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
    tags=["admin-reporting"],
    dependencies=[Depends(require_role("admin"))],
)

_ERR_401 = {
    "application/json": {
        "example": {
            "error": {"code": "UNAUTHORIZED", "message": "Could not validate credentials.", "httpStatus": 401}
        }
    }
}
_ERR_403 = {
    "application/json": {
        "example": {
            "error": {"code": "FORBIDDEN", "message": "Insufficient permissions.", "httpStatus": 403}
        }
    }
}
_ERR_422 = {
    "application/json": {
        "example": {
            "error": {"code": "VALIDATION_ERROR", "message": "value is not a valid integer", "httpStatus": 422}
        }
    }
}


@router.get(
    "/events/stats",
    response_model=EventStatsPage,
    summary="Statistik peserta per event aktif",
    openapi_extra={"security": [{"BearerAuth": []}]},
    responses={
        401: {"description": "Token tidak valid atau tidak ada", "content": _ERR_401},
        403: {"description": "Bukan admin", "content": _ERR_403},
        422: {"description": "Parameter pagination tidak valid", "content": _ERR_422},
    },
)
async def get_event_stats(
    pagination: Annotated[PaginationParams, Depends(pagination_params)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> EventStatsPage:
    """Statistik jumlah peserta untuk setiap event aktif yang akan datang.

    **Akses**: Khusus admin — memerlukan token Bearer dengan role `admin`.

    Mengembalikan daftar event aktif beserta jumlah pendaftaran aktif (`total_registered`)
    dan sisa kuota (`remaining_quota`) masing-masing, diurutkan berdasarkan tanggal ASC
    kemudian ID ASC.

    **Catatan**: `remaining_quota` dapat bernilai negatif jika kuota event dikurangi
    setelah peserta mendaftar (FR-008).

    **Parameter pagination**:
    - `page`: Nomor halaman, mulai dari 1 (default: `1`).
    - `page_size`: Jumlah item per halaman (default: `20`, maksimal: `100`).
    """
    service = ReportingService(session)
    return await service.get_event_stats(
        page=pagination.page, size=pagination.page_size
    )


@router.get(
    "/events/summary",
    response_model=ReportSummaryResponse,
    summary="Ringkasan jumlah event aktif",
    openapi_extra={"security": [{"BearerAuth": []}]},
    responses={
        401: {"description": "Token tidak valid atau tidak ada", "content": _ERR_401},
        403: {"description": "Bukan admin", "content": _ERR_403},
    },
)
async def get_event_summary(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ReportSummaryResponse:
    """Ringkasan total jumlah event aktif yang akan datang.

    **Akses**: Khusus admin — memerlukan token Bearer dengan role `admin`.

    Menghitung jumlah event dengan status `active` dan tanggal pelaksanaan
    di masa depan (date > NOW()).
    """
    service = ReportingService(session)
    return await service.get_summary()
