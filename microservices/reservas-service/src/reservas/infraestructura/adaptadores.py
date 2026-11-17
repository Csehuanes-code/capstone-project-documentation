"""Adaptadores de salida: Catálogo (HTTP), pasarela de pagos (simulada) y correo (SMTP)."""

from datetime import date
from decimal import Decimal, InvalidOperation
from email.message import EmailMessage
import logging
import smtplib
import threading
import time
from typing import Any
import uuid

import httpx

from reservas.aplicacion.puertos import (
    CondicionesOfertaPort,
    NotificadorPort,
    PagoPort,
    ResultadoCobro,
)
from reservas.dominio.entidades import (
    CondicionesOferta,
    EstadoPago,
    Notificacion,
    PoliticaCancelacionCopia,
)
from reservas.dominio.excepciones import (
    OfertaNoDisponibleError,
    ServicioCatalogoNoDisponibleError,
)

log = logging.getLogger("reservas.adaptadores")

# Política de la plataforma cuando el prestador no definió una (Catálogo envía null):
# reembolso total hasta 24 h antes; después, sin reembolso.
POLITICA_PLATAFORMA = PoliticaCancelacionCopia(
    horas_reembolso_total=24, horas_reembolso_parcial=0, porcentaje_reembolso_parcial=0
)


# --- Catálogo -----------------------------------------------------------------------------

# Ofertas de demostración (ids de contratos/vocabulario.json, los mismos de IA). Solo se usan
# cuando CATALOGO_URL está vacío, para probar Reservas sin levantar Catálogo.
OFERTAS_DEMO: dict[str, dict[str, Any]] = {
    "minca-cascadas": {"nombre": "Tour cascadas de Minca", "zona_id": "minca", "tarifa": "120000",
                       "prestador_nombre": "Guías Sierra Viva", "prestador_contacto": "300 000 0000",
                       "punto_encuentro": "Parque principal de Minca"},
    "pueblito-caminata": {"nombre": "Caminata Pueblito", "zona_id": "tayrona", "tarifa": "95000",
                          "prestador_nombre": "Tayrona EcoTours", "prestador_contacto": "300 111 2233",
                          "punto_encuentro": "Entrada El Zaino - Parque Tayrona"},
    "cocina-caribena": {"nombre": "Taller de cocina caribeña", "zona_id": "centro", "tarifa": "80000",
                        "prestador_nombre": "Sabores Samarios", "prestador_contacto": "300 222 3344",
                        "punto_encuentro": "Plaza de San Francisco, Centro Histórico"},
    "museo-oro": {"nombre": "Visita guiada Museo del Oro Tairona", "zona_id": "centro", "tarifa": "45000",
                  "prestador_nombre": "Cultura Viva Santa Marta", "prestador_contacto": "300 333 4455",
                  "punto_encuentro": "Casa de la Aduana, Parque Bolívar"},
    "playa-cristal": {"nombre": "Excursión sostenible a Playa Cristal", "zona_id": "tayrona",
                      "tarifa": "135000", "prestador_nombre": "Operadora Mar Azul",
                      "prestador_contacto": "300 444 5566", "punto_encuentro": "Muelle de Neguanje"},
    "sendero-naranjos": {"nombre": "Sendero Los Naranjos", "zona_id": "los-naranjos", "tarifa": "75000",
                         "prestador_nombre": "Tayrona EcoTours", "prestador_contacto": "300 111 2233",
                         "punto_encuentro": "Puente Río Piedras, Los Naranjos"},
    "taganga-buceo": {"nombre": "Bautismo de buceo en Taganga", "zona_id": "taganga", "tarifa": "180000",
                      "prestador_nombre": "Taganga Dive Center", "prestador_contacto": "300 555 6677",
                      "punto_encuentro": "Camellón de Taganga frente al muelle"},
}

