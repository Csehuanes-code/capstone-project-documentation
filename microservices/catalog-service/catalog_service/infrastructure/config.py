"""Configuration settings loaded from environment variables (12-Factor App)."""

from __future__ import annotations

from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for Catálogo microservice."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Service info
    SERVICE_NAME: str = "catalog-service"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug(cls, v: Any) -> bool:
        if isinstance(v, str):
            return v.lower() in ("true", "1", "t", "yes", "debug", "dev")
        return bool(v)

    # Database (PostgreSQL 16, asyncpg)
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/catalogo_db"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 5

    # Reservas Service (sync call GET /reservas/{id}/estado)
    RESERVAS_SERVICE_URL: str = "http://localhost:8002"
    RESERVAS_TIMEOUT_SECONDS: float = 1.0

    # Security & JWT
    JWT_SECRET: str = "dev-secret-only-change-in-production-env"
    JWT_ALGORITHM: str = "HS256"

    # Use in-memory repositories (for testing or standalone dev mode)
    USE_IN_MEMORY_REPO: bool = False


settings = Settings()
