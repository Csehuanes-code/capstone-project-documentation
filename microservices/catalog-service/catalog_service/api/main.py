"""FastAPI application entrypoint for the Catálogo microservice."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from catalog_service.api.error_handlers import register_error_handlers
from catalog_service.api.routers import (
    calificaciones,
    favoritos,
    itinerarios,
    lotes,
    ofertas,
    zonas,
)
from catalog_service.infrastructure.config import settings
from catalog_service.infrastructure.database import get_engine
from catalog_service.infrastructure.models import Base
from catalog_service.infrastructure.seed import seed_canonical_data


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup and shutdown lifecycle."""
    # In development/test mode without Alembic, auto-create tables and seed
    if not settings.USE_IN_MEMORY_REPO:
        try:
            engine = get_engine()
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            await seed_canonical_data()
        except Exception:
            # PostgreSQL might not be running in isolated test environments
            pass
    else:
        await seed_canonical_data()

    yield

    if not settings.USE_IN_MEMORY_REPO:
        try:
            engine = get_engine()
            await engine.dispose()
        except Exception:
            pass


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    app = FastAPI(
        title="Plataforma Turística Santa Marta — Servicio Catálogo",
        description=(
            "Microservicio de Catálogos (Grupo 4). Gestiona atractivos, actividades, "
            "eventos, oferta turística, políticas de cancelación, tarifas estacionales, "
            "reseñas, favoritos, itinerarios y sincronización en lote. "
            "Sigue Clean Architecture, PostgreSQL 16 con JSONB, y contratos de eventos sobre RabbitMQ."
        ),
        version="1.0.0",
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Error handling
    register_error_handlers(app)

    # Health check (ADR-08 §3.2)
    @app.get("/health", tags=["Operación"], summary="Healthcheck endpoint")
    async def health() -> dict[str, str]:
        return {
            "status": "ok",
            "service": settings.SERVICE_NAME,
            "environment": settings.ENVIRONMENT,
        }

    # Include routers
    app.include_router(ofertas.router)
    app.include_router(calificaciones.router)
    app.include_router(favoritos.router)
    app.include_router(itinerarios.router)
    app.include_router(lotes.router)
    app.include_router(zonas.router)

    return app


app = create_app()
