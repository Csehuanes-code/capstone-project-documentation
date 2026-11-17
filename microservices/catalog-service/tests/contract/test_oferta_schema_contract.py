"""Contract tests validating offer event payloads against catalogo.oferta.schema.json."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

SCHEMA_PATH = Path(__file__).resolve().parents[4] / "contratos" / "eventos" / "catalogo.oferta.schema.json"


@pytest.fixture(scope="module")
def oferta_schema() -> dict:
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        return json.load(f)


def test_evento_oferta_valido_cumple_contrato(oferta_schema: dict) -> None:
    """A fully compliant offer event must validate against the JSON Schema."""
    payload = {
        "oferta_id": "minca-cascadas-001",
        "nombre": "Tour cascadas de Minca",
        "zona_id": "minca",
        "categorias": ["naturaleza", "aventura"],
        "calificacion_promedio": 4.75,
        "numero_resenas": 32,
        "indice_sostenibilidad": 0.95,
        "prestador_id": "prest-guias-sierra-viva",
        "activa": True,
    }
    jsonschema.validate(instance=payload, schema=oferta_schema)


def test_evento_oferta_retirada_valido(oferta_schema: dict) -> None:
    """'retirada' event has the exact same structure with activa=False."""
    payload = {
        "oferta_id": "minca-cascadas-001",
        "nombre": "Tour cascadas de Minca",
        "zona_id": "minca",
        "categorias": ["naturaleza"],
        "calificacion_promedio": 4.75,
        "numero_resenas": 32,
        "indice_sostenibilidad": 0.95,
        "prestador_id": "prest-guias-sierra-viva",
        "activa": False,
    }
    jsonschema.validate(instance=payload, schema=oferta_schema)


def test_campo_requerido_faltante_falla(oferta_schema: dict) -> None:
    """Omitting any required field must raise ValidationError."""
    payload = {
        "oferta_id": "minca-001",
        "nombre": "Tour Incompleto",
        "zona_id": "minca",
        "categorias": ["naturaleza"],
        # Missing calificacion_promedio, numero_resenas, indice_sostenibilidad, prestador_id, activa
    }
    with pytest.raises(jsonschema.ValidationError) as exc:
        jsonschema.validate(instance=payload, schema=oferta_schema)
    assert "calificacion_promedio" in str(exc.value) or "is a required property" in str(exc.value)


def test_categorias_vacias_falla_minitems(oferta_schema: dict) -> None:
    """'categorias' schema specifies minItems: 1."""
    payload = {
        "oferta_id": "minca-001",
        "nombre": "Tour Sin Categorias",
        "zona_id": "minca",
        "categorias": [],  # Violates minItems: 1
        "calificacion_promedio": 4.0,
        "numero_resenas": 1,
        "indice_sostenibilidad": 0.5,
        "prestador_id": "prest-123",
        "activa": True,
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=payload, schema=oferta_schema)


def test_categorias_duplicadas_falla_uniqueitems(oferta_schema: dict) -> None:
    """'categorias' schema specifies uniqueItems: true."""
    payload = {
        "oferta_id": "minca-001",
        "nombre": "Tour Categorias Duplicadas",
        "zona_id": "minca",
        "categorias": ["naturaleza", "naturaleza"],  # Violates uniqueItems
        "calificacion_promedio": 4.0,
        "numero_resenas": 1,
        "indice_sostenibilidad": 0.5,
        "prestador_id": "prest-123",
        "activa": True,
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=payload, schema=oferta_schema)


def test_calificacion_promedio_fuera_de_rango(oferta_schema: dict) -> None:
    """'calificacion_promedio' maximum is 5."""
    payload = {
        "oferta_id": "minca-001",
        "nombre": "Tour Score Invalido",
        "zona_id": "minca",
        "categorias": ["naturaleza"],
        "calificacion_promedio": 5.5,  # Violates maximum: 5
        "numero_resenas": 1,
        "indice_sostenibilidad": 0.5,
        "prestador_id": "prest-123",
        "activa": True,
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=payload, schema=oferta_schema)


def test_indice_sostenibilidad_fuera_de_rango(oferta_schema: dict) -> None:
    """'indice_sostenibilidad' maximum is 1.0, minimum is 0.0."""
    payload = {
        "oferta_id": "minca-001",
        "nombre": "Tour Sost Invalido",
        "zona_id": "minca",
        "categorias": ["naturaleza"],
        "calificacion_promedio": 4.5,
        "numero_resenas": 1,
        "indice_sostenibilidad": 1.2,  # Violates maximum: 1.0
        "prestador_id": "prest-123",
        "activa": True,
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=payload, schema=oferta_schema)
