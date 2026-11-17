from __future__ import annotations

from datetime import datetime, timezone

import pytest

from ia.dominio.modelos import EstadoZona, ProyeccionOferta
from ia.infraestructura import semilla

AHORA = datetime(2026, 11, 14, 12, 0, tzinfo=timezone.utc)


def oferta(
    oferta_id: str,
    zona_id: str = "z1",
    categorias: set[str] | None = None,
    nota: float = 4.5,
    resenas: int = 50,
    sost: float = 0.5,
    prestador: str = "p1",
    reservas: int = 0,
) -> ProyeccionOferta:
    return ProyeccionOferta(
        oferta_id=oferta_id,
        nombre=oferta_id.title(),
        zona_id=zona_id,
        categorias=frozenset(categorias or {"naturaleza"}),
        calificacion_promedio=nota,
        numero_resenas=resenas,
        indice_sostenibilidad=sost,
        prestador_id=prestador,
        reservas_confirmadas=reservas,
    )


def zona(zona_id: str, ocupacion: float, nombre: str | None = None) -> EstadoZona:
    return EstadoZona(zona_id, nombre or zona_id.title(), ocupacion, AHORA)


@pytest.fixture
def config():
    return semilla.CRITERIOS_V1
