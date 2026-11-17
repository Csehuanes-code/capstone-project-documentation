"""Validación del sobre compartido y evento reservas.reserva.confirmada v1."""

from __future__ import annotations

import json
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID

from analitica.aplicacion import ProcesarReserva
from analitica.dominio import ZONAS_VALIDAS, ReservaConfirmada

TIPO_RESERVA = "reservas.reserva.confirmada"
PATRON_TIPO = re.compile(r"^[a-z]+\.[a-z_]+\.[a-z_]+$")


class MensajeInvalido(ValueError):
    """Mensaje mal formado; se envía a dead-letter sin reintento."""


def procesar_mensaje(cuerpo: bytes | str, caso: ProcesarReserva) -> str:
    try:
        envelope = json.loads(cuerpo)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise MensajeInvalido("El mensaje no es JSON válido") from exc
    if not isinstance(envelope, dict):
        raise MensajeInvalido("El sobre debe ser un objeto")
    required = {"evento_id", "tipo", "version", "ocurrido_en", "datos"}
    allowed = required | {"correlation_id"}
    if required - envelope.keys() or envelope.keys() - allowed:
        raise MensajeInvalido("El sobre no cumple el esquema común")
    try:
        UUID(envelope["evento_id"])
        timestamp = datetime.fromisoformat(str(envelope["ocurrido_en"]))
    except (ValueError, TypeError):
        raise MensajeInvalido("evento_id u ocurrido_en inválido") from None
    if timestamp.tzinfo is None:
        raise MensajeInvalido("ocurrido_en debe incluir zona horaria")
    correlation_id = envelope.get("correlation_id")
    if correlation_id is not None and not isinstance(correlation_id, str):
        raise MensajeInvalido("correlation_id debe ser texto o null")
    tipo = envelope["tipo"]
    if not isinstance(tipo, str) or not PATRON_TIPO.fullmatch(tipo):
        raise MensajeInvalido("tipo debe seguir servicio.entidad.hecho")
    if tipo != TIPO_RESERVA:
        return "ignorado"
    if isinstance(envelope["version"], bool) or envelope["version"] != 1 or not isinstance(envelope["datos"], dict):
        raise MensajeInvalido("Versión o datos inválidos")
    data: dict[str, Any] = envelope["datos"]
    fields = {"reserva_id", "oferta_id", "zona_id", "personas", "fecha_servicio", "total", "moneda"}
    if fields - data.keys():
        raise MensajeInvalido("datos no cumplen reservas.reserva.confirmada v1")
    if not isinstance(data["moneda"], str) or data["moneda"] != "COP" or not isinstance(data["zona_id"], str) or data["zona_id"] not in ZONAS_VALIDAS:
        raise MensajeInvalido("Moneda o zona no pertenece al vocabulario compartido")
    try:
        count = data["personas"]
        if isinstance(count, bool) or not isinstance(count, int) or count < 1:
            raise ValueError
        service_date = date.fromisoformat(data["fecha_servicio"])
        amount = Decimal(str(data["total"]))
        if not amount.is_finite() or amount < 0:
            raise ValueError
        if not all(isinstance(data[key], str) and data[key] for key in ("reserva_id", "oferta_id")):
            raise ValueError
        reservation = ReservaConfirmada(
            evento_id=envelope["evento_id"], reserva_id=data["reserva_id"], oferta_id=data["oferta_id"],
            zona_id=data["zona_id"], personas=count, fecha_servicio=service_date, total=amount,
        )
    except (ValueError, TypeError, InvalidOperation):
        raise MensajeInvalido("Datos de reserva inválidos") from None
    return "procesado" if caso.ejecutar(reservation) else "repetido"
