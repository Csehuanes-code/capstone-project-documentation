"""Integración con un RabbitMQ REAL (infraestructura/rabbitmq.py + main.py).

Se omite si no está definida IA_TEST_RABBITMQ_URL. En local:
  docker run -d --rm --name ia-rabbitmq-prueba -p 5673:5672 rabbitmq:3-management
  IA_TEST_RABBITMQ_URL=amqp://guest:guest@localhost:5673/%2F pytest tests/test_rabbitmq.py
En CI corre siempre (RabbitMQ es un servicio del workflow).

Cada prueba usa una cola con nombre único y la borra al final, para no ensuciar el broker.
"""

from __future__ import annotations

import json
import os
import time
import uuid

import pytest

URL = os.getenv("IA_TEST_RABBITMQ_URL")
pytestmark = pytest.mark.skipif(not URL, reason="IA_TEST_RABBITMQ_URL no definida")

pika = pytest.importorskip("pika")

from fastapi.testclient import TestClient  # noqa: E402

from ia.api.consumidor_eventos import (  # noqa: E402
    SUSCRIPCIONES,
    ManejadoresEventos,
    MensajeInvalido,
    procesar_mensaje,
)
from ia.aplicacion.eventos import (  # noqa: E402
    ProcesarOcupacionZona,
    ProcesarOfertaActualizada,
    ProcesarReservaConfirmada,
)
from ia.infraestructura.memoria import (  # noqa: E402
    EventosProcesadosEnMemoria,
    OfertasEnMemoria,
    UnidadDeTrabajoEnMemoria,
    ZonasEnMemoria,
)
from ia.infraestructura.rabbitmq import EXCHANGE_TURISMO, ConsumidorRabbitMQ  # noqa: E402

OFERTA = {
    "oferta_id": "minca-cascadas",
    "nombre": "Tour cascadas de Minca",
    "zona_id": "minca",
    "categorias": ["naturaleza", "aventura"],
    "calificacion_promedio": 4.7,
    "numero_resenas": 32,
    "indice_sostenibilidad": 1.0,
    "prestador_id": "prest-guias-sierra-viva",
    "activa": True,
}
RESERVA = {
    "reserva_id": "SMT-7K3Q9P",
    "oferta_id": "minca-cascadas",
    "zona_id": "minca",
    "personas": 2,
    "fecha_servicio": "2026-12-15",
    "total": 240000.0,
    "moneda": "COP",
}


def publicar(tipo: str, datos: dict, evento_id: str | None = None, cuerpo: bytes | None = None) -> str:
    """Publica como lo hace el ProcesadorOutbox de la plantilla común."""
    evento_id = evento_id or str(uuid.uuid4())
    if cuerpo is None:
        cuerpo = json.dumps(
            {
                "evento_id": evento_id,
                "tipo": tipo,
                "version": 1,
                "ocurrido_en": "2026-11-16T15:00:00+00:00",
                "correlation_id": None,
                "datos": datos,
            }
        ).encode()
    con = pika.BlockingConnection(pika.URLParameters(URL))
    try:
        canal = con.channel()
        canal.exchange_declare(exchange=EXCHANGE_TURISMO, exchange_type="topic", durable=True)
        canal.basic_publish(
            exchange=EXCHANGE_TURISMO,
            routing_key=tipo,
            body=cuerpo,
            properties=pika.BasicProperties(
                content_type="application/json", delivery_mode=2, message_id=evento_id
            ),
        )
    finally:
        con.close()
    return evento_id


def mensajes_en(cola: str) -> int:
    con = pika.BlockingConnection(pika.URLParameters(URL))
    try:
        return con.channel().queue_declare(queue=cola, passive=True).method.message_count
    finally:
        con.close()


def borrar_topologia(cola: str) -> None:
    con = pika.BlockingConnection(pika.URLParameters(URL))
    try:
        canal = con.channel()
        canal.queue_delete(queue=cola)
        canal.queue_delete(queue=f"{cola}.errores")
        canal.exchange_delete(exchange=f"{cola}.dlx")
    finally:
        con.close()


def esperar(condicion, segundos: float = 10.0) -> bool:
    limite = time.monotonic() + segundos
    while time.monotonic() < limite:
        if condicion():
            return True
        time.sleep(0.05)
    return False


@pytest.fixture
def cola():
    nombre = f"ia.eventos.prueba-{uuid.uuid4().hex[:8]}"
    yield nombre
    borrar_topologia(nombre)


