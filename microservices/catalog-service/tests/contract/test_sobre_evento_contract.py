"""Contract tests validating common event envelope against sobre-evento.schema.json."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import jsonschema
import pytest

SCHEMA_PATH = Path(__file__).parent.parent / "schemas" / "eventos" / "sobre-evento.schema.json"


@pytest.fixture(scope="module")
def sobre_schema() -> dict:
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        return json.load(f)


def test_sobre_evento_valido(sobre_schema: dict) -> None:
    envelope = {
        "evento_id": str(uuid4()),
        "tipo": "catalogo.oferta.publicada",
        "version": 1,
        "ocurrido_en": "2026-11-16T15:00:00Z",
        "correlation_id": str(uuid4()),
        "datos": {
            "oferta_id": "minca-cascadas",
            "nombre": "Tour cascadas de Minca",
        },
    }
    jsonschema.validate(instance=envelope, schema=sobre_schema)


def test_sobre_evento_sin_correlation_id_valido(sobre_schema: dict) -> None:
    envelope = {
        "evento_id": str(uuid4()),
        "tipo": "catalogo.oferta.retirada",
        "version": 1,
        "ocurrido_en": "2026-11-16T15:00:00Z",
        "datos": {},
    }
    jsonschema.validate(instance=envelope, schema=sobre_schema)


def test_sobre_evento_tipo_formato_invalido(sobre_schema: dict) -> None:
    """'tipo' requires pattern '^[a-z]+\\.[a-z_]+\\.[a-z_]+$'."""
    envelope = {
        "evento_id": str(uuid4()),
        "tipo": "INVALID_TYPE_FORMAT",  # Does not match pattern
        "version": 1,
        "ocurrido_en": "2026-11-16T15:00:00Z",
        "datos": {},
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=envelope, schema=sobre_schema)


def test_sobre_evento_campos_adicionales_rechazados(sobre_schema: dict) -> None:
    """'additionalProperties: false' in envelope schema."""
    envelope = {
        "evento_id": str(uuid4()),
        "tipo": "catalogo.oferta.actualizada",
        "version": 1,
        "ocurrido_en": "2026-11-16T15:00:00Z",
        "datos": {},
        "campo_no_permitido": "extra",  # Forbidden by additionalProperties: false
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=envelope, schema=sobre_schema)
