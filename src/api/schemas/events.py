"""Pydantic v2 schemas for event endpoints."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Self

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
    model_validator,
)

from src.domain.models import EventStatus


class EventCreate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Workshop Python untuk Pemula",
                "description": "Workshop intensif belajar Python dari nol.",
                "date": "2026-06-15T09:00:00+07:00",
                "registration_deadline": "2026-06-10T23:59:59+07:00",
                "quota": 30,
            }
        }
    )

    title: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Nama atau judul event.",
        examples=["Workshop Python untuk Pemula"],
    )
    description: str = Field(
        ...,
        min_length=1,
        description="Deskripsi lengkap event.",
        examples=["Workshop intensif belajar Python dari nol."],
    )
    date: AwareDatetime = Field(
        description="Waktu pelaksanaan event (timezone-aware, ISO 8601).",
        examples=["2026-06-15T09:00:00+07:00"],
    )
    registration_deadline: AwareDatetime = Field(
        description="Batas waktu pendaftaran. Harus sebelum atau sama dengan `date`.",
        examples=["2026-06-10T23:59:59+07:00"],
    )
    quota: int = Field(
        ...,
        ge=1,
        description="Jumlah maksimal peserta. Harus ≥ 1.",
        examples=[30],
    )

    @model_validator(mode="after")
    def validate_deadline_before_date(self) -> Self:
        if self.registration_deadline > self.date:
            raise ValueError(
                "registration_deadline must be on or before the event date"
            )
        return self


class EventUpdate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Workshop Python Lanjutan",
                "quota": 50,
            }
        }
    )

    title: str | None = Field(
        None,
        min_length=1,
        max_length=255,
        description="Nama event baru (opsional).",
        examples=["Workshop Python Lanjutan"],
    )
    description: str | None = Field(
        None,
        min_length=1,
        description="Deskripsi baru (opsional).",
        examples=["Workshop Python tingkat lanjut."],
    )
    date: AwareDatetime | None = Field(
        None,
        description="Waktu pelaksanaan baru (opsional).",
        examples=["2026-07-20T09:00:00+07:00"],
    )
    registration_deadline: AwareDatetime | None = Field(
        None,
        description="Batas pendaftaran baru (opsional).",
        examples=["2026-07-15T23:59:59+07:00"],
    )
    quota: int | None = Field(
        None,
        ge=1,
        description="Kuota baru. Tidak boleh lebih kecil dari jumlah peserta aktif saat ini.",
        examples=[50],
    )

    @model_validator(mode="after")
    def validate_deadline_before_date(self) -> Self:
        if self.registration_deadline is not None and self.date is not None:
            if self.registration_deadline > self.date:
                raise ValueError(
                    "registration_deadline must be on or before the event date"
                )
        return self


class EventResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "title": "Workshop Python untuk Pemula",
                "description": "Workshop intensif belajar Python dari nol.",
                "date": "2026-06-15T09:00:00+07:00",
                "registration_deadline": "2026-06-10T23:59:59+07:00",
                "quota": 30,
                "status": "active",
                "registration_closed": False,
                "created_at": "2026-03-01T10:00:00Z",
            }
        },
    )

    id: int = Field(description="ID unik event.", examples=[1])
    title: str = Field(
        description="Nama event.",
        examples=["Workshop Python untuk Pemula"],
    )
    description: str = Field(
        description="Deskripsi event.",
        examples=["Workshop intensif belajar Python dari nol."],
    )
    date: datetime = Field(
        description="Waktu pelaksanaan event.",
        examples=["2026-06-15T09:00:00+07:00"],
    )
    registration_deadline: datetime = Field(
        description="Batas waktu pendaftaran.",
        examples=["2026-06-10T23:59:59+07:00"],
    )
    quota: int = Field(
        description="Jumlah maksimal peserta.",
        examples=[30],
    )
    status: EventStatus = Field(
        description="Status event: `active` atau `cancelled`.",
        examples=["active"],
    )
    created_at: datetime = Field(
        description="Waktu event dibuat (UTC).",
        examples=["2026-03-01T10:00:00Z"],
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def registration_closed(self) -> bool:
        """True if registration_deadline is in the past (UTC now)."""
        dl = self.registration_deadline
        if dl.tzinfo is None:
            # Treat naive datetimes as UTC

            dl = dl.replace(tzinfo=UTC)
        return dl < datetime.now(UTC)
