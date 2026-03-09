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
# Shared error response content examples
# ---------------------------------------------------------------------------

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
_ERR_404 = {
    "application/json": {
        "example": {
            "error": {"code": "EVENT_NOT_FOUND", "message": "Event not found.", "httpStatus": 404}
        }
    }
}
_ERR_409_HAS_REG = {
    "application/json": {
        "example": {
            "error": {
                "code": "EVENT_HAS_REGISTRATIONS",
                "message": "Cannot delete event with active registrations.",
                "httpStatus": 409,
            }
        }
    }
}
_ERR_422 = {
    "application/json": {
        "example": {
            "error": {"code": "VALIDATION_ERROR", "message": "field required", "httpStatus": 422}
        }
    }
}
_ERR_422_QUOTA = {
    "application/json": {
        "example": {
            "error": {"code": "QUOTA_MUST_BE_POSITIVE", "message": "Quota must be at least 1.", "httpStatus": 422}
        }
    }
}
_ERR_409_QUOTA_BELOW = {
    "application/json": {
        "example": {
            "error": {
                "code": "QUOTA_BELOW_PARTICIPANTS",
                "message": "New quota is lower than the current number of active participants.",
                "httpStatus": 409,
            }
        }
    }
}

# ---------------------------------------------------------------------------
# Admin router — all endpoints require ADMIN role
# ---------------------------------------------------------------------------
admin_router = APIRouter(
    prefix="/admin/events",
    tags=["admin-events"],
    dependencies=[Depends(require_role("admin"))],
)


@admin_router.post(
    "", response_model=EventResponse, status_code=status.HTTP_201_CREATED,
    summary="Buat event baru",
    openapi_extra={"security": [{"BearerAuth": []}]},
    responses={
        401: {"description": "Token tidak valid atau tidak ada", "content": _ERR_401},
        403: {"description": "Bukan admin", "content": _ERR_403},
        422: {"description": "Data tidak valid", "content": _ERR_422},
    },
)
async def create_event(
    body: EventCreate,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> EventResponse:
    """Buat event baru.

    **Akses**: Khusus admin — memerlukan token Bearer dengan role `admin`.

    Membuat event baru dengan judul, deskripsi, tanggal pelaksanaan, batas pendaftaran,
    dan kuota peserta. Event yang baru dibuat otomatis berstatus `active`.

    **Aturan bisnis**:
    - `registration_deadline` harus sebelum atau sama dengan `date`.
    - `quota` minimal 1.
    - Tanggal `date` harus di masa depan saat pembuatan.
    """
    return await event_service.create_event(body, session)


@admin_router.get(
    "/{event_id}",
    response_model=EventResponse,
    summary="Lihat detail event (admin)",
    openapi_extra={"security": [{"BearerAuth": []}]},
    responses={
        401: {"description": "Token tidak valid atau tidak ada", "content": _ERR_401},
        403: {"description": "Bukan admin", "content": _ERR_403},
        404: {"description": "Event tidak ditemukan", "content": _ERR_404},
        422: {"description": "event_id bukan integer", "content": _ERR_422},
    },
)
async def get_event_admin(
    event_id: int,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> EventResponse:
    """Lihat detail event termasuk event yang sudah dibatalkan.

    **Akses**: Khusus admin — memerlukan token Bearer dengan role `admin`.

    Berbeda dari endpoint publik, endpoint ini juga mengembalikan event
    dengan status `cancelled`.
    """
    return await event_service.get_event_admin(event_id, session)


@admin_router.put(
    "/{event_id}",
    response_model=EventResponse,
    summary="Perbarui data event",
    openapi_extra={"security": [{"BearerAuth": []}]},
    responses={
        401: {"description": "Token tidak valid atau tidak ada", "content": _ERR_401},
        403: {"description": "Bukan admin", "content": _ERR_403},
        404: {"description": "Event tidak ditemukan", "content": _ERR_404},
        409: {"description": "Kuota di bawah jumlah peserta aktif", "content": _ERR_409_QUOTA_BELOW},
        422: {"description": "Data tidak valid", "content": _ERR_422_QUOTA},
    },
)
async def update_event(
    event_id: int,
    body: EventUpdate,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> EventResponse:
    """Perbarui data event yang sudah ada.

    **Akses**: Khusus admin — memerlukan token Bearer dengan role `admin`.

    Semua field bersifat opsional — hanya field yang dikirimkan yang akan diperbarui.

    **Aturan bisnis**:
    - Jika `quota` dikurangi, nilai baru tidak boleh lebih kecil dari jumlah peserta aktif saat ini.
    - Jika `registration_deadline` dan `date` keduanya diperbarui, `registration_deadline` harus ≤ `date`.
    """
    return await event_service.update_event(event_id, body, session)


@admin_router.delete(
    "/{event_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Hapus event",
    openapi_extra={"security": [{"BearerAuth": []}]},
    responses={
        401: {"description": "Token tidak valid atau tidak ada", "content": _ERR_401},
        403: {"description": "Bukan admin", "content": _ERR_403},
        404: {"description": "Event tidak ditemukan", "content": _ERR_404},
        409: {"description": "Event masih memiliki pendaftaran aktif", "content": _ERR_409_HAS_REG},
        422: {"description": "event_id bukan integer", "content": _ERR_422},
    },
)
async def delete_event(
    event_id: int,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Hapus event secara permanen.

    **Akses**: Khusus admin — memerlukan token Bearer dengan role `admin`.

    **Aturan bisnis**:
    - Event yang memiliki pendaftaran aktif tidak dapat dihapus (`409 EVENT_HAS_REGISTRATIONS`).
    - Operasi ini tidak dapat dibatalkan.
    """
    await event_service.delete_event(event_id, session)


# ---------------------------------------------------------------------------
# Public router — no authentication required
# ---------------------------------------------------------------------------
public_router = APIRouter(prefix="/events", tags=["events"])


@public_router.get(
    "",
    response_model=Page[EventResponse],
    summary="Daftar event aktif dengan pagination",
    responses={
        422: {"description": "Parameter tidak valid", "content": _ERR_422},
    },
)
async def list_events(
    session: Annotated[AsyncSession, Depends(get_db)],
    pagination: Annotated[PaginationParams, Depends(pagination_params)],
) -> Page[EventResponse]:
    """Daftar semua event aktif yang akan datang dengan pagination.

    **Akses**: Publik — tidak memerlukan token.

    Mengembalikan daftar event dengan status `active` dan tanggal di masa depan,
    diurutkan berdasarkan tanggal terdekat.

    **Parameter pagination**:
    - `page`: Nomor halaman, mulai dari 1 (default: `1`).
    - `page_size`: Jumlah item per halaman (default: `20`, maksimal: `100`).
    """
    return await event_service.list_public_events(
        session, page=pagination.page, page_size=pagination.page_size
    )


@public_router.get(
    "/{event_id}",
    response_model=EventResponse,
    summary="Lihat detail event",
    responses={
        404: {"description": "Event tidak ditemukan", "content": _ERR_404},
        422: {"description": "event_id bukan integer", "content": _ERR_422},
    },
)
async def get_event(
    event_id: int,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> EventResponse:
    """Lihat detail event aktif berdasarkan ID.

    **Akses**: Publik — tidak memerlukan token.

    Hanya mengembalikan event dengan status `active`. Event yang dibatalkan
    tidak dapat diakses melalui endpoint publik ini.
    """
    return await event_service.get_public_event(event_id, session)
