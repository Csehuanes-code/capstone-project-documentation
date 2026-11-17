import json
import os
import threading
import time
import uuid

import pika
import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from comun.eventos import (
    ConsumidorIdempotente,
    EventoProcesadoRegistro,
    ProcesadorOutbox,
    PublicadorRabbitMQ,
    registrar_en_outbox,
)
from reservas.infraestructura.rabbitmq import (
    TIPOS_OFERTA,
    ConsumidorRabbitMQ,
    manejar_evento_oferta_catalogo,
)
from reservas.infraestructura.sql.tablas import BaseReservas, ProyeccionOfertaORM


RABBITMQ_URL = os.getenv("RESERVAS_TEST_RABBITMQ_URL")
pytestmark = pytest.mark.skipif(
    not RABBITMQ_URL, reason="RESERVAS_TEST_RABBITMQ_URL no está configurada"
)


def _conectar():
    params = pika.URLParameters(RABBITMQ_URL)
    params.socket_timeout = 5
    return pika.BlockingConnection(params)


def _esperar(condicion, timeout: float = 6.0) -> bool:
    limite = time.monotonic() + timeout
    while time.monotonic() < limite:
        if condicion():
            return True
        time.sleep(0.05)
    return False


def test_outbox_publica_y_consumidor_recibe_eventos_de_catalogo(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'rabbit.sqlite'}")
    BaseReservas.metadata.create_all(engine)
    sesiones = sessionmaker(engine, expire_on_commit=False)
    cola_confirmadas = f"test.reservas.confirmadas.{uuid.uuid4().hex}"
    cola_catalogo = f"test.reservas.catalogo.{uuid.uuid4().hex}"
    recibidos: list[dict] = []
    confirmacion_recibida = threading.Event()
    consumidor_confirmadas = ConsumidorRabbitMQ(
        RABBITMQ_URL,
        cola_confirmadas,
        ("reservas.reserva.confirmada",),
        lambda cuerpo: (recibidos.append(json.loads(cuerpo)), confirmacion_recibida.set()),
        espera_reconexion_s=0.1,
        espera_reintento_s=0.1,
    )
    consumidor_catalogo = ConsumidorIdempotente(
        sesiones,
        manejadores={tipo: manejar_evento_oferta_catalogo for tipo in TIPOS_OFERTA},
    )
    consumidor_ofertas = ConsumidorRabbitMQ(
        RABBITMQ_URL,
        cola_catalogo,
        ("catalogo.oferta.*",),
        consumidor_catalogo.procesar_mensaje_raw,
        espera_reconexion_s=0.1,
        espera_reintento_s=0.1,
    )
    try:
        consumidor_confirmadas.iniciar()
        consumidor_ofertas.iniciar()
        assert consumidor_confirmadas.esperar_conexion(5)
        assert consumidor_ofertas.esperar_conexion(5)

        with sesiones() as session:
            registrar_en_outbox(
                session,
                "reservas.reserva.confirmada",
                {
                    "reserva_id": "SMT-123ABC",
                    "oferta_id": "minca-cascadas",
                    "zona_id": "minca",
                    "personas": 1,
                    "fecha_servicio": "2026-12-15",
                    "total": 120000,
                    "moneda": "COP",
                },
            )
            session.commit()
        publicador = PublicadorRabbitMQ(RABBITMQ_URL)
        assert ProcesadorOutbox(sesiones, publicador).procesar_pendientes() == 1
        assert confirmacion_recibida.wait(5)
        assert recibidos[0]["tipo"] == "reservas.reserva.confirmada"

        evento = {
            "evento_id": str(uuid.uuid4()),
            "tipo": "catalogo.oferta.publicada",
            "version": 1,
            "ocurrido_en": "2026-11-16T12:00:00+00:00",
            "correlation_id": None,
            "datos": {
                "oferta_id": "oferta-rabbit",
                "nombre": "Tour de prueba",
                "zona_id": "tayrona",
                "prestador_id": "prestador-rabbit",
                "activa": True,
            },
        }

        def publicar(routing_key: str, cuerpo: bytes) -> None:
            conexion = _conectar()
            try:
                canal = conexion.channel()
                canal.basic_publish(
                    exchange="turismo",
                    routing_key=routing_key,
                    body=cuerpo,
                    properties=pika.BasicProperties(delivery_mode=2),
                )
            finally:
                conexion.close()

        cuerpo_evento = json.dumps(evento).encode()
        publicar(evento["tipo"], cuerpo_evento)
        publicar(evento["tipo"], cuerpo_evento)
        assert _esperar(
            lambda: _conteo(sesiones, EventoProcesadoRegistro) == 1
        )
        with sesiones() as session:
            proyeccion = session.get(ProyeccionOfertaORM, "oferta-rabbit")
            assert proyeccion is not None
            assert proyeccion.prestador_id == "prestador-rabbit"

        publicar("catalogo.oferta.publicada", b'{"tipo":')
        conexion = _conectar()
        try:
            canal = conexion.channel()
            assert _esperar(
                lambda: _hay_mensaje(canal, f"{cola_catalogo}.errores")
            )
        finally:
            conexion.close()
    finally:
        consumidor_confirmadas.detener()
        consumidor_ofertas.detener()
        conexion = _conectar()
        try:
            canal = conexion.channel()
            for cola in (cola_confirmadas, f"{cola_confirmadas}.errores",
                         cola_catalogo, f"{cola_catalogo}.errores"):
                canal.queue_delete(queue=cola)
            for exchange in (f"{cola_confirmadas}.dlx", f"{cola_catalogo}.dlx"):
                canal.exchange_delete(exchange=exchange)
        finally:
            conexion.close()
        engine.dispose()


def _conteo(sesiones, modelo) -> int:
    with sesiones() as session:
        return int(session.execute(select(func.count()).select_from(modelo)).scalar_one())


def _hay_mensaje(canal, cola: str) -> bool:
    metodo, propiedades, cuerpo = canal.basic_get(cola, auto_ack=True)
    return metodo is not None
