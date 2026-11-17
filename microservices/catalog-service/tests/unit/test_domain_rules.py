"""Unit tests for pure domain rules and invariants (Domain layer)."""

from __future__ import annotations

import datetime
from decimal import Decimal
from uuid import uuid4

import pytest

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
from catalog_service.domain.rules import (
    calcular_calificacion_promedio,
    validate_atributos_contra_esquema,
    validate_calificacion_unica,
    validate_categorias_canonicas,
    validate_indice_sostenibilidad,
    validate_prestador_verificado,
    validate_tarifa_sin_solapamiento,
    validate_zona_canonica,
)
from catalog_service.domain.value_objects import Temporada


class TestVocabularioCanonico:
    """Tests canonical categories and zones according to vocabulario.json."""

    def test_categorias_canonicas_validas(self) -> None:
        # All 6 canonical categories
        validas = ["naturaleza", "cultura", "gastronomia", "historia", "playa", "aventura"]
        # Should not raise
        validate_categorias_canonicas(validas)

    def test_categorias_no_canonicas_rechazadas(self) -> None:
        # Synonyms or invented names must be strictly rejected
        invalidas = ["ecoturismo", "selva", "comida", "senderismo"]
        with pytest.raises(CategoriaNoCanonica) as exc_info:
            validate_categorias_canonicas(invalidas)
        assert "ecoturismo" in exc_info.value.categorias

    def test_zonas_canonicas_validas(self) -> None:
        # All 6 canonical zones
        for z in ["minca", "tayrona", "centro", "los-naranjos", "taganga", "rodadero"]:
            validate_zona_canonica(z)

    def test_zona_no_canonica_rechazada(self) -> None:
        with pytest.raises(ZonaNoCanonica):
            validate_zona_canonica("bogota")
        with pytest.raises(ZonaNoCanonica):
            validate_zona_canonica("parque-tayrona")  # Must be exactly "tayrona"


class TestCalificacionRules:
    """Tests review rules: uniqueness, scoring bounds, average calculation."""

    def test_calcular_promedio_valido(self) -> None:
        puntajes = [5, 4, 5, 4, 5]
        promedio = calcular_calificacion_promedio(puntajes)
        assert promedio == Decimal("4.60")

    def test_calcular_promedio_lista_vacia_falla(self) -> None:
        with pytest.raises(ValueError):
            calcular_calificacion_promedio([])

    def test_calcular_promedio_puntaje_invalido(self) -> None:
        with pytest.raises(PuntajeInvalido):
            calcular_calificacion_promedio([5, 6])
        with pytest.raises(PuntajeInvalido):
            calcular_calificacion_promedio([0, 4])

    def test_calificacion_unica_por_reserva(self) -> None:
        reserva_id = uuid4()
        reservas_ya_calificadas = {reserva_id}
        with pytest.raises(CalificacionDuplicada):
            validate_calificacion_unica(reserva_id, reservas_ya_calificadas)


class TestPrestadorRules:
    def test_prestador_verificado_pasa(self) -> None:
        pid = uuid4()
        validate_prestador_verificado(pid, verificado=True)

    def test_prestador_no_verificado_rechazado(self) -> None:
        pid = uuid4()
        with pytest.raises(PrestadorNoVerificado):
            validate_prestador_verificado(pid, verificado=False)


class TestTarifaSolapamiento:
    def test_tarifas_sin_solapamiento_pasa(self) -> None:
        existentes = [
            (Temporada.ALTA, datetime.date(2026, 12, 1), datetime.date(2026, 12, 15)),
        ]
        # Same season, later range
        validate_tarifa_sin_solapamiento(
            Temporada.ALTA,
            datetime.date(2026, 12, 16),
            datetime.date(2026, 12, 31),
            existentes,
        )
        # Different season, overlapping range is allowed
        validate_tarifa_sin_solapamiento(
            Temporada.BAJA,
            datetime.date(2026, 12, 5),
            datetime.date(2026, 12, 10),
            existentes,
        )

    def test_tarifas_solapadas_misma_temporada_rechazada(self) -> None:
        existentes = [
            (Temporada.ALTA, datetime.date(2026, 12, 1), datetime.date(2026, 12, 15)),
        ]
        with pytest.raises(TarifaSolapada):
            validate_tarifa_sin_solapamiento(
                Temporada.ALTA,
                datetime.date(2026, 12, 10),
                datetime.date(2026, 12, 20),
                existentes,
            )


class TestAtributosSchema:
    def test_atributos_validos_contra_esquema(self) -> None:
        esquema = {
            "type": "object",
            "required": ["duracion_horas", "dificultad"],
            "properties": {
                "duracion_horas": {"type": "number"},
                "dificultad": {"type": "string"},
            },
        }
        atributos = {"duracion_horas": 4.5, "dificultad": "media"}
        validate_atributos_contra_esquema(atributos, esquema)

    def test_atributos_campo_requerido_faltante(self) -> None:
        esquema = {
            "type": "object",
            "required": ["duracion_horas"],
            "properties": {"duracion_horas": {"type": "number"}},
        }
        with pytest.raises(AtributosInvalidos):
            validate_atributos_contra_esquema({}, esquema)

    def test_atributos_tipo_incorrecto(self) -> None:
        esquema = {
            "type": "object",
            "properties": {"duracion_horas": {"type": "number"}},
        }
        with pytest.raises(AtributosInvalidos):
            validate_atributos_contra_esquema({"duracion_horas": "tres"}, esquema)


class TestIndiceSostenibilidad:
    def test_indice_valido(self) -> None:
        validate_indice_sostenibilidad(0.0)
        validate_indice_sostenibilidad(0.75)
        validate_indice_sostenibilidad(1.0)

    def test_indice_fuera_de_rango(self) -> None:
        with pytest.raises(IndiceSostenibilidadInvalido):
            validate_indice_sostenibilidad(-0.1)
        with pytest.raises(IndiceSostenibilidadInvalido):
            validate_indice_sostenibilidad(1.05)
