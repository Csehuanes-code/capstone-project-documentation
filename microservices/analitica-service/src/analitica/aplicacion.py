"""Casos de uso y puertos; no conocen FastAPI, SQLAlchemy ni RabbitMQ."""

from dataclasses import dataclass
from datetime import date
from typing import Protocol

from analitica.dominio import ReservaConfirmada, UmbralZona


class PuertoAnalitica(Protocol):
    def guardar_umbral(self, umbral: UmbralZona) -> None: ...
    def obtener_umbrales(self) -> list[UmbralZona]: ...
    def obtener_umbral(self, zona_id: str) -> UmbralZona | None: ...
    def visitantes_historicos_promedio(self, zona_id: str, dias: int = 30) -> float: ...
    def indicadores(self, desde: date, hasta: date, zona_id: str | None = None) -> list[dict[str, object]]: ...
    def alertas_activas(self) -> list[dict[str, object]]: ...
    def procesar_reserva(self, reserva: ReservaConfirmada) -> bool: ...


@dataclass(frozen=True)
class AdvertenciaUmbral:
    zona_id: str
    visitantes_maximos: int
    promedio_historico: float
    advertir: bool
    mensaje: str | None
    guardado: bool


class ConfigurarUmbral:
    def __init__(self, repositorio: PuertoAnalitica) -> None:
        self._repositorio = repositorio

    def ejecutar(self, umbral: UmbralZona, confirmar_advertencia: bool = False) -> AdvertenciaUmbral:
        promedio = self._repositorio.visitantes_historicos_promedio(umbral.zona_id)
        advertir = promedio > umbral.visitantes_maximos
        guardado = not advertir or confirmar_advertencia
        if guardado:
            self._repositorio.guardar_umbral(umbral)
        return AdvertenciaUmbral(
            umbral.zona_id,
            umbral.visitantes_maximos,
            promedio,
            advertir,
            "El umbral está por debajo del promedio histórico de visitantes (30 días)."
            if advertir else None,
            guardado,
        )


class ConsultarIndicadores:
    def __init__(self, repositorio: PuertoAnalitica) -> None:
        self._repositorio = repositorio

    def ejecutar(self, desde: date, hasta: date, zona_id: str | None = None) -> list[dict[str, object]]:
        if desde > hasta:
            raise ValueError("desde no puede ser posterior a hasta")
        return self._repositorio.indicadores(desde, hasta, zona_id)


class ProcesarReserva:
    def __init__(self, repositorio: PuertoAnalitica) -> None:
        self._repositorio = repositorio

    def ejecutar(self, reserva: ReservaConfirmada) -> bool:
        return self._repositorio.procesar_reserva(reserva)
