"""DTO de salida: lo único que ve la capa api/ (que no puede depender del dominio)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from ia.dominio.modelos import ConfiguracionCriterios, ItemRecomendado, Recomendacion

from .casos_uso import OfertaPopular
from .explicaciones import ETIQUETAS, Idioma, explicar


@dataclass(frozen=True)
class AporteDTO:
    criterio: str
    etiqueta: str
    peso: float
    valor: float
    aporte: float


@dataclass(frozen=True)
class ZonaDTO:
    id: str
    nombre: str | None
    ocupacion: float | None
    nivel: str


@dataclass(frozen=True)
class AlternativaDeDTO:
    oferta_id: str
    nombre: str
    zona: str | None


@dataclass(frozen=True)
class ItemDTO:
    posicion: int
    oferta_id: str
    nombre: str
    zona: ZonaDTO
    calificacion_promedio: float
    numero_resenas: int
    puntaje: float
    motivo: str
    explicacion: str
    desglose: list[AporteDTO]
    alternativa_de: AlternativaDeDTO | None


@dataclass(frozen=True)
class RecomendacionDTO:
    id: UUID
    version_pesos: int
    intereses: list[str]
    generada_en: datetime
    idioma: str
    items: list[ItemDTO]


@dataclass(frozen=True)
class PesoDTO:
    criterio: str
    etiqueta: str
    peso: float


@dataclass(frozen=True)
class CriteriosDTO:
    version: int
    creada_en: datetime
    pesos: list[PesoDTO]
    umbral_tranquila: float
    umbral_saturacion: float
    prior_media: float
    prior_peso: int
    max_por_zona: int


@dataclass(frozen=True)
class PopularDTO:
    oferta_id: str
    nombre: str
    zona: ZonaDTO
    calificacion_promedio: float
    numero_resenas: int
    reservas_confirmadas: int


def _item_dto(item: ItemRecomendado, idioma: Idioma) -> ItemDTO:
    etiquetas = ETIQUETAS[idioma]
    return ItemDTO(
        posicion=item.posicion,
        oferta_id=item.oferta_id,
        nombre=item.nombre,
        zona=ZonaDTO(item.zona_id, item.zona_nombre, item.ocupacion, item.nivel.value),
        calificacion_promedio=item.calificacion_promedio,
        numero_resenas=item.numero_resenas,
        puntaje=item.puntaje,
        motivo=item.motivo.value,
        explicacion=explicar(item, idioma),
        desglose=[
            AporteDTO(a.criterio.value, etiquetas[a.criterio], a.peso, a.valor, a.aporte)
            for a in item.desglose
        ],
        alternativa_de=(
            AlternativaDeDTO(item.alternativa_de_id, item.alternativa_de_nombre or "",
                             item.alternativa_de_zona)
            if item.alternativa_de_id
            else None
        ),
    )


def recomendacion_dto(rec: Recomendacion, idioma: Idioma = "es") -> RecomendacionDTO:
    return RecomendacionDTO(
        id=rec.id,
        version_pesos=rec.version_pesos,
        intereses=sorted(rec.intereses),
        generada_en=rec.generada_en,
        idioma=idioma,
        items=[_item_dto(i, idioma) for i in rec.items],
    )


def criterios_dto(config: ConfiguracionCriterios, idioma: Idioma = "es") -> CriteriosDTO:
    etiquetas = ETIQUETAS[idioma]
    return CriteriosDTO(
        version=config.version,
        creada_en=config.creada_en,
        pesos=[PesoDTO(c.value, etiquetas[c], p) for c, p in config.pesos.items()],
        umbral_tranquila=config.umbral_tranquila,
        umbral_saturacion=config.umbral_saturacion,
        prior_media=config.prior_media,
        prior_peso=config.prior_peso,
        max_por_zona=config.max_por_zona,
    )


def popular_dto(p: OfertaPopular) -> PopularDTO:
    z = p.zona
    return PopularDTO(
        oferta_id=p.oferta.oferta_id,
        nombre=p.oferta.nombre,
        zona=ZonaDTO(
            p.oferta.zona_id, z.nombre if z else None, z.ocupacion if z else None, p.nivel.value
        ),
        calificacion_promedio=p.oferta.calificacion_promedio,
        numero_resenas=p.oferta.numero_resenas,
        reservas_confirmadas=p.oferta.reservas_confirmadas,
    )
