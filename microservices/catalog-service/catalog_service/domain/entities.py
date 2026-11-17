"""Domain entities for the Catálogo bounded context.

Every entity is a plain ``dataclass`` — no framework dependencies.
IDs use ``uuid.UUID``; bilingual fields use the ``_es`` / ``_en`` suffix
convention required by the data model.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any
from uuid import UUID

from catalog_service.domain.value_objects import (
    CategoriaPrestador,
    EstadoLote,
    EstadoModeracion,
    EstadoOferta,
    Temporada,
    TipoFuente,
)

# ---------------------------------------------------------------------------
# Reference / lookup entities
# ---------------------------------------------------------------------------


@dataclass
class Zona:
    """Geographic zone within Santa Marta."""

    id: UUID
    codigo: str  # canonical, e.g. "minca"
    nombre_es: str
    nombre_en: str
    ecosistema_sensible: bool = False
    latitud: float | None = None
    longitud: float | None = None


@dataclass
class TipoServicio:
    """Service type definition with an optional JSON-Schema for attributes."""

    id: UUID
    codigo: str  # e.g. "tour_ecologico"
    nombre_es: str
    nombre_en: str
    reservable: bool = True
    esquema_atributos: dict[str, Any] | None = None  # JSON Schema dict


# ---------------------------------------------------------------------------
# Provider
# ---------------------------------------------------------------------------


@dataclass
class PerfilPrestador:
    """Provider profile — the ``verificado`` flag gates publication."""

    prestador_id: UUID
    nombre_comercial: str
    numero_rnt: str | None = None
    verificado: bool = False
    categoria: CategoriaPrestador = CategoriaPrestador.PEQUENO_MEDIANO
    actualizado_en: datetime.datetime | None = None


# ---------------------------------------------------------------------------
# Offer aggregate root
# ---------------------------------------------------------------------------


@dataclass
class Oferta:
    """Tourism offer — aggregate root of the Catálogo domain."""

    id: UUID
    tipo_servicio_id: UUID
    zona_id: UUID
    nombre_es: str
    nombre_en: str
    prestador_id: UUID | None = (
        None  # None for public attractions managed by platform (data-model.md §3.2)
    )
    descripcion_es: str = ""
    descripcion_en: str = ""

    # Flexible attributes validated against TipoServicio.esquema_atributos
    atributos: dict[str, Any] = field(default_factory=dict)

    # Lifecycle
    estado: EstadoOferta = EstadoOferta.BORRADOR

    # External-source traceability
    fuente_id: UUID | None = None
    actualizado_fuente_en: datetime.datetime | None = None

    # Aggregated review metrics (eventually consistent)
    calificacion_promedio: Decimal = Decimal("0.00")
    total_calificaciones: int = 0

    # Timestamps
    creado_en: datetime.datetime | None = None
    actualizado_en: datetime.datetime | None = None


# ---------------------------------------------------------------------------
# Offer children
# ---------------------------------------------------------------------------


@dataclass
class ImagenOferta:
    """Image associated with an offer, ordered for display."""

    id: UUID
    oferta_id: UUID
    clave_objeto: str  # object-storage key
    orden: int = 0
    texto_alternativo_es: str = ""
    texto_alternativo_en: str = ""


@dataclass
class Tarifa:
    """Season-based pricing for an offer."""

    id: UUID
    oferta_id: UUID
    temporada: Temporada
    vigente_desde: datetime.date
    vigente_hasta: datetime.date
    precio_por_persona: Decimal
    moneda: str = "COP"


@dataclass
class PoliticaCancelacion:
    """Cancellation policy attached 1-to-1 with an offer."""

    oferta_id: UUID
    horas_reembolso_total: int
    horas_reembolso_parcial: int
    porcentaje_reembolso_parcial: int  # 0-100


# ---------------------------------------------------------------------------
# Reviews
# ---------------------------------------------------------------------------


@dataclass
class Calificacion:
    """Tourist review for a completed reservation."""

    id: UUID
    oferta_id: UUID
    turista_id: UUID
    reserva_id: UUID  # unique per reservation
    puntaje: int  # 1-5
    comentario: str = ""
    estado_moderacion: EstadoModeracion = EstadoModeracion.PUBLICADA
    creada_en: datetime.datetime | None = None


@dataclass
class RespuestaCalificacion:
    """Provider response to a tourist review."""

    calificacion_id: UUID
    prestador_id: UUID
    texto: str
    estado_moderacion: EstadoModeracion = EstadoModeracion.PUBLICADA
    creada_en: datetime.datetime | None = None


# ---------------------------------------------------------------------------
# Tourist personalisation
# ---------------------------------------------------------------------------


@dataclass
class Favorito:
    """A tourist's bookmarked offer."""

    turista_id: UUID
    oferta_id: UUID
    creado_en: datetime.datetime | None = None


@dataclass
class Itinerario:
    """Tourist-created travel itinerary."""

    id: UUID
    turista_id: UUID
    nombre: str
    fecha_inicio: datetime.date | None = None
    fecha_fin: datetime.date | None = None


@dataclass
class ItemItinerario:
    """Single stop within an itinerary."""

    id: UUID
    itinerario_id: UUID
    oferta_id: UUID
    dia: datetime.date
    orden: int = 0
    hora_inicio: datetime.time | None = None
    hora_fin: datetime.time | None = None


# ---------------------------------------------------------------------------
# External data sources / batch sync
# ---------------------------------------------------------------------------


@dataclass
class FuenteExterna:
    """External data source registered for batch ingestion."""

    id: UUID
    nombre: str
    tipo: TipoFuente = TipoFuente.API
    integracion_id: UUID | None = None
    activa: bool = True


@dataclass
class LoteSincronizacion:
    """Tracks a single batch-sync operation."""

    id: UUID
    prestador_id: UUID
    fuente_id: UUID
    estado: EstadoLote = EstadoLote.RECIBIDO
    total_registros: int = 0
    aceptados: int = 0
    rechazados: list[dict[str, Any]] = field(default_factory=list)
    recibido_en: datetime.datetime | None = None
    finalizado_en: datetime.datetime | None = None
