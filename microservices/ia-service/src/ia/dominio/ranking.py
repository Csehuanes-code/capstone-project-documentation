"""Reglas de selección sobre los puntajes: descongestión y diversidad (ADR-07, RC-A01)."""

from __future__ import annotations

from collections import Counter
from typing import Sequence

from .modelos import (
    ConfiguracionCriterios,
    ItemRecomendado,
    Motivo,
    NivelOcupacion,
    ProyeccionOferta,
    PuntajeOferta,
)


def _item(
    posicion: int, p: PuntajeOferta, motivo: Motivo, reemplaza: PuntajeOferta | None = None
) -> ItemRecomendado:
    return ItemRecomendado(
        posicion=posicion,
        oferta_id=p.oferta.oferta_id,
        nombre=p.oferta.nombre,
        zona_id=p.oferta.zona_id,
        zona_nombre=p.zona.nombre if p.zona else None,
        ocupacion=p.zona.ocupacion if p.zona else None,
        nivel=p.nivel,
        calificacion_promedio=p.oferta.calificacion_promedio,
        numero_resenas=p.oferta.numero_resenas,
        puntaje=p.total,
        desglose=p.desglose,
        coincidencias=p.coincidencias,
        motivo=motivo,
        alternativa_de_id=reemplaza.oferta.oferta_id if reemplaza else None,
        alternativa_de_nombre=reemplaza.oferta.nombre if reemplaza else None,
        alternativa_de_zona=(reemplaza.zona.nombre if reemplaza and reemplaza.zona else None),
    )


def seleccionar(
    puntajes: Sequence[PuntajeOferta], config: ConfiguracionCriterios, limite: int
) -> list[ItemRecomendado]:
    """Recorre los puntajes de mayor a menor y arma la lista final.

    - Descongestión: si una oferta cae en una zona muy concurrida, en su lugar se recomienda
      la mejor oferta de una zona no saturada que comparta al menos una categoría. Si no hay
      alternativa, se mantiene la original (su explicación advierte la congestión).
    - Diversidad: como máximo `config.max_por_zona` ofertas por zona.
    - Desempate determinista por oferta_id, para que la misma entrada dé la misma salida.
    """
    ordenados = sorted(puntajes, key=lambda p: (-p.total, p.oferta.oferta_id))
    elegidos: list[ItemRecomendado] = []
    usados: set[str] = set()
    por_zona: Counter[str] = Counter()

    def cabe(p: PuntajeOferta) -> bool:
        return por_zona[p.oferta.zona_id] < config.max_por_zona

    def agregar(p: PuntajeOferta, motivo: Motivo, reemplaza: PuntajeOferta | None = None) -> None:
        elegidos.append(_item(len(elegidos) + 1, p, motivo, reemplaza))
        usados.add(p.oferta.oferta_id)
        por_zona[p.oferta.zona_id] += 1

    for p in ordenados:
        if len(elegidos) >= limite:
            break
        if p.oferta.oferta_id in usados:
            continue
        if p.nivel is NivelOcupacion.MUY_CONCURRIDA:
            usados.add(p.oferta.oferta_id)
            alternativa = next(
                (
                    q
                    for q in ordenados
                    if q.oferta.oferta_id not in usados
                    and q.nivel is not NivelOcupacion.MUY_CONCURRIDA
                    and q.oferta.categorias & p.oferta.categorias
                    and cabe(q)
                ),
                None,
            )
            if alternativa is not None:
                agregar(alternativa, Motivo.ALTERNATIVA_DESCONGESTION, reemplaza=p)
            elif cabe(p):
                agregar(p, Motivo.PERSONALIZADA)
        elif cabe(p):
            agregar(p, Motivo.PERSONALIZADA)

    return elegidos


def ordenar_por_popularidad(
    ofertas: Sequence[ProyeccionOferta], limite: int
) -> list[ProyeccionOferta]:
    """Respaldo sin personalización: más reservas confirmadas primero."""
    activas = [o for o in ofertas if o.activa]
    activas.sort(key=lambda o: (-o.reservas_confirmadas, -o.calificacion_promedio, o.oferta_id))
    return activas[:limite]
