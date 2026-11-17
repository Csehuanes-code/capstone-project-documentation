"""Entrada de eventos (api/eventos.py): validación contra los contratos, sin base de datos."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

import jsonschema
import pytest

from catalog_service.api.eventos import (
    MensajeInvalido,
    procesar_mensaje,
    validar_sobre,
    validar_verificacion,
)

CONTRATOS = Path(__file__).resolve().parents[4] / "contratos" / "eventos"
SCHEMA = json.loads(
    (CONTRATOS / "auth.prestador.verificacion_resuelta.schema.json").read_text(encoding="utf-8")
)
SOBRE_SCHEMA = json.loads((CONTRATOS / "sobre-evento.schema.json").read_text(encoding="utf-8"))
EJEMPLO = SCHEMA["examples"][0]


def sobre(datos: Any = None, **cambios: Any) -> bytes:
    s = {
        "evento_id": str(uuid.uuid4()),
        "tipo": "auth.prestador.verificacion_resuelta",
        "version": 1,
        "ocurrido_en": "2026-11-17T03:00:00+00:00",
        "correlation_id": None,
        "datos": EJEMPLO if datos is None else datos,
    }
    s.update(cambios)
    return json.dumps(s).encode()


def test_el_ejemplo_del_contrato_es_valido_y_lo_que_publica_auth() -> None:
    jsonschema.validate(EJEMPLO, SCHEMA)
    jsonschema.validate(json.loads(sobre()), SOBRE_SCHEMA)
    # Mismas claves que escribe auth-service en resolve_verification.py
    assert set(EJEMPLO) == {"solicitud_id", "prestador_id", "estado", "justificacion"}


@pytest.mark.parametrize(("estado", "verificado"), [
    ("aprobada", True), ("rechazada", False), ("info_requerida", False),
])
def test_solo_aprobada_verifica(estado: str, verificado: bool) -> None:
    prestador_id, resultado = validar_verificacion(validar_sobre(sobre({**EJEMPLO, "estado": estado})))
    assert str(prestador_id) == EJEMPLO["prestador_id"]
    assert resultado is verificado


@pytest.mark.parametrize(
    "cuerpo",
    [
        pytest.param(b"no es json", id="no-json"),
        pytest.param(b"[]", id="no-objeto"),
        pytest.param(sobre(evento_id="123"), id="evento_id-no-uuid"),
        pytest.param(sobre(version=2), id="version-no-soportada"),
        pytest.param(sobre(extra=1), id="campo-de-mas"),
        pytest.param(sobre(ocurrido_en="ayer"), id="fecha-invalida"),
        pytest.param(sobre({**EJEMPLO, "estado": "aprobado"}), id="estado-desconocido"),
        pytest.param(sobre({**EJEMPLO, "prestador_id": "prest-1"}), id="prestador-no-uuid"),
        pytest.param(
            sobre({k: v for k, v in EJEMPLO.items() if k != "estado"}), id="sin-estado"
        ),
    ],
)
def test_mensaje_invalido(cuerpo: bytes) -> None:
    with pytest.raises(MensajeInvalido):
        validar_verificacion(validar_sobre(cuerpo))


async def test_tipo_que_catalogo_no_usa_se_ignora_sin_tocar_la_base() -> None:
    def sin_base() -> Any:
        raise AssertionError("no debía abrir sesión")

    assert await procesar_mensaje(sin_base, sobre(tipo="reservas.reserva.confirmada")) == "ignorado"
