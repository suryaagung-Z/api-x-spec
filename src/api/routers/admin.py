"""Admin router: admin-only endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies.auth import require_role
from src.api.schemas.auth import UserRead
from src.infrastructure.db.session import get_db
from src.infrastructure.repositories.user_repository import UserRepository

router = APIRouter(dependencies=[Depends(require_role("admin"))])

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


@router.get(
    "/users",
    response_model=list[UserRead],
    summary="Daftar semua pengguna terdaftar",
    openapi_extra={"security": [{"BearerAuth": []}]},
    responses={
        401: {"description": "Token tidak valid atau tidak ada", "content": _ERR_401},
        403: {"description": "Bukan admin", "content": _ERR_403},
    },
)
async def list_users(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[UserRead]:
    """Dapatkan daftar semua pengguna yang terdaftar di sistem.

    **Akses**: Khusus admin — memerlukan token Bearer dengan role `admin`.

    Mengembalikan semua akun pengguna (termasuk admin) tanpa pagination.
    Setiap entri mencakup id, nama, email, role, dan waktu pembuatan akun.
    """
    repo = UserRepository(session)
    users = await repo.get_all()
    return [UserRead.model_validate(u) for u in users]
