"""Seed script to populate canonical zones, service types, and test fixtures (vocabulario.json)."""

from __future__ import annotations

import datetime
from typing import Any, TypedDict
from uuid import NAMESPACE_DNS, uuid5

from catalog_service.domain.entities import (
    PerfilPrestador,
    TipoServicio,
    Zona,
)
from catalog_service.domain.value_objects import (
    CategoriaPrestador,
)
from catalog_service.infrastructure.dependencies_helper import get_repo_container

SEED_NAMESPACE = NAMESPACE_DNS


class ZonaSeed(TypedDict):
    codigo: str
    es: str
    en: str
    sensible: bool
    lat: float
    lon: float


class TipoSeed(TypedDict):
    codigo: str
    es: str
    en: str
    reservable: bool
    esquema: dict[str, Any]


# Deterministic UUIDs for reference data
ZONAS_DATA: list[ZonaSeed] = [
    {
        "codigo": "minca",
        "es": "Minca",
        "en": "Minca",
        "sensible": False,
        "lat": 11.1444,
        "lon": -74.1189,
    },
    {
        "codigo": "tayrona",
        "es": "Tayrona",
        "en": "Tayrona",
        "sensible": True,
        "lat": 11.3056,
        "lon": -74.0167,
    },
    {
        "codigo": "centro",
        "es": "Centro Histórico",
        "en": "Historic Center",
        "sensible": False,
        "lat": 11.2408,
        "lon": -74.2110,
    },
    {
        "codigo": "los-naranjos",
        "es": "Los Naranjos",
        "en": "Los Naranjos",
        "sensible": False,
        "lat": 11.3142,
        "lon": -73.9881,
    },
    {
        "codigo": "taganga",
        "es": "Taganga",
        "en": "Taganga",
        "sensible": False,
        "lat": 11.2672,
        "lon": -74.1914,
    },
    {
        "codigo": "rodadero",
        "es": "El Rodadero",
        "en": "El Rodadero",
        "sensible": False,
        "lat": 11.2083,
        "lon": -74.2289,
    },
]

TIPOS_DATA: list[TipoSeed] = [
    {
        "codigo": "tour",
        "es": "Tour y Excursiones",
        "en": "Tour & Sightseeing",
        "reservable": True,
        "esquema": {
            "type": "object",
            "required": ["duracion_horas", "nivel_dificultad"],
            "properties": {
                "duracion_horas": {"type": "number"},
                "nivel_dificultad": {"type": "string"},
                "incluye": {"type": "string"},
                "categorias": {"type": "array"},
            },
        },
    },
    {
        "codigo": "alojamiento",
        "es": "Alojamiento Turístico",
        "en": "Tourist Accommodation",
        "reservable": True,
        "esquema": {
            "type": "object",
            "required": ["numero_habitaciones"],
            "properties": {
                "numero_habitaciones": {"type": "integer"},
                "servicios": {"type": "string"},
                "categorias": {"type": "array"},
            },
        },
    },
    {
        "codigo": "gastronomia",
        "es": "Gastronomía Típica",
        "en": "Typical Gastronomy",
        "reservable": False,
        "esquema": {
            "type": "object",
            "properties": {
                "tipo_cocina": {"type": "string"},
                "categorias": {"type": "array"},
            },
        },
    },
]

# Canonical verified provider for testing
PRESTADOR_DEMO_ID = uuid5(SEED_NAMESPACE, "prestador-guias-sierra-viva")


async def seed_canonical_data() -> None:
    """Populate canonical zones and types if they do not exist."""
    repos = await get_repo_container()

    # 1. Seed Zonas
    for z in ZONAS_DATA:
        existing = await repos["zona_repo"].get_by_codigo(z["codigo"])
        if not existing:
            zona = Zona(
                id=uuid5(SEED_NAMESPACE, f"zona-{z['codigo']}"),
                codigo=z["codigo"],
                nombre_es=z["es"],
                nombre_en=z["en"],
                ecosistema_sensible=z["sensible"],
                latitud=z["lat"],
                longitud=z["lon"],
            )
            await repos["zona_repo"].save(zona)

    # 2. Seed Tipos de Servicio
    for t in TIPOS_DATA:
        existing_t = await repos["tipo_repo"].get_by_codigo(t["codigo"])
        if not existing_t:
            tipo = TipoServicio(
                id=uuid5(SEED_NAMESPACE, f"tipo-{t['codigo']}"),
                codigo=t["codigo"],
                nombre_es=t["es"],
                nombre_en=t["en"],
                reservable=t["reservable"],
                esquema_atributos=t["esquema"],
            )
            await repos["tipo_repo"].save(tipo)

    # 3. Seed Demo Verified Provider
    existing_p = await repos["prestador_repo"].get_by_id(PRESTADOR_DEMO_ID)
    if not existing_p:
        perfil = PerfilPrestador(
            prestador_id=PRESTADOR_DEMO_ID,
            nombre_comercial="Guías Sierra Viva",
            numero_rnt="12345",
            verificado=True,
            categoria=CategoriaPrestador.PEQUENO_MEDIANO,
            actualizado_en=datetime.datetime.now(datetime.UTC),
        )
        await repos["prestador_repo"].save(perfil)

    # Sin commit los datos se perdían al cerrar la sesión: Catálogo arrancaba sin zonas ni tipos.
    sesion = repos.get("session")
    if sesion is not None:
        await sesion.commit()
        await sesion.close()
