"""Reglas puras del dominio de Analítica."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

ZONAS_VALIDAS = frozenset({"minca", "tayrona", "centro", "los-naranjos", "taganga", "rodadero"})
ZONAS_NOMBRE = {
    "minca": "Minca", "tayrona": "Tayrona", "centro": "Centro Histórico",
    "los-naranjos": "Los Naranjos", "taganga": "Taganga", "rodadero": "El Rodadero",
}


class ReglaDominioError(ValueError):
    """Dato que incumple una regla de negocio."""


@dataclass(frozen=True)
class UmbralZona:
    zona_id: str
    visitantes_maximos: int
    periodo_dias: int = 1

    def __post_init__(self) -> None:
        if self.zona_id not in ZONAS_VALIDAS:
            raise ReglaDominioError(f"Zona desconocida: {self.zona_id}")
        if self.visitantes_maximos <= 0:
            raise ReglaDominioError("visitantes_maximos debe ser mayor que cero")
        if not 1 <= self.periodo_dias <= 365:
            raise ReglaDominioError("periodo_dias debe estar entre 1 y 365")


@dataclass(frozen=True)
class ReservaConfirmada:
    evento_id: str
    reserva_id: str
    oferta_id: str
    zona_id: str
    personas: int
    fecha_servicio: date
    total: Decimal

    def __post_init__(self) -> None:
        if self.zona_id not in ZONAS_VALIDAS:
            raise ReglaDominioError(f"Zona desconocida: {self.zona_id}")
        if self.personas < 1 or self.total < 0:
            raise ReglaDominioError("La reserva debe tener personas >= 1 y total >= 0")


def calcular_ocupacion(personas: int, umbral: UmbralZona) -> float:
    """Proporción de visitantes confirmados frente a capacidad (puede superar 1)."""
    return personas / umbral.visitantes_maximos


def requiere_alerta(ocupacion: float, proporcion: float = 0.90) -> bool:
    return ocupacion >= proporcion
