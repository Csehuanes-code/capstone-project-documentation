"""Tablas de reservas_db (sección 3.2). La migración de Alembic debe producir exactamente esto
(prueba tests/test_migraciones.py)."""

from datetime import date, datetime, time, timezone
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from comun.eventos import OutboxBase


def _ahora() -> datetime:
    return datetime.now(timezone.utc)


class BaseReservas(OutboxBase):
    """Base declarativa de reservas_db (incluye outbox y evento_procesado de comun)."""
    __abstract__ = True


class FranjaDisponibilidadORM(BaseReservas):
    __tablename__ = "franja_disponibilidad"
    __table_args__ = (
        CheckConstraint(
            "0 <= cupo_disponible AND cupo_disponible <= cupo_total",
            name="ck_franja_cupo_valido",
        ),
        CheckConstraint("cupo_total > 0", name="ck_franja_cupo_total_positivo"),
        Index("ix_franja_oferta_fecha", "oferta_id", "fecha"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    oferta_id: Mapped[str] = mapped_column(String(80), nullable=False)
    zona_id: Mapped[str] = mapped_column(String(50), nullable=False)
    prestador_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    hora_inicio: Mapped[time] = mapped_column(Time, nullable=False)
    cupo_total: Mapped[int] = mapped_column(Integer, nullable=False)
    cupo_disponible: Mapped[int] = mapped_column(Integer, nullable=False)


class ReservaORM(BaseReservas):
    __tablename__ = "reserva"
    __table_args__ = (
        UniqueConstraint("turista_id", "clave_idempotencia", name="uq_reserva_turista_idempotencia"),
        CheckConstraint("personas > 0", name="ck_reserva_personas_positivas"),
        CheckConstraint(
            "estado IN ('pendiente_pago', 'confirmada', 'expirada', 'cancelada', "
            "'cancelacion_pendiente')",
            name="ck_reserva_estado",
        ),
        Index("ix_reserva_estado_bloqueo", "estado", "bloqueo_expira_en"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    codigo: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    clave_idempotencia: Mapped[str] = mapped_column(String(120), nullable=False)
    franja_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("franja_disponibilidad.id"), nullable=False, index=True
    )
    oferta_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    nombre_oferta: Mapped[str] = mapped_column(String(200), nullable=False)
    zona_id: Mapped[str] = mapped_column(String(50), nullable=False)
    prestador_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    prestador_nombre: Mapped[str] = mapped_column(String(150), nullable=False, default="")
    prestador_contacto: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    punto_encuentro: Mapped[str] = mapped_column(String(250), nullable=False, default="")
    turista_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    correo_turista: Mapped[str] = mapped_column(String(180), nullable=False)
    idioma: Mapped[str] = mapped_column(String(5), nullable=False, default="es")
    fecha_servicio: Mapped[date] = mapped_column(Date, nullable=False)
    hora_servicio: Mapped[time] = mapped_column(Time, nullable=False)
    personas: Mapped[int] = mapped_column(Integer, nullable=False)
    # Precio y política COPIADOS al reservar (sección 3.1)
    precio_unitario_copiado: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    moneda: Mapped[str] = mapped_column(String(10), nullable=False, default="COP")
    pol_horas_reembolso_total: Mapped[int] = mapped_column(Integer, nullable=False)
    pol_horas_reembolso_parcial: Mapped[int] = mapped_column(Integer, nullable=False)
    pol_porcentaje_reembolso_parcial: Mapped[int] = mapped_column(Integer, nullable=False)

    estado: Mapped[str] = mapped_column(String(30), nullable=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_ahora)
    bloqueo_expira_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confirmada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    monto_reembolso: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)

    asistentes: Mapped[list["AsistenteORM"]] = relationship(
        "AsistenteORM", back_populates="reserva", cascade="all, delete-orphan", lazy="selectin"
    )


class AsistenteORM(BaseReservas):
    __tablename__ = "asistente"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    reserva_id: Mapped[str] = mapped_column(String(36), ForeignKey("reserva.id"), nullable=False, index=True)
    nombre_completo: Mapped[str] = mapped_column(String(150), nullable=False)
    documento: Mapped[str | None] = mapped_column(String(50), nullable=True)

    reserva: Mapped[ReservaORM] = relationship("ReservaORM", back_populates="asistentes")


class PagoORM(BaseReservas):
    __tablename__ = "pago"
    __table_args__ = (
        CheckConstraint("tipo IN ('cobro', 'reembolso')", name="ck_pago_tipo"),
        CheckConstraint("monto >= 0", name="ck_pago_monto"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    reserva_id: Mapped[str] = mapped_column(String(36), ForeignKey("reserva.id"), nullable=False, index=True)
    tipo: Mapped[str] = mapped_column(String(20), nullable=False, default="cobro")
    monto: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    moneda: Mapped[str] = mapped_column(String(10), nullable=False, default="COP")
    metodo: Mapped[str] = mapped_column(String(30), nullable=False)
    estado: Mapped[str] = mapped_column(String(30), nullable=False)
    referencia_pasarela: Mapped[str] = mapped_column(String(120), nullable=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_ahora)


class DisputaORM(BaseReservas):
    __tablename__ = "disputa"
    __table_args__ = (
        CheckConstraint(
            "estado IN ('en_revision', 'aprobada', 'rechazada')", name="ck_disputa_estado"
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    reserva_id: Mapped[str] = mapped_column(String(36), ForeignKey("reserva.id"), nullable=False, index=True)
    pago_id: Mapped[str] = mapped_column(String(36), ForeignKey("pago.id"), nullable=False, index=True)
    turista_id: Mapped[str] = mapped_column(String(80), nullable=False)
    motivo: Mapped[str] = mapped_column(Text, nullable=False)
    estado: Mapped[str] = mapped_column(String(30), nullable=False, default="en_revision", index=True)
    justificacion: Mapped[str | None] = mapped_column(Text, nullable=True)
    monto_reembolso: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    resuelta_por: Mapped[str | None] = mapped_column(String(80), nullable=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_ahora)
    resuelta_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class EntradaListaEsperaORM(BaseReservas):
    __tablename__ = "entrada_lista_espera"
    __table_args__ = (
        CheckConstraint("personas > 0", name="ck_lista_espera_personas"),
        CheckConstraint(
            "estado IN ('esperando', 'ofrecida', 'convertida', 'expirada', 'retirada')",
            name="ck_lista_espera_estado",
        ),
        Index("ix_lista_espera_franja_estado_orden", "franja_id", "estado", "creado_en"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    franja_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("franja_disponibilidad.id"), nullable=False
    )
    turista_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    correo_turista: Mapped[str] = mapped_column(String(180), nullable=False)
    idioma: Mapped[str] = mapped_column(String(5), nullable=False, default="es")
    personas: Mapped[int] = mapped_column(Integer, nullable=False)
    estado: Mapped[str] = mapped_column(String(30), nullable=False, default="esperando")
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_ahora)
    oferta_expira_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class NotificacionORM(BaseReservas):
    __tablename__ = "notificacion"
    __table_args__ = (Index("ix_notificacion_pendientes", "enviada", "creado_en"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    reserva_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("reserva.id"), nullable=True, index=True
    )
    destinatario_id: Mapped[str] = mapped_column(String(80), nullable=False)
    correo_destino: Mapped[str] = mapped_column(String(180), nullable=False)
    idioma: Mapped[str] = mapped_column(String(5), nullable=False, default="es")
    asunto: Mapped[str] = mapped_column(String(250), nullable=False)
    cuerpo_texto: Mapped[str] = mapped_column(Text, nullable=False)
    enviada: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    intentos: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_ahora)


class ProyeccionOfertaORM(BaseReservas):
    """Copia local de lo que Reservas necesita de Catálogo (eventos catalogo.oferta.*)."""
    __tablename__ = "proyeccion_oferta_local"

    oferta_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    zona_id: Mapped[str] = mapped_column(String(50), nullable=False)
    prestador_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    activa: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
