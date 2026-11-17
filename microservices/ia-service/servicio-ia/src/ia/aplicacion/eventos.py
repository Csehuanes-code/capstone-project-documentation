"""Manejadores de eventos entrantes (ADR-04). Mantienen las proyecciones locales de ia_db.

Hoy se invocan desde pruebas; cuando exista el consumidor RabbitMQ de la plantilla común,
la capa api/ solo tendrá que traducir el mensaje a estos DTO y llamar al manejador.

Cada manejador trabaja dentro de una unidad de trabajo: el registro del evento en
evento_procesado y el cambio de la proyección se guardan juntos o no se guarda ninguno.
Así un evento repetido no cambia nada, y un fallo a mitad de camino no deja el evento
marcado como procesado sin haberlo aplicado (el mensaje se reintenta).
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from typing import Callable

from ia.dominio.modelos import EstadoZona, ProyeccionOferta

from .puertos import UnidadDeTrabajo

FabricaUnidad = Callable[[], UnidadDeTrabajo]


@dataclass(frozen=True)
class OfertaActualizada:
    """catalogo.oferta.publicada / catalogo.oferta.actualizada / catalogo.oferta.retirada"""

    evento_id: str
    oferta_id: str
    nombre: str
    zona_id: str
    categorias: tuple[str, ...]
    calificacion_promedio: float
    numero_resenas: int
    indice_sostenibilidad: float
    prestador_id: str
    activa: bool = True


@dataclass(frozen=True)
class ReservaConfirmada:
    """reservas.reserva.confirmada"""

    evento_id: str
    oferta_id: str


@dataclass(frozen=True)
class OcupacionZonaActualizada:
    """analitica.zona.ocupacion_actualizada"""

    evento_id: str
    zona_id: str
    nombre: str
    ocupacion: float
    medido_en: datetime


class ProcesarOfertaActualizada:
    def __init__(self, unidad: FabricaUnidad) -> None:
        self._unidad = unidad

    def ejecutar(self, evento: OfertaActualizada) -> bool:
        with self._unidad() as uow:
            if not uow.eventos.registrar_si_nuevo(evento.evento_id):
                return False
            previa = uow.ofertas.obtener(evento.oferta_id)
            uow.ofertas.guardar(
                ProyeccionOferta(
                    oferta_id=evento.oferta_id,
                    nombre=evento.nombre,
                    zona_id=evento.zona_id,
                    categorias=frozenset(evento.categorias),
                    calificacion_promedio=evento.calificacion_promedio,
                    numero_resenas=evento.numero_resenas,
                    indice_sostenibilidad=evento.indice_sostenibilidad,
                    prestador_id=evento.prestador_id,
                    activa=evento.activa,
                    reservas_confirmadas=previa.reservas_confirmadas if previa else 0,
                )
            )
            uow.commit()
            return True


class ProcesarReservaConfirmada:
    def __init__(self, unidad: FabricaUnidad) -> None:
        self._unidad = unidad

    def ejecutar(self, evento: ReservaConfirmada) -> bool:
        with self._unidad() as uow:
            if not uow.eventos.registrar_si_nuevo(evento.evento_id):
                return False
            oferta = uow.ofertas.obtener(evento.oferta_id)
            if oferta is not None:
                uow.ofertas.guardar(
                    replace(oferta, reservas_confirmadas=oferta.reservas_confirmadas + 1)
                )
            # Si la proyección aún no llegó se ignora: la popularidad es un dato aproximado.
            uow.commit()
            return True


class ProcesarOcupacionZona:
    def __init__(self, unidad: FabricaUnidad) -> None:
        self._unidad = unidad

    def ejecutar(self, evento: OcupacionZonaActualizada) -> bool:
        with self._unidad() as uow:
            if not uow.eventos.registrar_si_nuevo(evento.evento_id):
                return False
            actual = uow.zonas.obtener(evento.zona_id)
            # Si llegó fuera de orden se conserva la medición más reciente.
            if actual is None or actual.actualizado_en <= evento.medido_en:
                uow.zonas.guardar(
                    EstadoZona(
                        zona_id=evento.zona_id,
                        nombre=evento.nombre,
                        ocupacion=evento.ocupacion,
                        actualizado_en=evento.medido_en,
                    )
                )
            uow.commit()
            return True
