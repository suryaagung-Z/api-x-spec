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
_ERR_404_REG = {
    "application/json": {
        "example": {
            "error": {"code": "REGISTRATION_NOT_FOUND", "message": "No active registration found for this event.", "httpStatus": 404}
        }
    }
}
_ERR_404_EVENT = {
    "application/json": {
        "example": {
            "error": {"code": "EVENT_NOT_FOUND", "message": "Event not found.", "httpStatus": 404}
        }
    }
}
_ERR_409_DUPLICATE = {
    "application/json": {
        "example": {
            "error": {
                "code": "DUPLICATE_REGISTRATION",
                "message": "You are already registered for this event.",
                "httpStatus": 409,
            }
        }
    }
}
_ERR_422_QUOTA = {
    "application/json": {
        "example": {
            "error": {"code": "QUOTA_FULL", "message": "This event has reached its maximum capacity.", "httpStatus": 422}
        }
    }
}
_ERR_422_PATH = {
    "application/json": {
        "example": {
            "error": {"code": "VALIDATION_ERROR", "message": "value is not a valid integer", "httpStatus": 422}
        }
    }
}
_ERR_422_CLOSED = {
    "application/json": {
        "example": {
            "error": {
                "code": "REGISTRATION_DEADLINE_PASSED",
                "message": "Registration deadline has passed.",
                "httpStatus": 422,
            }
        }
    }
}


@router.post(
    "/{event_id}",
    status_code=status.HTTP_201_CREATED,
    response_model=RegistrationResponse,
    summary="Daftar ke event",
    openapi_extra={"security": [{"BearerAuth": []}]},
    responses={
        401: {"description": "Token tidak valid atau tidak ada", "content": _ERR_401},
        404: {"description": "Event tidak ditemukan", "content": _ERR_404_EVENT},
        409: {"description": "Sudah terdaftar di event ini", "content": _ERR_409_DUPLICATE},
        422: {"description": "Kuota penuh atau batas pendaftaran terlampaui", "content": _ERR_422_QUOTA},
    },
)
async def register_for_event(
    event_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> RegistrationResponse:
    """Daftarkan pengguna yang sedang login ke event tertentu.

    **Akses**: Memerlukan token Bearer yang valid.

    Membuat pendaftaran baru untuk pengguna saat ini ke event yang ditentukan.

    **Aturan bisnis**:
    - Event harus aktif dan batas pendaftaran belum terlampaui (`REGISTRATION_DEADLINE_PASSED`).
    - Kuota event belum penuh (`QUOTA_FULL`).
    - Pengguna belum terdaftar secara aktif di event yang sama (`DUPLICATE_REGISTRATION`).
    """
    return await registration_service.register(session, current_user.id, event_id)


@router.delete(
    "/{event_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Batalkan pendaftaran event",
    openapi_extra={"security": [{"BearerAuth": []}]},
    responses={
        401: {"description": "Token tidak valid atau tidak ada", "content": _ERR_401},
        403: {"description": "Bukan pemilik pendaftaran", "content": _ERR_403},
        404: {"description": "Pendaftaran tidak ditemukan", "content": _ERR_404_REG},
        422: {"description": "event_id bukan integer", "content": _ERR_422_PATH},
    },
)
async def cancel_registration(
    event_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Batalkan pendaftaran pengguna yang sedang login dari event tertentu.

    **Akses**: Memerlukan token Bearer yang valid.

    **Aturan bisnis**:
    - Pengguna hanya dapat membatalkan pendaftaran miliknya sendiri.
    - Pendaftaran yang sudah dibatalkan tidak dapat dibatalkan lagi (`REGISTRATION_NOT_FOUND`).
    """
    await registration_service.cancel(session, current_user.id, event_id)


@router.get(
    "/me",
    response_model=list[RegistrationWithEventResponse],
    summary="Lihat daftar event yang sudah didaftarkan",
    openapi_extra={"security": [{"BearerAuth": []}]},
    responses={
        401: {"description": "Token tidak valid atau tidak ada", "content": _ERR_401},
    },
)
async def get_my_registrations(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[RegistrationWithEventResponse]:
    """Dapatkan semua pendaftaran event milik pengguna yang sedang login.

    **Akses**: Memerlukan token Bearer yang valid.

    Mengembalikan semua pendaftaran (aktif maupun yang sudah dibatalkan) beserta
    ringkasan detail event masing-masing.
    """
    return await registration_service.get_my_registrations(session, current_user.id)
