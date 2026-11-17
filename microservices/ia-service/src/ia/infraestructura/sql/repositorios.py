"""Repositorios SQLAlchemy: implementan las mismas interfaces abstractas que los de memoria."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Iterator
from uuid import UUID

from sqlalchemy import func, insert, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from ia.aplicacion.puertos import RegistroEventosProcesados, UnidadDeTrabajo
from ia.dominio.modelos import (
    AporteCriterio,
    ConfiguracionCriterios,
    Criterio,
    EstadoZona,
    ItemRecomendado,
    Motivo,
    NivelOcupacion,
    ProyeccionOferta,
    Recomendacion,
)
from ia.dominio.repositorios import (
    RepositorioCriterios,
    RepositorioOfertas,
    RepositorioRecomendaciones,
    RepositorioZonas,
)

from .tablas import (
    ConfiguracionCriteriosTabla,
    EstadoZonaTabla,
    EventoProcesadoTabla,
    ItemRecomendadoTabla,
    ProyeccionOfertaTabla,
    RecomendacionTabla,
)


def _utc(fecha: datetime) -> datetime:
    """SQLite pierde la zona horaria; PostgreSQL (timestamptz) la conserva."""
    return fecha if fecha.tzinfo else fecha.replace(tzinfo=timezone.utc)


class _BaseSql:
    """Trabaja de dos modos:

    - con `sesiones` (fábrica): cada operación abre y confirma su propia transacción;
    - con `sesion` (compartida): opera dentro de la transacción de una unidad de trabajo,
      que es quien confirma o revierte todo junto.
    """

    def __init__(
        self, sesiones: sessionmaker[Session] | None = None, *, sesion: Session | None = None
    ) -> None:
        if (sesiones is None) == (sesion is None):
            raise ValueError("Indique `sesiones` o `sesion`, no ambos")
        self._sesiones = sesiones
        self._sesion = sesion

    @contextmanager
    def _leer(self) -> Iterator[Session]:
        if self._sesion is not None:
            yield self._sesion
        else:
            with self._sesiones() as s:
                yield s

    @contextmanager
    def _escribir(self) -> Iterator[Session]:
        if self._sesion is not None:
            yield self._sesion
            self._sesion.flush()
        else:
            with self._sesiones.begin() as s:
                yield s


# --- proyeccion_oferta -------------------------------------------------------------------


def _oferta_a_dominio(f: ProyeccionOfertaTabla) -> ProyeccionOferta:
    return ProyeccionOferta(
        oferta_id=f.oferta_id,
        nombre=f.nombre,
        zona_id=f.zona_id,
        categorias=frozenset(f.categorias),
        calificacion_promedio=f.calificacion_promedio,
        numero_resenas=f.numero_resenas,
        indice_sostenibilidad=f.indice_sostenibilidad,
        prestador_id=f.prestador_id,
        activa=f.activa,
        reservas_confirmadas=f.reservas_confirmadas,
    )


class OfertasSql(_BaseSql, RepositorioOfertas):
    def listar_activas(self) -> list[ProyeccionOferta]:
        with self._leer() as s:
            filas = s.scalars(select(ProyeccionOfertaTabla).where(ProyeccionOfertaTabla.activa))
            return [_oferta_a_dominio(f) for f in filas]

    def obtener(self, oferta_id: str) -> ProyeccionOferta | None:
        with self._leer() as s:
            fila = s.get(ProyeccionOfertaTabla, oferta_id)
            return _oferta_a_dominio(fila) if fila else None

    def guardar(self, oferta: ProyeccionOferta) -> None:
        with self._escribir() as s:
            s.merge(
                ProyeccionOfertaTabla(
                    oferta_id=oferta.oferta_id,
                    nombre=oferta.nombre,
                    zona_id=oferta.zona_id,
                    categorias=sorted(oferta.categorias),
                    calificacion_promedio=oferta.calificacion_promedio,
                    numero_resenas=oferta.numero_resenas,
                    indice_sostenibilidad=oferta.indice_sostenibilidad,
                    prestador_id=oferta.prestador_id,
                    activa=oferta.activa,
                    reservas_confirmadas=oferta.reservas_confirmadas,
                )
            )


# --- estado_zona -------------------------------------------------------------------------


def _zona_a_dominio(f: EstadoZonaTabla) -> EstadoZona:
    return EstadoZona(f.zona_id, f.nombre, f.ocupacion, _utc(f.actualizado_en))


class ZonasSql(_BaseSql, RepositorioZonas):
    def listar(self) -> dict[str, EstadoZona]:
        with self._leer() as s:
            return {f.zona_id: _zona_a_dominio(f) for f in s.scalars(select(EstadoZonaTabla))}

    def obtener(self, zona_id: str) -> EstadoZona | None:
        with self._leer() as s:
            fila = s.get(EstadoZonaTabla, zona_id)
            return _zona_a_dominio(fila) if fila else None

    def guardar(self, zona: EstadoZona) -> None:
        with self._escribir() as s:
            s.merge(
                EstadoZonaTabla(
                    zona_id=zona.zona_id,
                    nombre=zona.nombre,
                    ocupacion=zona.ocupacion,
                    actualizado_en=zona.actualizado_en,
                )
            )


# --- configuracion_criterios -------------------------------------------------------------


def _criterios_a_dominio(f: ConfiguracionCriteriosTabla) -> ConfiguracionCriterios:
    return ConfiguracionCriterios(
        version=f.version,
        pesos={Criterio(k): v for k, v in f.pesos.items()},
        creada_en=_utc(f.creada_en),
        umbral_tranquila=f.umbral_tranquila,
        umbral_saturacion=f.umbral_saturacion,
        prior_media=f.prior_media,
        prior_peso=f.prior_peso,
        max_por_zona=f.max_por_zona,
    )


class CriteriosSql(_BaseSql, RepositorioCriterios):
    def vigente(self) -> ConfiguracionCriterios:
        with self._leer() as s:
            fila = s.scalars(
                select(ConfiguracionCriteriosTabla)
                .order_by(ConfiguracionCriteriosTabla.version.desc())
                .limit(1)
            ).first()
            if fila is None:
                raise LookupError("No hay ninguna versión de criterios cargada en ia_db")
            return _criterios_a_dominio(fila)

    def obtener(self, version: int) -> ConfiguracionCriterios | None:
        with self._leer() as s:
            fila = s.get(ConfiguracionCriteriosTabla, version)
            return _criterios_a_dominio(fila) if fila else None

    def agregar_version(self, config: ConfiguracionCriterios) -> None:
        with self._escribir() as s:
            maxima = s.scalar(select(func.max(ConfiguracionCriteriosTabla.version)))
            if maxima is not None and config.version <= maxima:
                raise ValueError("Una versión nueva debe ser mayor que la vigente")
            s.add(
                ConfiguracionCriteriosTabla(
                    version=config.version,
                    pesos={c.value: p for c, p in config.pesos.items()},
                    umbral_tranquila=config.umbral_tranquila,
                    umbral_saturacion=config.umbral_saturacion,
                    prior_media=config.prior_media,
                    prior_peso=config.prior_peso,
                    max_por_zona=config.max_por_zona,
                    creada_en=config.creada_en,
                )
            )


# --- recomendacion + item_recomendado ----------------------------------------------------


def _item_a_fila(recomendacion_id: UUID, i: ItemRecomendado) -> dict:
    return dict(
        recomendacion_id=recomendacion_id,
        posicion=i.posicion,
        oferta_id=i.oferta_id,
        nombre=i.nombre,
        zona_id=i.zona_id,
        zona_nombre=i.zona_nombre,
        ocupacion=i.ocupacion,
        nivel=i.nivel.value,
        calificacion_promedio=i.calificacion_promedio,
        numero_resenas=i.numero_resenas,
        puntaje=i.puntaje,
        desglose=[
            {"criterio": a.criterio.value, "peso": a.peso, "valor": a.valor, "aporte": a.aporte}
            for a in i.desglose
        ],
        coincidencias=sorted(i.coincidencias),
        motivo=i.motivo.value,
        alternativa_de_id=i.alternativa_de_id,
        alternativa_de_nombre=i.alternativa_de_nombre,
        alternativa_de_zona=i.alternativa_de_zona,
    )


def _item_a_dominio(f: ItemRecomendadoTabla) -> ItemRecomendado:
    return ItemRecomendado(
        posicion=f.posicion,
        oferta_id=f.oferta_id,
        nombre=f.nombre,
        zona_id=f.zona_id,
        zona_nombre=f.zona_nombre,
        ocupacion=f.ocupacion,
        nivel=NivelOcupacion(f.nivel),
        calificacion_promedio=f.calificacion_promedio,
        numero_resenas=f.numero_resenas,
        puntaje=f.puntaje,
        desglose=tuple(
            AporteCriterio(Criterio(d["criterio"]), d["peso"], d["valor"], d["aporte"])
            for d in f.desglose
        ),
        coincidencias=frozenset(f.coincidencias),
        motivo=Motivo(f.motivo),
        alternativa_de_id=f.alternativa_de_id,
        alternativa_de_nombre=f.alternativa_de_nombre,
        alternativa_de_zona=f.alternativa_de_zona,
    )


class RecomendacionesSql(_BaseSql, RepositorioRecomendaciones):
    def guardar(self, recomendacion: Recomendacion) -> None:
        with self._escribir() as s:
            if s.get_bind().dialect.name == "postgresql":
                # La recomendación es un registro histórico: no esperar el fsync del disco.
                # Ante un apagón se perderían como mucho las de los últimos milisegundos, nunca
                # datos inconsistentes. Pesos y eventos conservan la confirmación síncrona.
                s.execute(text("SET LOCAL synchronous_commit TO OFF"))
            # INSERT directo (Core) en vez del ORM: misma operación, mucha menos CPU por petición.
            s.execute(
                insert(RecomendacionTabla).values(
                    id=recomendacion.id,
                    turista_id=recomendacion.turista_id,
                    intereses=sorted(recomendacion.intereses),
                    version_pesos=recomendacion.version_pesos,
                    generada_en=recomendacion.generada_en,
                )
            )
            if recomendacion.items:
                # Un solo INSERT ... VALUES (...), (...) para todos los ítems: un viaje a la base.
                s.execute(
                    insert(ItemRecomendadoTabla.__table__).values(
                        [_item_a_fila(recomendacion.id, i) for i in recomendacion.items]
                    )
                )

    def obtener(self, recomendacion_id: UUID) -> Recomendacion | None:
        with self._leer() as s:
            fila = s.get(RecomendacionTabla, recomendacion_id)
            if fila is None:
                return None
            return Recomendacion(
                id=fila.id,
                turista_id=fila.turista_id,
                intereses=frozenset(fila.intereses),
                version_pesos=fila.version_pesos,
                generada_en=_utc(fila.generada_en),
                items=tuple(_item_a_dominio(i) for i in fila.items),
            )


# --- evento_procesado --------------------------------------------------------------------


class EventosProcesadosSql(_BaseSql, RegistroEventosProcesados):
    def registrar_si_nuevo(self, evento_id: str) -> bool:
        if self._sesion is not None:
            # Dentro de una unidad de trabajo: si otra réplica lo insertó a la vez, el flush falla,
            # toda la transacción se revierte y el mensaje se reintenta (y entonces ya existe).
            if self._sesion.get(EventoProcesadoTabla, evento_id) is not None:
                return False
            self._sesion.add(_evento(evento_id))
            self._sesion.flush()
            return True
        try:
            with self._escribir() as s:
                s.add(_evento(evento_id))
            return True
        except IntegrityError:
            return False


def _evento(evento_id: str) -> EventoProcesadoTabla:
    return EventoProcesadoTabla(evento_id=evento_id, procesado_en=datetime.now(timezone.utc))


# --- unidad de trabajo -------------------------------------------------------------------


class UnidadDeTrabajoSql(UnidadDeTrabajo):
    """Una sola transacción para el registro del evento y el cambio de las proyecciones."""

    def __init__(self, sesiones: sessionmaker[Session]) -> None:
        self._fabrica = sesiones
        self._s: Session | None = None

    def _iniciar(self) -> None:
        self._s = self._fabrica()
        self.ofertas = OfertasSql(sesion=self._s)
        self.zonas = ZonasSql(sesion=self._s)
        self.eventos = EventosProcesadosSql(sesion=self._s)

    def _confirmar(self) -> None:
        self._s.commit()

    def rollback(self) -> None:
        self._s.rollback()

    def _cerrar(self) -> None:
        self._s.close()
        self._s = None
