"""Puntaje multicriterio explícito (ADR-07).

puntaje = Σ peso_i × valor_i, con cuatro criterios normalizados en [0, 1]:

- afinidad:       coeficiente de solapamiento |I ∩ C| / min(|I|, |C|) entre los intereses
                  del turista (I) y las categorías de la oferta (C). Sin intereses → 0,5 (neutro).
- calidad:        calificación bayesiana (C·m + n·x̄) / (C + n), dividida entre 5. Evita que una
                  oferta con 1 reseña de 5 estrellas supere a una con 200 reseñas de 4,8.
- descongestion:  1 − ocupación de la zona (acotada a [0, 1]). Zona sin dato → 0,5 (neutro).
- sostenibilidad: índice 0..1 de la oferta.

El prestador NO interviene en ningún criterio (equidad, EC-IA-02).
"""

from __future__ import annotations

from typing import Iterable

from .modelos import (
    AporteCriterio,
    ConfiguracionCriterios,
    Criterio,
    EstadoZona,
    NivelOcupacion,
    ProyeccionOferta,
    PuntajeOferta,
)

VALOR_NEUTRO = 0.5


def normalizar_intereses(intereses: Iterable[str]) -> frozenset[str]:
    return frozenset(i.strip().lower() for i in intereses if i and i.strip())


def nivel_ocupacion(zona: EstadoZona | None, config: ConfiguracionCriterios) -> NivelOcupacion:
    if zona is None:
        return NivelOcupacion.DESCONOCIDA
    if zona.ocupacion >= config.umbral_saturacion:
        return NivelOcupacion.MUY_CONCURRIDA
    if zona.ocupacion < config.umbral_tranquila:
        return NivelOcupacion.TRANQUILA
    return NivelOcupacion.MODERADA


def afinidad(intereses: frozenset[str], categorias: frozenset[str]) -> float:
    if not intereses:
        return VALOR_NEUTRO
    if not categorias:
        return 0.0
    return len(intereses & categorias) / min(len(intereses), len(categorias))


def calidad_bayesiana(promedio: float, resenas: int, config: ConfiguracionCriterios) -> float:
    c, m = config.prior_peso, config.prior_media
    ajustada = (c * m + resenas * promedio) / (c + resenas)
    return ajustada / 5


def descongestion(zona: EstadoZona | None) -> float:
    if zona is None:
        return VALOR_NEUTRO
    return 1 - min(zona.ocupacion, 1.0)


def calcular_puntaje(
    oferta: ProyeccionOferta,
    zona: EstadoZona | None,
    intereses: frozenset[str],
    config: ConfiguracionCriterios,
) -> PuntajeOferta:
    valores = {
        Criterio.AFINIDAD: afinidad(intereses, oferta.categorias),
        Criterio.CALIDAD: calidad_bayesiana(
            oferta.calificacion_promedio, oferta.numero_resenas, config
        ),
        Criterio.DESCONGESTION: descongestion(zona),
        Criterio.SOSTENIBILIDAD: oferta.indice_sostenibilidad,
    }
    desglose = tuple(
        AporteCriterio(
            criterio=criterio,
            peso=config.pesos[criterio],
            valor=round(valor, 4),
            aporte=round(config.pesos[criterio] * valor, 4),
        )
        for criterio, valor in valores.items()
    )
    total = round(sum(config.pesos[c] * v for c, v in valores.items()), 4)
    return PuntajeOferta(
        oferta=oferta,
        zona=zona,
        nivel=nivel_ocupacion(zona, config),
        desglose=desglose,
        total=total,
        coincidencias=intereses & oferta.categorias,
    )
