from collections.abc import Iterator
from datetime import datetime, time, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from comun.seguridad import emitir_token_prueba, generar_par_claves_es256
from reservas.dominio.entidades import (
    CondicionesOferta,
    FranjaDisponibilidad,
    PoliticaCancelacionCopia,
    ProyeccionOfertaLocal,
)
from reservas.dominio.excepciones import ServicioCatalogoNoDisponibleError
from reservas.infraestructura.adaptadores import PagoSimuladoAdapter
from reservas.main import crear_app

AHORA = datetime(2026, 11, 16, 12, 0, tzinfo=timezone.utc)
FECHA_SERVICIO = AHORA.date() + timedelta(days=14)
FRANJA_ID = "franja-prueba"
OFERTA_ID = "oferta-prueba"
PRESTADOR_ID = "prestador-1"
TURISTA_ID = "turista-1"


class CatalogoFalso:
    def __init__(self) -> None:
        self.disponible = True
        self.activa = True
        self.con_tarifa = True

    def obtener_condiciones(self, oferta_id: str, fecha=None) -> CondicionesOferta:
        if not self.disponible:
            raise ServicioCatalogoNoDisponibleError("Catálogo fuera de línea.")
        if not self.con_tarifa:
            from reservas.dominio.excepciones import OfertaNoDisponibleError

            raise OfertaNoDisponibleError("La oferta no tiene tarifa vigente.")
        return CondicionesOferta(
            oferta_id=oferta_id,
            nombre_oferta="Tour de prueba",
            zona_id="tayrona",
            activa=self.activa,
            tarifa_por_persona=Decimal("100000"),
            moneda="COP",
            politica_cancelacion=PoliticaCancelacionCopia(48, 24, 50),
            prestador_nombre="Guía de prueba",
            prestador_contacto="3000000000",
            punto_encuentro="Santa Marta",
        )


class NotificadorFalso:
    def __init__(self) -> None:
        self.enviados = []

    def enviar_correo(self, notificacion) -> None:
        self.enviados.append(notificacion)


@pytest.fixture
def claves() -> tuple[str, str]:
    return generar_par_claves_es256()


@pytest.fixture
def reloj() -> list[datetime]:
    return [AHORA]


@pytest.fixture
def catalogo() -> CatalogoFalso:
    return CatalogoFalso()


@pytest.fixture
def notificador() -> NotificadorFalso:
    return NotificadorFalso()


@pytest.fixture
def app(tmp_path: Path, claves, reloj, catalogo, notificador):
    database = tmp_path / "reservas.sqlite"
    application = crear_app(
        database_url=f"sqlite:///{database.as_posix()}",
        rabbitmq_url="",
        catalogo_port=catalogo,
        pago_port=PagoSimuladoAdapter(max_reintentos=1),
        notificador_port=notificador,
        jwt_clave_publica=claves[1],
        habilitar_workers=False,
        crear_tablas=True,
        reloj=lambda: reloj[0],
    )
    with application.state.uow_factory() as uow:
        uow.franjas.guardar(
            FranjaDisponibilidad(
                id=FRANJA_ID,
                oferta_id=OFERTA_ID,
                zona_id="tayrona",
                prestador_id=PRESTADOR_ID,
                fecha=FECHA_SERVICIO,
                hora_inicio=time(10, 0),
                cupo_total=4,
                cupo_disponible=4,
            )
        )
        uow.proyecciones.guardar_o_actualizar(
            ProyeccionOfertaLocal(OFERTA_ID, "Tour de prueba", "tayrona", PRESTADOR_ID, True)
        )
        uow.commit()
    yield application
    application.state.engine.dispose()


@pytest.fixture
def cliente(app) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


def token(claves, sujeto: str = TURISTA_ID, rol: str = "turista", minutos: int = 15) -> str:
    return emitir_token_prueba(claves[0], sujeto, rol, minutos_validez=minutos)


def autorizacion(claves, sujeto: str = TURISTA_ID, rol: str = "turista") -> dict[str, str]:
    return {"Authorization": f"Bearer {token(claves, sujeto, rol)}"}


def payload_reserva(
    *,
    franja_id: str = FRANJA_ID,
    personas: int = 1,
    tarjeta: str = "4111111111111111",
    acompanantes: list[str] | None = None,
    entrada_lista_espera_id: str | None = None,
) -> dict:
    return {
        "franja_id": franja_id,
        "personas": personas,
        "correo_turista": "turista@example.com",
        "idioma": "es",
        "metodo_pago": "tarjeta",
        "datos_pago": {"numero_tarjeta": tarjeta},
        "acompanantes": acompanantes or [],
        "entrada_lista_espera_id": entrada_lista_espera_id,
    }


def crear_reserva(cliente: TestClient, claves, *, key: str = "clave-prueba", **kwargs):
    return cliente.post(
        "/api/v1/reservas",
        json=payload_reserva(**kwargs),
        headers={**autorizacion(claves), "Idempotency-Key": key},
    )
