"""Ports (interfaces) for the Catálogo application layer.

In Clean Architecture, the application layer defines interfaces (ports)
that outer layers (infrastructure) must implement.
NO imports from FastAPI, SQLAlchemy or external I/O frameworks are permitted here.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from typing import Any
from uuid import UUID

from catalog_service.domain.entities import (
    Calificacion,
    Favorito,
    ImagenOferta,
    ItemItinerario,
    Itinerario,
    LoteSincronizacion,
    Oferta,
    PerfilPrestador,
    PoliticaCancelacion,
    RespuestaCalificacion,
    Tarifa,
    TipoServicio,
    Zona,
)
from catalog_service.domain.value_objects import EstadoOferta

# ---------------------------------------------------------------------------
# Repository Ports
# ---------------------------------------------------------------------------


class OfertaRepository(ABC):
    """Port for Oferta persistence."""

    @abstractmethod
    async def get_by_id(self, oferta_id: UUID) -> Oferta | None:
        """Fetch offer by its primary key."""
        ...

    @abstractmethod
    async def list_offers(
        self,
        *,
        tipo_codigo: str | None = None,
        zona_codigo: str | None = None,
        categoria: str | None = None,
        estado: EstadoOferta | None = EstadoOferta.PUBLICADA,
        prestador_id: UUID | None = None,
        orden: str = "relevancia",
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Oferta], int]:
        """List offers with filtering, ordering and pagination. Returns (items, total_count)."""
        ...

    @abstractmethod
    async def save(self, oferta: Oferta) -> Oferta:
        """Create or update an offer."""
        ...

    @abstractmethod
    async def update_estado(self, oferta_id: UUID, estado: EstadoOferta) -> None:
        """Update offer status."""
        ...


class ZonaRepository(ABC):
    """Port for Zona persistence."""

    @abstractmethod
    async def get_by_id(self, zona_id: UUID) -> Zona | None: ...

    @abstractmethod
    async def get_by_codigo(self, codigo: str) -> Zona | None: ...

    @abstractmethod
    async def list_all(self) -> list[Zona]: ...

    @abstractmethod
    async def save(self, zona: Zona) -> Zona: ...


class TipoServicioRepository(ABC):
    """Port for TipoServicio persistence."""

    @abstractmethod
    async def get_by_id(self, tipo_id: UUID) -> TipoServicio | None: ...

    @abstractmethod
    async def get_by_codigo(self, codigo: str) -> TipoServicio | None: ...

    @abstractmethod
    async def list_all(self) -> list[TipoServicio]: ...

    @abstractmethod
    async def save(self, tipo: TipoServicio) -> TipoServicio: ...


class PerfilPrestadorRepository(ABC):
    """Port for provider profiles."""

    @abstractmethod
    async def get_by_id(self, prestador_id: UUID) -> PerfilPrestador | None: ...

    @abstractmethod
    async def save(self, perfil: PerfilPrestador) -> PerfilPrestador: ...


class TarifaRepository(ABC):
    """Port for tariffs."""

    @abstractmethod
    async def list_by_oferta(self, oferta_id: UUID) -> list[Tarifa]: ...

    @abstractmethod
    async def get_vigente(self, oferta_id: UUID, fecha: date) -> Tarifa | None:
        """Find the active tariff for an offer on a given date."""
        ...

    @abstractmethod
    async def save(self, tarifa: Tarifa) -> Tarifa: ...


class PoliticaCancelacionRepository(ABC):
    """Port for cancellation policies."""

    @abstractmethod
    async def get_by_oferta(self, oferta_id: UUID) -> PoliticaCancelacion | None: ...

    @abstractmethod
    async def save(self, politica: PoliticaCancelacion) -> PoliticaCancelacion: ...


class ImagenOfertaRepository(ABC):
    """Port for offer images."""

    @abstractmethod
    async def list_by_oferta(self, oferta_id: UUID) -> list[ImagenOferta]: ...

    @abstractmethod
    async def save(self, imagen: ImagenOferta) -> ImagenOferta: ...


class CalificacionRepository(ABC):
    """Port for reviews."""

    @abstractmethod
    async def get_by_id(self, calificacion_id: UUID) -> Calificacion | None: ...

    @abstractmethod
    async def get_by_reserva_id(self, reserva_id: UUID) -> Calificacion | None: ...

    @abstractmethod
    async def list_by_oferta(
        self, oferta_id: UUID, limit: int = 20, offset: int = 0
    ) -> tuple[list[Calificacion], int]: ...

    @abstractmethod
    async def list_puntajes_by_oferta(self, oferta_id: UUID) -> list[int]: ...

    @abstractmethod
    async def save(self, calificacion: Calificacion) -> Calificacion: ...

    @abstractmethod
    async def save_respuesta(self, respuesta: RespuestaCalificacion) -> RespuestaCalificacion: ...

    @abstractmethod
    async def get_respuesta(self, calificacion_id: UUID) -> RespuestaCalificacion | None: ...


class FavoritoRepository(ABC):
    """Port for favorites."""

    @abstractmethod
    async def get(self, turista_id: UUID, oferta_id: UUID) -> Favorito | None: ...

    @abstractmethod
    async def list_by_turista(self, turista_id: UUID) -> list[Oferta]: ...

    @abstractmethod
    async def add(self, favorito: Favorito) -> None: ...

    @abstractmethod
    async def remove(self, turista_id: UUID, oferta_id: UUID) -> None: ...


class ItinerarioRepository(ABC):
    """Port for itineraries."""

    @abstractmethod
    async def get_by_id(self, itinerario_id: UUID) -> Itinerario | None: ...

    @abstractmethod
    async def list_by_turista(self, turista_id: UUID) -> list[Itinerario]: ...

    @abstractmethod
    async def save(self, itinerario: Itinerario) -> Itinerario: ...

    @abstractmethod
    async def add_item(self, item: ItemItinerario) -> ItemItinerario: ...

    @abstractmethod
    async def list_items(self, itinerario_id: UUID) -> list[ItemItinerario]: ...


class LoteRepository(ABC):
    """Port for batch synchronization lots."""

    @abstractmethod
    async def get_by_id(self, lote_id: UUID) -> LoteSincronizacion | None: ...

    @abstractmethod
    async def save(self, lote: LoteSincronizacion) -> LoteSincronizacion: ...


# ---------------------------------------------------------------------------
# Outgoing Integration Ports
# ---------------------------------------------------------------------------


class EventPublisher(ABC):
    """Port for publishing domain events via transactional outbox (ADR-04)."""

    @abstractmethod
    async def publish(
        self,
        tipo: str,
        datos: dict[str, Any],
        *,
        correlation_id: str | None = None,
    ) -> None:
        """Store event in outbox for asynchronous delivery."""
        ...


class ReservasClient(ABC):
    """Synchronous client to call Reservas service: GET /reservas/{id}/estado (ADR-04 §4.2)."""

    @abstractmethod
    async def get_reserva_estado(self, reserva_id: UUID) -> dict[str, Any] | None:
        """Returns dict with reserva details including 'estado', or None if unavailable/error."""
        ...
