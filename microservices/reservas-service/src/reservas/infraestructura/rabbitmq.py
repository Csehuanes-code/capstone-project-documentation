"""Mensajería con RabbitMQ (ADR-04): consumidor de eventos de Catálogo con cola de errores.

Topología (todo duradero):

  exchange `turismo` (topic, compartido por los 5 servicios)
     │  binding: catalogo.oferta.*
     ▼
  cola `reservas.catalogo.ofertas` ──(rechazado)──► exchange `reservas.catalogo.ofertas.dlx`
                                                    └─► cola `reservas.catalogo.ofertas.errores`

- El mensaje se confirma (ack) solo después de guardar la proyección. Los repetidos se
  descartan con evento_procesado en la MISMA transacción (comun.eventos.ConsumidorIdempotente).
- Mensaje que no cumple el contrato → cola de errores (queda para revisarlo en el panel).
- Fallo temporal (ej. base caída) → espera y se reencola para reintentar.
- Si RabbitMQ se cae, el hilo se reconecta solo; las reservas siguen funcionando.
"""

from __future__ import annotations

import json
import logging
import threading
from collections.abc import Callable

import jsonschema
import pika
from pydantic import ValidationError
from sqlalchemy.orm import Session

from comun.correlacion import establecer_correlation_id
from comun.eventos import EXCHANGE_TURISMO, SobreEvento
from reservas.aplicacion import textos
from reservas.dominio.entidades import ProyeccionOfertaLocal
from reservas.infraestructura.sql.repositorios import (
    NotificacionRepositoryPostgres,
    ProyeccionOfertaRepositoryPostgres,
)

log = logging.getLogger("reservas.mensajeria")

TIPOS_OFERTA = ("catalogo.oferta.publicada", "catalogo.oferta.actualizada", "catalogo.oferta.retirada")
TIPO_NOTIFICACION_AUTH = "auth.notificacion.solicitada"

# Errores que no se arreglan reintentando: el mensaje no cumple el contrato.
ERRORES_PERMANENTES: tuple[type[BaseException], ...] = (
    ValidationError,
    jsonschema.ValidationError,
    json.JSONDecodeError,
    UnicodeDecodeError,
    KeyError,
    TypeError,
    ValueError,
)


def manejar_evento_oferta_catalogo(sesion: Session, sobre: SobreEvento) -> None:
    """catalogo.oferta.{publicada,actualizada,retirada} (contratos/eventos/catalogo.oferta.schema.json).

    Reservas solo guarda lo que necesita: zona, prestador (para que solo el dueño cree franjas)
    y si la oferta está activa.
    """
    if sobre.tipo not in TIPOS_OFERTA:
        return
    if sobre.version != 1:
        raise ValueError(f"{sobre.tipo} versión {sobre.version} no soportada.")
    d = sobre.datos
    for campo in ("oferta_id", "nombre", "zona_id", "prestador_id"):
        if not isinstance(d.get(campo), str) or not d[campo]:
            raise ValueError(f"{campo} debe ser un texto no vacío.")
    if not isinstance(d.get("activa"), bool):
        raise ValueError("activa debe ser true o false.")
    ProyeccionOfertaRepositoryPostgres(sesion).guardar_o_actualizar(
        ProyeccionOfertaLocal(
            oferta_id=d["oferta_id"],
            nombre=d["nombre"],
            zona_id=d["zona_id"],
            prestador_id=d["prestador_id"],
            activa=False if sobre.tipo == "catalogo.oferta.retirada" else d["activa"],
        )
    )


def crear_manejador_notificacion_auth(url_frontend: str) -> Callable[[Session, SobreEvento], None]:
    """auth.notificacion.solicitada: Auth pide enviar un correo (hoy, confirmación de registro).

    Se guarda en la tabla `notificacion` en la misma transacción que evento_procesado; el
    proceso de fondo de Reservas la envía por SMTP y la reintenta si el correo falla.
    """

    def manejar(sesion: Session, sobre: SobreEvento) -> None:
        if sobre.tipo != TIPO_NOTIFICACION_AUTH:
            return
        d = sobre.datos
        if d.get("tipo") != "confirmacion_registro":
            return  # otros avisos de Auth aún no tienen plantilla
        for campo in ("destinatario_id", "correo", "token_confirmacion"):
            if not isinstance(d.get(campo), str) or not d[campo]:
                raise ValueError(f"{campo} debe ser un texto no vacío.")
        NotificacionRepositoryPostgres(sesion).guardar(
            textos.confirmacion_registro(
                destinatario_id=d["destinatario_id"],
                correo=d["correo"],
                token=d["token_confirmacion"],
                idioma=str(d.get("idioma") or "es"),
                url_frontend=url_frontend,
            )
        )

    return manejar


