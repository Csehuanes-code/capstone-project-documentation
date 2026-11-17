"""Entrada de eventos de RabbitMQ (ADR-04 §4.3): el equivalente de un controlador, para mensajes.

Hoy Catálogo consume un evento:

  auth.prestador.verificacion_resuelta  (contratos/eventos/auth.prestador.verificacion_resuelta.schema.json)
      Auth lo publica cuando un administrador resuelve la verificación de un prestador (CU-28).
      Catálogo marca PerfilPrestador.verificado = (estado == "aprobada"): solo un prestador
      verificado puede publicar ofertas (RF-USR-19).

Cada evento se aplica UNA sola vez: el registro en `evento_procesado` y el cambio del perfil van
en la misma transacción. Un evento repetido (reenvío del outbox de Auth) no cambia nada.

Resultado de procesar un mensaje:
  "procesado" / "repetido" / "ignorado"  → se confirma (ack)
  MensajeInvalido                        → no cumple el contrato: va a la cola de errores
  cualquier otra excepción               → fallo temporal (ej. base caída): se reintenta
"""

from __future__ import annotations

import datetime
import json
import re
from collections.abc import Callable
from typing import Any, Literal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from catalog_service.application.use_cases import ProcesarVerificacionPrestadorUseCase
from catalog_service.infrastructure.models import EventoProcesadoModel
from catalog_service.infrastructure.repositories import SqlAlchemyPerfilPrestadorRepository

Resultado = Literal["procesado", "repetido", "ignorado"]

TIPO_VERIFICACION_RESUELTA = "auth.prestador.verificacion_resuelta"
SUSCRIPCIONES: tuple[str, ...] = (TIPO_VERIFICACION_RESUELTA,)
ESTADOS_VERIFICACION = frozenset({"aprobada", "rechazada", "info_requerida"})

_CAMPOS_SOBRE = {"evento_id", "tipo", "version", "ocurrido_en", "correlation_id", "datos"}
_OBLIGATORIOS_SOBRE = _CAMPOS_SOBRE - {"correlation_id"}
_PATRON_TIPO = re.compile(r"^[a-z]+\.[a-z_]+\.[a-z_]+$")


class MensajeInvalido(ValueError):
    """El mensaje no cumple el contrato: reintentarlo no sirve."""


def _uuid(valor: Any, campo: str) -> UUID:
    try:
        return UUID(str(valor))
    except (ValueError, TypeError, AttributeError):
        raise MensajeInvalido(f"{campo} debe ser un UUID") from None


def validar_sobre(cuerpo: bytes | str) -> dict[str, Any]:
    """Sobre común (contratos/eventos/sobre-evento.schema.json)."""
    try:
        sobre = json.loads(cuerpo)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MensajeInvalido(f"el cuerpo no es JSON: {exc}") from None
    if not isinstance(sobre, dict):
        raise MensajeInvalido("el sobre debe ser un objeto JSON")
    faltan = _OBLIGATORIOS_SOBRE - sobre.keys()
    if faltan:
        raise MensajeInvalido(f"faltan campos del sobre: {sorted(faltan)}")
    sobran = sobre.keys() - _CAMPOS_SOBRE
    if sobran:
        raise MensajeInvalido(f"campos no permitidos en el sobre: {sorted(sobran)}")
    _uuid(sobre["evento_id"], "evento_id")
    if not isinstance(sobre["tipo"], str) or not _PATRON_TIPO.match(sobre["tipo"]):
        raise MensajeInvalido("tipo debe cumplir servicio.entidad.hecho")
    if isinstance(sobre["version"], bool) or not isinstance(sobre["version"], int) or sobre["version"] < 1:
        raise MensajeInvalido("version debe ser un entero >= 1")
    try:
        datetime.datetime.fromisoformat(str(sobre["ocurrido_en"]))
    except ValueError:
        raise MensajeInvalido("ocurrido_en debe ser fecha y hora ISO 8601") from None
    if not isinstance(sobre["datos"], dict):
        raise MensajeInvalido("datos debe ser un objeto")
    return sobre


def validar_verificacion(sobre: dict[str, Any]) -> tuple[UUID, bool]:
    """Datos de auth.prestador.verificacion_resuelta v1. Devuelve (prestador_id, verificado)."""
    if sobre["version"] != 1:
        raise MensajeInvalido(f"versión {sobre['version']} no soportada (Catálogo entiende la 1)")
    datos = sobre["datos"]
    faltan = {"solicitud_id", "prestador_id", "estado", "justificacion"} - datos.keys()
    if faltan:
        raise MensajeInvalido(f"faltan campos en datos: {sorted(faltan)}")
    _uuid(datos["solicitud_id"], "solicitud_id")
    prestador_id = _uuid(datos["prestador_id"], "prestador_id")
    if datos["estado"] not in ESTADOS_VERIFICACION:
        raise MensajeInvalido(f"estado debe ser uno de {sorted(ESTADOS_VERIFICACION)}")
    return prestador_id, datos["estado"] == "aprobada"


async def procesar_mensaje(
    sesiones: Callable[[], AsyncSession], cuerpo: bytes | str
) -> Resultado:
    sobre = validar_sobre(cuerpo)
    if sobre["tipo"] != TIPO_VERIFICACION_RESUELTA:
        return "ignorado"
    prestador_id, verificado = validar_verificacion(sobre)
    evento_id = UUID(str(sobre["evento_id"]))

    async with sesiones() as sesion, sesion.begin():
        if await sesion.get(EventoProcesadoModel, evento_id) is not None:
            return "repetido"
        await ProcesarVerificacionPrestadorUseCase(
            SqlAlchemyPerfilPrestadorRepository(sesion)
        ).execute(prestador_id, verificado)
        sesion.add(
            EventoProcesadoModel(
                evento_id=evento_id,
                tipo=sobre["tipo"],
                procesado_en=datetime.datetime.now(datetime.UTC),
            )
        )
    return "procesado"
