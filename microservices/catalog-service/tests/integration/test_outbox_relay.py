"""Relevo del outbox (infrastructure/outbox_relay.py).

- El sobre publicado cumple contratos/eventos/sobre-evento.schema.json (siempre corre).
- Con PostgreSQL y RabbitMQ reales (solo si están definidas CATALOG_TEST_DATABASE_URL y
  CATALOG_TEST_RABBITMQ_URL; en CI siempre): el evento guardado en la tabla outbox llega al
  exchange `turismo`, se marca publicado y no se reenvía; si RabbitMQ falla, espera.
"""

from __future__ import annotations

import datetime
import json
import os
import uuid
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

import jsonschema
import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from catalog_service.infrastructure.event_publisher import SqlAlchemyOutboxEventPublisher
from catalog_service.infrastructure.models import Base, OutboxModel
from catalog_service.infrastructure.outbox_relay import (
    Mensaje,
    PublicadorRabbitMQ,
    RelevoOutbox,
    construir_sobre,
)

ESQUEMAS = Path(__file__).resolve().parents[4] / "contratos" / "eventos"
SOBRE_SCHEMA = json.loads((ESQUEMAS / "sobre-evento.schema.json").read_text(encoding="utf-8"))
OFERTA_SCHEMA = json.loads((ESQUEMAS / "catalogo.oferta.schema.json").read_text(encoding="utf-8"))
OFERTA = OFERTA_SCHEMA["examples"][0]

DB_URL = os.getenv("CATALOG_TEST_DATABASE_URL")
MQ_URL = os.getenv("CATALOG_TEST_RABBITMQ_URL")
requiere_infra = pytest.mark.skipif(
    not (DB_URL and MQ_URL),
    reason="requiere CATALOG_TEST_DATABASE_URL y CATALOG_TEST_RABBITMQ_URL",
)


def _fila(**cambios: Any) -> OutboxModel:
    valores: dict[str, Any] = {
        "id": uuid.uuid4(),
        "tipo": "catalogo.oferta.publicada",
        "version": 1,
        "correlation_id": None,
        "datos": OFERTA,
        "ocurrido_en": datetime.datetime.now(datetime.UTC),
        "publicado_en": None,
        "intentos": 0,
    }
    valores.update(cambios)
    return OutboxModel(**valores)


@pytest.mark.parametrize("correlation_id", [None, uuid.uuid4()])
def test_sobre_cumple_el_contrato(correlation_id: uuid.UUID | None) -> None:
    sobre = construir_sobre(_fila(correlation_id=correlation_id))
    jsonschema.validate(sobre, SOBRE_SCHEMA, format_checker=jsonschema.FormatChecker())
    jsonschema.validate(sobre["datos"], OFERTA_SCHEMA)
    assert datetime.datetime.fromisoformat(sobre["ocurrido_en"]).tzinfo is not None


# --- con PostgreSQL y RabbitMQ reales ----------------------------------------------------


@pytest.fixture
async def sesiones() -> AsyncGenerator[async_sessionmaker[AsyncSession], None]:
    assert DB_URL
    motor = create_async_engine(DB_URL)
    async with motor.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(delete(OutboxModel))
    yield async_sessionmaker(motor, expire_on_commit=False)
    await motor.dispose()


@pytest.fixture
def cola() -> Any:
    pika = pytest.importorskip("pika")
    assert MQ_URL
    con = pika.BlockingConnection(pika.URLParameters(MQ_URL))
    canal = con.channel()
    canal.exchange_declare(exchange="turismo", exchange_type="topic", durable=True)
    nombre = canal.queue_declare(queue="", exclusive=True).method.queue
    canal.queue_bind(queue=nombre, exchange="turismo", routing_key="catalogo.oferta.*")

    def recibir() -> list[dict[str, Any]]:
        mensajes = []
        while True:
            metodo, props, cuerpo = canal.basic_get(queue=nombre, auto_ack=True)
            if metodo is None:
                return mensajes
            mensajes.append({"routing_key": metodo.routing_key, "message_id": props.message_id,
                             "sobre": json.loads(cuerpo)})

    yield recibir
    con.close()


async def _guardar_evento(sesiones: async_sessionmaker[AsyncSession]) -> None:
    """Como lo hace el caso de uso: el evento se guarda en la transacción del cambio."""
    async with sesiones() as s, s.begin():
        await SqlAlchemyOutboxEventPublisher(s).publish("catalogo.oferta.publicada", OFERTA)


@requiere_infra
async def test_evento_del_outbox_llega_a_rabbitmq_una_vez(
    sesiones: async_sessionmaker[AsyncSession], cola: Any
) -> None:
    assert MQ_URL
    await _guardar_evento(sesiones)
    relevo = RelevoOutbox(sesiones, PublicadorRabbitMQ(MQ_URL))

    assert await relevo.procesar_pendientes() == 1
    assert await relevo.procesar_pendientes() == 0  # ya no se reenvía

    (mensaje,) = cola()
    assert mensaje["routing_key"] == "catalogo.oferta.publicada"
    assert mensaje["message_id"] == mensaje["sobre"]["evento_id"]
    jsonschema.validate(mensaje["sobre"], SOBRE_SCHEMA)
    assert mensaje["sobre"]["datos"] == OFERTA

    async with sesiones() as s:
        fila = (await s.execute(select(OutboxModel))).scalar_one()
    assert fila.publicado_en is not None and fila.intentos == 1


class _BrokerCaido:
    def publicar_lote(self, mensajes: list[Mensaje]) -> None:
        raise ConnectionError("RabbitMQ no responde (simulado)")


@requiere_infra
async def test_si_rabbitmq_falla_el_evento_espera_y_luego_sale(
    sesiones: async_sessionmaker[AsyncSession], cola: Any
) -> None:
    assert MQ_URL
    await _guardar_evento(sesiones)

    assert await RelevoOutbox(sesiones, _BrokerCaido()).procesar_pendientes() == 0
    async with sesiones() as s:
        fila = (await s.execute(select(OutboxModel))).scalar_one()
    assert fila.publicado_en is None and fila.intentos == 1

    assert await RelevoOutbox(sesiones, PublicadorRabbitMQ(MQ_URL)).procesar_pendientes() == 1
    assert len(cola()) == 1