class ConsumidorRabbitMQ:
    """Hilo de fondo que escucha una cola y entrega cada mensaje a `procesar(bytes)`."""

    def __init__(
        self,
        url: str,
        cola: str,
        suscripciones: tuple[str, ...],
        procesar: Callable[[bytes], object],
        errores_permanentes: tuple[type[BaseException], ...] = ERRORES_PERMANENTES,
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

    def iniciar(self) -> None:
        if self._hilo is None:
            self._detener.clear()
            self._hilo = threading.Thread(target=self._bucle, name="consumidor-rabbitmq", daemon=True)
            self._hilo.start()

    def detener(self, espera_s: float = 5.0) -> None:
        self._detener.set()
        if self._hilo is not None:
            self._hilo.join(timeout=espera_s)
            self._hilo = None

    def esperar_conexion(self, espera_s: float) -> bool:
        return self._conectado.wait(espera_s)

    def _bucle(self) -> None:
        while not self._detener.is_set():
            conexion = None
            try:
                parametros = pika.URLParameters(self._url)
                parametros.socket_timeout = 5
                parametros.heartbeat = 30
                conexion = pika.BlockingConnection(parametros)
                canal = conexion.channel()
                self._declarar(canal)
                canal.basic_qos(prefetch_count=1)
                self._conectado.set()
                log.info("Escuchando la cola %s", self._cola)
                self._consumir(conexion, canal)
            except Exception as exc:  # noqa: BLE001 — se reintenta la conexión
                if not self._detener.is_set():
                    log.warning("RabbitMQ no disponible (%s); reintento en %ss", exc, self._espera_reconexion)
            finally:
                self._conectado.clear()
                if conexion is not None and conexion.is_open:
                    try:
                        conexion.close()
                    except Exception:  # noqa: BLE001
                        pass
            self._detener.wait(self._espera_reconexion)

    def _declarar(self, canal) -> None:  # type: ignore[no-untyped-def]
        canal.exchange_declare(exchange=self._exchange, exchange_type="topic", durable=True)
        canal.exchange_declare(exchange=self._dlx, exchange_type="fanout", durable=True)
        canal.queue_declare(queue=self._cola_errores, durable=True)
        canal.queue_bind(queue=self._cola_errores, exchange=self._dlx)
        canal.queue_declare(queue=self._cola, durable=True,
                            arguments={"x-dead-letter-exchange": self._dlx})
        for routing_key in self._suscripciones:
            canal.queue_bind(queue=self._cola, exchange=self._exchange, routing_key=routing_key)

    def _consumir(self, conexion, canal) -> None:  # type: ignore[no-untyped-def]
        for metodo, props, cuerpo in canal.consume(self._cola, inactivity_timeout=1.0):
            if self._detener.is_set():
                break
            if metodo is None:
                continue
            message_id = getattr(props, "message_id", None)
            try:
                self._procesar(cuerpo)
            except self._permanentes as exc:
                log.error("Mensaje %s (%s) no cumple el contrato; va a %s: %s",
                          message_id, metodo.routing_key, self._cola_errores, exc)
                canal.basic_nack(delivery_tag=metodo.delivery_tag, requeue=False)
            except Exception as exc:  # noqa: BLE001
                log.warning("Fallo temporal con %s (%s); se reintentará: %s",
                            message_id, metodo.routing_key, exc)
                conexion.sleep(self._espera_reintento)
                canal.basic_nack(delivery_tag=metodo.delivery_tag, requeue=True)
            else:
                canal.basic_ack(delivery_tag=metodo.delivery_tag)
            finally:
                establecer_correlation_id(None)
        canal.cancel()


def verificar_rabbitmq(url: str) -> bool:
    parametros = pika.URLParameters(url)
    parametros.socket_timeout = 2
    conexion = pika.BlockingConnection(parametros)
    conexion.close()
    return True
