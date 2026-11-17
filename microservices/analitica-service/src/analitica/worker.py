"""Consumidor y publicador RabbitMQ con confirmación de mensajes."""

from __future__ import annotations

import logging
import threading

import pika

from analitica.aplicacion import ProcesarReserva
from analitica.configuracion import config
from analitica.eventos import MensajeInvalido, procesar_mensaje
from analitica.persistencia import RepositorioSql

log = logging.getLogger("analitica.rabbitmq")


class Consumidor:
    def __init__(self, repository: RepositorioSql) -> None:
        self._repo = repository
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.connected = threading.Event()

    def start(self) -> None:
        if self._thread is None and config.rabbitmq_url:
            self._thread = threading.Thread(target=self._loop, name="analitica-consumer", daemon=True)
            self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=6)
            self._thread = None

    def _loop(self) -> None:
        while not self._stop.is_set():
            connection = None
            try:
                params = pika.URLParameters(config.rabbitmq_url)
                params.heartbeat = 30
                params.socket_timeout = 5
                connection = pika.BlockingConnection(params)
                channel = connection.channel()
                channel.exchange_declare(exchange=config.exchange, exchange_type="topic", durable=True)
                dlx = f"{config.queue}.dlx"
                channel.exchange_declare(exchange=dlx, exchange_type="fanout", durable=True)
                channel.queue_declare(queue=f"{config.queue}.errores", durable=True)
                channel.queue_bind(queue=f"{config.queue}.errores", exchange=dlx)
                channel.queue_declare(queue=config.queue, durable=True, arguments={"x-dead-letter-exchange": dlx})
                channel.queue_bind(queue=config.queue, exchange=config.exchange, routing_key="reservas.reserva.confirmada")
                channel.basic_qos(prefetch_count=1)
                self.connected.set()
                for method, _, body in channel.consume(config.queue, inactivity_timeout=1):
                    if self._stop.is_set():
                        break
                    if method is None:
                        continue
                    try:
                        result = procesar_mensaje(body, ProcesarReserva(self._repo))
                    except MensajeInvalido as exc:
                        log.error("Evento inválido enviado a DLQ: %s", exc)
                        channel.basic_nack(method.delivery_tag, requeue=False)
                    except Exception:
                        log.exception("Error temporal; se reintentará el evento")
                        connection.sleep(2)
                        channel.basic_nack(method.delivery_tag, requeue=True)
                    else:
                        channel.basic_ack(method.delivery_tag)
                        log.info("Evento de reserva %s", result)
                channel.cancel()
            except Exception:
                if not self._stop.is_set():
                    log.exception("Consumidor RabbitMQ no disponible; reintentando")
            finally:
                self.connected.clear()
                if connection is not None and connection.is_open:
                    connection.close()
            self._stop.wait(3)


class RelevoOutbox:
    def __init__(self, repository: RepositorioSql) -> None:
        self._repo = repository
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.connected = threading.Event()

    def start(self) -> None:
        if config.rabbitmq_url and self._thread is None:
            self._thread = threading.Thread(target=self._loop, name="analitica-outbox", daemon=True)
            self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=6)
            self._thread = None

    def _loop(self) -> None:
        while not self._stop.is_set():
            connection = None
            try:
                connection = pika.BlockingConnection(pika.URLParameters(config.rabbitmq_url))
                channel = connection.channel()
                channel.exchange_declare(exchange=config.exchange, exchange_type="topic", durable=True)
                channel.confirm_delivery()
                self.connected.set()

                def publish(
                    routing_key: str, body: bytes, event_id: str,
                    channel: pika.adapters.blocking_connection.BlockingChannel = channel,
                ) -> None:
                    ok = channel.basic_publish(
                        exchange=config.exchange, routing_key=routing_key, body=body,
                        properties=pika.BasicProperties(delivery_mode=2, content_type="application/json", message_id=event_id, type=routing_key),
                        mandatory=True,
                    )
                    if not ok:
                        raise RuntimeError("RabbitMQ no confirmó el evento")

                while not self._stop.is_set():
                    count = self._repo.publicar_pendientes(publish)
                    if not count:
                        self._stop.wait(config.outbox_interval)
            except Exception:
                if not self._stop.is_set():
                    log.exception("Publicador outbox no disponible; reintentando")
            finally:
                self.connected.clear()
                if connection is not None and connection.is_open:
                    connection.close()
            self._stop.wait(3)


class RecalculoPeriodico:
    """Recalcula y publica la ocupación de las zonas cada `recalculo_segundos`.

    Sin esto, la ocupación solo cambiaba al llegar una reserva: al pasar el día, IA seguía
    viendo la del día anterior y su regla de descongestión (>= 80 %) usaba datos viejos.
    """

    def __init__(self, repository: RepositorioSql) -> None:
        self._repo = repository
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is None:
            self._thread = threading.Thread(target=self._loop, name="analitica-recalculo", daemon=True)
            self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=6)
            self._thread = None

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                zonas = self._repo.recalcular_ocupaciones()
                log.info("Ocupación recalculada en %d zonas", zonas)
            except Exception:
                log.exception("No se pudo recalcular la ocupación; se reintentará")
            self._stop.wait(config.recalculo_segundos)
