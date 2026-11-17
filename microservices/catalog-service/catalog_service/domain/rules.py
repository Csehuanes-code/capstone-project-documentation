"""Pure business-rule functions for the Catálogo domain.

Every function in this module is a **pure function** — no I/O, no framework
imports.  They raise domain exceptions on violation and return ``None`` (or a
computed value) on success.
"""

from __future__ import annotations

import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from catalog_service.domain.exceptions import (
    AtributosInvalidos,
    CalificacionDuplicada,
    CategoriaNoCanonica,
    IndiceSostenibilidadInvalido,
    PrestadorNoVerificado,
    PuntajeInvalido,
    TarifaSolapada,
    ZonaNoCanonica,
)
from catalog_service.domain.value_objects import (
    CategoriaInteres,
    Temporada,
    ZonaCodigo,
)

# ---------------------------------------------------------------------------
# Canonical vocabulary helpers
# ---------------------------------------------------------------------------

_CANONICAL_CATEGORIAS: frozenset[str] = frozenset(c.value for c in CategoriaInteres)
_CANONICAL_ZONAS: frozenset[str] = frozenset(z.value for z in ZonaCodigo)


def validate_categorias_canonicas(categorias: list[str]) -> None:
    """Ensure every interest category belongs to the canonical vocabulary.

    Raises:
        CategoriaNoCanonica: if any value is not in the canonical set.
    """
    invalidas = [c for c in categorias if c not in _CANONICAL_CATEGORIAS]
    if invalidas:
        raise CategoriaNoCanonica(invalidas)


def validate_zona_canonica(zona: str) -> None:
    """Ensure a zone code belongs to the canonical vocabulary.

    Raises:
        ZonaNoCanonica: if *zona* is not canonical.
    """
    if zona not in _CANONICAL_ZONAS:
        raise ZonaNoCanonica(zona)


# ---------------------------------------------------------------------------
# Provider verification
# ---------------------------------------------------------------------------


def validate_prestador_verificado(
    prestador_id: UUID,
    verificado: bool,
) -> None:
    """Only a verified provider may publish an offer.

    Raises:
        PrestadorNoVerificado: if *verificado* is ``False``.
    """
    if not verificado:
        raise PrestadorNoVerificado(prestador_id)


# ---------------------------------------------------------------------------
# Review uniqueness
# ---------------------------------------------------------------------------


def validate_calificacion_unica(
    reserva_id: UUID,
    reservas_calificadas: set[UUID],
) -> None:
    """One review per completed reservation.

    Args:
        reserva_id: the reservation being reviewed.
        reservas_calificadas: set of reservation IDs that already have a review.

    Raises:
        CalificacionDuplicada: if *reserva_id* is already in the set.
    """
    if reserva_id in reservas_calificadas:
        raise CalificacionDuplicada(reserva_id)


# ---------------------------------------------------------------------------
# Tariff overlap
# ---------------------------------------------------------------------------


def _ranges_overlap(
    a_start: datetime.date,
    a_end: datetime.date,
    b_start: datetime.date,
    b_end: datetime.date,
) -> bool:
    """Return True if [a_start, a_end] and [b_start, b_end] overlap."""
    return a_start <= b_end and b_start <= a_end


def validate_tarifa_sin_solapamiento(
    temporada: Temporada,
    vigente_desde: datetime.date,
    vigente_hasta: datetime.date,
    tarifas_existentes: list[tuple[Temporada, datetime.date, datetime.date]],
) -> None:
    """No two tariffs for the same season may overlap in date range.

    Args:
        temporada: season tier of the new tariff.
        vigente_desde: start date of the new tariff.
        vigente_hasta: end date of the new tariff.
        tarifas_existentes: list of ``(temporada, desde, hasta)`` tuples for
            all existing tariffs of the same offer.

    Raises:
        TarifaSolapada: if any overlap is detected for the same season.
    """
    for t_existente, d_existente, h_existente in tarifas_existentes:
        if t_existente != temporada:
            continue
        if _ranges_overlap(vigente_desde, vigente_hasta, d_existente, h_existente):
            rango_existente = f"{d_existente.isoformat()}–{h_existente.isoformat()}"
            rango_nuevo = f"{vigente_desde.isoformat()}–{vigente_hasta.isoformat()}"
            raise TarifaSolapada(temporada.value, rango_existente, rango_nuevo)


