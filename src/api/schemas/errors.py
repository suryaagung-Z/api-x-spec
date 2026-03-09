"""Pydantic schemas for the shared error envelope."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    model_config = {
        "json_schema_extra": {
            "example": {
                "code": "UNAUTHORIZED",
                "message": "Could not validate credentials.",
                "httpStatus": 401,
            }
        }
    }

    code: str = Field(
        description="Kode error mesin-readable. Contoh: `UNAUTHORIZED`, `NOT_FOUND`, `VALIDATION_ERROR`.",
        examples=["UNAUTHORIZED"],
    )
    message: str = Field(
        description="Pesan error yang dapat dibaca manusia.",
        examples=["Could not validate credentials."],
    )
    httpStatus: int = Field(
        description="HTTP status code yang sesuai.",
        examples=[401],
    )


class ErrorEnvelope(BaseModel):
    model_config = {
        "json_schema_extra": {
            "example": {
                "error": {
                    "code": "UNAUTHORIZED",
                    "message": "Could not validate credentials.",
                    "httpStatus": 401,
                }
            }
        }
    }

    error: ErrorDetail = Field(description="Detail kesalahan yang terjadi.")
