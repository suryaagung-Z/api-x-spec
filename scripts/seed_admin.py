"""Seed an initial admin user.

Usage:
    SEED_ADMIN_EMAIL=admin@example.com \\
    SEED_ADMIN_PASSWORD=StrongP@ss123 \\
    python scripts/seed_admin.py

Idempotent: skips creation if the email already exists.
Reads credentials from the SEED_ADMIN_EMAIL and SEED_ADMIN_PASSWORD
environment variables (or from a .env file via pydantic-settings).
"""
from __future__ import annotations

import asyncio
import os
import sys

# Add repo root to path so src/ is importable when run as a script
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.domain.exceptions import EmailAlreadyExistsError
from src.infrastructure.auth.password import hash_password
from src.infrastructure.config import settings
from src.infrastructure.db.models import Base
from src.infrastructure.repositories.user_repository import UserRepository


async def seed_admin() -> None:
    email = os.environ.get("SEED_ADMIN_EMAIL", "")
    password = os.environ.get("SEED_ADMIN_PASSWORD", "")

    if not email or not password:
        print(
            "ERROR: Set SEED_ADMIN_EMAIL and SEED_ADMIN_PASSWORD environment variables.",
            file=sys.stderr,
        )
        sys.exit(1)

    engine = create_async_engine(settings.DATABASE_URL)
    factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
        engine, expire_on_commit=False
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with factory() as session:
        repo = UserRepository(session)
        existing = await repo.get_by_email(email)
        if existing:
            print(f"Admin user already exists: {email} — skipping.")
            await engine.dispose()
            return

        try:
            user = await repo.create(
                name="Admin",
                email=email,
                hashed_password=hash_password(password),
                role="admin",
            )
            await session.commit()
            print(f"Admin user created: id={user.id} email={user.email}")
        except EmailAlreadyExistsError:
            print(f"Admin user already exists (concurrent creation): {email} — skipping.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_admin())
