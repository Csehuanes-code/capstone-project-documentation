"""Entidades y objetos de valor del servicio IA (tablas lógicas de ia_db)."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from types import MappingProxyType
from typing import Mapping
from uuid import UUID


class Criterio(str, Enum):
    AFINIDAD = "afinidad"
    CALIDAD = "calidad"
    DESCONGESTION = "descongestion"
    SOSTENIBILIDAD = "sostenibilidad"


class NivelOcupacion(str, Enum):
    TRANQUILA = "tranquila"
    MODERADA = "moderada"
    MUY_CONCURRIDA = "muy_concurrida"
    DESCONOCIDA = "desconocida"


class Motivo(str, Enum):
    PERSONALIZADA = "personalizada"
    ALTERNATIVA_DESCONGESTION = "alternativa_descongestion"


class ConfiguracionInvalida(ValueError):
    """La configuración de criterios viola una regla del dominio."""


@dataclass(frozen=True)
class EstadoZona:
    """Proyección local de la ocupación de una zona (llega por eventos de Analítica)."""

    zona_id: str
    nombre: str
    ocupacion: float  # visitantes / capacidad de carga; puede superar 1
    actualizado_en: datetime

    def __post_init__(self) -> None:
        if self.ocupacion < 0:
            raise ValueError("La ocupación no puede ser negativa")


@dataclass(frozen=True)
class ProyeccionOferta:
    """Copia local de la oferta publicada en Catálogo, solo con lo que usa el puntaje."""

    oferta_id: str
    nombre: str
    zona_id: str
    categorias: frozenset[str]
    calificacion_promedio: float  # 0..5
    numero_resenas: int
    indice_sostenibilidad: float  # 0..1
    prestador_id: str  # solo referencia: NO participa del puntaje (EC-IA-02)
    activa: bool = True
    reservas_confirmadas: int = 0  # popularidad, alimentada por reservas.reserva.confirmada

    def __post_init__(self) -> None:
        if not 0 <= self.calificacion_promedio <= 5:
            raise ValueError("La calificación promedio debe estar entre 0 y 5")
        if self.numero_resenas < 0:
            raise ValueError("El número de reseñas no puede ser negativo")
        if not 0 <= self.indice_sostenibilidad <= 1:
            raise ValueError("El índice de sostenibilidad debe estar entre 0 y 1")
        object.__setattr__(
            self, "categorias", frozenset(c.strip().lower() for c in self.categorias if c.strip())
        )


@dataclass(frozen=True)
class ConfiguracionCriterios:
    """Pesos versionados e inmutables. Cambiar un peso = crear una versión nueva."""

    version: int
    pesos: Mapping[Criterio, float]
    creada_en: datetime
    umbral_tranquila: float = 0.5  # ocupación < umbral → zona tranquila
    umbral_saturacion: float = 0.8  # ocupación >= umbral → zona muy concurrida
    prior_media: float = 4.3  # media a priori de la calificación bayesiana
    prior_peso: int = 10  # "reseñas virtuales" del prior
    max_por_zona: int = 2  # regla de diversidad

    def __post_init__(self) -> None:
        if self.version < 1:
            raise ConfiguracionInvalida("La versión debe ser >= 1")
        faltantes = set(Criterio) - set(self.pesos)
        if faltantes:
            raise ConfiguracionInvalida(f"Faltan pesos para: {sorted(c.value for c in faltantes)}")
        if any(p < 0 for p in self.pesos.values()):
            raise ConfiguracionInvalida("Los pesos no pueden ser negativos")
        if not math.isclose(sum(self.pesos.values()), 1.0, abs_tol=1e-9):
            raise ConfiguracionInvalida("Los pesos deben sumar 1")
        if not 0 < self.umbral_tranquila < self.umbral_saturacion:
            raise ConfiguracionInvalida("Se requiere 0 < umbral_tranquila < umbral_saturacion")
        if self.max_por_zona < 1:
            raise ConfiguracionInvalida("max_por_zona debe ser >= 1")
        object.__setattr__(self, "pesos", MappingProxyType(dict(self.pesos)))


@dataclass(frozen=True)
class AporteCriterio:
    """Una fila del desglose de "¿Por qué veo esto?": peso × valor = aporte."""

    criterio: Criterio
    peso: float
    valor: float
    aporte: float


@dataclass(frozen=True)
class PuntajeOferta:
    oferta: ProyeccionOferta
    zona: EstadoZona | None
    nivel: NivelOcupacion
    desglose: tuple[AporteCriterio, ...]
    total: float
    coincidencias: frozenset[str]  # intereses del turista que coinciden con la oferta


@dataclass(frozen=True)
class ItemRecomendado:
    posicion: int
    oferta_id: str
    nombre: str
    zona_id: str
    zona_nombre: str | None
    ocupacion: float | None
    nivel: NivelOcupacion
    calificacion_promedio: float
    numero_resenas: int
    puntaje: float
    desglose: tuple[AporteCriterio, ...]
    coincidencias: frozenset[str]
    motivo: Motivo = Motivo.PERSONALIZADA
    alternativa_de_id: str | None = None
    alternativa_de_nombre: str | None = None
    alternativa_de_zona: str | None = None


@dataclass(frozen=True)
class Recomendacion:
    """Recomendación emitida; guarda la versión de pesos y el desglose con que se calculó."""

    id: UUID
    turista_id: str | None
    intereses: frozenset[str]
    version_pesos: int
    generada_en: datetime
    items: tuple[ItemRecomendado, ...] = field(default_factory=tuple)
