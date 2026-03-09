"""User repository: async data access layer for the users table."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.exceptions import EmailAlreadyExistsError
from src.domain.models import User, UserRole
from src.infrastructure.db.models import User as OrmUser


def _to_domain(orm: OrmUser) -> User:
    return User(
        id=orm.id,
        name=orm.name,
        email=orm.email,
        hashed_password=orm.hashed_password,
        role=UserRole(orm.role),
        created_at=orm.created_at,
    )


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_email(self, email: str) -> User | None:
        """Look up a user by email (case-insensitive, input normalised by caller)."""
        stmt = select(OrmUser).where(OrmUser.email == email.lower())
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return _to_domain(orm) if orm else None

    async def get_by_id(self, user_id: str) -> User | None:
        result = await self._session.execute(
            select(OrmUser).where(OrmUser.id == user_id)
        )
        orm = result.scalar_one_or_none()
        return _to_domain(orm) if orm else None

    async def create(
        self,
        name: str,
        email: str,
        hashed_password: str,
        role: str = "user",
    ) -> User:
        """Persist a new user; raises EmailAlreadyExistsError on duplicate email."""
        orm = OrmUser(
            id=str(uuid.uuid4()),
            name=name,
            email=email.lower(),  # normalise at persistence layer too
            hashed_password=hashed_password,
            role=role,
            created_at=datetime.now(tz=UTC),
        )
        self._session.add(orm)
        try:
            await self._session.flush()
        except IntegrityError:
            await self._session.rollback()
            raise EmailAlreadyExistsError(email) from None
        return _to_domain(orm)

    async def get_all(self) -> list[User]:
        result = await self._session.execute(select(OrmUser))
        return [_to_domain(row) for row in result.scalars().all()]
