"""Interfaces abstractas de repositorio (ABC).

La infraestructura las implementa: en memoria para desarrollo y SQLAlchemy/PostgreSQL (ia_db)
para producción. El dominio y los casos de uso solo conocen estas abstracciones.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from .modelos import ConfiguracionCriterios, EstadoZona, ProyeccionOferta, Recomendacion


class RepositorioOfertas(ABC):
    @abstractmethod
    def listar_activas(self) -> list[ProyeccionOferta]: ...

    @abstractmethod
    def obtener(self, oferta_id: str) -> ProyeccionOferta | None: ...

    @abstractmethod
    def guardar(self, oferta: ProyeccionOferta) -> None: ...


class RepositorioZonas(ABC):
    @abstractmethod
    def listar(self) -> dict[str, EstadoZona]: ...

    @abstractmethod
    def obtener(self, zona_id: str) -> EstadoZona | None: ...

    @abstractmethod
    def guardar(self, zona: EstadoZona) -> None: ...


class RepositorioCriterios(ABC):
    @abstractmethod
    def vigente(self) -> ConfiguracionCriterios: ...

    @abstractmethod
    def obtener(self, version: int) -> ConfiguracionCriterios | None: ...

    @abstractmethod
    def agregar_version(self, config: ConfiguracionCriterios) -> None:
        """Agrega una versión nueva, mayor que la vigente. Nunca modifica una existente."""


class RepositorioRecomendaciones(ABC):
    @abstractmethod
    def guardar(self, recomendacion: Recomendacion) -> None: ...

    @abstractmethod
    def obtener(self, recomendacion_id: UUID) -> Recomendacion | None: ...
