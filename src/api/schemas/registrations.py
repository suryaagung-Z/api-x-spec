"""Pydantic schemas for event registration endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from src.domain.models import EventStatus, RegistrationStatus


class EventSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    date: datetime
    registration_deadline: datetime
    status: EventStatus


class RegistrationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_id: int
    status: RegistrationStatus
    registered_at: datetime


class RegistrationWithEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_id: int
    status: RegistrationStatus
    registered_at: datetime
    cancelled_at: datetime | None
    event: EventSummary
