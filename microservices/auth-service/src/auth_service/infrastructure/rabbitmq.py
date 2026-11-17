"""Publicador de eventos del outbox en RabbitMQ (ADR-04), con confirmación del broker.

Cada evento sale envuelto en el sobre común (contratos/eventos/sobre-evento.schema.json) al
exchange topic `turismo`, con el tipo como routing key. Los tipos que no siguen el formato
`servicio.entidad.hecho` (hoy `notificacion.solicitada`) se publican con prefijo `auth.`.

Si RabbitMQ no confirma, se lanza EventPublishError: DispatchOutbox deja el evento pendiente y
lo reintenta con espera creciente. Entrega al menos una vez: el `evento_id` es el id del outbox,
así los consumidores descartan repetidos.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime

import aio_pika
from aio_pika.abc import AbstractRobustConnection

from auth_service.application.outbox import EventPublishError, OutboxEvent

_PATRON_TIPO = re.compile(r"^[a-z]+\.[a-z_]+\.[a-z_]+$")


def routing_key(event_type: str) -> str:
    return event_type if _PATRON_TIPO.match(event_type) else f"auth.{event_type}"


def sobre(event: OutboxEvent, ocurrido_en: datetime | None = None) -> dict[str, object]:
    return {
        "evento_id": str(event.id),
        "tipo": routing_key(event.event_type),
        "version": 1,
        "ocurrido_en": (ocurrido_en or datetime.now(UTC)).isoformat(),
        "correlation_id": None,
        "datos": event.payload,
    }


class RabbitMqEventPublisher:
    def __init__(self, url: str, exchange: str = "turismo") -> None:
        self._url = url
        self._exchange_name = exchange
        self._connection: AbstractRobustConnection | None = None
        self._exchange: aio_pika.abc.AbstractExchange | None = None

    async def _exchange_listo(self) -> aio_pika.abc.AbstractExchange:
        if self._exchange is None or self._connection is None or self._connection.is_closed:
            self._connection = await aio_pika.connect_robust(self._url, timeout=5)
            channel = await self._connection.channel(publisher_confirms=True)
            self._exchange = await channel.declare_exchange(
                self._exchange_name, aio_pika.ExchangeType.TOPIC, durable=True
            )
        return self._exchange

    async def publish(self, event: OutboxEvent) -> None:
        try:
            exchange = await self._exchange_listo()
            cuerpo = sobre(event)
            await exchange.publish(
                aio_pika.Message(
                    body=json.dumps(cuerpo, ensure_ascii=False).encode("utf-8"),
                    content_type="application/json",
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                    message_id=str(event.id),
                ),
                routing_key=str(cuerpo["tipo"]),
            )
        except Exception as exc:
            self._exchange = None  # fuerza reconexión en el siguiente intento
            raise EventPublishError("rabbitmq_unavailable") from exc

    async def close(self) -> None:
        if self._connection is not None and not self._connection.is_closed:
            await self._connection.close()
