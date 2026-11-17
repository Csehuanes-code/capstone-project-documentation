"""Entrada de eventos de RabbitMQ (ADR-04): traduce el mensaje a los DTO de aplicación.

Es el equivalente de un controlador REST, pero para mensajes: no sabe nada de RabbitMQ
(eso vive en infraestructura/rabbitmq.py), solo recibe los bytes del mensaje, valida el sobre
y los datos contra los contratos y llama al manejador que corresponde.

Contratos que se aplican (contratos/eventos/):
  sobre-evento.schema.json                              → el sobre común
  catalogo.oferta.schema.json                           → catalogo.oferta.{publicada,actualizada,retirada}
  reservas.reserva.confirmada.schema.json               → reservas.reserva.confirmada
  analitica.zona.ocupacion_actualizada.schema.json      → analitica.zona.ocupacion_actualizada

La validación está escrita en Python (sin leer los .json) porque la imagen Docker no incluye
contratos/. Las pruebas comparan esta validación con los ejemplos de esos archivos.
Cuando el monorepo tenga la plantilla común instalable, el sobre se puede validar con
comun.eventos.SobreEvento cambiando solo `_validar_sobre`.

Resultado de procesar un mensaje:
  - "procesado" / "repetido" / "ignorado" → el mensaje se confirma (ack).
  - MensajeInvalido                       → nunca va a funcionar: va a la cola de errores.
  - cualquier otra excepción              → fallo temporal (ej. base caída): se reintenta.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from ia.aplicacion.eventos import (
    OcupacionZonaActualizada,
    OfertaActualizada,
    ProcesarOcupacionZona,
    ProcesarOfertaActualizada,
    ProcesarReservaConfirmada,
    ReservaConfirmada,
)

Resultado = Literal["procesado", "repetido", "ignorado"]

TIPO_OFERTA_PUBLICADA = "catalogo.oferta.publicada"
TIPO_OFERTA_ACTUALIZADA = "catalogo.oferta.actualizada"
TIPO_OFERTA_RETIRADA = "catalogo.oferta.retirada"
TIPO_RESERVA_CONFIRMADA = "reservas.reserva.confirmada"
TIPO_OCUPACION_ZONA = "analitica.zona.ocupacion_actualizada"

# Routing keys a las que se suscribe la cola de IA en el exchange `turismo`.
SUSCRIPCIONES: tuple[str, ...] = (
    "catalogo.oferta.*",
    TIPO_RESERVA_CONFIRMADA,
    TIPO_OCUPACION_ZONA,
)

_CAMPOS_SOBRE = {"evento_id", "tipo", "version", "ocurrido_en", "correlation_id", "datos"}
_CAMPOS_SOBRE_OBLIGATORIOS = _CAMPOS_SOBRE - {"correlation_id"}
_PATRON_TIPO = re.compile(r"^[a-z]+\.[a-z_]+\.[a-z_]+$")
_VERSION_SOPORTADA = 1


class MensajeInvalido(ValueError):
    """El mensaje no cumple el contrato: reintentarlo no sirve de nada."""


@dataclass(frozen=True)
class ManejadoresEventos:
    ofertas: ProcesarOfertaActualizada
    reservas: ProcesarReservaConfirmada
    ocupacion: ProcesarOcupacionZona


@dataclass(frozen=True)
class Sobre:
    evento_id: str
    tipo: str
    version: int
    datos: dict[str, Any]
    correlation_id: str | None


def procesar_mensaje(cuerpo: bytes | str, manejadores: ManejadoresEventos) -> Resultado:
    sobre = _validar_sobre(cuerpo)

    if sobre.tipo in (TIPO_OFERTA_PUBLICADA, TIPO_OFERTA_ACTUALIZADA, TIPO_OFERTA_RETIRADA):
        nuevo = manejadores.ofertas.ejecutar(_oferta(sobre))
    elif sobre.tipo == TIPO_RESERVA_CONFIRMADA:
        nuevo = manejadores.reservas.ejecutar(_reserva(sobre))
    elif sobre.tipo == TIPO_OCUPACION_ZONA:
        nuevo = manejadores.ocupacion.ejecutar(_ocupacion(sobre))
    else:
        # Llegó por un binding más amplio que lo que IA entiende: no es un error.
        return "ignorado"
    return "procesado" if nuevo else "repetido"


# --- sobre -------------------------------------------------------------------------------


def _validar_sobre(cuerpo: bytes | str) -> Sobre:
    try:
        datos = json.loads(cuerpo)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MensajeInvalido(f"el cuerpo no es JSON: {exc}") from None
    if not isinstance(datos, dict):
        raise MensajeInvalido("el sobre debe ser un objeto JSON")

    faltan = _CAMPOS_SOBRE_OBLIGATORIOS - datos.keys()
    if faltan:
        raise MensajeInvalido(f"faltan campos del sobre: {sorted(faltan)}")
    sobran = datos.keys() - _CAMPOS_SOBRE
    if sobran:
        raise MensajeInvalido(f"campos no permitidos en el sobre: {sorted(sobran)}")

    evento_id = _texto(datos, "evento_id")
    try:
        UUID(evento_id)
    except ValueError:
        raise MensajeInvalido("evento_id debe ser un UUID") from None

    tipo = _texto(datos, "tipo")
    if not _PATRON_TIPO.match(tipo):
        raise MensajeInvalido(f"tipo '{tipo}' no cumple servicio.entidad.hecho")

    version = _entero(datos, "version", minimo=1)
    _fecha_hora(datos, "ocurrido_en")

    correlation_id = datos.get("correlation_id")
    if correlation_id is not None and not isinstance(correlation_id, str):
        raise MensajeInvalido("correlation_id debe ser texto o null")

    cuerpo_datos = datos["datos"]
    if not isinstance(cuerpo_datos, dict):
        raise MensajeInvalido("datos debe ser un objeto")

    return Sobre(evento_id, tipo, version, cuerpo_datos, correlation_id)


def _exigir_version(sobre: Sobre) -> None:
    if sobre.version != _VERSION_SOPORTADA:
        raise MensajeInvalido(
            f"{sobre.tipo} versión {sobre.version} no soportada (IA entiende la {_VERSION_SOPORTADA})"
        )


# --- datos por tipo ----------------------------------------------------------------------


def _oferta(sobre: Sobre) -> OfertaActualizada:
    _exigir_version(sobre)
    d = sobre.datos
    categorias = d.get("categorias")
    if (
        not isinstance(categorias, list)
        or not categorias
        or not all(isinstance(c, str) for c in categorias)
        or len(set(categorias)) != len(categorias)
    ):
        raise MensajeInvalido("categorias debe ser una lista no vacía de textos sin repetir")
    activa = d.get("activa")
    if not isinstance(activa, bool):
        raise MensajeInvalido("activa debe ser true o false")
    return OfertaActualizada(
        evento_id=sobre.evento_id,
        oferta_id=_texto(d, "oferta_id"),
        nombre=_texto(d, "nombre"),
        zona_id=_texto(d, "zona_id"),
        categorias=tuple(categorias),
        calificacion_promedio=_numero(d, "calificacion_promedio", minimo=0, maximo=5),
        numero_resenas=_entero(d, "numero_resenas", minimo=0),
        indice_sostenibilidad=_numero(d, "indice_sostenibilidad", minimo=0, maximo=1),
        prestador_id=_texto(d, "prestador_id"),
        # 'retirada' manda el mismo cuerpo con activa=false; se fuerza por si acaso.
        activa=False if sobre.tipo == TIPO_OFERTA_RETIRADA else activa,
    )


def _reserva(sobre: Sobre) -> ReservaConfirmada:
    _exigir_version(sobre)
    d = sobre.datos
    # IA solo usa oferta_id, pero se valida el contrato completo para detectar a tiempo
    # si Reservas lo cambia sin avisar.
    _texto(d, "reserva_id")
    _texto(d, "zona_id")
    _entero(d, "personas", minimo=1)
    _fecha(d, "fecha_servicio")
    _numero(d, "total", minimo=0)
    if d.get("moneda") != "COP":
        raise MensajeInvalido("moneda debe ser 'COP'")
    return ReservaConfirmada(evento_id=sobre.evento_id, oferta_id=_texto(d, "oferta_id"))


def _ocupacion(sobre: Sobre) -> OcupacionZonaActualizada:
    _exigir_version(sobre)
    d = sobre.datos
    return OcupacionZonaActualizada(
        evento_id=sobre.evento_id,
        zona_id=_texto(d, "zona_id"),
        nombre=_texto(d, "nombre"),
        ocupacion=_numero(d, "ocupacion", minimo=0),
        medido_en=_fecha_hora(d, "medido_en"),
    )


# --- validadores de campos ---------------------------------------------------------------


def _texto(d: dict[str, Any], campo: str) -> str:
    valor = d.get(campo)
    if not isinstance(valor, str) or not valor:
        raise MensajeInvalido(f"{campo} debe ser un texto no vacío")
    return valor


def _entero(d: dict[str, Any], campo: str, minimo: int) -> int:
    valor = d.get(campo)
    if isinstance(valor, bool) or not isinstance(valor, int) or valor < minimo:
        raise MensajeInvalido(f"{campo} debe ser un entero >= {minimo}")
    return valor


def _numero(d: dict[str, Any], campo: str, minimo: float, maximo: float | None = None) -> float:
    valor = d.get(campo)
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        raise MensajeInvalido(f"{campo} debe ser un número")
    if valor < minimo or (maximo is not None and valor > maximo):
        rango = f"entre {minimo} y {maximo}" if maximo is not None else f">= {minimo}"
        raise MensajeInvalido(f"{campo} debe estar {rango}")
    return float(valor)


def _fecha_hora(d: dict[str, Any], campo: str) -> datetime:
    valor = _texto(d, campo)
    try:
        fecha = datetime.fromisoformat(valor)
    except ValueError:
        raise MensajeInvalido(f"{campo} debe ser fecha y hora ISO 8601") from None
    if fecha.tzinfo is None:
        raise MensajeInvalido(f"{campo} debe incluir zona horaria")
    return fecha


def _fecha(d: dict[str, Any], campo: str) -> date:
    valor = _texto(d, campo)
    try:
        return date.fromisoformat(valor)
    except ValueError:
        raise MensajeInvalido(f"{campo} debe ser una fecha AAAA-MM-DD") from None
