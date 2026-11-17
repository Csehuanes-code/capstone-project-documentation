"""Pydantic v2 schemas for HTTP requests and responses (OpenAPI contracts)."""

from __future__ import annotations

import datetime
from decimal import Decimal
from typing import Any, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from catalog_service.domain.value_objects import (
    EstadoModeracion,
    EstadoOferta,
    Temporada,
)

T = TypeVar("T")


# ---------------------------------------------------------------------------
# Common / Pagination
# ---------------------------------------------------------------------------


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict[str, Any] | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


# ---------------------------------------------------------------------------
# Zonas & Tipos de Servicio
# ---------------------------------------------------------------------------


class ZonaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    codigo: str
    nombre_es: str
    nombre_en: str
    ecosistema_sensible: bool
    latitud: float | None = None
    longitud: float | None = None


class TipoServicioResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    codigo: str
    nombre_es: str
    nombre_en: str
    reservable: bool
    esquema_atributos: dict[str, Any] | None = None


# ---------------------------------------------------------------------------
# Tarifa & Politica
# ---------------------------------------------------------------------------


class TarifaCreateRequest(BaseModel):
    temporada: Temporada
    vigente_desde: datetime.date
    vigente_hasta: datetime.date
    precio_por_persona: Decimal = Field(..., ge=0)
    moneda: str = Field(default="COP", min_length=3, max_length=3)


class TarifaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    oferta_id: UUID
    temporada: str
    vigente_desde: datetime.date
    vigente_hasta: datetime.date
    precio_por_persona: float
    moneda: str


class PoliticaCancelacionRequest(BaseModel):
    horas_reembolso_total: int = Field(..., ge=0)
    horas_reembolso_parcial: int = Field(..., ge=0)
    porcentaje_reembolso_parcial: int = Field(..., ge=0, le=100)


class PoliticaCancelacionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    oferta_id: UUID
    horas_reembolso_total: int
    horas_reembolso_parcial: int
    porcentaje_reembolso_parcial: int


class ImagenOfertaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    clave_objeto: str
    orden: int
    texto_alternativo_es: str
    texto_alternativo_en: str


# ---------------------------------------------------------------------------
# Oferta
# ---------------------------------------------------------------------------


class OfertaCreateRequest(BaseModel):
    tipo_servicio_id: UUID
    zona_id: UUID
    nombre_es: str = Field(..., min_length=2, max_length=160)
    nombre_en: str = Field(..., min_length=2, max_length=160)
    descripcion_es: str = ""
    descripcion_en: str = ""
    atributos: dict[str, Any] = Field(default_factory=dict)
    estado: EstadoOferta = EstadoOferta.BORRADOR
    indice_sostenibilidad: float = Field(default=1.0, ge=0.0, le=1.0)


class OfertaUpdateRequest(BaseModel):
    nombre_es: str | None = Field(default=None, min_length=2, max_length=160)
    nombre_en: str | None = Field(default=None, min_length=2, max_length=160)
    descripcion_es: str | None = None
    descripcion_en: str | None = None
    atributos: dict[str, Any] | None = None
    estado: EstadoOferta | None = None
    indice_sostenibilidad: float = Field(default=1.0, ge=0.0, le=1.0)


class OfertaItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tipo_servicio_id: UUID
    zona_id: UUID
    prestador_id: UUID | None
    nombre_es: str
    nombre_en: str
    descripcion_es: str
    descripcion_en: str
    atributos: dict[str, Any]
    estado: str
    calificacion_promedio: float
    total_calificaciones: int
    creado_en: datetime.datetime | None = None
    actualizado_en: datetime.datetime | None = None


class OfertaDetalleResponse(BaseModel):
    oferta: OfertaItemResponse
    zona: ZonaResponse | None
    tipo_servicio: TipoServicioResponse | None
    imagenes: list[ImagenOfertaResponse]
    tarifas: list[TarifaResponse]
    politica_cancelacion: PoliticaCancelacionResponse | None


class CondicionesTarifa(BaseModel):
    precio_por_persona: float
    moneda: str
    temporada: str


class CondicionesPolitica(BaseModel):
    horas_reembolso_total: int
    horas_reembolso_parcial: int
    porcentaje_reembolso_parcial: int


class OfertaCondicionesResponse(BaseModel):
    """Sync contract response for Reservas: GET /ofertas/{id}/condiciones (ADR-04 §4.2)."""

    oferta_id: str
    nombre_es: str
    nombre_en: str
    estado: str
    activa: bool
    zona_id: str
    tarifa_vigente: CondicionesTarifa | None
    politica_cancelacion: CondicionesPolitica | None


# ---------------------------------------------------------------------------
# Calificaciones (Reviews)
# ---------------------------------------------------------------------------


class CalificacionCreateRequest(BaseModel):
    reserva_id: UUID
    puntaje: int = Field(..., ge=1, le=5)
    comentario: str = Field(default="", max_length=2000)


class CalificacionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    oferta_id: UUID
    turista_id: UUID
    reserva_id: UUID
    puntaje: int
    comentario: str
    estado_moderacion: str
    creada_en: datetime.datetime | None = None


class RespuestaCalificacionRequest(BaseModel):
    texto: str = Field(..., min_length=2, max_length=2000)


class RespuestaCalificacionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    calificacion_id: UUID
    prestador_id: UUID
    texto: str
    estado_moderacion: str
    creada_en: datetime.datetime | None = None


class ModeracionRequest(BaseModel):
    nuevo_estado: EstadoModeracion
    justificacion: str = ""


# ---------------------------------------------------------------------------
# Favoritos & Itinerarios
# ---------------------------------------------------------------------------


class ItinerarioCreateRequest(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=120)
    fecha_inicio: datetime.date | None = None
    fecha_fin: datetime.date | None = None


class ItinerarioItemRequest(BaseModel):
    oferta_id: UUID
    dia: datetime.date
    orden: int = 0
    hora_inicio: datetime.time | None = None
    hora_fin: datetime.time | None = None


class ItinerarioItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    itinerario_id: UUID
    oferta_id: UUID
    dia: datetime.date
    orden: int
    hora_inicio: datetime.time | None = None
    hora_fin: datetime.time | None = None


class ItinerarioResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    turista_id: UUID
    nombre: str
    fecha_inicio: datetime.date | None = None
    fecha_fin: datetime.date | None = None
    items: list[ItinerarioItemResponse] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Lotes (Batch Synchronization)
# ---------------------------------------------------------------------------


class RegistroLoteItem(BaseModel):
    nombre_es: str = Field(..., min_length=2, max_length=160)
    nombre_en: str = Field(..., min_length=2, max_length=160)
    tipo_codigo: str
    zona_codigo: str
    descripcion_es: str = ""
    descripcion_en: str = ""
    atributos: dict[str, Any] = Field(default_factory=dict)


class SincronizacionLoteRequest(BaseModel):
    fuente_id: UUID
    registros: list[RegistroLoteItem] = Field(..., min_length=1, max_length=1000)


class LoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    prestador_id: UUID
    fuente_id: UUID
    estado: str
    total_registros: int
    aceptados: int
    rechazados: list[dict[str, Any]]
    recibido_en: datetime.datetime | None = None
    finalizado_en: datetime.datetime | None = None
