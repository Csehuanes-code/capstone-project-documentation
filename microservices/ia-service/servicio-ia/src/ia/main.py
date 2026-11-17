"""Raíz de composición: el único lugar que conoce todas las capas y las conecta.

Variables de entorno:
  IA_DATABASE_URL            si existe, usa SQLAlchemy (ej. postgresql+psycopg://u:c@host/ia_db);
                             si no, repositorios en memoria con los datos de prueba.
  IA_SEMBRAR_DATOS_PRUEBA=1  carga los tours de prueba si no hay ofertas (solo desarrollo).
  IA_CREAR_ESQUEMA=1         crea las tablas sin Alembic (atajo para SQLite local).
                             En PostgreSQL usar:  alembic upgrade head
  IA_CACHE_TTL_S=5           segundos que se guardan en memoria ofertas, zonas y pesos (0 = sin caché).
  IA_RABBITMQ_URL            si existe (ej. amqp://guest:guest@rabbitmq:5672/%2F), escucha los
                             eventos de Catálogo, Reservas y Analítica en la cola `ia.eventos`.
                             Si no, el servicio funciona igual pero sin recibir eventos.
  IA_RABBITMQ_COLA=ia.eventos  nombre de la cola (cambiarlo solo en pruebas).
Ejecutar:  uvicorn ia.main:app --reload --app-dir src
"""

from __future__ import annotations

import logging
import os
from collections.abc import Callable
from functools import partial

from fastapi import FastAPI

from ia.api.app import CasosDeUso, crear_app
from ia.api.consumidor_eventos import (
    SUSCRIPCIONES,
    ManejadoresEventos,
    MensajeInvalido,
    procesar_mensaje,
)
from ia.aplicacion.casos_uso import (
    ConsultarCriterios,
    ConsultarRecomendacion,
    ConsultarSalud,
    GenerarRecomendaciones,
    ListarPopulares,
)
from ia.aplicacion.eventos import (
    ProcesarOcupacionZona,
    ProcesarOfertaActualizada,
    ProcesarReservaConfirmada,
)
from ia.aplicacion.puertos import ComprobacionSalud, UnidadDeTrabajo
from ia.dominio.repositorios import (
    RepositorioCriterios,
    RepositorioOfertas,
    RepositorioRecomendaciones,
    RepositorioZonas,
)
from ia.infraestructura import semilla
from ia.infraestructura.memoria import (
    CriteriosEnMemoria,
    EventosProcesadosEnMemoria,
    OfertasEnMemoria,
    RecomendacionesEnMemoria,
    RelojSistema,
    UnidadDeTrabajoEnMemoria,
    ZonasEnMemoria,
)

FabricaUnidad = Callable[[], UnidadDeTrabajo]


def _componer(
    ofertas: RepositorioOfertas,
    zonas: RepositorioZonas,
    criterios: RepositorioCriterios,
    recomendaciones: RepositorioRecomendaciones,
    unidad: FabricaUnidad,
    comprobaciones: list[ComprobacionSalud] | None = None,
    rabbitmq_url: str | None = None,
) -> FastAPI:
    comprobaciones = list(comprobaciones or [])
    al_iniciar: list[Callable[[], None]] = []
    al_detener: list[Callable[[], None]] = []

    if rabbitmq_url:
        consumidor = _crear_consumidor(rabbitmq_url, unidad)
        from ia.infraestructura.rabbitmq import SaludRabbitMQ

        comprobaciones.append(SaludRabbitMQ(consumidor))
        al_iniciar.append(consumidor.iniciar)
        al_detener.append(consumidor.detener)

    return crear_app(
        CasosDeUso(
            generar=GenerarRecomendaciones(
                ofertas, zonas, criterios, recomendaciones, RelojSistema()
            ),
            consultar=ConsultarRecomendacion(recomendaciones),
            criterios=ConsultarCriterios(criterios),
            populares=ListarPopulares(ofertas, zonas, criterios),
            salud=ConsultarSalud(comprobaciones),
        ),
        al_iniciar=al_iniciar,
        al_detener=al_detener,
    )


