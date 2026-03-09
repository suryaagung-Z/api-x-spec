"""Pydantic schemas for event registration endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from src.domain.models import EventStatus, RegistrationStatus


class EventSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="ID unik event.", examples=[1])
    title: str = Field(description="Nama event.", examples=["Workshop Python untuk Pemula"])
    date: datetime = Field(description="Waktu pelaksanaan event.", examples=["2026-06-15T09:00:00+07:00"])
    registration_deadline: datetime = Field(
        description="Batas waktu pendaftaran.",
        examples=["2026-06-10T23:59:59+07:00"],
    )
    status: EventStatus = Field(
        description="Status event: `active` atau `cancelled`.",
        examples=["active"],
    )


class RegistrationResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 42,
                "event_id": 1,
                "status": "active",
                "registered_at": "2026-03-09T10:00:00Z",
            }
        },
    )

    id: int = Field(description="ID unik pendaftaran.", examples=[42])
    event_id: int = Field(description="ID event yang didaftarkan.", examples=[1])
    status: RegistrationStatus = Field(
        description="Status pendaftaran: `active` atau `cancelled`.",
        examples=["active"],
    )
    registered_at: datetime = Field(
        description="Waktu pendaftaran dibuat (UTC).",
        examples=["2026-03-09T10:00:00Z"],
    )


class RegistrationWithEventResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 42,
                "event_id": 1,
                "status": "active",
                "registered_at": "2026-03-09T10:00:00Z",
                "cancelled_at": None,
                "event": {
                    "id": 1,
                    "title": "Workshop Python untuk Pemula",
                    "date": "2026-06-15T09:00:00+07:00",
                    "registration_deadline": "2026-06-10T23:59:59+07:00",
                    "status": "active",
                },
            }
        },
    )

    id: int = Field(description="ID unik pendaftaran.", examples=[42])
    event_id: int = Field(description="ID event yang didaftarkan.", examples=[1])
    status: RegistrationStatus = Field(
        description="Status pendaftaran: `active` atau `cancelled`.",
        examples=["active"],
    )
    registered_at: datetime = Field(
        description="Waktu pendaftaran dibuat (UTC).",
        examples=["2026-03-09T10:00:00Z"],
    )
    cancelled_at: datetime | None = Field(
        description="Waktu pembatalan (UTC). `null` jika masih aktif.",
        examples=[None],
    )
    event: EventSummary = Field(description="Ringkasan event yang didaftarkan.")
