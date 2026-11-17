"""Entrada de eventos (api/consumidor_eventos.py): el mensaje de RabbitMQ → manejador correcto.

Los datos de prueba salen de los `examples` de contratos/eventos/*.schema.json: si alguien
cambia un contrato, estas pruebas lo detectan.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest

from ia.api.consumidor_eventos import (
    SUSCRIPCIONES,
    ManejadoresEventos,
    MensajeInvalido,
    procesar_mensaje,
)
from ia.aplicacion.casos_uso import ConsultarSalud
from ia.aplicacion.eventos import (
    ProcesarOcupacionZona,
    ProcesarOfertaActualizada,
    ProcesarReservaConfirmada,
)
from ia.aplicacion.puertos import ComprobacionSalud
from ia.infraestructura.memoria import (
    EventosProcesadosEnMemoria,
    OfertasEnMemoria,
    UnidadDeTrabajoEnMemoria,
    ZonasEnMemoria,
)

CONTRATOS = Path(__file__).resolve().parents[3] / "contratos" / "eventos"


def _ejemplo(archivo: str) -> dict:
    return json.loads((CONTRATOS / archivo).read_text(encoding="utf-8"))["examples"][0]


OFERTA = _ejemplo("catalogo.oferta.schema.json")
RESERVA = _ejemplo("reservas.reserva.confirmada.schema.json")
OCUPACION = _ejemplo("analitica.zona.ocupacion_actualizada.schema.json")


def sobre(tipo: str, datos: dict, **cambios) -> bytes:
    """Mismo formato que publica la plantilla común (comun.eventos.SobreEvento.model_dump_json)."""
    s = {
        "evento_id": str(uuid.uuid4()),
        "tipo": tipo,
        "version": 1,
        "ocurrido_en": "2026-11-16T15:00:00.123456+00:00",
        "correlation_id": "c0rr-1",
        "datos": datos,
    }
    s.update(cambios)
    return json.dumps(s).encode("utf-8")


@pytest.fixture
def entorno():
    ofertas, zonas, eventos = OfertasEnMemoria(), ZonasEnMemoria(), EventosProcesadosEnMemoria()

    def unidad():
        return UnidadDeTrabajoEnMemoria(ofertas, zonas, eventos)

    manejadores = ManejadoresEventos(
        ofertas=ProcesarOfertaActualizada(unidad),
        reservas=ProcesarReservaConfirmada(unidad),
        ocupacion=ProcesarOcupacionZona(unidad),
    )
    return manejadores, ofertas, zonas


# --- camino feliz ------------------------------------------------------------------------


def test_oferta_publicada_crea_la_proyeccion(entorno):
    manejadores, ofertas, _ = entorno
    assert procesar_mensaje(sobre("catalogo.oferta.publicada", OFERTA), manejadores) == "procesado"
    o = ofertas.obtener(OFERTA["oferta_id"])
    assert o.zona_id == OFERTA["zona_id"]
    assert o.categorias == frozenset(OFERTA["categorias"])
    assert o.activa is True


def test_oferta_retirada_queda_inactiva_aunque_diga_activa_true(entorno):
    manejadores, ofertas, _ = entorno
    procesar_mensaje(sobre("catalogo.oferta.retirada", {**OFERTA, "activa": True}), manejadores)
    assert ofertas.obtener(OFERTA["oferta_id"]).activa is False


def test_reserva_confirmada_suma_popularidad(entorno):
    manejadores, ofertas, _ = entorno
    procesar_mensaje(sobre("catalogo.oferta.publicada", OFERTA), manejadores)
    assert procesar_mensaje(sobre("reservas.reserva.confirmada", RESERVA), manejadores) == "procesado"
    assert ofertas.obtener(RESERVA["oferta_id"]).reservas_confirmadas == 1


def test_reserva_tal_como_la_publica_el_servicio_reservas(entorno):
    """Copia del payload de reservas/aplicacion/casos_uso.py: total llega como float."""
    manejadores, ofertas, _ = entorno
    procesar_mensaje(sobre("catalogo.oferta.publicada", OFERTA), manejadores)
    datos = {
        "reserva_id": "SMT-AB12CD",
        "oferta_id": OFERTA["oferta_id"],
        "zona_id": OFERTA["zona_id"],
        "personas": 3,
        "fecha_servicio": "2026-12-20",
        "total": 360000.0,
        "moneda": "COP",
    }
    assert procesar_mensaje(sobre("reservas.reserva.confirmada", datos), manejadores) == "procesado"
    assert ofertas.obtener(OFERTA["oferta_id"]).reservas_confirmadas == 1


def test_ocupacion_de_zona_se_guarda(entorno):
    manejadores, _, zonas = entorno
    procesar_mensaje(sobre("analitica.zona.ocupacion_actualizada", OCUPACION), manejadores)
    assert zonas.obtener(OCUPACION["zona_id"]).ocupacion == pytest.approx(OCUPACION["ocupacion"])


def test_el_mismo_evento_dos_veces_cuenta_una(entorno):
    manejadores, ofertas, _ = entorno
    procesar_mensaje(sobre("catalogo.oferta.publicada", OFERTA), manejadores)
    mensaje = sobre("reservas.reserva.confirmada", RESERVA)
    assert procesar_mensaje(mensaje, manejadores) == "procesado"
    assert procesar_mensaje(mensaje, manejadores) == "repetido"
    assert ofertas.obtener(RESERVA["oferta_id"]).reservas_confirmadas == 1


def test_tipo_que_ia_no_usa_se_ignora_sin_error(entorno):
    manejadores, _, _ = entorno
    assert procesar_mensaje(sobre("reservas.notificacion.solicitada", {}), manejadores) == "ignorado"


def test_suscripciones_cubren_los_tres_productores():
    assert set(SUSCRIPCIONES) == {
        "catalogo.oferta.*",
        "reservas.reserva.confirmada",
        "analitica.zona.ocupacion_actualizada",
    }


# --- mensajes que no cumplen el contrato → cola de errores --------------------------------


@pytest.mark.parametrize(
    "cuerpo",
    [
        pytest.param(b"no soy json", id="no-json"),
        pytest.param(b"[1, 2]", id="no-es-objeto"),
        pytest.param(sobre("reservas.reserva.confirmada", RESERVA, evento_id="123"), id="evento_id-no-uuid"),
        pytest.param(sobre("Reservas.Confirmada", RESERVA), id="tipo-mal-formado"),
        pytest.param(sobre("reservas.reserva.confirmada", RESERVA, version=2), id="version-no-soportada"),
        pytest.param(sobre("reservas.reserva.confirmada", RESERVA, version=0), id="version-cero"),
        pytest.param(sobre("reservas.reserva.confirmada", RESERVA, ocurrido_en="ayer"), id="fecha-invalida"),
        pytest.param(sobre("reservas.reserva.confirmada", RESERVA, extra=1), id="campo-de-mas-en-sobre"),
        pytest.param(sobre("reservas.reserva.confirmada", []), id="datos-no-objeto"),
        pytest.param(sobre("reservas.reserva.confirmada", {**RESERVA, "moneda": "USD"}), id="moneda"),
        pytest.param(sobre("reservas.reserva.confirmada", {**RESERVA, "personas": 0}), id="personas-0"),
        pytest.param(
            sobre("reservas.reserva.confirmada", {k: v for k, v in RESERVA.items() if k != "oferta_id"}),
            id="sin-oferta_id",
        ),
        pytest.param(sobre("catalogo.oferta.publicada", {**OFERTA, "categorias": []}), id="sin-categorias"),
        pytest.param(
            sobre("catalogo.oferta.publicada", {**OFERTA, "calificacion_promedio": 7}), id="nota-fuera-de-rango"
        ),
        pytest.param(sobre("catalogo.oferta.publicada", {**OFERTA, "activa": "si"}), id="activa-no-bool"),
        pytest.param(
            sobre("analitica.zona.ocupacion_actualizada", {**OCUPACION, "medido_en": "2026-11-14T08:00:00"}),
            id="fecha-sin-zona-horaria",
        ),
    ],
)
def test_mensaje_invalido_se_rechaza_sin_tocar_nada(entorno, cuerpo):
    manejadores, ofertas, zonas = entorno
    with pytest.raises(MensajeInvalido):
        procesar_mensaje(cuerpo, manejadores)
    assert ofertas.listar_activas() == [] and zonas.obtener(OCUPACION["zona_id"]) is None


def test_correlation_id_puede_faltar(entorno):
    manejadores, _, _ = entorno
    s = json.loads(sobre("analitica.zona.ocupacion_actualizada", OCUPACION))
    del s["correlation_id"]
    assert procesar_mensaje(json.dumps(s), manejadores) == "procesado"


# --- /health/ready: RabbitMQ se informa pero no saca al servicio de la rotación -----------


class _Dep(ComprobacionSalud):
    def __init__(self, nombre: str, ok: bool, critica: bool) -> None:
        self.nombre, self._ok, self.critica = nombre, ok, critica

    def disponible(self) -> bool:
        return self._ok


def test_dependencia_no_critica_caida_no_quita_el_listo():
    estado = ConsultarSalud(
        [_Dep("base_de_datos", True, True), _Dep("rabbitmq", False, False)]
    ).ejecutar()
    assert estado.listo is True
    assert estado.dependencias == {"base_de_datos": True, "rabbitmq": False}


def test_dependencia_critica_caida_si_quita_el_listo():
    estado = ConsultarSalud(
        [_Dep("base_de_datos", False, True), _Dep("rabbitmq", True, False)]
    ).ejecutar()
    assert estado.listo is False
