"""Auth router: register, login, and current-user endpoints."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies.auth import get_current_user
from src.api.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserRead,
)
from src.application import auth_service
from src.domain.models import User
from src.infrastructure.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter()

_ERR_409_EMAIL = {
    "application/json": {
        "example": {
            "error": {
                "code": "EMAIL_ALREADY_EXISTS",
                "message": "An account with this email already exists.",
                "httpStatus": 409,
            }
        }
    }
}
_ERR_401 = {
    "application/json": {
        "example": {
            "error": {
                "code": "UNAUTHORIZED",
                "message": "Could not validate credentials.",
                "httpStatus": 401,
            }
        }
    }
}
_ERR_401_INVALID = {
    "application/json": {
        "example": {
            "error": {
                "code": "INVALID_CREDENTIALS",
                "message": "Invalid email or password.",
                "httpStatus": 401,
            }
        }
    }
}
_ERR_422 = {
    "application/json": {
        "example": {
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "field required",
                "httpStatus": 422,
            }
        }
    }
}


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Daftar akun baru",
    responses={
        409: {"description": "Email sudah digunakan", "content": _ERR_409_EMAIL},
        422: {"description": "Data tidak valid", "content": _ERR_422},
    },
)
async def register(
    body: RegisterRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> UserRead:
    """Buat akun pengguna baru.

    **Akses**: Publik — tidak memerlukan token.

    Membuat akun baru dengan nama, email, dan kata sandi. Kata sandi disimpan
    sebagai hash bcrypt — password asli tidak pernah tersimpan.

    **Aturan bisnis**:
    - Email harus unik; jika sudah digunakan akan mengembalikan `409 EMAIL_ALREADY_EXISTS`.
    - Kata sandi minimal 8 karakter, maksimal 72 karakter.
    - Akun baru selalu mendapat role `user`.
    """
    user = await auth_service.register(
        name=body.name,
        email=body.email,
        password=body.password,
        session=session,
    )
    logger.info("POST /auth/register success: id=%s", user.id)
    return UserRead.model_validate(user)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login dan dapatkan JWT token",
    responses={
        401: {"description": "Email atau password salah", "content": _ERR_401_INVALID},
        422: {"description": "Data tidak valid", "content": _ERR_422},
    },
)
async def login(
    body: LoginRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    """Login dan dapatkan JWT Bearer token.

    **Akses**: Publik — tidak memerlukan token.

    Memverifikasi email dan password. Jika valid, mengembalikan JWT Bearer token
    yang dapat digunakan untuk mengakses endpoint yang memerlukan autentikasi.

    **Cara menggunakan token**:
    1. Salin nilai `access_token` dari respons.
    2. Klik tombol **Authorize** di kanan atas Swagger UI.
    3. Masukkan token dengan format: `Bearer <token>`.

    **Aturan bisnis**:
    - Email dan password diverifikasi bersamaan; tidak membedakan mana yang salah demi keamanan.
    - Token berlaku selama durasi yang dikonfigurasi server (default: 30 menit).
    """
    token = await auth_service.login(
        email=body.email,
        password=body.password,
        session=session,
    )
    return TokenResponse(access_token=token)


@router.get(
    "/me",
    response_model=UserRead,
    summary="Lihat profil pengguna yang sedang login",
    openapi_extra={"security": [{"BearerAuth": []}]},
    responses={
        401: {"description": "Token tidak valid atau tidak ada", "content": _ERR_401},
    },
)
async def me(current_user: Annotated[User, Depends(get_current_user)]) -> UserRead:
    """Dapatkan profil pengguna yang sedang terautentikasi.

    **Akses**: Memerlukan token Bearer yang valid.

    Mengembalikan data profil (id, nama, email, role, waktu dibuat) dari pengguna
    yang pemilik token yang dikirimkan.
    """
    return UserRead.model_validate(current_user)
