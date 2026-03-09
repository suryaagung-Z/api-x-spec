"""Domain models for the authentication and event-management features."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class UserRole(StrEnum):
    user = "user"
    admin = "admin"


class EventStatus(StrEnum):
    ACTIVE = "active"
    DELETED = "deleted"


class RegistrationStatus(StrEnum):
    ACTIVE = "active"
    CANCELLED = "cancelled"


@dataclass
class User:
    id: str
    name: str
    email: str
    hashed_password: str
    role: UserRole
    created_at: datetime