@pytest.fixture
def consumidor(cola):
    ofertas, zonas, eventos = OfertasEnMemoria(), ZonasEnMemoria(), EventosProcesadosEnMemoria()
    fallos_temporales = {"pendientes": 0}

    def unidad():
        if fallos_temporales["pendientes"] > 0:
            fallos_temporales["pendientes"] -= 1
            raise ConnectionError("la base no responde (simulado)")
        return UnidadDeTrabajoEnMemoria(ofertas, zonas, eventos)

    manejadores = ManejadoresEventos(
        ProcesarOfertaActualizada(unidad),
        ProcesarReservaConfirmada(unidad),
        ProcesarOcupacionZona(unidad),
    )
    c = ConsumidorRabbitMQ(
        url=URL,
        cola=cola,
        suscripciones=SUSCRIPCIONES,
        procesar=lambda cuerpo: procesar_mensaje(cuerpo, manejadores),
        errores_permanentes=(MensajeInvalido,),
        espera_reintento_s=0.2,
    )
    c.iniciar()
    assert c.esperar_conexion(10), "no se pudo conectar a RabbitMQ"
    yield c, ofertas, fallos_temporales
    c.detener()


def test_oferta_y_reserva_publicadas_actualizan_la_popularidad(consumidor):
    _, ofertas, _ = consumidor
    publicar("catalogo.oferta.publicada", OFERTA)
    assert esperar(lambda: ofertas.obtener("minca-cascadas") is not None)
    publicar("reservas.reserva.confirmada", RESERVA)
    assert esperar(lambda: ofertas.obtener("minca-cascadas").reservas_confirmadas == 1)


def test_evento_reenviado_por_el_outbox_cuenta_una_vez(consumidor, cola):
    _, ofertas, _ = consumidor
    publicar("catalogo.oferta.publicada", OFERTA)
    assert esperar(lambda: ofertas.obtener("minca-cascadas") is not None)
    evento_id = str(uuid.uuid4())
    publicar("reservas.reserva.confirmada", RESERVA, evento_id=evento_id)
    publicar("reservas.reserva.confirmada", RESERVA, evento_id=evento_id)
    assert esperar(lambda: mensajes_en(cola) == 0)
    time.sleep(0.3)
    assert ofertas.obtener("minca-cascadas").reservas_confirmadas == 1


def test_mensaje_invalido_termina_en_la_cola_de_errores(consumidor, cola):
    publicar("reservas.reserva.confirmada", {}, cuerpo=b'{"esto": "no es un sobre"}')
    assert esperar(lambda: mensajes_en(f"{cola}.errores") == 1)
    assert mensajes_en(cola) == 0


def test_fallo_temporal_se_reintenta_hasta_aplicarse(consumidor):
    c, ofertas, fallos = consumidor
    fallos["pendientes"] = 2  # las dos primeras veces "la base no responde"
    publicar("catalogo.oferta.publicada", OFERTA)
    assert esperar(lambda: ofertas.obtener("minca-cascadas") is not None)
    assert fallos["pendientes"] == 0


def test_eventos_que_ia_no_escucha_no_llegan_a_su_cola(consumidor, cola):
    publicar("reservas.notificacion.solicitada", {"reserva_id": "x"})
    time.sleep(0.5)
    assert mensajes_en(cola) == 0 and mensajes_en(f"{cola}.errores") == 0


def test_app_completa_arranca_el_consumidor_e_informa_rabbitmq(monkeypatch, cola):
    """main.py: con IA_RABBITMQ_URL el consumidor arranca con la app y se ve en /health/ready."""
    from ia.main import crear_app_en_memoria

    monkeypatch.setenv("IA_RABBITMQ_COLA", cola)
    with TestClient(crear_app_en_memoria(rabbitmq_url=URL)) as cliente:
        assert esperar(
            lambda: cliente.get("/health/ready").json()["dependencias"].get("rabbitmq") is True
        )
        publicar("reservas.reserva.confirmada", {**RESERVA, "oferta_id": "museo-oro"})

        def reservas_museo() -> int:
            populares = cliente.get("/api/v1/ia/populares", params={"limite": 20}).json()
            return next(p["reservas_confirmadas"] for p in populares if p["oferta_id"] == "museo-oro")

        assert esperar(lambda: mensajes_en(cola) == 0)
        antes = reservas_museo()
        publicar("reservas.reserva.confirmada", {**RESERVA, "oferta_id": "museo-oro"})
        assert esperar(lambda: reservas_museo() == antes + 1)


def test_sin_rabbitmq_la_app_sigue_lista(monkeypatch, cola):
    from ia.main import crear_app_en_memoria

    monkeypatch.setenv("IA_RABBITMQ_COLA", cola)
    with TestClient(crear_app_en_memoria(rabbitmq_url="amqp://guest:guest@localhost:1/%2F")) as cliente:
        r = cliente.get("/health/ready")
        assert r.status_code == 200
        assert r.json()["dependencias"]["rabbitmq"] is False
        assert cliente.get("/api/v1/ia/recomendaciones", params={"intereses": "naturaleza"}).status_code == 200
