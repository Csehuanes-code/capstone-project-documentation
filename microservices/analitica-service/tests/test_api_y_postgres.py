"""Seguridad de la API y comportamiento con PostgreSQL real (umbrales, ocupación, alertas, outbox)."""

from __future__ import annotations

import json
import uuid
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from analitica import api
from analitica.dominio import ReservaConfirmada, UmbralZona, hoy_colombia
from analitica.persistencia import (
    alertas,
    eventos_procesados,
    get_engine,
    metadata,
    outbox,
    reservas,
    umbrales,
)
from tests.conftest import cabeceras, requiere_postgres, token

CONTRATO_OCUPACION = json.loads(
    (Path(__file__).resolve().parents[3] / "contratos" / "eventos"
     / "analitica.zona.ocupacion_actualizada.schema.json").read_text(encoding="utf-8")
)
cliente = TestClient(api.app)  # sin `with`: no arranca los hilos de fondo


# --- seguridad (no necesita base) -----------------------------------------------------------


@pytest.mark.parametrize("ruta", ["/api/v1/analitica/umbrales", "/api/v1/analitica/alertas"])
def test_sin_token_401_y_rol_no_admin_403(ruta: str) -> None:
    assert cliente.get(ruta).status_code == 401
    assert cliente.get(ruta, headers=cabeceras("turista")).status_code == 403
    assert cliente.get(ruta, headers=cabeceras("prestador")).status_code == 403


def test_token_de_otro_emisor_o_vencido_401() -> None:
    for malo in (token("administrador", iss="otro"), token("administrador", exp=0)):
        resp = cliente.get("/api/v1/analitica/umbrales", headers={"Authorization": f"Bearer {malo}"})
        assert resp.status_code == 401


def test_health_vivo() -> None:
    assert cliente.get("/health").json()["status"] == "ok"


# --- con PostgreSQL real --------------------------------------------------------------------


@pytest.fixture
def base() -> None:
    motor = get_engine()
    metadata.create_all(motor)
    with motor.begin() as c:
        for tabla in (alertas, outbox, reservas, eventos_procesados, umbrales):
            c.execute(delete(tabla))


def reserva(personas: int, dias: int = 0, zona: str = "tayrona") -> ReservaConfirmada:
    return ReservaConfirmada(
        evento_id=str(uuid.uuid4()), reserva_id=f"SMT-{uuid.uuid4().hex[:6]}", oferta_id="oferta-1",
        zona_id=zona, personas=personas, fecha_servicio=hoy_colombia() + timedelta(days=dias),
        total=Decimal(100000),
    )


def eventos_ocupacion() -> list[dict[str, object]]:
    with get_engine().connect() as c:
        filas = c.execute(select(outbox.c.datos).where(
            outbox.c.tipo == "analitica.zona.ocupacion_actualizada").order_by(outbox.c.ocurrido_en))
        return [dict(f.datos) for f in filas]


@requiere_postgres
def test_reserva_repetida_cuenta_una_vez(base: None) -> None:
    r = reserva(2)
    assert api.repository.procesar_reserva(r) is True
    assert api.repository.procesar_reserva(r) is False


@requiere_postgres
def test_umbral_alerta_y_evento_para_ia_cumplen_el_contrato(base: None) -> None:
    admin = cabeceras("administrador")
    resp = cliente.put("/api/v1/analitica/umbrales", headers=admin,
                       json={"zona_id": "tayrona", "visitantes_maximos": 10})
    assert resp.status_code == 200 and resp.json()["guardado"] is True

    api.repository.procesar_reserva(reserva(9))  # 9/10 = 90 % → alerta
    assert [a["zona_id"] for a in cliente.get("/api/v1/analitica/alertas", headers=admin).json()] == ["tayrona"]

    ultimo = eventos_ocupacion()[-1]
    assert ultimo["zona_id"] == "tayrona" and ultimo["ocupacion"] == pytest.approx(0.9)
    assert set(CONTRATO_OCUPACION["required"]) <= ultimo.keys()

    filas = cliente.get("/api/v1/analitica/indicadores", headers=admin, params={
        "desde": hoy_colombia().isoformat(), "hasta": hoy_colombia().isoformat(), "zona_id": "tayrona"}).json()
    assert filas[0]["visitantes_reservados"] == 9


@requiere_postgres
def test_reservas_futuras_tambien_publican_ocupacion(base: None) -> None:
    """Antes solo publicaba si la reserva era para HOY: IA casi nunca recibía datos."""
    api.repository.guardar_umbral(UmbralZona("minca", 100))
    antes = len(eventos_ocupacion())
    api.repository.procesar_reserva(reserva(3, dias=10, zona="minca"))
    assert len(eventos_ocupacion()) == antes + 1


@requiere_postgres
def test_recalculo_periodico_publica_todas_las_zonas_con_umbral(base: None) -> None:

    api.repository.guardar_umbral(UmbralZona("minca", 100))
    api.repository.guardar_umbral(UmbralZona("centro", 100))
    antes = len(eventos_ocupacion())
    assert api.repository.recalcular_ocupaciones() == 2
    assert len(eventos_ocupacion()) == antes + 2


@requiere_postgres
def test_csv_exportable(base: None) -> None:
    hoy = hoy_colombia().isoformat()
    resp = cliente.get("/api/v1/analitica/indicadores.csv", headers=cabeceras("administrador"),
                       params={"desde": hoy, "hasta": hoy})
    assert resp.status_code == 200 and resp.text.startswith("﻿zona_id,")
