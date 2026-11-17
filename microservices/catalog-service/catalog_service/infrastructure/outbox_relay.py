"""Relevo del outbox a RabbitMQ (ADR-04, patrón Transactional Outbox).

Los casos de uso guardan cada evento en la tabla `outbox` en la MISMA transacción del cambio
(event_publisher.py). Este proceso de fondo los lee y los publica en el exchange topic
`turismo`, con el tipo como routing key (ej. catalogo.oferta.publicada), y marca
`publicado_en`. Si RabbitMQ no responde, los eventos esperan en la tabla y se reintentan:
el catálogo sigue funcionando.

Garantía: al menos una vez. Si el proceso cae después de publicar y antes de marcar, el evento
se vuelve a enviar con el MISMO evento_id, y los consumidores (IA, Reservas) lo descartan con
su tabla evento_procesado.

Varias réplicas pueden correr el relevo a la vez: `FOR UPDATE SKIP LOCKED` hace que cada fila
la tome una sola.

Sobre publicado (contratos/eventos/sobre-evento.schema.json):
  {evento_id, tipo, version, ocurrido_en, correlation_id, datos}
"""

from __future__ import annotations

import asyncio
import datetime
import json
import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

import pika
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from catalog_service.infrastructure.models import OutboxModel

log = logging.getLogger("catalog_service.outbox")


@dataclass(frozen=True)
class Mensaje:
    routing_key: str
    cuerpo: bytes
    message_id: str


class Publicador(Protocol):
    def publicar_lote(self, mensajes: list[Mensaje]) -> None: ...


def construir_sobre(fila: OutboxModel) -> dict[str, Any]:
    return {
        "evento_id": str(fila.id),
        "tipo": fila.tipo,
        "version": fila.version,
        "ocurrido_en": fila.ocurrido_en.isoformat(),
        "correlation_id": str(fila.correlation_id) if fila.correlation_id else None,
        "datos": fila.datos,
    }


def construir_mensaje(fila: OutboxModel) -> Mensaje:
    sobre = construir_sobre(fila)
    return Mensaje(
        routing_key=fila.tipo,
        cuerpo=json.dumps(sobre, ensure_ascii=False).encode("utf-8"),
        message_id=sobre["evento_id"],
    )


class PublicadorRabbitMQ:
    """Publica un lote con confirmación del broker (publisher confirms): si RabbitMQ no
    confirma algún mensaje, lanza excepción y el lote no se marca como publicado."""

    def __init__(self, url: str, exchange: str = "turismo") -> None:
        self._url = url
        self._exchange = exchange

    def publicar_lote(self, mensajes: list[Mensaje]) -> None:
        parametros = pika.URLParameters(self._url)
        parametros.socket_timeout = 5
        conexion = pika.BlockingConnection(parametros)
        try:
            canal = conexion.channel()
            canal.confirm_delivery()
            canal.exchange_declare(exchange=self._exchange, exchange_type="topic", durable=True)
            for m in mensajes:
                canal.basic_publish(
                    exchange=self._exchange,
                    routing_key=m.routing_key,
                    body=m.cuerpo,
                    properties=pika.BasicProperties(
                        content_type="application/json",
                        delivery_mode=2,  # persistente: sobrevive a un reinicio de RabbitMQ
                        message_id=m.message_id,
                    ),
                )
        finally:
            conexion.close()


class RelevoOutbox:
    def __init__(
        self,
        session_factory: Callable[[], AsyncSession],
        publicador: Publicador,
        lote: int = 50,
    ) -> None:
        self._sesiones = session_factory
        self._publicador = publicador
        self._lote = lote

    async def procesar_pendientes(self) -> int:
        """Publica hasta `lote` eventos pendientes. Devuelve cuántos quedaron publicados."""
        async with self._sesiones() as sesion, sesion.begin():
            filas = list(
                (
                    await sesion.execute(
                        select(OutboxModel)
                        .where(OutboxModel.publicado_en.is_(None))
                        .order_by(OutboxModel.ocurrido_en)
                        .limit(self._lote)
                        .with_for_update(skip_locked=True)
                    )
                )
                .scalars()
                .all()
            )
            if not filas:
                return 0
            mensajes = [construir_mensaje(f) for f in filas]
            try:
                await asyncio.to_thread(self._publicador.publicar_lote, mensajes)
            except Exception as exc:
                for f in filas:
                    f.intentos += 1
                log.warning(
                    "No se pudieron publicar %d eventos (se reintentarán): %s", len(filas), exc
                )
                return 0
            ahora = datetime.datetime.now(datetime.UTC)
            for f in filas:
                f.publicado_en = ahora
                f.intentos += 1
        log.info("Publicados %d eventos del outbox", len(filas))
        return len(filas)

    async def ejecutar(self, intervalo_s: float) -> None:
        """Bucle de fondo: vacía el outbox y espera `intervalo_s` cuando no hay pendientes."""
        while True:
            try:
                publicados = await self.procesar_pendientes()
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # base caída, etc.: se reintenta en la siguiente vuelta
                log.warning("Fallo en el relevo del outbox: %s", exc)
                publicados = 0
            if publicados < self._lote:
                await asyncio.sleep(intervalo_s)
