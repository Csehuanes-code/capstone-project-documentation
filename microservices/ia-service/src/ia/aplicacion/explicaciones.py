"""Textos de explicación en ES/EN (RC-ET01, RC-S02).

El texto se arma a partir del mismo desglose guardado en la recomendación, así que lo que
lee el turista y el cálculo nunca pueden diferir (EC-IA-01).
"""

from __future__ import annotations

from typing import Literal

from ia.dominio.modelos import Criterio, ItemRecomendado, Motivo, NivelOcupacion

Idioma = Literal["es", "en"]

ETIQUETAS: dict[str, dict[Criterio, str]] = {
    "es": {
        Criterio.AFINIDAD: "Afinidad con tus intereses",
        Criterio.CALIDAD: "Calidad (calificación ajustada)",
        Criterio.DESCONGESTION: "Poca congestión de la zona",
        Criterio.SOSTENIBILIDAD: "Sostenibilidad",
    },
    "en": {
        Criterio.AFINIDAD: "Match with your interests",
        Criterio.CALIDAD: "Quality (adjusted rating)",
        Criterio.DESCONGESTION: "Low crowding in the area",
        Criterio.SOSTENIBILIDAD: "Sustainability",
    },
}

UMBRAL_BIEN_CALIFICADA = 4.0
UMBRAL_SOSTENIBLE = 0.8


def _decimal(valor: float, idioma: Idioma) -> str:
    texto = f"{valor:.1f}"
    return texto.replace(".", ",") if idioma == "es" else texto


def explicar(item: ItemRecomendado, idioma: Idioma = "es") -> str:
    es = idioma == "es"
    partes: list[str] = []
    valor_sost = next(a.valor for a in item.desglose if a.criterio is Criterio.SOSTENIBILIDAD)

    if item.motivo is Motivo.ALTERNATIVA_DESCONGESTION:
        lugar = item.alternativa_de_zona or item.alternativa_de_nombre
        partes.append(
            f"Te la sugerimos porque el sector {lugar} está muy concurrido hoy."
            if es
            else f"We suggest it because {lugar} is very crowded today."
        )
    if item.coincidencias:
        lista = ", ".join(sorted(item.coincidencias))
        partes.append(
            f"Coincide con tus intereses: {lista}." if es else f"Matches your interests: {lista}."
        )
    if item.numero_resenas > 0 and item.calificacion_promedio >= UMBRAL_BIEN_CALIFICADA:
        nota = _decimal(item.calificacion_promedio, idioma)
        partes.append(
            f"Bien calificada: {nota} de 5 en {item.numero_resenas} reseñas."
            if es
            else f"Well rated: {nota} out of 5 in {item.numero_resenas} reviews."
        )
    if item.nivel is NivelOcupacion.TRANQUILA and item.ocupacion is not None:
        pct = round(item.ocupacion * 100)
        partes.append(
            f"Hoy su zona está tranquila ({pct} % de su capacidad)."
            if es
            else f"Its area is quiet today ({pct}% of capacity)."
        )
    elif item.nivel is NivelOcupacion.MUY_CONCURRIDA:
        partes.append(
            "Atención: su zona está muy concurrida hoy."
            if es
            else "Heads up: its area is very crowded today."
        )
    if valor_sost >= UMBRAL_SOSTENIBLE:
        partes.append(
            "Cumple prácticas de turismo sostenible."
            if es
            else "Follows sustainable tourism practices."
        )
    if not partes:
        partes.append(
            "Es una de las ofertas mejor puntuadas para hoy."
            if es
            else "It is one of today's top-scored offers."
        )
    return " ".join(partes)
