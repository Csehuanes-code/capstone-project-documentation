"""Caché de lectura en memoria del proceso (patrón decorador sobre los repositorios).

Las proyecciones (ofertas, zonas) y los pesos cambian solo cuando llega un evento o se publica
una versión nueva, pero se leen en CADA recomendación. Guardarlas unos segundos en memoria
evita tres consultas por petición (medido junto con el INSERT directo: ~56 % menos CPU).

- Una versión concreta de pesos es inmutable: se guarda para siempre.
- Lo demás vence a los `ttl` segundos; las escrituras hechas a través del decorador lo
  invalidan al instante. Las que llegan por otro proceso (otra réplica, un evento) se ven a
  más tardar en `ttl` segundos, coherente con la consistencia eventual de ADR-04.
"""

from __future__ import annotations

import time
from typing import Callable, Generic, TypeVar

from ia.dominio.modelos import ConfiguracionCriterios, EstadoZona, ProyeccionOferta
from ia.dominio.repositorios import RepositorioCriterios, RepositorioOfertas, RepositorioZonas

T = TypeVar("T")


class _Entrada(Generic[T]):
    def __init__(self, ttl: float, reloj: Callable[[], float]) -> None:
        self._ttl = ttl
        self._reloj = reloj
        self._valor: tuple[T, float] | None = None

    def obtener(self, cargar: Callable[[], T]) -> T:
        guardado = self._valor
        if guardado is not None and guardado[1] > self._reloj():
            return guardado[0]
        valor = cargar()
        self._valor = (valor, self._reloj() + self._ttl)
        return valor

    def invalidar(self) -> None:
        self._valor = None


class OfertasConCache(RepositorioOfertas):
    def __init__(self, base: RepositorioOfertas, ttl: float, reloj=time.monotonic) -> None:
        self._base = base
        self._activas: _Entrada[tuple[ProyeccionOferta, ...]] = _Entrada(ttl, reloj)

    def listar_activas(self) -> list[ProyeccionOferta]:
        return list(self._activas.obtener(lambda: tuple(self._base.listar_activas())))

    def obtener(self, oferta_id: str) -> ProyeccionOferta | None:
        return self._base.obtener(oferta_id)

    def guardar(self, oferta: ProyeccionOferta) -> None:
        self._base.guardar(oferta)
        self._activas.invalidar()


class ZonasConCache(RepositorioZonas):
    def __init__(self, base: RepositorioZonas, ttl: float, reloj=time.monotonic) -> None:
        self._base = base
        self._todas: _Entrada[dict[str, EstadoZona]] = _Entrada(ttl, reloj)

    def listar(self) -> dict[str, EstadoZona]:
        return dict(self._todas.obtener(self._base.listar))

    def obtener(self, zona_id: str) -> EstadoZona | None:
        return self._base.obtener(zona_id)

    def guardar(self, zona: EstadoZona) -> None:
        self._base.guardar(zona)
        self._todas.invalidar()


class CriteriosConCache(RepositorioCriterios):
    def __init__(self, base: RepositorioCriterios, ttl: float, reloj=time.monotonic) -> None:
        self._base = base
        self._vigente: _Entrada[ConfiguracionCriterios] = _Entrada(ttl, reloj)
        self._versiones: dict[int, ConfiguracionCriterios] = {}

    def vigente(self) -> ConfiguracionCriterios:
        return self._vigente.obtener(self._base.vigente)

    def obtener(self, version: int) -> ConfiguracionCriterios | None:
        if version not in self._versiones:
            config = self._base.obtener(version)
            if config is None:
                return None
            self._versiones[version] = config  # inmutable: no vence nunca
        return self._versiones[version]

    def agregar_version(self, config: ConfiguracionCriterios) -> None:
        self._base.agregar_version(config)
        self._vigente.invalidar()