def _crear_consumidor(url: str, unidad: FabricaUnidad):
    # Import tardío: pika solo hace falta si se configura RabbitMQ.
    from ia.infraestructura.rabbitmq import ConsumidorRabbitMQ

    manejadores = ManejadoresEventos(
        ofertas=ProcesarOfertaActualizada(unidad),
        reservas=ProcesarReservaConfirmada(unidad),
        ocupacion=ProcesarOcupacionZona(unidad),
    )
    return ConsumidorRabbitMQ(
        url=url,
        cola=os.getenv("IA_RABBITMQ_COLA", "ia.eventos"),
        suscripciones=SUSCRIPCIONES,
        procesar=partial(procesar_mensaje, manejadores=manejadores),
        errores_permanentes=(MensajeInvalido,),
    )


def crear_app_en_memoria(rabbitmq_url: str | None = None) -> FastAPI:
    ofertas = OfertasEnMemoria(semilla.OFERTAS)
    zonas = ZonasEnMemoria(semilla.ZONAS)
    eventos = EventosProcesadosEnMemoria()
    return _componer(
        ofertas,
        zonas,
        CriteriosEnMemoria(semilla.CRITERIOS_V1),
        RecomendacionesEnMemoria(),
        unidad=lambda: UnidadDeTrabajoEnMemoria(ofertas, zonas, eventos),
        rabbitmq_url=rabbitmq_url,
    )


def crear_app_con_base_de_datos(
    url: str,
    sembrar: bool = False,
    con_esquema: bool = False,
    cache_ttl: float = 0,
    rabbitmq_url: str | None = None,
) -> FastAPI:
    from ia.infraestructura.sql.conexion import (
        crear_esquema,
        crear_motor,
        crear_sesiones,
        sembrar_si_vacia,
    )
    from ia.infraestructura.sql.repositorios import (
        CriteriosSql,
        OfertasSql,
        RecomendacionesSql,
        UnidadDeTrabajoSql,
        ZonasSql,
    )
    from ia.infraestructura.sql.salud import SaludBaseDatos

    motor = crear_motor(url)
    sesiones = crear_sesiones(motor)
    if con_esquema:
        crear_esquema(motor)
    if sembrar:
        sembrar_si_vacia(sesiones, semilla.CRITERIOS_V1, semilla.ZONAS, semilla.OFERTAS)
    ofertas: RepositorioOfertas = OfertasSql(sesiones)
    zonas: RepositorioZonas = ZonasSql(sesiones)
    criterios: RepositorioCriterios = CriteriosSql(sesiones)
    if cache_ttl > 0:
        # Los eventos escriben directo en la base (sin pasar por la caché): las recomendaciones
        # los ven a más tardar en cache_ttl segundos (consistencia eventual, ADR-04).
        from ia.infraestructura.cache import CriteriosConCache, OfertasConCache, ZonasConCache

        ofertas = OfertasConCache(ofertas, cache_ttl)
        zonas = ZonasConCache(zonas, cache_ttl)
        criterios = CriteriosConCache(criterios, cache_ttl)
    return _componer(
        ofertas,
        zonas,
        criterios,
        RecomendacionesSql(sesiones),
        unidad=lambda: UnidadDeTrabajoSql(sesiones),
        comprobaciones=[SaludBaseDatos(motor)],
        rabbitmq_url=rabbitmq_url,
    )


def crear_app_desde_entorno() -> FastAPI:
    logging.basicConfig(level=os.getenv("IA_LOG_LEVEL", "INFO"))
    rabbitmq_url = os.getenv("IA_RABBITMQ_URL") or None
    url = os.getenv("IA_DATABASE_URL")
    if not url:
        return crear_app_en_memoria(rabbitmq_url=rabbitmq_url)
    return crear_app_con_base_de_datos(
        url,
        sembrar=os.getenv("IA_SEMBRAR_DATOS_PRUEBA") == "1",
        con_esquema=os.getenv("IA_CREAR_ESQUEMA") == "1",
        cache_ttl=float(os.getenv("IA_CACHE_TTL_S", "5")),
        rabbitmq_url=rabbitmq_url,
    )


app = crear_app_desde_entorno()
