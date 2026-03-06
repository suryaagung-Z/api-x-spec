"""SQLAlchemy 2.x async ORM models for users, events, and event registrations."""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
    text,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from src.domain.models import EventStatus, RegistrationStatus


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('user', 'admin')", name="ck_users_role"),
        Index("ix_users_email_lower", func.lower(text("email")), unique=True),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(10), nullable=False, default="user")
    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=lambda: datetime.now(tz=UTC),
    )


class Event(Base):
    __tablename__ = "events"
    __table_args__ = (
        CheckConstraint("quota >= 1", name="chk_quota_positive"),
        CheckConstraint(
            "registration_deadline <= date", name="chk_deadline_before_date"
        ),
        Index("ix_events_date_title", "date", "title"),
        Index("ix_events_registration_deadline", "registration_deadline"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    registration_deadline: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    quota: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[EventStatus] = mapped_column(
        SAEnum(
            EventStatus,
            name="eventstatus",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=EventStatus.ACTIVE,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(tz=UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(tz=UTC),
        onupdate=lambda: datetime.now(tz=UTC),
    )
    current_participants: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )


class EventRegistration(Base):
    __tablename__ = "event_registrations"
    __table_args__ = (
        # Partial unique index: only one ACTIVE registration per (user, event)
        Index(
            "uq_active_registration",
            "user_id",
            "event_id",
            unique=True,
            postgresql_where=text("status = 'active'"),
            sqlite_where=text("status = 'active'"),
        ),
        # Covers WHERE user_id = ? ORDER BY registered_at DESC
        Index("ix_event_registrations_user_registered", "user_id", "registered_at"),
        # Covers WHERE event_id = ? AND status = 'active'
        Index(
            "ix_event_registrations_event_active",
            "event_id",
            postgresql_where=text("status = 'active'"),
            sqlite_where=text("status = 'active'"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )
    event_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("events.id"), nullable=False
    )
    status: Mapped[RegistrationStatus] = mapped_column(
        SAEnum(
            RegistrationStatus,
            name="registrationstatus",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=RegistrationStatus.ACTIVE,
        server_default="active",
    )
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(tz=UTC),
        server_default=func.now(),
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )

    event: Mapped[Event] = relationship("Event", lazy="raise")
