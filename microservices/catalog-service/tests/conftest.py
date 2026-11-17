"""Pytest configuration and shared test fixtures."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from catalog_service.api.dependencies import get_repos
from catalog_service.api.main import app
from catalog_service.domain.entities import (
    PerfilPrestador,
    TipoServicio,
    Zona,
)
from catalog_service.domain.value_objects import (
    CategoriaPrestador,
)
from catalog_service.infrastructure.config import settings
from catalog_service.infrastructure.event_publisher import InMemoryEventPublisher
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
from catalog_service.infrastructure.reservas_client import MockReservasClient
from tests.auth_util import configurar_servicio

# Configure settings for test
settings.ENVIRONMENT = "test"
settings.USE_IN_MEMORY_REPO = True
settings.RABBITMQ_URL = ""
configurar_servicio()  # valida JWT con la clave pública de prueba de tests/auth_util.py


@pytest.fixture
def fake_repos() -> dict[str, object]:
    """Isolated repository container for each test."""
    zona_minca = Zona(
        id=uuid4(),
        codigo="minca",
        nombre_es="Minca",
        nombre_en="Minca",
        ecosistema_sensible=False,
    )
    zona_tayrona = Zona(
        id=uuid4(),
        codigo="tayrona",
        nombre_es="Tayrona",
        nombre_en="Tayrona",
        ecosistema_sensible=True,
    )
    zona_centro = Zona(
        id=uuid4(),
        codigo="centro",
        nombre_es="Centro Histórico",
        nombre_en="Historic Center",
        ecosistema_sensible=False,
    )
    zona_repo = InMemoryZonaRepository([zona_minca, zona_tayrona, zona_centro])

    tipo_tour = TipoServicio(
        id=uuid4(),
        codigo="tour",
        nombre_es="Tour",
        nombre_en="Tour",
        reservable=True,
        esquema_atributos={
            "type": "object",
            "required": ["duracion_horas"],
            "properties": {
                "duracion_horas": {"type": "number"},
                "categorias": {"type": "array"},
            },
        },
    )
    tipo_repo = InMemoryTipoServicioRepository([tipo_tour])

    prestador_verificado = PerfilPrestador(
        prestador_id=uuid4(),
        nombre_comercial="Guías Sierra Viva",
        numero_rnt="12345",
        verificado=True,
        categoria=CategoriaPrestador.PEQUENO_MEDIANO,
    )
    prestador_no_verificado = PerfilPrestador(
        prestador_id=uuid4(),
        nombre_comercial="Nuevo Operador",
        verificado=False,
        categoria=CategoriaPrestador.PEQUENO_MEDIANO,
    )
    prestador_repo = InMemoryPerfilPrestadorRepository(
        [prestador_verificado, prestador_no_verificado]
    )

    oferta_repo = InMemoryOfertaRepository(zona_repo=zona_repo, tipo_repo=tipo_repo)
    tarifa_repo = InMemoryTarifaRepository()
    politica_repo = InMemoryPoliticaCancelacionRepository()
    imagen_repo = InMemoryImagenOfertaRepository()
    calificacion_repo = InMemoryCalificacionRepository()
    favorito_repo = InMemoryFavoritoRepository(oferta_repo=oferta_repo)
    itinerario_repo = InMemoryItinerarioRepository()
    lote_repo = InMemoryLoteRepository()
    event_publisher = InMemoryEventPublisher()
    reservas_client = MockReservasClient()

    return {
        "zona_repo": zona_repo,
        "tipo_repo": tipo_repo,
        "oferta_repo": oferta_repo,
        "prestador_repo": prestador_repo,
        "tarifa_repo": tarifa_repo,
        "politica_repo": politica_repo,
        "imagen_repo": imagen_repo,
        "calificacion_repo": calificacion_repo,
        "favorito_repo": favorito_repo,
        "itinerario_repo": itinerario_repo,
        "lote_repo": lote_repo,
        "event_publisher": event_publisher,
        "reservas_client": reservas_client,
        # Fixture shortcuts
        "zona_minca": zona_minca,
        "zona_tayrona": zona_tayrona,
        "zona_centro": zona_centro,
        "tipo_tour": tipo_tour,
        "prestador_verificado": prestador_verificado,
        "prestador_no_verificado": prestador_no_verificado,
    }


@pytest.fixture
async def async_client(fake_repos: dict[str, object]) -> AsyncGenerator[AsyncClient, None]:
    """Test HTTP client with overridden dependencies."""
    app.dependency_overrides[get_repos] = lambda: fake_repos

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()
