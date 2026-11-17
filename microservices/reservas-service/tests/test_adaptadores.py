from datetime import date

import httpx
import pytest

from reservas.dominio.excepciones import OfertaNoDisponibleError, ServicioCatalogoNoDisponibleError
from reservas.infraestructura.adaptadores import CatalogoHttpClient, CircuitBreaker


RESPUESTA_CATALOGO = {
    "oferta_id": "minca-cascadas",
    "nombre_es": "Cascadas de Minca",
    "nombre_en": "Minca Waterfalls",
    "estado": "publicada",
    "activa": True,
    "zona_id": "minca",
    "tarifa_vigente": {
        "precio_por_persona": 120000,
        "moneda": "COP",
        "temporada": "alta",
    },
    "politica_cancelacion": {
        "horas_reembolso_total": 48,
        "horas_reembolso_parcial": 24,
        "porcentaje_reembolso_parcial": 50,
    },
}


def test_cliente_parsea_respuesta_real_de_catalogo_y_envia_fecha():
    solicitudes = []

    def responder(request: httpx.Request) -> httpx.Response:
        solicitudes.append(request)
        return httpx.Response(200, json=RESPUESTA_CATALOGO)

    transporte = httpx.MockTransport(responder)
    cliente = CatalogoHttpClient(
        "http://catalogo.local", transporte=transporte
    )

    condiciones = cliente.obtener_condiciones("minca-cascadas", date(2026, 12, 1))

    assert condiciones.nombre_oferta == "Cascadas de Minca"
    assert condiciones.tarifa_por_persona == 120000
    assert condiciones.politica_cancelacion.horas_reembolso_total == 48
    assert solicitudes[0].url.params["fecha"] == "2026-12-01"


@pytest.mark.parametrize("estado", [404, 422])
def test_cliente_traduce_no_encontrado_o_no_disponible(estado):
    cliente = CatalogoHttpClient(
        "http://catalogo.local",
        transporte=httpx.MockTransport(lambda _request: httpx.Response(estado)),
    )

    with pytest.raises(OfertaNoDisponibleError):
        cliente.obtener_condiciones("no-existe")


def test_error_500_abre_circuit_breaker():
    breaker = CircuitBreaker(umbral_fallos=2, segundos_recuperacion=60)
    cliente = CatalogoHttpClient(
        "http://catalogo.local",
        circuit_breaker=breaker,
        transporte=httpx.MockTransport(lambda _request: httpx.Response(500)),
    )

    for _ in range(2):
        with pytest.raises(ServicioCatalogoNoDisponibleError):
            cliente.obtener_condiciones("minca-cascadas")
    assert breaker.abierto
    with pytest.raises(ServicioCatalogoNoDisponibleError, match="circuit breaker"):
        cliente.obtener_condiciones("minca-cascadas")


def test_timeout_se_convierte_en_error_de_catalogo():
    def expirar(_request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("sin respuesta")

    cliente = CatalogoHttpClient(
        "http://catalogo.local", transporte=httpx.MockTransport(expirar)
    )

    with pytest.raises(ServicioCatalogoNoDisponibleError, match="no respondió"):
        cliente.obtener_condiciones("minca-cascadas")
