from dataclasses import replace

import pytest

from ia.dominio.modelos import ConfiguracionCriterios, ConfiguracionInvalida, Criterio, NivelOcupacion
from ia.dominio.puntaje import (
    afinidad,
    calcular_puntaje,
    calidad_bayesiana,
    nivel_ocupacion,
    normalizar_intereses,
)
from ia.infraestructura import semilla

from .conftest import AHORA, oferta, zona


def _minca():
    return next(o for o in semilla.OFERTAS if o.oferta_id == "minca-cascadas")


def test_reproduce_el_ejemplo_del_boceto_w3(config):
    """W3: Tour cascadas de Minca = 0,45 + 0,23 + 0,14 + 0,10 = 0,92."""
    p = calcular_puntaje(_minca(), zona("minca", 0.30), frozenset({"naturaleza"}), config)

    aportes = {a.criterio: round(a.aporte, 2) for a in p.desglose}
    assert aportes == {
        Criterio.AFINIDAD: 0.45,
        Criterio.CALIDAD: 0.23,
        Criterio.DESCONGESTION: 0.14,
        Criterio.SOSTENIBILIDAD: 0.10,
    }
    assert round(p.total, 2) == 0.92


def test_el_total_es_la_suma_del_desglose(config):
    p = calcular_puntaje(_minca(), zona("minca", 0.30), frozenset({"cultura"}), config)
    assert p.total == pytest.approx(sum(a.aporte for a in p.desglose), abs=1e-3)
    for a in p.desglose:
        assert a.aporte == pytest.approx(a.peso * a.valor, abs=1e-3)


def test_calidad_bayesiana_desconfia_de_pocas_resenas(config):
    una_resena_perfecta = calidad_bayesiana(5.0, 1, config)
    muchas_resenas_buenas = calidad_bayesiana(4.8, 200, config)
    assert una_resena_perfecta < muchas_resenas_buenas


def test_calidad_sin_resenas_es_el_prior(config):
    assert calidad_bayesiana(0.0, 0, config) == pytest.approx(config.prior_media / 5)


@pytest.mark.parametrize(
    ("intereses", "categorias", "esperado"),
    [
        (set(), {"naturaleza"}, 0.5),
        ({"naturaleza"}, {"naturaleza", "aventura"}, 1.0),
        ({"naturaleza", "cultura"}, {"naturaleza", "aventura"}, 0.5),
        ({"playa"}, {"cultura"}, 0.0),
    ],
)
def test_afinidad(intereses, categorias, esperado):
    assert afinidad(frozenset(intereses), frozenset(categorias)) == esperado


def test_intereses_se_normalizan():
    assert normalizar_intereses([" Naturaleza ", "CULTURA", "", "  "]) == {"naturaleza", "cultura"}


def test_el_prestador_no_influye_en_el_puntaje(config):
    """EC-IA-02: misma oferta con otro prestador → mismo puntaje y mismo desglose."""
    base = oferta("x", prestador="prestador-grande")
    otro = replace(base, prestador_id="prestador-pequeno")
    z, i = zona("z1", 0.4), frozenset({"naturaleza"})
    assert calcular_puntaje(base, z, i, config).desglose == calcular_puntaje(otro, z, i, config).desglose


def test_zona_desconocida_es_neutra(config):
    p = calcular_puntaje(oferta("x"), None, frozenset(), config)
    assert p.nivel is NivelOcupacion.DESCONOCIDA
    assert next(a for a in p.desglose if a.criterio is Criterio.DESCONGESTION).valor == 0.5


@pytest.mark.parametrize(
    ("ocupacion", "nivel"),
    [
        (0.10, NivelOcupacion.TRANQUILA),
        (0.50, NivelOcupacion.MODERADA),
        (0.80, NivelOcupacion.MUY_CONCURRIDA),
        (1.40, NivelOcupacion.MUY_CONCURRIDA),
    ],
)
def test_nivel_de_ocupacion(config, ocupacion, nivel):
    assert nivel_ocupacion(zona("z", ocupacion), config) is nivel


def test_sobrecupo_no_da_descongestion_negativa(config):
    p = calcular_puntaje(oferta("x"), zona("z1", 1.5), frozenset(), config)
    assert next(a for a in p.desglose if a.criterio is Criterio.DESCONGESTION).valor == 0.0


def _pesos(**cambios):
    pesos = {c: 0.25 for c in Criterio}
    pesos.update({Criterio(k): v for k, v in cambios.items()})
    return pesos


def test_pesos_deben_sumar_uno():
    with pytest.raises(ConfiguracionInvalida):
        ConfiguracionCriterios(version=2, pesos=_pesos(afinidad=0.5), creada_en=AHORA)


def test_deben_estar_todos_los_criterios():
    pesos = {Criterio.AFINIDAD: 0.5, Criterio.CALIDAD: 0.5}
    with pytest.raises(ConfiguracionInvalida):
        ConfiguracionCriterios(version=2, pesos=pesos, creada_en=AHORA)


def test_los_pesos_son_inmutables(config):
    with pytest.raises(TypeError):
        config.pesos[Criterio.AFINIDAD] = 0.9  # type: ignore[index]