# ---------------------------------------------------------------------------
# Average rating calculation
# ---------------------------------------------------------------------------


def calcular_calificacion_promedio(
    puntajes: list[int],
) -> Decimal:
    """Compute the average rating rounded to two decimal places.

    Args:
        puntajes: non-empty list of scores in the 1–5 range.

    Returns:
        Average as ``Decimal`` with two decimal places.

    Raises:
        PuntajeInvalido: if any score is outside 1–5.
        ValueError: if the list is empty.
    """
    if not puntajes:
        raise ValueError("Se requiere al menos un puntaje para calcular el promedio.")

    for p in puntajes:
        if not (1 <= p <= 5):
            raise PuntajeInvalido(p)

    total = sum(puntajes)
    promedio = Decimal(total) / Decimal(len(puntajes))
    return promedio.quantize(Decimal("0.01"))


# ---------------------------------------------------------------------------
# Attribute schema validation (lightweight, no jsonschema dependency)
# ---------------------------------------------------------------------------


def validate_atributos_contra_esquema(
    atributos: dict[str, Any],
    esquema: dict[str, Any] | None,
) -> None:
    """Validate offer attributes against the service-type JSON Schema.

    This is a **lightweight structural check** that validates:
    - ``required`` properties are present.
    - ``type`` of each property matches (string, number, integer, boolean,
      array, object, null).

    For full JSON-Schema validation a richer validator should be plugged in at
    the infrastructure layer; this function guarantees the domain invariant
    without any third-party dependency.

    Raises:
        AtributosInvalidos: if validation errors are found.
    """
    if esquema is None:
        # No schema defined → any attributes are acceptable.
        return

    errores: list[str] = []

    # --- required -----------------------------------------------------------
    required: list[str] = esquema.get("required", [])
    for prop_name in required:
        if prop_name not in atributos:
            errores.append(f"Propiedad requerida ausente: '{prop_name}'")

    # --- property types -----------------------------------------------------
    properties: dict[str, Any] = esquema.get("properties", {})
    _JSON_TYPE_MAP: dict[str, tuple[type, ...]] = {
        "string": (str,),
        "number": (int, float, Decimal),
        "integer": (int,),
        "boolean": (bool,),
        "array": (list,),
        "object": (dict,),
    }

    for prop_name, prop_schema in properties.items():
        if prop_name not in atributos:
            continue  # missing-required already caught above
        value = atributos[prop_name]
        expected_type = prop_schema.get("type")
        if expected_type is None:
            continue
        if expected_type == "null":
            if value is not None:
                errores.append(f"'{prop_name}' debe ser null, recibido: {type(value).__name__}")
            continue
        allowed = _JSON_TYPE_MAP.get(expected_type)
        if allowed is None:
            continue  # unknown type keyword – skip
        if not isinstance(value, allowed):
            errores.append(
                f"'{prop_name}' debe ser {expected_type}, recibido: {type(value).__name__}"
            )

    if errores:
        raise AtributosInvalidos(errores)


# ---------------------------------------------------------------------------
# Sustainability index
# ---------------------------------------------------------------------------


def validate_indice_sostenibilidad(valor: float) -> None:
    """Ensure the sustainability index is within [0.0, 1.0].

    Raises:
        IndiceSostenibilidadInvalido: if out of range.
    """
    if not (0.0 <= valor <= 1.0):
        raise IndiceSostenibilidadInvalido(valor)
