"""Formato con el que Auth publica su outbox en RabbitMQ (lo que leen Catálogo y Reservas)."""

import json
from pathlib import Path
from uuid import uuid4

from auth_service.application.outbox import OutboxEvent
from auth_service.infrastructure.rabbitmq import routing_key, sobre

CONTRATOS = Path(__file__).resolve().parents[5] / "contratos" / "eventos"


def test_tipos_con_tres_partes_se_publican_tal_cual() -> None:
    assert routing_key("auth.prestador.verificacion_resuelta") == "auth.prestador.verificacion_resuelta"


def test_notificacion_solicitada_recibe_prefijo_auth() -> None:
    assert routing_key("notificacion.solicitada") == "auth.notificacion.solicitada"


def test_sobre_cumple_el_contrato_comun() -> None:
    evento = OutboxEvent(uuid4(), "auth.prestador.verificacion_resuelta", {"estado": "aprobada"})
    s = sobre(evento)
    contrato = json.loads((CONTRATOS / "sobre-evento.schema.json").read_text(encoding="utf-8"))
    assert set(s) == set(contrato["properties"])
    assert set(contrato["required"]) <= set(s)
    assert s["evento_id"] == str(evento.id)
    assert s["version"] == 1 and s["datos"] == {"estado": "aprobada"}
