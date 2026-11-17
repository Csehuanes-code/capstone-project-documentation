"""Verificación de prestadores de punta a punta con PostgreSQL y RabbitMQ REALES.

Auth publica auth.prestador.verificacion_resuelta → Catálogo marca al prestador como verificado
→ ya puede publicar ofertas (RF-USR-19). Solo corre con CATALOG_TEST_DATABASE_URL y
CATALOG_TEST_RABBITMQ_URL (en CI siempre).
"""

from __future__ import annotations

import asyncio
import json
import os
import uuid
from collections.abc import AsyncGenerator
from typing import Any

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from catalog_service.api.eventos import SUSCRIPCIONES, MensajeInvalido, procesar_mensaje
from catalog_service.infrastructure.event_consumer import ConsumidorEventos
from catalog_service.infrastructure.models import Base, EventoProcesadoModel, PerfilPrestadorModel

DB_URL = os.getenv("CATALOG_TEST_DATABASE_URL")
MQ_URL = os.getenv("CATALOG_TEST_RABBITMQ_URL")
pytestmark = pytest.mark.skipif(
    not (DB_URL and MQ_URL), reason="requiere CATALOG_TEST_DATABASE_URL y CATALOG_TEST_RABBITMQ_URL"
)


def sobre(prestador_id: uuid.UUID, estado: str, evento_id: str | None = None) -> bytes:
    """Exactamente lo que escribe auth-service en su outbox (resolve_verification.py)."""
    return json.dumps({
        "evento_id": evento_id or str(uuid.uuid4()),
        "tipo": "auth.prestador.verificacion_resuelta",
        "version": 1,
        "ocurrido_en": "2026-11-17T03:00:00+00:00",
        "correlation_id": None,
        "datos": {
            "solicitud_id": str(uuid.uuid4()),
            "prestador_id": str(prestador_id),
            "estado": estado,
            "justificacion": "Revisión del administrador.",
        },
    }).encode()


@pytest.fixture
async def sesiones() -> AsyncGenerator[async_sessionmaker[AsyncSession], None]:
    assert DB_URL
    motor = create_async_engine(DB_URL)
    async with motor.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(delete(EventoProcesadoModel))
    yield async_sessionmaker(motor, expire_on_commit=False)
    await motor.dispose()


async def verificado(sesiones: async_sessionmaker[AsyncSession], prestador_id: uuid.UUID) -> bool | None:
    async with sesiones() as s:
        perfil = await s.get(PerfilPrestadorModel, prestador_id)
        return None if perfil is None else perfil.verificado


async def test_aprobada_verifica_repetido_no_cambia_y_rechazada_revoca(
    sesiones: async_sessionmaker[AsyncSession],
) -> None:
    prestador = uuid.uuid4()
    evento = str(uuid.uuid4())
    assert await procesar_mensaje(sesiones, sobre(prestador, "aprobada", evento)) == "procesado"
    assert await verificado(sesiones, prestador) is True
    assert await procesar_mensaje(sesiones, sobre(prestador, "aprobada", evento)) == "repetido"
    assert await procesar_mensaje(sesiones, sobre(prestador, "rechazada")) == "procesado"
    assert await verificado(sesiones, prestador) is False


# --- con RabbitMQ real ---------------------------------------------------------------------


@pytest.fixture
def broker() -> Any:
    pika = pytest.importorskip("pika")
    assert MQ_URL
    cola = f"catalogo.eventos.prueba-{uuid.uuid4().hex[:8]}"
    con = pika.BlockingConnection(pika.URLParameters(MQ_URL))
    canal = con.channel()
    canal.exchange_declare(exchange="turismo", exchange_type="topic", durable=True)

    def publicar(cuerpo: bytes) -> None:
        canal.basic_publish("turismo", "auth.prestador.verificacion_resuelta", cuerpo,
                            pika.BasicProperties(content_type="application/json", delivery_mode=2))

    def mensajes_en(nombre: str) -> int:
        return canal.queue_declare(queue=nombre, passive=True).method.message_count

    yield cola, publicar, mensajes_en
    canal.queue_delete(queue=cola)
    canal.queue_delete(queue=f"{cola}.errores")
    canal.exchange_delete(exchange=f"{cola}.dlx")
    con.close()


async def esperar(condicion: Any, segundos: float = 10.0) -> bool:
    limite = asyncio.get_running_loop().time() + segundos
    while asyncio.get_running_loop().time() < limite:
        if await condicion():
            return True
        await asyncio.sleep(0.1)
    return False


async def test_evento_publicado_en_rabbitmq_verifica_al_prestador(
    sesiones: async_sessionmaker[AsyncSession], broker: Any
) -> None:
    assert MQ_URL
    cola, publicar, mensajes_en = broker

    async def _procesar(cuerpo: bytes) -> object:
        return await procesar_mensaje(sesiones, cuerpo)

    consumidor = ConsumidorEventos(
        url=MQ_URL, procesar=_procesar, suscripciones=SUSCRIPCIONES,
        errores_permanentes=(MensajeInvalido,), cola=cola,
    )
    tarea = asyncio.create_task(consumidor.ejecutar())
    try:
        async def conectado() -> bool:
            return consumidor.conectado

        assert await esperar(conectado), "el consumidor no se conectó a RabbitMQ"
        prestador = uuid.uuid4()
        publicar(sobre(prestador, "aprobada"))

        async def ya_verificado() -> bool:
            return await verificado(sesiones, prestador) is True

        assert await esperar(ya_verificado)

        publicar(b'{"esto": "no es un sobre"}')

        async def en_errores() -> bool:
            return await asyncio.to_thread(mensajes_en, f"{cola}.errores") == 1

        assert await esperar(en_errores), "el mensaje inválido no llegó a la cola de errores"
    finally:
        tarea.cancel()
        with pytest.raises(asyncio.CancelledError):
            await tarea
