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
    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    date: AwareDatetime
    registration_deadline: AwareDatetime
    quota: int = Field(..., ge=1)

    @model_validator(mode="after")
    def validate_deadline_before_date(self) -> Self:
        if self.registration_deadline > self.date:
            raise ValueError(
                "registration_deadline must be on or before the event date"
            )
        return self


class EventUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, min_length=1)
    date: AwareDatetime | None = None
    registration_deadline: AwareDatetime | None = None
    quota: int | None = Field(None, ge=1)

    @model_validator(mode="after")
    def validate_deadline_before_date(self) -> Self:
        if self.registration_deadline is not None and self.date is not None:
            if self.registration_deadline > self.date:
                raise ValueError(
                    "registration_deadline must be on or before the event date"
                )
        return self


class EventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    date: datetime
    registration_deadline: datetime
    quota: int
    status: EventStatus
    created_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def registration_closed(self) -> bool:
        """True if registration_deadline is in the past (UTC now)."""
        dl = self.registration_deadline
        if dl.tzinfo is None:
            # Treat naive datetimes as UTC

            dl = dl.replace(tzinfo=UTC)
        return dl < datetime.now(UTC)
