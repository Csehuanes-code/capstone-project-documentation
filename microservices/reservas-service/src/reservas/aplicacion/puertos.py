"""Puertos de salida (ABC) que la infraestructura debe implementar."""

from abc import ABC, abstractmethod
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from reservas.dominio.entidades import CondicionesOferta, EstadoPago, Notificacion
from reservas.dominio.repositorios import (
    DisputaRepository,
    FranjaRepository,
    ListaEsperaRepository,
    NotificacionRepository,
    PagoRepository,
    ProyeccionOfertaRepository,
    ReservaRepository,
)


@dataclass(frozen=True)
class ResultadoCobro:
    estado: EstadoPago
    referencia_pasarela: str
    detalle: str


class CondicionesOfertaPort(ABC):
    """Puerto de salida hacia Catálogo: GET /api/v1/catalogo/ofertas/{id}/condiciones."""

    @abstractmethod
    def obtener_condiciones(self, oferta_id: str, fecha: Any = None) -> CondicionesOferta:
        """Lanza ServicioCatalogoNoDisponibleError (Catálogo caído) u OfertaNoDisponibleError."""


class PagoPort(ABC):
    """Puerto hacia la pasarela de pagos (ADR-02: PagoSimuladoAdapter / PagoSandboxAdapter).

    Cambiar de pasarela es cambiar el adaptador en main.py: ni el dominio ni los casos de uso
    se modifican.
    """

    @abstractmethod
    def cobrar(
        self,
        *,
        reserva_id: str,
        monto: Decimal,
        moneda: str,
        metodo: str,
        datos_pago: dict[str, Any],
    ) -> ResultadoCobro: ...

    @abstractmethod
    def reembolsar(
        self,
        *,
        reserva_id: str,
        referencia_cobro: str,
        monto: Decimal,
        moneda: str,
    ) -> ResultadoCobro:
        """Devuelve APROBADO si la pasarela reembolsó; RECHAZADO o TIEMPO_AGOTADO si no."""


class NotificadorPort(ABC):
    """Puerto de salida para envío de correos (Mailpit en local, SMTP en producción)."""

    @abstractmethod
    def enviar_correo(self, notificacion: Notificacion) -> None: ...


class Reloj(ABC):
    @abstractmethod
    def ahora(self) -> datetime: ...


class UnitOfWork(AbstractContextManager["UnitOfWork"], ABC):
    """Unidad de trabajo transaccional: repositorios y outbox en la MISMA transacción.

    Si no se llama a commit() (o hay una excepción) todo se revierte al salir del bloque.
    """

    franjas: FranjaRepository
    reservas: ReservaRepository
    pagos: PagoRepository
    notificaciones: NotificacionRepository
    lista_espera: ListaEsperaRepository
    disputas: DisputaRepository
    proyecciones: ProyeccionOfertaRepository

    @abstractmethod
    def registrar_evento_outbox(self, tipo: str, datos: dict[str, Any], version: int = 1) -> str:
        """Inserta un evento en la tabla outbox en la misma transacción y retorna su evento_id."""

    @abstractmethod
    def commit(self) -> None: ...

    @abstractmethod
    def rollback(self) -> None: ...
