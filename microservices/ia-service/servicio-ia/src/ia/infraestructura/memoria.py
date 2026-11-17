"""Repositorios en memoria. Cumplen las mismas interfaces que tendrán los de PostgreSQL."""

from __future__ import annotations

from datetime import datetime, timezone
from threading import Lock
from uuid import UUID

from ia.aplicacion.puertos import RegistroEventosProcesados, Reloj, UnidadDeTrabajo
from ia.dominio.modelos import ConfiguracionCriterios, EstadoZona, ProyeccionOferta, Recomendacion
from ia.dominio.repositorios import (
    RepositorioCriterios,
    RepositorioOfertas,
    RepositorioRecomendaciones,
    RepositorioZonas,
)


class OfertasEnMemoria(RepositorioOfertas):
    def __init__(self, ofertas: list[ProyeccionOferta] | None = None) -> None:
        self._datos = {o.oferta_id: o for o in ofertas or []}

    def listar_activas(self) -> list[ProyeccionOferta]:
        return [o for o in self._datos.values() if o.activa]

    def obtener(self, oferta_id: str) -> ProyeccionOferta | None:
        return self._datos.get(oferta_id)

    def guardar(self, oferta: ProyeccionOferta) -> None:
        self._datos[oferta.oferta_id] = oferta


class ZonasEnMemoria(RepositorioZonas):
    def __init__(self, zonas: list[EstadoZona] | None = None) -> None:
        self._datos = {z.zona_id: z for z in zonas or []}

    def listar(self) -> dict[str, EstadoZona]:
        return dict(self._datos)

    def obtener(self, zona_id: str) -> EstadoZona | None:
        return self._datos.get(zona_id)

    def guardar(self, zona: EstadoZona) -> None:
        self._datos[zona.zona_id] = zona


class CriteriosEnMemoria(RepositorioCriterios):
    def __init__(self, inicial: ConfiguracionCriterios) -> None:
        self._versiones: dict[int, ConfiguracionCriterios] = {inicial.version: inicial}

    def vigente(self) -> ConfiguracionCriterios:
        return self._versiones[max(self._versiones)]

    def obtener(self, version: int) -> ConfiguracionCriterios | None:
        return self._versiones.get(version)

    def agregar_version(self, config: ConfiguracionCriterios) -> None:
        if config.version in self._versiones:
            raise ValueError(f"La versión {config.version} ya existe y es inmutable")
        if config.version <= max(self._versiones):
            raise ValueError("Una versión nueva debe ser mayor que la vigente")
        self._versiones[config.version] = config


class RecomendacionesEnMemoria(RepositorioRecomendaciones):
    def __init__(self) -> None:
        self._datos: dict[UUID, Recomendacion] = {}

    def guardar(self, recomendacion: Recomendacion) -> None:
        self._datos[recomendacion.id] = recomendacion

    def obtener(self, recomendacion_id: UUID) -> Recomendacion | None:
        return self._datos.get(recomendacion_id)


class EventosProcesadosEnMemoria(RegistroEventosProcesados):
    def __init__(self) -> None:
        self._ids: set[str] = set()
        self._lock = Lock()

    def registrar_si_nuevo(self, evento_id: str) -> bool:
        with self._lock:
            if evento_id in self._ids:
                return False
            self._ids.add(evento_id)
            return True


class UnidadDeTrabajoEnMemoria(UnidadDeTrabajo):
    """Guarda una copia al empezar y la restaura si no se confirma (solo desarrollo y pruebas)."""

    def __init__(
        self,
        ofertas: OfertasEnMemoria,
        zonas: ZonasEnMemoria,
        eventos: EventosProcesadosEnMemoria,
    ) -> None:
        self._repos = (ofertas, zonas, eventos)
        self._copia: tuple | None = None

    def _iniciar(self) -> None:
        ofertas, zonas, eventos = self._repos
        self.ofertas, self.zonas, self.eventos = ofertas, zonas, eventos
        self._copia = (dict(ofertas._datos), dict(zonas._datos), set(eventos._ids))

    def _confirmar(self) -> None:
        self._copia = None

    def rollback(self) -> None:
        if self._copia is None:
            return
        ofertas, zonas, eventos = self._repos
        ofertas._datos, zonas._datos, eventos._ids = self._copia
        self._copia = None

    def _cerrar(self) -> None:
        pass


class RelojSistema(Reloj):
    def ahora(self) -> datetime:
        return datetime.now(timezone.utc)
