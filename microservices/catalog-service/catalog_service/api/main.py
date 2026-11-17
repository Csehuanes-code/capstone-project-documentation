"""FastAPI application entrypoint for the Catálogo microservice."""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from catalog_service.api.error_handlers import register_error_handlers
from catalog_service.api.eventos import SUSCRIPCIONES, MensajeInvalido, procesar_mensaje
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
from catalog_service.infrastructure.event_consumer import ConsumidorEventos
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
    tareas: list[asyncio.Task[None]] = []
    if settings.RABBITMQ_URL and not settings.USE_IN_MEMORY_REPO:
        tareas.append(
            asyncio.create_task(
                RelevoOutbox(
                    get_sessionmaker(),
                    PublicadorRabbitMQ(settings.RABBITMQ_URL, settings.RABBITMQ_EXCHANGE),
                    lote=settings.OUTBOX_LOTE,
                ).ejecutar(settings.OUTBOX_INTERVALO_SEGUNDOS)
            )
        )
        # Consumidor de eventos de otros servicios (hoy: verificación de prestadores de Auth).
        sesiones = get_sessionmaker()

        async def _procesar(cuerpo: bytes) -> object:
            return await procesar_mensaje(sesiones, cuerpo)

        consumidor = ConsumidorEventos(
            url=settings.RABBITMQ_URL,
            procesar=_procesar,
            suscripciones=SUSCRIPCIONES,
            errores_permanentes=(MensajeInvalido,),
            cola=settings.RABBITMQ_COLA_EVENTOS,
            exchange=settings.RABBITMQ_EXCHANGE,
        )
        app.state.consumidor_eventos = consumidor
        tareas.append(asyncio.create_task(consumidor.ejecutar()))

    yield

    for tarea in tareas:
        tarea.cancel()
    for tarea in tareas:
        with contextlib.suppress(asyncio.CancelledError):
            await tarea

    if not settings.USE_IN_MEMORY_REPO:
        try:
            engine = get_engine()
            await engine.dispose()
        except Exception:
            pass


async def verificar_base_datos() -> bool:
    """SELECT 1 con un límite de 2 s. En modo memoria no hay base: siempre lista."""
    if settings.USE_IN_MEMORY_REPO:
        return True
    try:
        async with asyncio.timeout(2):
            async with get_engine().connect() as conn:
                await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


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

    app.state.consumidor_eventos = None

    # Health check (ADR-08 §3.2)
    @app.get("/health", tags=["Operación"], summary="Liveness: el proceso está vivo")
    async def health() -> dict[str, str]:
        return {
            "status": "ok",
            "service": settings.SERVICE_NAME,
            "environment": settings.ENVIRONMENT,
        }

    @app.get(
        "/health/ready",
        tags=["Operación"],
        summary="Readiness: 503 si PostgreSQL no responde (el Gateway deja de enviarle tráfico)",
    )
    async def ready() -> JSONResponse:
        base_ok = await verificar_base_datos()
        consumidor = app.state.consumidor_eventos
        dependencias: dict[str, bool | None] = {
            "base_de_datos": base_ok,
            # Informativo: sin RabbitMQ el catálogo sigue atendiendo y los eventos esperan.
            "rabbitmq": None if consumidor is None else consumidor.conectado,
        }
        return JSONResponse(
            status_code=200 if base_ok else 503,
            content={
                "estado": "listo" if base_ok else "no_listo",
                "servicio": settings.SERVICE_NAME,
                "dependencias": dependencias,
            },
        )

    # Include routers
    app.include_router(ofertas.router)
    app.include_router(calificaciones.router)
    app.include_router(favoritos.router)
    app.include_router(itinerarios.router)
    app.include_router(lotes.router)
    app.include_router(zonas.router)

    return app


app = create_app()
