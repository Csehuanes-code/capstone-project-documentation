"""Helper to obtain repository container whether using SQLAlchemy or In-Memory."""

from __future__ import annotations

from typing import Any

from catalog_service.infrastructure.config import settings
from catalog_service.infrastructure.database import get_sessionmaker
from catalog_service.infrastructure.event_publisher import (
    InMemoryEventPublisher,
    SqlAlchemyOutboxEventPublisher,
)
from catalog_service.infrastructure.memory_repositories import (
    InMemoryCalificacionRepository,
    InMemoryFavoritoRepository,
    InMemoryImagenOfertaRepository,
    InMemoryItinerarioRepository,
    InMemoryLoteRepository,
    InMemoryOfertaRepository,
    InMemoryPerfilPrestadorRepository,
    InMemoryPoliticaCancelacionRepository,
    InMemoryTarifaRepository,
    InMemoryTipoServicioRepository,
    InMemoryZonaRepository,
)
from catalog_service.infrastructure.repositories import (
    SqlAlchemyCalificacionRepository,
    SqlAlchemyFavoritoRepository,
    SqlAlchemyImagenOfertaRepository,
    SqlAlchemyItinerarioRepository,
    SqlAlchemyLoteRepository,
    SqlAlchemyOfertaRepository,
    SqlAlchemyPerfilPrestadorRepository,
    SqlAlchemyPoliticaCancelacionRepository,
    SqlAlchemyTarifaRepository,
    SqlAlchemyTipoServicioRepository,
    SqlAlchemyZonaRepository,
)
from catalog_service.infrastructure.reservas_client import (
    HttpReservasClient,
    MockReservasClient,
)

_singleton_in_memory: dict[str, Any] = {}


def get_singleton_in_memory_container() -> dict[str, Any]:
    global _singleton_in_memory
    if not _singleton_in_memory:
        zona_repo = InMemoryZonaRepository()
        tipo_repo = InMemoryTipoServicioRepository()
        oferta_repo = InMemoryOfertaRepository(zona_repo=zona_repo, tipo_repo=tipo_repo)
        _singleton_in_memory = {
            "zona_repo": zona_repo,
            "tipo_repo": tipo_repo,
            "oferta_repo": oferta_repo,
            "prestador_repo": InMemoryPerfilPrestadorRepository(),
            "tarifa_repo": InMemoryTarifaRepository(),
            "politica_repo": InMemoryPoliticaCancelacionRepository(),
            "imagen_repo": InMemoryImagenOfertaRepository(),
            "calificacion_repo": InMemoryCalificacionRepository(),
            "favorito_repo": InMemoryFavoritoRepository(oferta_repo=oferta_repo),
            "itinerario_repo": InMemoryItinerarioRepository(),
            "lote_repo": InMemoryLoteRepository(),
            "event_publisher": InMemoryEventPublisher(),
            "reservas_client": MockReservasClient(),
        }
    return _singleton_in_memory


async def get_repo_container() -> dict[str, Any]:
    """Retrieve repository container according to settings."""
    if settings.USE_IN_MEMORY_REPO:
        return get_singleton_in_memory_container()

    sessionmaker = get_sessionmaker()
    session = sessionmaker()
    return {
        "session": session,
        "zona_repo": SqlAlchemyZonaRepository(session),
        "tipo_repo": SqlAlchemyTipoServicioRepository(session),
        "oferta_repo": SqlAlchemyOfertaRepository(session),
        "prestador_repo": SqlAlchemyPerfilPrestadorRepository(session),
        "tarifa_repo": SqlAlchemyTarifaRepository(session),
        "politica_repo": SqlAlchemyPoliticaCancelacionRepository(session),
        "imagen_repo": SqlAlchemyImagenOfertaRepository(session),
        "calificacion_repo": SqlAlchemyCalificacionRepository(session),
        "favorito_repo": SqlAlchemyFavoritoRepository(session),
        "itinerario_repo": SqlAlchemyItinerarioRepository(session),
        "lote_repo": SqlAlchemyLoteRepository(session),
        "event_publisher": SqlAlchemyOutboxEventPublisher(session),
        "reservas_client": HttpReservasClient()
        if settings.ENVIRONMENT == "production"
        else MockReservasClient(),
    }
