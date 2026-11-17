"""SQLAlchemy 2.0 ORM models for catalogo_db (ADR-03, data-model.md §3.2)."""

from __future__ import annotations

import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    Time,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base declarative class for all catalogo_db models."""


class ZonaModel(Base):
    __tablename__ = "zona"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    codigo: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    nombre_es: Mapped[str] = mapped_column(String(120), nullable=False)
    nombre_en: Mapped[str] = mapped_column(String(120), nullable=False)
    ecosistema_sensible: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    latitud: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitud: Mapped[float | None] = mapped_column(Float, nullable=True)

    ofertas = relationship("OfertaModel", back_populates="zona")


class TipoServicioModel(Base):
    __tablename__ = "tipo_servicio"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    codigo: Mapped[str] = mapped_column(String(40), unique=True, nullable=False, index=True)
    nombre_es: Mapped[str] = mapped_column(String(80), nullable=False)
    nombre_en: Mapped[str] = mapped_column(String(80), nullable=False)
    reservable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    esquema_atributos: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    ofertas = relationship("OfertaModel", back_populates="tipo_servicio")


class PerfilPrestadorModel(Base):
    __tablename__ = "perfil_prestador"

    prestador_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    nombre_comercial: Mapped[str] = mapped_column(String(160), nullable=False)
    numero_rnt: Mapped[str | None] = mapped_column(String(20), nullable=True)
    verificado: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    categoria: Mapped[str] = mapped_column(String(30), default="pequeno_mediano", nullable=False)
    actualizado_en: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    ofertas = relationship("OfertaModel", back_populates="prestador")


class FuenteExternaModel(Base):
    __tablename__ = "fuente_externa"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    tipo: Mapped[str] = mapped_column(String(20), default="api", nullable=False)
    integracion_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    activa: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class OfertaModel(Base):
    __tablename__ = "oferta"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    prestador_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("perfil_prestador.prestador_id"),
        nullable=True,
        index=True,
    )
    tipo_servicio_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("tipo_servicio.id"),
        nullable=False,
        index=True,
    )
    zona_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("zona.id"),
        nullable=False,
        index=True,
    )
    nombre_es: Mapped[str] = mapped_column(String(160), nullable=False)
    nombre_en: Mapped[str] = mapped_column(String(160), nullable=False)
    descripcion_es: Mapped[str] = mapped_column(Text, default="", nullable=False)
    descripcion_en: Mapped[str] = mapped_column(Text, default="", nullable=False)
    atributos: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    estado: Mapped[str] = mapped_column(String(30), default="borrador", nullable=False, index=True)
    fuente_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("fuente_externa.id"),
        nullable=True,
    )
    actualizado_fuente_en: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    calificacion_promedio: Mapped[Decimal] = mapped_column(
        Numeric(3, 2), default=Decimal("0.00"), nullable=False
    )
    total_calificaciones: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    creado_en: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    actualizado_en: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    zona = relationship("ZonaModel", back_populates="ofertas")
    tipo_servicio = relationship("TipoServicioModel", back_populates="ofertas")
    prestador = relationship("PerfilPrestadorModel", back_populates="ofertas")
    imagenes = relationship(
        "ImagenOfertaModel", back_populates="oferta", cascade="all, delete-orphan"
    )
    tarifas = relationship("TarifaModel", back_populates="oferta", cascade="all, delete-orphan")
    politica_cancelacion = relationship(
        "PoliticaCancelacionModel",
        back_populates="oferta",
        uselist=False,
        cascade="all, delete-orphan",
    )
    calificaciones = relationship("CalificacionModel", back_populates="oferta")


class ImagenOfertaModel(Base):
    __tablename__ = "imagen_oferta"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    oferta_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("oferta.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    clave_objeto: Mapped[str] = mapped_column(Text, nullable=False)
    orden: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    texto_alternativo_es: Mapped[str] = mapped_column(String(250), default="", nullable=False)
    texto_alternativo_en: Mapped[str] = mapped_column(String(250), default="", nullable=False)

    oferta = relationship("OfertaModel", back_populates="imagenes")


class TarifaModel(Base):
    __tablename__ = "tarifa"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    oferta_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("oferta.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    temporada: Mapped[str] = mapped_column(String(20), nullable=False)
    vigente_desde: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    vigente_hasta: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    precio_por_persona: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    moneda: Mapped[str] = mapped_column(String(3), default="COP", nullable=False)

    oferta = relationship("OfertaModel", back_populates="tarifas")


class PoliticaCancelacionModel(Base):
    __tablename__ = "politica_cancelacion"

    oferta_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("oferta.id", ondelete="CASCADE"),
        primary_key=True,
    )
    horas_reembolso_total: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    horas_reembolso_parcial: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    porcentaje_reembolso_parcial: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    oferta = relationship("OfertaModel", back_populates="politica_cancelacion")


class CalificacionModel(Base):
    __tablename__ = "calificacion"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    oferta_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("oferta.id"),
        nullable=False,
        index=True,
    )
    turista_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    reserva_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), unique=True, nullable=False, index=True
    )
    puntaje: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    comentario: Mapped[str] = mapped_column(Text, default="", nullable=False)
    estado_moderacion: Mapped[str] = mapped_column(String(30), default="publicada", nullable=False)
    creada_en: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    oferta = relationship("OfertaModel", back_populates="calificaciones")
    respuesta = relationship(
        "RespuestaCalificacionModel", back_populates="calificacion", uselist=False
    )


class RespuestaCalificacionModel(Base):
    __tablename__ = "respuesta_calificacion"

    calificacion_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("calificacion.id", ondelete="CASCADE"),
        primary_key=True,
    )
    prestador_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    texto: Mapped[str] = mapped_column(Text, nullable=False)
    estado_moderacion: Mapped[str] = mapped_column(String(30), default="publicada", nullable=False)
    creada_en: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    calificacion = relationship("CalificacionModel", back_populates="respuesta")


class FavoritoModel(Base):
    __tablename__ = "favorito"

    turista_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    oferta_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("oferta.id", ondelete="CASCADE"),
        primary_key=True,
    )
    creado_en: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ItinerarioModel(Base):
    __tablename__ = "itinerario"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    turista_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    fecha_inicio: Mapped[datetime.date | None] = mapped_column(Date, nullable=True)
    fecha_fin: Mapped[datetime.date | None] = mapped_column(Date, nullable=True)

    items = relationship(
        "ItemItinerarioModel", back_populates="itinerario", cascade="all, delete-orphan"
    )


class ItemItinerarioModel(Base):
    __tablename__ = "item_itinerario"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    itinerario_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("itinerario.id", ondelete="CASCADE"),
        nullable=False,
    )
    oferta_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("oferta.id"),
        nullable=False,
    )
    dia: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    orden: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    hora_inicio: Mapped[datetime.time | None] = mapped_column(Time, nullable=True)
    hora_fin: Mapped[datetime.time | None] = mapped_column(Time, nullable=True)

    itinerario = relationship("ItinerarioModel", back_populates="items")


class LoteSincronizacionModel(Base):
    __tablename__ = "lote_sincronizacion"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    prestador_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("perfil_prestador.prestador_id"),
        nullable=False,
    )
    fuente_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("fuente_externa.id"),
        nullable=False,
    )
    estado: Mapped[str] = mapped_column(String(30), default="recibido", nullable=False)
    total_registros: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    aceptados: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rechazados: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    recibido_en: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finalizado_en: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class OutboxModel(Base):
    __tablename__ = "outbox"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    tipo: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    version: Mapped[int] = mapped_column(SmallInteger, default=1, nullable=False)
    correlation_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    datos: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    ocurrido_en: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    publicado_en: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    intentos: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)


class EventoProcesadoModel(Base):
    __tablename__ = "evento_procesado"

    evento_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    tipo: Mapped[str] = mapped_column(String(80), nullable=False)
    procesado_en: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
