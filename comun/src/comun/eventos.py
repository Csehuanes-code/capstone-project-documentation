from datetime import datetime, timezone
import json
import logging
import re
from typing import Any, Callable, Protocol
import uuid
import jsonschema
import pika
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import Column, DateTime, Integer, JSON, String, select
from sqlalchemy.orm import DeclarativeBase, Session
from comun.correlacion import establecer_correlation_id, obtener_correlation_id

EXCHANGE_TURISMO = "turismo"
PATRON_TIPO_EVENTO = re.compile(r"^[a-z]+\.[a-z_]+\.[a-z_]+$")

SOBRE_EVENTO_JSON_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["evento_id", "tipo", "version", "ocurrido_en", "datos"],
    "additionalProperties": False,
    "properties": {
        "evento_id": {"type": "string", "format": "uuid"},
        "tipo": {"type": "string", "pattern": "^[a-z]+\\.[a-z_]+\\.[a-z_]+$"},
        "version": {"type": "integer", "minimum": 1},
        "ocurrido_en": {"type": "string", "format": "date-time"},
        "correlation_id": {"type": ["string", "null"]},
        "datos": {"type": "object"},
    },
}


class SobreEvento(BaseModel):
    """Sobre estándar de todo mensaje en RabbitMQ (contratos/eventos/sobre-evento.schema.json)."""
    model_config = ConfigDict(extra="forbid")

    evento_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tipo: str
    version: int = Field(default=1, ge=1)
    ocurrido_en: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    correlation_id: str | None = Field(default_factory=obtener_correlation_id)
    datos: dict[str, Any]

    @field_validator("evento_id")
    @classmethod
    def _validar_uuid(cls, v: str) -> str:
        uuid.UUID(v)
        return v

    @field_validator("tipo")
    @classmethod
    def _validar_tipo(cls, v: str) -> str:
        if not PATRON_TIPO_EVENTO.match(v):
            raise ValueError(f"El tipo de evento '{v}' debe cumplir 'servicio.entidad.hecho'.")
        return v

    def validar_contra_schema(self) -> None:
        jsonschema.validate(instance=self.model_dump(), schema=SOBRE_EVENTO_JSON_SCHEMA)


class OutboxBase(DeclarativeBase):
    pass


class OutboxRegistro(OutboxBase):
    """Tabla transaccional outbox compartida por los microservicios (ADR-04)."""
    __tablename__ = "outbox"

    evento_id = Column(String(36), primary_key=True)
    tipo = Column(String(120), nullable=False, index=True)
    version = Column(Integer, nullable=False, default=1)
    ocurrido_en = Column(String(40), nullable=False)
    correlation_id = Column(String(64), nullable=True)
    datos = Column(JSON, nullable=False)
    creado_en = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    publicado_en = Column(DateTime(timezone=True), nullable=True, index=True)
    intentos = Column(Integer, nullable=False, default=0)


class EventoProcesadoRegistro(OutboxBase):
    """Tabla de deduplicación para consumidores idempotentes."""
    __tablename__ = "evento_procesado"

    evento_id = Column(String(36), primary_key=True)
    tipo = Column(String(120), nullable=False)
    procesado_en = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


def registrar_en_outbox(
    sesion: Session,
    tipo: str,
    datos: dict[str, Any],
    version: int = 1,
    correlation_id: str | None = None,
    evento_id: str | None = None,
) -> SobreEvento:
    """Inserta el sobre de evento en la tabla outbox dentro de la MISMA transacción de negocio."""
    sobre = SobreEvento(
        evento_id=evento_id or str(uuid.uuid4()),
        tipo=tipo,
        version=version,
        ocurrido_en=datetime.now(timezone.utc).isoformat(),
        correlation_id=correlation_id if correlation_id is not None else obtener_correlation_id(),
        datos=datos,
    )
    sobre.validar_contra_schema()
    registro = OutboxRegistro(
        evento_id=sobre.evento_id,
        tipo=sobre.tipo,
        version=sobre.version,
        ocurrido_en=sobre.ocurrido_en,
        correlation_id=sobre.correlation_id,
        datos=sobre.datos,
        creado_en=datetime.now(timezone.utc),
        publicado_en=None,
        intentos=0,
    )
    sesion.add(registro)
    return sobre


class PublicadorBroker(Protocol):
    def publicar(self, routing_key: str, cuerpo_json: str, message_id: str) -> None:
        ...


