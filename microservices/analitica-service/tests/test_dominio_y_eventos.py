"""Reglas de dominio y validación de reservas.reserva.confirmada contra el contrato compartido."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from analitica.dominio import (
    ZONA_HORARIA_COLOMBIA,
    ReglaDominioError,
    ReservaConfirmada,
    UmbralZona,
    calcular_ocupacion,
    hoy_colombia,
)
from analitica.eventos import MensajeInvalido, procesar_mensaje

CONTRATOS = Path(__file__).resolve().parents[3] / "contratos" / "eventos"
EJEMPLO = json.loads(
    (CONTRATOS / "reservas.reserva.confirmada.schema.json").read_text(encoding="utf-8")
)["examples"][0]


class CasoFalso:
    """Simula ProcesarReserva: True la primera vez, False si el evento se repite."""

    def __init__(self) -> None:
        self.vistos: set[str] = set()
        self.recibidas: list[ReservaConfirmada] = []

    def ejecutar(self, reserva: ReservaConfirmada) -> bool:
        if reserva.evento_id in self.vistos:
            return False
        self.vistos.add(reserva.evento_id)
        self.recibidas.append(reserva)
        return True


def sobre(datos: Any = None, **cambios: Any) -> bytes:
    s = {
        "evento_id": str(uuid.uuid4()), "tipo": "reservas.reserva.confirmada", "version": 1,
        "ocurrido_en": "2026-11-17T03:00:00+00:00", "correlation_id": None,
        "datos": EJEMPLO if datos is None else datos,
    }
    s.update(cambios)
    return json.dumps(s).encode()


# --- dominio --------------------------------------------------------------------------------


def test_umbral_valida_zona_y_rangos() -> None:
    assert UmbralZona("tayrona", 1200).periodo_dias == 1
    for args in [("marte", 10), ("tayrona", 0), ("tayrona", 10, 0), ("tayrona", 10, 400)]:
        with pytest.raises(ReglaDominioError):
            UmbralZona(*args)  # type: ignore[arg-type]


def test_ocupacion_puede_superar_el_100() -> None:
    assert calcular_ocupacion(1500, UmbralZona("tayrona", 1000)) == 1.5


def test_hoy_es_el_de_colombia_no_el_del_servidor() -> None:
    assert hoy_colombia() == datetime.now(ZONA_HORARIA_COLOMBIA).date()
    # A las 2 a. m. UTC en Colombia todavía es el día anterior.
    madrugada_utc = datetime(2026, 11, 17, 2, 0, tzinfo=UTC)
    assert madrugada_utc.astimezone(ZONA_HORARIA_COLOMBIA).date() == madrugada_utc.date() - timedelta(days=1)


# --- evento entrante ------------------------------------------------------------------------


def test_ejemplo_del_contrato_se_procesa_y_el_repetido_no() -> None:
    caso = CasoFalso()
    cuerpo = sobre()
    assert procesar_mensaje(cuerpo, caso) == "procesado"  # type: ignore[arg-type]
    assert procesar_mensaje(cuerpo, caso) == "repetido"  # type: ignore[arg-type]
    (reserva,) = caso.recibidas
    assert reserva.zona_id == EJEMPLO["zona_id"] and reserva.personas == EJEMPLO["personas"]


def test_lo_que_publica_reservas_con_total_decimal() -> None:
    caso = CasoFalso()
    assert procesar_mensaje(sobre({**EJEMPLO, "total": 360000.0}), caso) == "procesado"  # type: ignore[arg-type]


def test_otros_tipos_se_ignoran() -> None:
    assert procesar_mensaje(sobre(tipo="reservas.disputa.abierta"), CasoFalso()) == "ignorado"  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "cuerpo",
    [
        pytest.param(b"no es json", id="no-json"),
        pytest.param(sobre(evento_id="1"), id="evento-id"),
        pytest.param(sobre(version=2), id="version"),
        pytest.param(sobre(extra=1), id="campo-de-mas"),
        pytest.param(sobre(ocurrido_en="2026-11-17T03:00:00"), id="sin-zona-horaria"),
        pytest.param(sobre({**EJEMPLO, "zona_id": "marte"}), id="zona-fuera-del-vocabulario"),
        pytest.param(sobre({**EJEMPLO, "moneda": "USD"}), id="moneda"),
        pytest.param(sobre({**EJEMPLO, "personas": 0}), id="personas"),
        pytest.param(sobre({k: v for k, v in EJEMPLO.items() if k != "oferta_id"}), id="sin-oferta"),
    ],
)
def test_mensaje_invalido_va_a_la_cola_de_errores(cuerpo: bytes) -> None:
    with pytest.raises(MensajeInvalido):
        procesar_mensaje(cuerpo, CasoFalso())  # type: ignore[arg-type]
