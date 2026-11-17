"""Contract tests confirming architectural boundary responsibilities (Reservas, Analítica, IA)."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema

SCHEMAS_DIR = Path(__file__).resolve().parents[4] / "contratos"


def test_contrato_reservas_confirmada_pertenece_a_reservas() -> None:
    """Confirms that reservas.reserva.confirmada is published by Reservas (Santiago), NOT Catálogos.

    Catálogos does NOT emit this event and does NOT manage reservation lifecycle or payments.
    """
    path = SCHEMAS_DIR / "eventos" / "reservas.reserva.confirmada.schema.json"
    with open(path, encoding="utf-8") as f:
        schema = json.load(f)

    # In README.md: "reservas.reserva.confirmada.schema.json | Santiago publica"
    # Consumen: IA y Analítica. Catálogos is neither publisher nor consumer.
    assert "reservas.reserva.confirmada" in schema["title"]
    assert "Santiago" in schema["description"]

    # Verify sample payload structure
    sample = {
        "reserva_id": "SMT-7K3Q9P",
        "oferta_id": "minca-cascadas",
        "zona_id": "minca",
        "personas": 2,
        "fecha_servicio": "2026-12-15",
        "total": 240000,
        "moneda": "COP",
    }
    jsonschema.validate(instance=sample, schema=schema)


def test_contrato_analitica_ocupacion_pertenece_a_analitica() -> None:
    """Confirms that analitica.zona.ocupacion_actualizada is published by Analítica (Carlos), NOT Catálogos.

    Catálogos does NOT calculate carrying capacity or zone occupancy.
    """
    path = SCHEMAS_DIR / "eventos" / "analitica.zona.ocupacion_actualizada.schema.json"
    with open(path, encoding="utf-8") as f:
        schema = json.load(f)

    # In README.md: "analitica.zona.ocupacion_actualizada.schema.json | Carlos publica"
    # Consume: IA.
    assert "analitica.zona.ocupacion_actualizada" in schema["title"]
    assert "Carlos" in schema["description"]

    sample = {
        "zona_id": "tayrona",
        "nombre": "Tayrona",
        "ocupacion": 0.92,
        "medido_en": "2026-11-14T08:00:00Z",
    }
    jsonschema.validate(instance=sample, schema=schema)


def test_ia_openapi_integracion_catalogo() -> None:
    """Inspects ia-openapi.json: Catálogos does NOT implement IA recommendation endpoints.

    Catálogos only:
    1. Publishes catalogo.oferta.* events which IA consumes to maintain proyeccion_oferta.
    2. Exposes GET /ofertas?orden=popularidad as a fallback when IA is unavailable (RF-IA-04).
    """
    path = SCHEMAS_DIR / "ia-openapi.json"
    with open(path, encoding="utf-8") as f:
        ia_api = json.load(f)

    # IA has /api/v1/ia/recomendaciones, /api/v1/ia/criterios, /api/v1/ia/populares
    paths = ia_api["paths"]
    assert "/api/v1/ia/recomendaciones" in paths
    assert "/api/v1/ia/populares" in paths

    # None of these IA paths belong in Catálogo
    assert not any(p.startswith("/api/v1/catalogo") for p in paths)
