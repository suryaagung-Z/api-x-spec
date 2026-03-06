"""Pydantic schemas for the shared error envelope."""
from __future__ import annotations

from pydantic import BaseModel


class ErrorDetail(BaseModel):
    code: str
    message: str
    httpStatus: int


class ErrorEnvelope(BaseModel):
    error: ErrorDetail
