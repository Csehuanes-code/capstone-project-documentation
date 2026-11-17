"""Consumidor de RabbitMQ (ADR-04) en un hilo de fondo, con pika.

Topología que declara (todo duradero, así que sobrevive a reinicios de RabbitMQ):

  exchange `turismo` (topic, lo comparten los 5 servicios)
     │  bindings: catalogo.oferta.* · reservas.reserva.confirmada · analitica.zona.ocupacion_actualizada
     ▼
  cola `ia.eventos` ──(rechazado sin reintento)──► exchange `ia.eventos.dlx` ──► cola `ia.eventos.errores`

Reglas de confirmación:
  - El mensaje se confirma (ack) solo DESPUÉS de que el manejador guardó en la base.
    Si el proceso muere antes, RabbitMQ lo vuelve a entregar y evento_procesado evita
    aplicarlo dos veces.
  - Error permanente (el mensaje no cumple el contrato) → nack sin reencolar → cola de errores,
    donde queda guardado para revisarlo en el panel (http://localhost:15672).
  - Error temporal (ej. la base no responde) → espera y lo reencola para reintentarlo.
  - Si RabbitMQ se cae, el hilo se reconecta solo; mientras tanto las recomendaciones siguen
    funcionando con las proyecciones que ya están en ia_db.

Con varios procesos (IA_WORKERS) o réplicas, cada uno abre su consumidor sobre la MISMA cola:
RabbitMQ reparte los mensajes entre ellos (consumidores competidores).
"""

from __future__ import annotations

import logging
import threading
from typing import Callable

import pika
from pika.adapters.blocking_connection import BlockingChannel

from ia.aplicacion.puertos import ComprobacionSalud

EXCHANGE_TURISMO = "turismo"

log = logging.getLogger("ia.rabbitmq")


class ConsumidorRabbitMQ:
    def __init__(
        self,
        url: str,
        cola: str,
        suscripciones: tuple[str, ...],
        procesar: Callable[[bytes], object],
        errores_permanentes: tuple[type[BaseException], ...] = (),
        exchange: str = EXCHANGE_TURISMO,
        espera_reconexion_s: float = 3.0,
        espera_reintento_s: float = 2.0,
    ) -> None:
        self._url = url
        self._cola = cola
        self._cola_errores = f"{cola}.errores"
        self._dlx = f"{cola}.dlx"
        self._suscripciones = suscripciones
        self._procesar = procesar
        self._permanentes = errores_permanentes
        self._exchange = exchange
        self._espera_reconexion = espera_reconexion_s
        self._espera_reintento = espera_reintento_s
        self._detener = threading.Event()
        self._conectado = threading.Event()
        self._hilo: threading.Thread | None = None

    # --- ciclo de vida -------------------------------------------------------------------

    def iniciar(self) -> None:
        if self._hilo is not None:
            return
        self._detener.clear()
        self._hilo = threading.Thread(target=self._bucle, name="consumidor-rabbitmq", daemon=True)
        self._hilo.start()

    def detener(self, espera_s: float = 5.0) -> None:
        self._detener.set()
        if self._hilo is not None:
            self._hilo.join(timeout=espera_s)
            self._hilo = None

    @property
    def conectado(self) -> bool:
        return self._conectado.is_set()

    def esperar_conexion(self, espera_s: float) -> bool:
        return self._conectado.wait(espera_s)

    # --- conexión ------------------------------------------------------------------------

    def _bucle(self) -> None:
        while not self._detener.is_set():
            conexion = None
            try:
                parametros = pika.URLParameters(self._url)
                parametros.socket_timeout = 5
                parametros.heartbeat = 30
                conexion = pika.BlockingConnection(parametros)
                canal = conexion.channel()
                self._declarar_topologia(canal)
                canal.basic_qos(prefetch_count=1)
                self._conectado.set()
                log.info("Conectado a RabbitMQ; escuchando la cola %s", self._cola)
                self._consumir(conexion, canal)
            except Exception as exc:  # noqa: BLE001 — cualquier fallo de red se reintenta
                if not self._detener.is_set():
                    log.warning(
                        "RabbitMQ no disponible (%s); reintento en %ss", exc, self._espera_reconexion
                    )
            finally:
                self._conectado.clear()
                if conexion is not None and conexion.is_open:
                    try:
                        conexion.close()
                    except Exception:  # noqa: BLE001
                        pass
            self._detener.wait(self._espera_reconexion)

    def _declarar_topologia(self, canal: BlockingChannel) -> None:
        canal.exchange_declare(exchange=self._exchange, exchange_type="topic", durable=True)
        canal.exchange_declare(exchange=self._dlx, exchange_type="fanout", durable=True)
        canal.queue_declare(queue=self._cola_errores, durable=True)
        canal.queue_bind(queue=self._cola_errores, exchange=self._dlx)
        canal.queue_declare(
            queue=self._cola,
            durable=True,
            arguments={"x-dead-letter-exchange": self._dlx},
        )
        for routing_key in self._suscripciones:
            canal.queue_bind(queue=self._cola, exchange=self._exchange, routing_key=routing_key)

    def _consumir(self, conexion: pika.BlockingConnection, canal: BlockingChannel) -> None:
        for metodo, propiedades, cuerpo in canal.consume(self._cola, inactivity_timeout=1.0):
            if self._detener.is_set():
                break
            if metodo is None:  # pasó 1 s sin mensajes: vuelve a revisar si hay que detenerse
                continue
            message_id = getattr(propiedades, "message_id", None)
            try:
                resultado = self._procesar(cuerpo)
            except self._permanentes as exc:
                log.error(
                    "Mensaje %s (%s) no cumple el contrato, va a %s: %s",
                    message_id, metodo.routing_key, self._cola_errores, exc,
                )
                canal.basic_nack(delivery_tag=metodo.delivery_tag, requeue=False)
            except Exception as exc:  # noqa: BLE001
                log.warning(
                    "Fallo temporal procesando %s (%s), se reintentará: %s",
                    message_id, metodo.routing_key, exc,
                )
                # conexion.sleep sigue atendiendo los heartbeats mientras espera.
                conexion.sleep(self._espera_reintento)
                canal.basic_nack(delivery_tag=metodo.delivery_tag, requeue=True)
            else:
                canal.basic_ack(delivery_tag=metodo.delivery_tag)
                log.info("Evento %s %s: %s", metodo.routing_key, message_id, resultado)
        canal.cancel()


class SaludRabbitMQ(ComprobacionSalud):
    """Informa si el consumidor está conectado. No es crítica: sin RabbitMQ las
    recomendaciones siguen saliendo de ia_db (solo se retrasan las actualizaciones)."""

    nombre = "rabbitmq"
    critica = False

    def __init__(self, consumidor: ConsumidorRabbitMQ) -> None:
        self._consumidor = consumidor

    def disponible(self) -> bool:
        return self._consumidor.conectado
