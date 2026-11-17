"""FastAPI application entrypoint for the Catálogo microservice."""

from __future__ import annotations

import asyncio
import contextlib
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
from catalog_service.infrastructure.database import get_engine, get_sessionmaker
from catalog_service.infrastructure.models import Base
from catalog_service.infrastructure.outbox_relay import PublicadorRabbitMQ, RelevoOutbox
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

    # Relevo del outbox a RabbitMQ (ADR-04): sin él, los eventos catalogo.oferta.* nunca salen
    # de la tabla outbox y ni IA ni Reservas se enteran de las ofertas.
    relevo: asyncio.Task[None] | None = None
    if settings.RABBITMQ_URL and not settings.USE_IN_MEMORY_REPO:
        relevo = asyncio.create_task(
            RelevoOutbox(
                get_sessionmaker(),
                PublicadorRabbitMQ(settings.RABBITMQ_URL, settings.RABBITMQ_EXCHANGE),
                lote=settings.OUTBOX_LOTE,
            ).ejecutar(settings.OUTBOX_INTERVALO_SEGUNDOS)
        )

    yield

    if relevo is not None:
        relevo.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await relevo

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
