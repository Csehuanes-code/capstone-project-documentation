"""Datos que entran y salen de los casos de uso (sin frameworks)."""

from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class SolicitudIniciarReserva:
    clave_idempotencia: str
    franja_id: str
    personas: int
    turista_id: str
    correo_turista: str
    idioma: str = "es"
    metodo_pago: str = "tarjeta"
    datos_pago: dict[str, Any] | None = None
    acompanantes: list[str] | None = None
    # CU-13: si viene de una oferta de la lista de espera, el cupo ya está reservado para él.
    entrada_lista_espera_id: str | None = None


@dataclass(frozen=True)
class ResultadoIniciarReserva:
    """Comprobante de la reserva (W5)."""

    reserva_id: str
    codigo: str
    estado: str
    oferta_id: str
    nombre_oferta: str
    zona_id: str
    prestador_id: str
    prestador_nombre: str
    prestador_contacto: str
    punto_encuentro: str
    fecha_servicio: str
    hora_servicio: str
    personas: int
    acompanantes: list[str]
    precio_unitario: Decimal
    total: Decimal
    moneda: str
    politica_cancelacion: dict[str, Any]
    pago_aprobado: bool
    mensaje_es: str
    mensaje_en: str
    referencia_pago: str | None = None
    monto_reembolso: Decimal | None = None


@dataclass(frozen=True)
class SolicitudCrearFranja:
    prestador_id: str
    oferta_id: str
    fecha: date
    hora_inicio: time
    cupo_total: int


@dataclass(frozen=True)
class FiltroReservas:
    """RF-RES-15: historial clasificado por estado, con filtro por fechas y prestador."""

    estado: str | None = None
    desde: date | None = None
    hasta: date | None = None
    prestador_id: str | None = None


@dataclass(frozen=True)
class ResultadoListaEspera:
    entrada_id: str
    franja_id: str
    personas: int
    estado: str
    posicion: int | None
    oferta_expira_en: datetime | None
    mensaje_es: str
    mensaje_en: str


@dataclass(frozen=True)
class ResultadoDisputa:
    disputa_id: str
    reserva_id: str
    estado: str
    motivo: str
    justificacion: str | None
    monto_reembolso: Decimal | None
    creado_en: datetime
    resuelta_en: datetime | None
