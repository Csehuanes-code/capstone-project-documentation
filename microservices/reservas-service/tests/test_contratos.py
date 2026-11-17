import json
from pathlib import Path
import subprocess
import sys

import jsonschema
from sqlalchemy import select
from sqlalchemy.orm import Session

from comun.eventos import OutboxRegistro
from conftest import autorizacion, crear_reserva

RAIZ_REPO = Path(__file__).resolve().parents[3]
CONTRATOS = RAIZ_REPO / "contratos" / "eventos"


def _datos_evento(app, tipo: str) -> dict:
    with Session(app.state.engine) as session:
        evento = session.execute(
            select(OutboxRegistro).where(OutboxRegistro.tipo == tipo)
        ).scalar_one()
        return evento.datos


def test_eventos_de_cancelacion_y_disputa_validan_sus_contratos(cliente, app, claves):
    reserva = crear_reserva(
        cliente, claves, key="cancelacion-fallida", tarjeta="4111111111110019"
    ).json()
    cliente.post(
        f"/api/v1/reservas/{reserva['reserva_id']}/cancelar",
        headers=autorizacion(claves),
    )
    datos_cancelacion = _datos_evento(app, "reservas.cancelacion.pendiente")
    jsonschema.validate(
        datos_cancelacion,
        json.loads((CONTRATOS / "reservas.cancelacion.pendiente.schema.json").read_text()),
    )
    assert not {"turista_id", "correo_turista"}.intersection(datos_cancelacion)

    reserva_disputa = crear_reserva(
        cliente, claves, key="disputa-abierta"
    ).json()
    cliente.post(
        f"/api/v1/reservas/{reserva_disputa['reserva_id']}/disputas",
        json={"motivo": "El monto cobrado requiere una revisión"},
        headers=autorizacion(claves),
    )
    datos_disputa = _datos_evento(app, "reservas.disputa.abierta")
    jsonschema.validate(
        datos_disputa,
        json.loads((CONTRATOS / "reservas.disputa.abierta.schema.json").read_text()),
    )
    assert not {"turista_id", "correo_turista"}.intersection(datos_disputa)


def test_openapi_exportado_esta_al_dia():
    resultado = subprocess.run(
        [sys.executable, str(RAIZ_REPO / "microservices" / "reservas-service" / "scripts" / "exportar_openapi.py"), "--check"],
        cwd=RAIZ_REPO,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert resultado.returncode == 0, resultado.stdout + resultado.stderr
