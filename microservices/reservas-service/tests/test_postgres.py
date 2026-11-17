from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, time, timedelta, timezone
from decimal import Decimal
import os
import uuid

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from reservas.aplicacion.casos_uso import IniciarReservaUseCase
from reservas.aplicacion.dto import SolicitudIniciarReserva
from reservas.dominio.entidades import (
    CondicionesOferta,
    FranjaDisponibilidad,
    PoliticaCancelacionCopia,
    ZONA_HORARIA_COLOMBIA,
)
from reservas.dominio.excepciones import CupoInsuficienteError
from reservas.infraestructura.adaptadores import PagoSimuladoAdapter
from reservas.infraestructura.sql.tablas import BaseReservas, FranjaDisponibilidadORM, PagoORM, ReservaORM
from reservas.infraestructura.sql.repositorios import SqlAlchemyUnitOfWork


DATABASE_URL = os.getenv("RESERVAS_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DATABASE_URL, reason="RESERVAS_TEST_DATABASE_URL no está configurada"
)


class CatalogoFalso:
    def obtener_condiciones(self, oferta_id: str, fecha=None) -> CondicionesOferta:
        return CondicionesOferta(
            oferta_id,
            "Oferta concurrente",
            "tayrona",
            True,
            Decimal("10000"),
            "COP",
            PoliticaCancelacionCopia(48, 24, 50),
        )


@pytest.fixture
def postgres():
    engine = create_engine(DATABASE_URL, pool_size=16, max_overflow=16)
    BaseReservas.metadata.create_all(engine)
    sesiones = sessionmaker(bind=engine, expire_on_commit=False)

    def crear_franja(cupo: int) -> str:
        ahora = datetime.now(timezone.utc)
        inicio = (ahora + timedelta(days=7)).astimezone(ZONA_HORARIA_COLOMBIA)
        franja_id = f"pg-{uuid.uuid4().hex}"
        with SqlAlchemyUnitOfWork(sesiones) as uow:
            uow.franjas.guardar(
                FranjaDisponibilidad(
                    franja_id,
                    "oferta-pg",
                    "tayrona",
                    "prestador-pg",
                    inicio.date(),
                    time(inicio.hour, inicio.minute),
                    cupo,
                    cupo,
                )
            )
            uow.commit()
        return franja_id

    yield engine, sesiones, crear_franja
    engine.dispose()


def _solicitud(franja_id: str, indice: int, clave: str | None = None):
    return SolicitudIniciarReserva(
        clave_idempotencia=clave or f"key-{indice}-{uuid.uuid4()}",
        franja_id=franja_id,
        personas=1,
        turista_id=f"turista-{indice}",
        correo_turista=f"turista-{indice}@example.com",
        metodo_pago="tarjeta",
    )


def _ejecutar(sesiones, franja_id: str, solicitudes):
    caso = IniciarReservaUseCase(
        lambda: SqlAlchemyUnitOfWork(sesiones),
        CatalogoFalso(),
        PagoSimuladoAdapter(max_reintentos=1),
        reloj=lambda: datetime.now(timezone.utc),
    )

    def reservar(solicitud):
        try:
            return caso.ejecutar(solicitud)
        except CupoInsuficienteError as exc:
            return exc

    with ThreadPoolExecutor(max_workers=12) as pool:
        return list(pool.map(reservar, solicitudes))


def _conteos(engine, franja_id: str) -> tuple[int, int, int]:
    with engine.connect() as conn:
        reservas = conn.execute(
            select(func.count()).select_from(ReservaORM).where(
                ReservaORM.franja_id == franja_id
            )
        ).scalar_one()
        disponibles = conn.execute(
            select(FranjaDisponibilidadORM.cupo_disponible).where(
                FranjaDisponibilidadORM.id == franja_id
            )
        ).scalar_one()
        cobros = conn.execute(
            select(func.count()).select_from(PagoORM).join(
                ReservaORM, PagoORM.reserva_id == ReservaORM.id
            ).where(
                ReservaORM.franja_id == franja_id,
                PagoORM.tipo == "cobro",
            )
        ).scalar_one()
    return reservas, disponibles, cobros


def test_postgres_ultimo_cupo_acepta_exactamente_una_reserva(postgres):
    engine, sesiones, crear_franja = postgres
    franja_id = crear_franja(1)
    resultados = _ejecutar(
        sesiones, franja_id, [_solicitud(franja_id, i) for i in range(12)]
    )

    assert sum(not isinstance(resultado, CupoInsuficienteError) for resultado in resultados) == 1
    reservas, disponibles, cobros = _conteos(engine, franja_id)
    assert reservas == cobros == 1
    assert disponibles == 0


def test_postgres_misma_clave_en_paralelo_no_duplica_reserva_ni_cobro(postgres):
    engine, sesiones, crear_franja = postgres
    franja_id = crear_franja(1)
    clave = f"idempotencia-{uuid.uuid4()}"
    turista = f"turista-{uuid.uuid4()}"
    solicitudes = [
        SolicitudIniciarReserva(
            clave_idempotencia=clave,
            franja_id=franja_id,
            personas=1,
            turista_id=turista,
            correo_turista="unico@example.com",
        )
        for _ in range(12)
    ]

    resultados = _ejecutar(sesiones, franja_id, solicitudes)

    reservas, disponibles, cobros = _conteos(engine, franja_id)
    assert reservas == cobros == 1
    assert disponibles == 0
    assert all(not isinstance(resultado, CupoInsuficienteError) for resultado in resultados)
