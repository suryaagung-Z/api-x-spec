"""Application settings loaded from environment variables."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    JWT_SECRET_KEY: str = "dev-secret-change-me-in-production-minimum-32-chars"  # noqa: S105
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    DATABASE_URL: str = "sqlite+aiosqlite:///./dev.db"


settings = Settings()