class PublicadorRabbitMQ:
    """Publica mensajes persistentes en el exchange topic 'turismo'."""

    def __init__(self, amqp_url: str, exchange: str = EXCHANGE_TURISMO):
        self.amqp_url = amqp_url
        self.exchange = exchange

    def publicar(self, routing_key: str, cuerpo_json: str, message_id: str) -> None:
        params = pika.URLParameters(self.amqp_url)
        params.socket_timeout = 3
        conexion = pika.BlockingConnection(params)
        try:
            canal = conexion.channel()
            canal.confirm_delivery()  # basic_publish lanza excepción si RabbitMQ no confirma
            canal.exchange_declare(exchange=self.exchange, exchange_type="topic", durable=True)
            canal.basic_publish(
                exchange=self.exchange,
                routing_key=routing_key,
                body=cuerpo_json.encode("utf-8"),
                properties=pika.BasicProperties(
                    content_type="application/json",
                    delivery_mode=2,
                    message_id=message_id,
                ),
            )
        finally:
            conexion.close()


class ProcesadorOutbox:
    """Lee eventos pendientes de la tabla outbox, los publica en RabbitMQ y marca publicado_en."""

    def __init__(self, session_factory: Callable[[], Session], publicador: PublicadorBroker, lote: int = 50):
        self.session_factory = session_factory
        self.publicador = publicador
        self.lote = lote
        self.logger = logging.getLogger("comun.outbox")

    def procesar_pendientes(self) -> int:
        publicados = 0
        with self.session_factory() as sesion:
            pendientes = (
                sesion.execute(
                    select(OutboxRegistro)
                    .where(OutboxRegistro.publicado_en.is_(None))
                    .order_by(OutboxRegistro.creado_en.asc())
                    .limit(self.lote)
                )
                .scalars()
                .all()
            )
            for reg in pendientes:
                sobre = SobreEvento(
                    evento_id=reg.evento_id,
                    tipo=reg.tipo,
                    version=reg.version,
                    ocurrido_en=reg.ocurrido_en,
                    correlation_id=reg.correlation_id,
                    datos=reg.datos,
                )
                try:
                    self.publicador.publicar(
                        routing_key=sobre.tipo,
                        cuerpo_json=sobre.model_dump_json(),
                        message_id=sobre.evento_id,
                    )
                    reg.publicado_en = datetime.now(timezone.utc)
                    reg.intentos += 1
                    sesion.commit()
                    publicados += 1
                except Exception as exc:
                    sesion.rollback()
                    reg.intentos += 1
                    sesion.commit()
                    self.logger.warning(
                        f"Fallo publicando evento {reg.evento_id} ({reg.tipo}); quedará pendiente para reintento: {exc}"
                    )
                    break
        return publicados


class ConsumidorIdempotente:
    """Procesa un SobreEvento garantizando exactamente-una-vez mediante evento_procesado."""

    def __init__(
        self,
        session_factory: Callable[[], Session],
        manejadores: dict[str, Callable[[Session, SobreEvento], None]],
    ):
        self.session_factory = session_factory
        self.manejadores = manejadores
        self.logger = logging.getLogger("comun.consumidor")

    def procesar_mensaje_raw(self, cuerpo_raw: bytes | str) -> bool:
        """Devuelve True si el evento fue procesado por primera vez, False si ya existía (duplicado)."""
        if isinstance(cuerpo_raw, bytes):
            cuerpo_raw = cuerpo_raw.decode("utf-8")
        data = json.loads(cuerpo_raw)
        sobre = SobreEvento.model_validate(data)
        sobre.validar_contra_schema()

        establecer_correlation_id(sobre.correlation_id)
        try:
            with self.session_factory() as sesion:
                ya_existe = sesion.get(EventoProcesadoRegistro, sobre.evento_id)
                if ya_existe is not None:
                    self.logger.info(f"Evento duplicado ignorado: {sobre.evento_id}")
                    return False

                manejador = self.manejadores.get(sobre.tipo)
                if manejador is not None:
                    manejador(sesion, sobre)

                sesion.add(
                    EventoProcesadoRegistro(
                        evento_id=sobre.evento_id,
                        tipo=sobre.tipo,
                        procesado_en=datetime.now(timezone.utc),
                    )
                )
                sesion.commit()
                return True
        finally:
            establecer_correlation_id(None)
