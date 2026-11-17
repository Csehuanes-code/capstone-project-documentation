"""Raíz de composición: el único lugar que conoce todas las capas y las conecta.

Variables de entorno:
  DATABASE_URL             postgresql+psycopg://reservas:reservas@localhost:5434/reservas_db
  RABBITMQ_URL             amqp://guest:guest@localhost:5672/%2F (vacío = sin publicar ni consumir)
  CATALOGO_URL             http://localhost:8002 (vacío = ofertas de demostración, sin Catálogo)
  SMTP_HOST / SMTP_PORT    Mailpit en local (localhost:1025)
  JWT_CLAVE_PUBLICA[_FILE] clave pública de Auth; JWT_ISSUER / JWT_AUDIENCE (ver comun.seguridad)
  RESERVAS_SEMBRAR_DEMO=1  carga ofertas y franjas de demostración si la base está vacía
  RESERVAS_CREAR_TABLAS=1  crea tablas sin Alembic (solo SQLite/pruebas; en PostgreSQL: alembic)
  RESERVAS_WORKERS=0       desactiva tareas de fondo y consumidor (pruebas)
Ejecutar:  uvicorn reservas.main:app --port 8003
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from contextlib import asynccontextmanager, suppress
from datetime import date, datetime, time, timedelta, timezone
import logging
import os
from typing import Any

from fastapi import FastAPI
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from comun.correlacion import CorrelationIdMiddleware
from comun.eventos import ConsumidorIdempotente, ProcesadorOutbox, PublicadorRabbitMQ
from comun.logging_json import RequestLoggingMiddleware, configurar_logging_json
from comun.salud import crear_router_salud
from comun.seguridad import ValidadorJWT, crear_dependencia_identidad
from reservas.api.app import CasosDeUsoReservas, crear_router_reservas, registrar_manejadores_error
from reservas.aplicacion.casos_uso import (
    AbrirDisputaUseCase,
    CancelarReservaUseCase,
    ConsultarComprobanteUseCase,
    ConsultarDisponibilidadUseCase,
    ConsultarEstadoReservaUseCase,
    CrearFranjaPrestadorUseCase,
    EnviarNotificacionesPendientesUseCase,
    ExpirarBloqueosVencidosUseCase,
    ExpirarOfertasListaEsperaUseCase,
    IniciarReservaUseCase,
    ListarDisputasUseCase,
    ListarMiListaEsperaUseCase,
    ListarReservasPrestadorUseCase,
    ListarReservasTuristaUseCase,
    ResolverDisputaUseCase,
    RetirarseListaEsperaUseCase,
    SugerirFechasCercanasUseCase,
    UnirseListaEsperaUseCase,
)
from reservas.aplicacion.puertos import CondicionesOfertaPort, NotificadorPort, PagoPort, UnitOfWork
from reservas.dominio.entidades import FranjaDisponibilidad, ProyeccionOfertaLocal
from reservas.infraestructura.adaptadores import (
    OFERTAS_DEMO,
    PRESTADORES_DEMO,
    CatalogoHttpClient,
    CorreoSmtpAdapter,
    PagoSimuladoAdapter,
)
from reservas.infraestructura.rabbitmq import (
    TIPO_NOTIFICACION_AUTH,
    TIPOS_OFERTA,
    crear_manejador_notificacion_auth,
    ConsumidorRabbitMQ,
    manejar_evento_oferta_catalogo,
    verificar_rabbitmq,
)
from reservas.infraestructura.sql.tablas import BaseReservas
from reservas.infraestructura.sql.repositorios import SqlAlchemyUnitOfWork

COLA_EVENTOS = "reservas.catalogo.ofertas"
INTERVALO_TAREAS_S = 2.0


def crear_app(
    *,
    database_url: str | None = None,
    rabbitmq_url: str | None = None,
    catalogo_port: CondicionesOfertaPort | None = None,
    pago_port: PagoPort | None = None,
    notificador_port: NotificadorPort | None = None,
    jwt_clave_publica: str | None = None,
    habilitar_workers: bool = True,
    crear_tablas: bool = False,
    sembrar_demo: bool = False,
    reloj: Callable[[], datetime] | None = None,
) -> FastAPI:
    db_url = database_url or os.getenv(
        "DATABASE_URL", "postgresql+psycopg://reservas:reservas@localhost:5434/reservas_db"
    )
    mq_url = rabbitmq_url if rabbitmq_url is not None else os.getenv("RABBITMQ_URL", "")
    logger = configurar_logging_json("reservas")

    connect_args = {"check_same_thread": False} if db_url.startswith("sqlite") else {}
    engine = create_engine(db_url, pool_pre_ping=True, connect_args=connect_args)
    sesiones = sessionmaker(bind=engine, expire_on_commit=False)
    if crear_tablas:
        BaseReservas.metadata.create_all(engine)

    def uow_factory() -> UnitOfWork:
        return SqlAlchemyUnitOfWork(sesiones)

    catalogo = catalogo_port or CatalogoHttpClient(os.getenv("CATALOGO_URL", ""), timeout_segundos=1.0)
    pagos = pago_port or PagoSimuladoAdapter(timeout_segundos=5.0, max_reintentos=3)
    correo = notificador_port or CorreoSmtpAdapter(
        host=os.getenv("SMTP_HOST", "localhost"), port=int(os.getenv("SMTP_PORT", "1025"))
    )
    extra: dict[str, Any] = {"reloj": reloj} if reloj else {}

    casos = CasosDeUsoReservas(
        disponibilidad=ConsultarDisponibilidadUseCase(uow_factory, **extra),
        fechas_cercanas=SugerirFechasCercanasUseCase(uow_factory, **extra),
        iniciar_reserva=IniciarReservaUseCase(uow_factory, catalogo, pagos, correo, **extra),
        comprobante=ConsultarComprobanteUseCase(uow_factory),
        mis_reservas=ListarReservasTuristaUseCase(uow_factory),
        reservas_prestador=ListarReservasPrestadorUseCase(uow_factory),
        crear_franja=CrearFranjaPrestadorUseCase(uow_factory, **extra),
        cancelar=CancelarReservaUseCase(uow_factory, pagos, **extra),
        unirse_lista=UnirseListaEsperaUseCase(uow_factory, **extra),
        retirarse_lista=RetirarseListaEsperaUseCase(uow_factory, **extra),
        mi_lista=ListarMiListaEsperaUseCase(uow_factory),
        abrir_disputa=AbrirDisputaUseCase(uow_factory),
        estado_reserva=ConsultarEstadoReservaUseCase(uow_factory, **extra),
        listar_disputas=ListarDisputasUseCase(uow_factory),
        resolver_disputa=ResolverDisputaUseCase(uow_factory, pagos),
    )
    expirar_reservas = ExpirarBloqueosVencidosUseCase(uow_factory, **extra)
    expirar_lista = ExpirarOfertasListaEsperaUseCase(uow_factory, **extra)
    enviar_correos = EnviarNotificacionesPendientesUseCase(uow_factory, correo)

    procesador_outbox = ProcesadorOutbox(sesiones, PublicadorRabbitMQ(amqp_url=mq_url)) if mq_url else None
    consumidor = None
    if mq_url:
        idempotente = ConsumidorIdempotente(
            sesiones,
            manejadores={
                **{t: manejar_evento_oferta_catalogo for t in TIPOS_OFERTA},
                TIPO_NOTIFICACION_AUTH: crear_manejador_notificacion_auth(
                    os.getenv("RESERVAS_URL_FRONTEND", "http://localhost:8080")
                ),
            },
        )
        consumidor = ConsumidorRabbitMQ(
            url=mq_url,
            cola=os.getenv("RESERVAS_RABBITMQ_COLA", COLA_EVENTOS),
            suscripciones=("catalogo.oferta.*", TIPO_NOTIFICACION_AUTH),
            procesar=idempotente.procesar_mensaje_raw,
        )

    def ejecutar_tareas_periodicas() -> None:
        """Una vuelta de las tareas de fondo; cada una falla sin detener a las demás."""
        tareas: list[tuple[str, Callable[[], object]]] = [
            ("expirar reservas", expirar_reservas.ejecutar),
            ("expirar ofertas de lista de espera", expirar_lista.ejecutar),
            ("enviar correos pendientes", enviar_correos.ejecutar),
        ]
        if procesador_outbox is not None:
            tareas.insert(0, ("publicar outbox", procesador_outbox.procesar_pendientes))
        for nombre, tarea in tareas:
            try:
                tarea()
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"Tarea de fondo '{nombre}' falló: {exc}")

    async def ciclo_tareas() -> None:
        while True:
            await asyncio.to_thread(ejecutar_tareas_periodicas)
            await asyncio.sleep(INTERVALO_TAREAS_S)

    @asynccontextmanager
    async def ciclo_de_vida(_app: FastAPI):  # type: ignore[no-untyped-def]
        if sembrar_demo:
            sembrar_datos_demo(uow_factory)
        tarea = None
        if habilitar_workers:
            tarea = asyncio.create_task(ciclo_tareas())
            if consumidor is not None:
                consumidor.iniciar()
        yield
        if tarea is not None:
            tarea.cancel()
            with suppress(asyncio.CancelledError):
                await tarea
        if consumidor is not None:
            consumidor.detener()

    app = FastAPI(
        title="Servicio Reservas — Turismo Santa Marta (Grupo 4)",
        description=(
            "Disponibilidad, reservas (individuales y en grupo), pago simulado, cancelación con "
            "reembolso, lista de espera, disputas de pago y notificaciones."
        ),
        version="1.0.0",
        lifespan=ciclo_de_vida,
    )
    app.add_middleware(RequestLoggingMiddleware, nombre_servicio="reservas")
    app.add_middleware(CorrelationIdMiddleware)
    registrar_manejadores_error(app)

    obtener_identidad = crear_dependencia_identidad(ValidadorJWT(clave_publica_pem=jwt_clave_publica))

    def verificar_db() -> bool:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True

    app.include_router(
        crear_router_salud(
            "reservas",
            verificar_db=verificar_db,
            verificar_broker=(lambda: verificar_rabbitmq(mq_url)) if mq_url else None,
        )
    )
    app.include_router(crear_router_reservas(obtener_identidad=obtener_identidad, casos=casos))

    app.state.engine = engine
    app.state.uow_factory = uow_factory
    app.state.ejecutar_tareas_periodicas = ejecutar_tareas_periodicas
    app.state.procesador_outbox = procesador_outbox
    app.state.consumidor = consumidor
    return app


def sembrar_datos_demo(uow_factory: Callable[[], UnitOfWork]) -> None:
    """Ofertas (proyecciones) y franjas de demostración con los ids de contratos/vocabulario.json.

    Las franjas se crean desde mañana, para que siempre haya fechas futuras que reservar.
    Solo corre si la base no tiene franjas de minca-cascadas.
    """
    log = logging.getLogger("reservas.demo")
    hoy = datetime.now(timezone.utc).date()
    try:
        with uow_factory() as uow:
            if uow.franjas.buscar_disponibles("minca-cascadas", personas=0):
                return
            for oferta_id, datos in OFERTAS_DEMO.items():
                prestador_id = PRESTADORES_DEMO[oferta_id]
                uow.proyecciones.guardar_o_actualizar(
                    ProyeccionOfertaLocal(oferta_id, datos["nombre"], datos["zona_id"], prestador_id, True)
                )
                for dias in (3, 10):
                    for hora, cupo in ((time(8, 0), 8), (time(13, 0), 4)):
                        fecha: date = hoy + timedelta(days=dias)
                        uow.franjas.guardar(
                            FranjaDisponibilidad(
                                id=f"demo-{oferta_id}-{dias}d-{hora.hour:02d}",
                                oferta_id=oferta_id,
                                zona_id=datos["zona_id"],
                                prestador_id=prestador_id,
                                fecha=fecha,
                                hora_inicio=hora,
                                cupo_total=cupo,
                                cupo_disponible=cupo,
                            )
                        )
            uow.commit()
            log.info("Datos de demostración cargados")
    except Exception as exc:  # noqa: BLE001
        log.warning("No se pudieron cargar los datos de demostración: %s", exc)


def crear_app_desde_entorno() -> FastAPI:
    return crear_app(
        habilitar_workers=os.getenv("RESERVAS_WORKERS", "1") != "0",
        crear_tablas=os.getenv("RESERVAS_CREAR_TABLAS") == "1",
        sembrar_demo=os.getenv("RESERVAS_SEMBRAR_DEMO") == "1",
    )


app = crear_app_desde_entorno()