# Prestador dueño de cada oferta de demostración (para sembrar franjas y proyecciones).
PRESTADORES_DEMO = {
    "minca-cascadas": "prest-guias-sierra-viva",
    "pueblito-caminata": "prest-tayrona-eco",
    "cocina-caribena": "prest-sabores-samarios",
    "museo-oro": "prest-cultura-viva",
    "playa-cristal": "prest-mar-azul",
    "sendero-naranjos": "prest-tayrona-eco",
    "taganga-buceo": "prest-taganga-dive",
}


class CircuitBreaker:
    """Circuit breaker simple (cerrado → abierto → semiabierto) y seguro entre hilos.

    Tras `umbral_fallos` fallos seguidos se abre y rechaza al instante durante
    `segundos_recuperacion`; luego deja pasar una prueba (semiabierto).
    """

    def __init__(self, umbral_fallos: int = 3, segundos_recuperacion: float = 15.0):
        self.umbral_fallos = umbral_fallos
        self.segundos_recuperacion = segundos_recuperacion
        self.fallos_consecutivos = 0
        self.abierto_hasta = 0.0
        self._lock = threading.Lock()

    @property
    def abierto(self) -> bool:
        with self._lock:
            return (self.fallos_consecutivos >= self.umbral_fallos
                    and time.monotonic() < self.abierto_hasta)

    def permitir(self) -> bool:
        return not self.abierto

    def registrar_exito(self) -> None:
        with self._lock:
            self.fallos_consecutivos = 0
            self.abierto_hasta = 0.0

    def registrar_fallo(self) -> None:
        with self._lock:
            self.fallos_consecutivos += 1
            if self.fallos_consecutivos >= self.umbral_fallos:
                self.abierto_hasta = time.monotonic() + self.segundos_recuperacion


def _decimal(valor: Any, campo: str) -> Decimal:
    try:
        return Decimal(str(valor))
    except (InvalidOperation, TypeError, ValueError):
        raise ServicioCatalogoNoDisponibleError(f"Catálogo envió un {campo} inválido.") from None


