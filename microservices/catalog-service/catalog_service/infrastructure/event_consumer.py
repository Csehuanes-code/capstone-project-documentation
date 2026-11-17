"""Consumidor de eventos de RabbitMQ (ADR-04 §4.3), asíncrono con aio-pika.

Topología (todo duradero):

  exchange `turismo` (topic, compartido por los 5 servicios)
     │  bindings: los de api/eventos.SUSCRIPCIONES (hoy auth.prestador.verificacion_resuelta)
     ▼
  cola `catalogo.eventos` ──(rechazado)──► exchange `catalogo.eventos.dlx` ──► cola `catalogo.eventos.errores`

- Se confirma (ack) solo después de guardar en la base.
- Mensaje que no cumple el contrato → cola de errores (se revisa en el panel :15672).
- Fallo temporal (ej. PostgreSQL caído) → se reencola tras una pausa.
- Si RabbitMQ se cae, el bucle se reconecta; el catálogo sigue atendiendo.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable

import aio_pika
from aio_pika.abc import AbstractIncomingMessage

log = logging.getLogger("catalog_service.eventos")


class ConsumidorEventos:
    def __init__(
        self,
        url: str,
        procesar: Callable[[bytes], Awaitable[object]],
        suscripciones: tuple[str, ...],
        errores_permanentes: tuple[type[BaseException], ...],
        cola: str = "catalogo.eventos",
        exchange: str = "turismo",
        espera_reconexion_s: float = 3.0,
        espera_reintento_s: float = 2.0,
    ) -> None:
        self._url = url
        self._procesar = procesar
        self._suscripciones = suscripciones
        self._permanentes = errores_permanentes
        self._cola = cola
        self._exchange = exchange
        self._espera_reconexion = espera_reconexion_s
        self._espera_reintento = espera_reintento_s
        self.conectado = False

    async def ejecutar(self) -> None:
        """Bucle de fondo: conecta, escucha y se reconecta si RabbitMQ cae."""
        while True:
            try:
                conexion = await aio_pika.connect(self._url, timeout=5)
                async with conexion:
                    canal = await conexion.channel()
                    await canal.set_qos(prefetch_count=10)
                    cola = await self._declarar(canal)
                    self.conectado = True
                    log.info("Escuchando la cola %s", self._cola)
                    async with cola.iterator() as mensajes:
                        async for mensaje in mensajes:
                            await self._manejar(mensaje)
            except asyncio.CancelledError:
                self.conectado = False
                raise
            except Exception as exc:
                log.warning("RabbitMQ no disponible (%s); reintento en %ss", exc, self._espera_reconexion)
            self.conectado = False
            await asyncio.sleep(self._espera_reconexion)

    async def _declarar(self, canal: aio_pika.abc.AbstractChannel) -> aio_pika.abc.AbstractQueue:
        exchange = await canal.declare_exchange(
            self._exchange, aio_pika.ExchangeType.TOPIC, durable=True
        )
        dlx = await canal.declare_exchange(
            f"{self._cola}.dlx", aio_pika.ExchangeType.FANOUT, durable=True
        )
        errores = await canal.declare_queue(f"{self._cola}.errores", durable=True)
        await errores.bind(dlx)
        cola = await canal.declare_queue(
            self._cola, durable=True, arguments={"x-dead-letter-exchange": f"{self._cola}.dlx"}
        )
        for routing_key in self._suscripciones:
            await cola.bind(exchange, routing_key=routing_key)
        return cola

    async def _manejar(self, mensaje: AbstractIncomingMessage) -> None:
        try:
            resultado = await self._procesar(mensaje.body)
        except self._permanentes as exc:
            log.error("Mensaje %s (%s) no cumple el contrato; va a %s.errores: %s",
                      mensaje.message_id, mensaje.routing_key, self._cola, exc)
            await mensaje.reject(requeue=False)
        except Exception as exc:
            log.warning("Fallo temporal con %s (%s); se reintentará: %s",
                        mensaje.message_id, mensaje.routing_key, exc)
            await asyncio.sleep(self._espera_reintento)
            await mensaje.reject(requeue=True)
        else:
            await mensaje.ack()
            log.info("Evento %s %s: %s", mensaje.routing_key, mensaje.message_id, resultado)
