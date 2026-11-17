"""Modelo lógico de ia_db (sección 3.2 del documento de diseño).

proyeccion_oferta, estado_zona, configuracion_criterios, recomendacion, item_recomendado
+ outbox y evento_procesado (comunes a todas las bases).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    DDL,
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Uuid,
    event,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# JSONB en PostgreSQL, JSON genérico en otros motores (SQLite para pruebas).
Json = JSON().with_variant(JSONB(), "postgresql")
Fecha = DateTime(timezone=True)


class Base(DeclarativeBase):
    pass


class ProyeccionOfertaTabla(Base):
    __tablename__ = "proyeccion_oferta"
    __table_args__ = (
        CheckConstraint("calificacion_promedio BETWEEN 0 AND 5", name="ck_oferta_calificacion"),
        CheckConstraint("numero_resenas >= 0", name="ck_oferta_resenas"),
        CheckConstraint("indice_sostenibilidad BETWEEN 0 AND 1", name="ck_oferta_sostenibilidad"),
        CheckConstraint("reservas_confirmadas >= 0", name="ck_oferta_reservas"),
    )

    oferta_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(200))
    zona_id: Mapped[str] = mapped_column(String(64), index=True)
    categorias: Mapped[list[str]] = mapped_column(Json)
    calificacion_promedio: Mapped[float] = mapped_column(Float)
    numero_resenas: Mapped[int] = mapped_column(Integer)
    indice_sostenibilidad: Mapped[float] = mapped_column(Float)
    prestador_id: Mapped[str] = mapped_column(String(64))
    activa: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    reservas_confirmadas: Mapped[int] = mapped_column(Integer, default=0)


class EstadoZonaTabla(Base):
    __tablename__ = "estado_zona"
    __table_args__ = (CheckConstraint("ocupacion >= 0", name="ck_zona_ocupacion"),)

    zona_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(200))
    ocupacion: Mapped[float] = mapped_column(Float)
    actualizado_en: Mapped[datetime] = mapped_column(Fecha)


class ConfiguracionCriteriosTabla(Base):
    """Inmutable: en PostgreSQL un trigger rechaza UPDATE y DELETE."""

    __tablename__ = "configuracion_criterios"

    version: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    pesos: Mapped[dict[str, float]] = mapped_column(Json)
    umbral_tranquila: Mapped[float] = mapped_column(Float)
    umbral_saturacion: Mapped[float] = mapped_column(Float)
    prior_media: Mapped[float] = mapped_column(Float)
    prior_peso: Mapped[int] = mapped_column(Integer)
    max_por_zona: Mapped[int] = mapped_column(Integer)
    creada_en: Mapped[datetime] = mapped_column(Fecha)


FUNCION_INMUTABLE = """
CREATE OR REPLACE FUNCTION configuracion_criterios_inmutable() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'configuracion_criterios es inmutable: cree una version nueva';
END;
$$ LANGUAGE plpgsql
"""
TRIGGER_INMUTABLE = """
CREATE TRIGGER tg_configuracion_criterios_inmutable
    BEFORE UPDATE OR DELETE ON configuracion_criterios
    FOR EACH ROW EXECUTE FUNCTION configuracion_criterios_inmutable()
"""

for _sentencia in (FUNCION_INMUTABLE, TRIGGER_INMUTABLE):
    event.listen(
        ConfiguracionCriteriosTabla.__table__,
        "after_create",
        DDL(_sentencia).execute_if(dialect="postgresql"),
    )


class RecomendacionTabla(Base):
    __tablename__ = "recomendacion"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    turista_id: Mapped[str | None] = mapped_column(String(64), index=True)
    intereses: Mapped[list[str]] = mapped_column(Json)
    version_pesos: Mapped[int] = mapped_column(ForeignKey("configuracion_criterios.version"))
    generada_en: Mapped[datetime] = mapped_column(Fecha)

    items: Mapped[list[ItemRecomendadoTabla]] = relationship(
        back_populates="recomendacion",
        cascade="all, delete-orphan",
        order_by="ItemRecomendadoTabla.posicion",
        lazy="selectin",
    )


class ItemRecomendadoTabla(Base):
    __tablename__ = "item_recomendado"

    recomendacion_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("recomendacion.id", ondelete="CASCADE"), primary_key=True
    )
    posicion: Mapped[int] = mapped_column(Integer, primary_key=True)
    oferta_id: Mapped[str] = mapped_column(String(64), index=True)
    nombre: Mapped[str] = mapped_column(String(200))
    zona_id: Mapped[str] = mapped_column(String(64))
    zona_nombre: Mapped[str | None] = mapped_column(String(200))
    ocupacion: Mapped[float | None] = mapped_column(Float)
    nivel: Mapped[str] = mapped_column(String(20))
    calificacion_promedio: Mapped[float] = mapped_column(Float)
    numero_resenas: Mapped[int] = mapped_column(Integer)
    puntaje: Mapped[float] = mapped_column(Float)
    desglose: Mapped[list[dict]] = mapped_column(Json)  # [{criterio, peso, valor, aporte}]
    coincidencias: Mapped[list[str]] = mapped_column(Json)
    motivo: Mapped[str] = mapped_column(String(40))
    alternativa_de_id: Mapped[str | None] = mapped_column(String(64))
    alternativa_de_nombre: Mapped[str | None] = mapped_column(String(200))
    alternativa_de_zona: Mapped[str | None] = mapped_column(String(200))

    recomendacion: Mapped[RecomendacionTabla] = relationship(back_populates="items")


class EventoProcesadoTabla(Base):
    __tablename__ = "evento_procesado"

    evento_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    procesado_en: Mapped[datetime] = mapped_column(Fecha)


class OutboxTabla(Base):
    """Estructura estándar; el proceso de reenvío lo aporta la plantilla común."""

    __tablename__ = "outbox"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tipo: Mapped[str] = mapped_column(String(100))
    payload: Mapped[dict] = mapped_column(Json)
    creado_en: Mapped[datetime] = mapped_column(Fecha)
    publicado_en: Mapped[datetime | None] = mapped_column(Fecha, index=True)