def condiciones_desde_respuesta_catalogo(payload: dict[str, Any]) -> CondicionesOferta:
    """Traduce la respuesta REAL de Catálogo (catalog_service.api.schemas.OfertaCondicionesResponse):

    {oferta_id, nombre_es, nombre_en, estado, activa, zona_id,
     tarifa_vigente: {precio_por_persona, moneda, temporada} | null,
     politica_cancelacion: {horas_reembolso_total, horas_reembolso_parcial,
                            porcentaje_reembolso_parcial} | null}
    Campos opcionales que se usan si Catálogo los agrega: prestador_nombre, prestador_contacto,
    punto_encuentro.
    """
    try:
        tarifa = payload.get("tarifa_vigente")
        if not tarifa:
            raise OfertaNoDisponibleError("La oferta no tiene tarifa vigente para esa fecha.")
        pol = payload.get("politica_cancelacion")
        politica = (
            PoliticaCancelacionCopia(
                horas_reembolso_total=int(pol["horas_reembolso_total"]),
                horas_reembolso_parcial=int(pol["horas_reembolso_parcial"]),
                porcentaje_reembolso_parcial=int(pol["porcentaje_reembolso_parcial"]),
            )
            if pol
            else POLITICA_PLATAFORMA
        )
        return CondicionesOferta(
            oferta_id=str(payload["oferta_id"]),
            nombre_oferta=str(payload.get("nombre_es") or payload.get("nombre_en") or payload["oferta_id"]),
            zona_id=str(payload["zona_id"]),
            activa=bool(payload["activa"]),
            tarifa_por_persona=_decimal(tarifa["precio_por_persona"], "precio"),
            moneda=str(tarifa.get("moneda") or "COP"),
            politica_cancelacion=politica,
            prestador_nombre=str(payload.get("prestador_nombre") or ""),
            prestador_contacto=str(payload.get("prestador_contacto") or ""),
            punto_encuentro=str(payload.get("punto_encuentro") or ""),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ServicioCatalogoNoDisponibleError(f"Respuesta de Catálogo inesperada: {exc}") from exc


class CatalogoHttpClient(CondicionesOfertaPort):
    """GET {CATALOGO_URL}/api/v1/catalogo/ofertas/{id}/condiciones con timeout de 1 s y
    circuit breaker (sección 4.2). Si CATALOGO_URL está vacío usa OFERTAS_DEMO."""

    RUTA = "/api/v1/catalogo/ofertas/{oferta_id}/condiciones"

    def __init__(
        self,
        catalogo_url: str = "",
        timeout_segundos: float = 1.0,
        circuit_breaker: CircuitBreaker | None = None,
        transporte: httpx.BaseTransport | None = None,
    ):
        self.catalogo_url = catalogo_url.rstrip("/")
        self.timeout_segundos = timeout_segundos
        self.cb = circuit_breaker or CircuitBreaker()
        self._transporte = transporte  # solo pruebas (httpx.MockTransport)

    def obtener_condiciones(self, oferta_id: str, fecha: date | None = None) -> CondicionesOferta:
        if not self.catalogo_url:
            return self._demo(oferta_id)
        if not self.cb.permitir():
            raise ServicioCatalogoNoDisponibleError(
                "Catálogo no está disponible en este momento (circuit breaker abierto)."
            )
        url = self.catalogo_url + self.RUTA.format(oferta_id=oferta_id)
        params = {"fecha": fecha.isoformat()} if fecha else None
        try:
            with httpx.Client(timeout=self.timeout_segundos, transport=self._transporte) as client:
                resp = client.get(url, params=params)
        except httpx.HTTPError as exc:  # timeout o fallo de red
            self.cb.registrar_fallo()
            raise ServicioCatalogoNoDisponibleError(
                f"Catálogo no respondió en {self.timeout_segundos} s."
            ) from exc

        if resp.status_code >= 500:
            self.cb.registrar_fallo()
            raise ServicioCatalogoNoDisponibleError(f"Catálogo respondió con error {resp.status_code}.")
        self.cb.registrar_exito()  # Catálogo está vivo, aunque la oferta no exista
        if resp.status_code in (404, 422):
            raise OfertaNoDisponibleError(f"La oferta '{oferta_id}' no existe en Catálogo.")
        if resp.status_code != 200:
            raise ServicioCatalogoNoDisponibleError(f"Catálogo respondió {resp.status_code}.")
        try:
            payload = resp.json()
        except ValueError as exc:
            raise ServicioCatalogoNoDisponibleError("Catálogo envió una respuesta que no es JSON.") from exc
        return condiciones_desde_respuesta_catalogo(payload)

    @staticmethod
    def _demo(oferta_id: str) -> CondicionesOferta:
        data = OFERTAS_DEMO.get(oferta_id)
        if data is None:
            raise OfertaNoDisponibleError(f"La oferta '{oferta_id}' no existe en Catálogo.")
        return CondicionesOferta(
            oferta_id=oferta_id,
            nombre_oferta=data["nombre"],
            zona_id=data["zona_id"],
            activa=True,
            tarifa_por_persona=Decimal(data["tarifa"]),
            moneda="COP",
            politica_cancelacion=PoliticaCancelacionCopia(
                horas_reembolso_total=48, horas_reembolso_parcial=24, porcentaje_reembolso_parcial=50
            ),
            prestador_nombre=data["prestador_nombre"],
            prestador_contacto=data["prestador_contacto"],
            punto_encuentro=data["punto_encuentro"],
        )


# --- Pagos ---------------------------------------------------------------------------------


class PagoSimuladoAdapter(PagoPort):
    """Pasarela simulada (CU-16, ADR-02). No guarda datos de tarjeta (PCI-DSS delegado).

    Tarjetas de prueba (o datos_pago["simular"]):
      termina en 0002 / "rechazado"      → RECHAZADO
      termina en 9999 / "timeout"        → TIEMPO_AGOTADO tras `max_reintentos` intentos
      termina en 0019 / "sin_reembolso"  → cobro APROBADO, pero sus reembolsos fallan
                                           (para probar CU-14 3a y CU-17 4a)
      cualquier otra                     → APROBADO
    """

    PREFIJO_SIN_REEMBOLSO = "SIM-OKNR-"

    def __init__(self, timeout_segundos: float = 5.0, max_reintentos: int = 3):
        self.timeout_segundos = timeout_segundos
        self.max_reintentos = max_reintentos

    def cobrar(
        self, *, reserva_id: str, monto: Decimal, moneda: str, metodo: str, datos_pago: dict[str, Any]
    ) -> ResultadoCobro:
        tarjeta = str(datos_pago.get("numero_tarjeta", "4111111111111111")).replace(" ", "")
        simular = str(datos_pago.get("simular", "")).lower()

        if simular == "rechazado" or tarjeta.endswith("0002"):
            return ResultadoCobro(EstadoPago.RECHAZADO, f"SIM-REJ-{uuid.uuid4().hex[:8].upper()}",
                                  "Tarjeta rechazada por el emisor.")
        if simular == "timeout" or tarjeta.endswith("9999"):
            for intento in range(1, self.max_reintentos + 1):
                log.warning("Intento %d/%d sin respuesta cobrando la reserva %s",
                            intento, self.max_reintentos, reserva_id)
            return ResultadoCobro(
                EstadoPago.TIEMPO_AGOTADO, f"SIM-TMO-{uuid.uuid4().hex[:8].upper()}",
                f"Sin respuesta en {self.timeout_segundos} s tras {self.max_reintentos} intentos.",
            )
        prefijo = self.PREFIJO_SIN_REEMBOLSO if (simular == "sin_reembolso" or tarjeta.endswith("0019")) else "SIM-OK-"
        return ResultadoCobro(EstadoPago.APROBADO, f"{prefijo}{uuid.uuid4().hex[:10].upper()}",
                              "Pago aprobado en pasarela simulada.")

    def reembolsar(
        self, *, reserva_id: str, referencia_cobro: str, monto: Decimal, moneda: str
    ) -> ResultadoCobro:
        if referencia_cobro.startswith(self.PREFIJO_SIN_REEMBOLSO) or monto <= 0:
            return ResultadoCobro(EstadoPago.RECHAZADO, "", "La pasarela rechazó el reembolso.")
        return ResultadoCobro(EstadoPago.APROBADO, f"SIM-REF-{uuid.uuid4().hex[:10].upper()}",
                              "Reembolso aprobado en pasarela simulada.")


class PagoSandboxAdapter(PagoPort):
    """Lugar para la pasarela real (sandbox). Demuestra ADR-02: cambiarla solo toca main.py."""

    def __init__(self, endpoint_url: str = "", api_key: str = ""):
        self.endpoint_url = endpoint_url
        self.api_key = api_key

    def cobrar(self, *, reserva_id: str, monto: Decimal, moneda: str, metodo: str,
               datos_pago: dict[str, Any]) -> ResultadoCobro:
        raise NotImplementedError("PagoSandboxAdapter: integración con pasarela real pendiente.")

    def reembolsar(self, *, reserva_id: str, referencia_cobro: str, monto: Decimal,
                   moneda: str) -> ResultadoCobro:
        raise NotImplementedError("PagoSandboxAdapter: integración con pasarela real pendiente.")


# --- Correo -------------------------------------------------------------------------------


class CorreoSmtpAdapter(NotificadorPort):
    """Envía correos por SMTP (Mailpit en local: http://localhost:8025)."""

    def __init__(self, host: str = "mailpit", port: int = 1025,
                 remitente: str = "reservas@turismosantamarta.co"):
        self.host = host
        self.port = port
        self.remitente = remitente

    def enviar_correo(self, notificacion: Notificacion) -> None:
        msg = EmailMessage()
        msg["Subject"] = notificacion.asunto
        msg["From"] = self.remitente
        msg["To"] = notificacion.correo_destino
        msg.set_content(notificacion.cuerpo_texto)
        with smtplib.SMTP(self.host, self.port, timeout=3) as smtp:
            smtp.send_message(msg)
        log.info("Correo enviado (notificación %s)", notificacion.id)
