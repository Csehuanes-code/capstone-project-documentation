"""Casos de uso de consulta (CU-21)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable
from uuid import UUID, uuid4

from ia.dominio.modelos import (
    ConfiguracionCriterios,
    EstadoZona,
    NivelOcupacion,
    ProyeccionOferta,
    Recomendacion,
)
from ia.dominio.puntaje import calcular_puntaje, nivel_ocupacion, normalizar_intereses
from ia.dominio.ranking import ordenar_por_popularidad, seleccionar
from ia.dominio.repositorios import (
    RepositorioCriterios,
    RepositorioOfertas,
    RepositorioRecomendaciones,
    RepositorioZonas,
)

from .errores import RecomendacionNoEncontrada, SolicitudInvalida, VersionCriteriosNoEncontrada
from .puertos import ComprobacionSalud, Reloj

LIMITE_MAXIMO = 20


def _validar_limite(limite: int) -> None:
    if not 1 <= limite <= LIMITE_MAXIMO:
        raise SolicitudInvalida(f"El límite debe estar entre 1 y {LIMITE_MAXIMO}")


class GenerarRecomendaciones:
    """CU-21: genera, guarda y devuelve una recomendación personalizada explicable."""

    def __init__(
        self,
        ofertas: RepositorioOfertas,
        zonas: RepositorioZonas,
        criterios: RepositorioCriterios,
        recomendaciones: RepositorioRecomendaciones,
        reloj: Reloj,
        generar_id: Callable[[], UUID] = uuid4,
    ) -> None:
        self._ofertas = ofertas
        self._zonas = zonas
        self._criterios = criterios
        self._recomendaciones = recomendaciones
        self._reloj = reloj
        self._generar_id = generar_id

    def ejecutar(
        self, intereses: Iterable[str], limite: int = 5, turista_id: str | None = None
    ) -> Recomendacion:
        _validar_limite(limite)
        config = self._criterios.vigente()
        intereses_n = normalizar_intereses(intereses)
        zonas = self._zonas.listar()
        puntajes = [
            calcular_puntaje(o, zonas.get(o.zona_id), intereses_n, config)
            for o in self._ofertas.listar_activas()
        ]
        recomendacion = Recomendacion(
            id=self._generar_id(),
            turista_id=turista_id,
            intereses=intereses_n,
            version_pesos=config.version,
            generada_en=self._reloj.ahora(),
            items=tuple(seleccionar(puntajes, config, limite)),
        )
        self._recomendaciones.guardar(recomendacion)
        return recomendacion


class ConsultarRecomendacion:
    """Devuelve una recomendación ya emitida, con el mismo desglose con que se calculó."""

    def __init__(self, recomendaciones: RepositorioRecomendaciones) -> None:
        self._recomendaciones = recomendaciones

    def ejecutar(self, recomendacion_id: UUID) -> Recomendacion:
        recomendacion = self._recomendaciones.obtener(recomendacion_id)
        if recomendacion is None:
            raise RecomendacionNoEncontrada(str(recomendacion_id))
        return recomendacion


class ConsultarCriterios:
    """'Cómo funcionan las recomendaciones': pesos vigentes o de una versión dada."""

    def __init__(self, criterios: RepositorioCriterios) -> None:
        self._criterios = criterios

    def ejecutar(self, version: int | None = None) -> ConfiguracionCriterios:
        if version is None:
            return self._criterios.vigente()
        config = self._criterios.obtener(version)
        if config is None:
            raise VersionCriteriosNoEncontrada(str(version))
        return config


@dataclass(frozen=True)
class EstadoSalud:
    listo: bool
    dependencias: dict[str, bool]


class ConsultarSalud:
    """Readiness: el servicio está listo si responden todas sus dependencias críticas.

    Las no críticas (ej. RabbitMQ) se informan en `dependencias` pero no lo sacan de servicio.
    """

    def __init__(self, comprobaciones: list[ComprobacionSalud]) -> None:
        self._comprobaciones = comprobaciones

    def ejecutar(self) -> EstadoSalud:
        resultado = {}
        listo = True
        for c in self._comprobaciones:
            try:
                resultado[c.nombre] = bool(c.disponible())
            except Exception:
                resultado[c.nombre] = False
            if c.critica and not resultado[c.nombre]:
                listo = False
        return EstadoSalud(listo=listo, dependencias=resultado)


@dataclass(frozen=True)
class OfertaPopular:
    oferta: ProyeccionOferta
    zona: EstadoZona | None
    nivel: NivelOcupacion


class ListarPopulares:
    """Respaldo sin personalización (turista sin intereses o criterio degradado)."""

    def __init__(
        self, ofertas: RepositorioOfertas, zonas: RepositorioZonas, criterios: RepositorioCriterios
    ) -> None:
        self._ofertas = ofertas
        self._zonas = zonas
        self._criterios = criterios

    def ejecutar(self, limite: int = 5) -> list[OfertaPopular]:
        _validar_limite(limite)
        config = self._criterios.vigente()
        zonas = self._zonas.listar()
        resultado = []
        for o in ordenar_por_popularidad(self._ofertas.listar_activas(), limite):
            zona = zonas.get(o.zona_id)
            resultado.append(OfertaPopular(o, zona, nivel_ocupacion(zona, config)))
        return resultado
