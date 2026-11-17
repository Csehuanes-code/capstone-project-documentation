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

    # Reservas Service (sync call GET /reservas/{id}/estado). Puertos acordados:
    # IA 8000, Auth 8001, Catálogo 8002, Reservas 8003, Analítica 8004.
    RESERVAS_SERVICE_URL: str = "http://localhost:8003"
    RESERVAS_TIMEOUT_SECONDS: float = 1.0

    # Security & JWT (ADR-06): tokens ES256 emitidos por Auth, validados con su clave pública.
    # Ver infrastructure/security.py. Sin clave configurada, ninguna ruta protegida acepta tokens.
    JWT_PUBLIC_KEY: str = ""  # PEM de la clave pública de Auth
    JWT_PUBLIC_KEY_FILE: str = ""  # o la ruta a ese PEM
    JWT_JWKS_URL: str = ""  # o el endpoint /jwks de Auth (ej. http://auth:8001/jwks)
    JWT_ISSUER: str = "http://localhost:8001"
    JWT_AUDIENCE: str = "santa-marta-platform"

    # RabbitMQ (ADR-04): si está vacío, los eventos se quedan en la tabla outbox sin publicarse.
    RABBITMQ_URL: str = ""
    RABBITMQ_EXCHANGE: str = "turismo"
    RABBITMQ_COLA_EVENTOS: str = "catalogo.eventos"  # eventos que consume Catálogo (api/eventos.py)
    OUTBOX_INTERVALO_SEGUNDOS: float = 2.0
    OUTBOX_LOTE: int = 50

    # Use in-memory repositories (for testing or standalone dev mode)
    USE_IN_MEMORY_REPO: bool = False


settings = Settings()
