"""Puertos de salida (ABC) que la infraestructura debe implementar."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from ia.dominio.repositorios import RepositorioOfertas, RepositorioZonas


class Reloj(ABC):
    @abstractmethod
    def ahora(self) -> datetime: ...


class ComprobacionSalud(ABC):
    """Una dependencia que se revisa en /health/ready (ej. la base de datos).

    critica=True: si falla, el servicio no está listo (503) y el balanceador deja de enviarle
    tráfico. critica=False: se informa, pero el servicio puede seguir atendiendo sin ella.
    """

    nombre: str
    critica: bool = True

    @abstractmethod
    def disponible(self) -> bool: ...


class RegistroEventosProcesados(ABC):
    """Tabla evento_procesado: hace idempotentes a los consumidores de eventos.

    Con PostgreSQL, el registro y el cambio de la proyección van en la misma transacción.
    """

    @abstractmethod
    def registrar_si_nuevo(self, evento_id: str) -> bool:
        """Devuelve True si el evento no se había procesado (y lo marca); False si es repetido."""


class UnidadDeTrabajo(ABC):
    """Agrupa varios cambios en una sola transacción: o se guardan todos, o ninguno.

    Uso:
        with uow:
            if uow.eventos.registrar_si_nuevo(evento_id):
                uow.ofertas.guardar(...)
                uow.commit()
    Si no se llama a commit() (o hay una excepción), todo se revierte al salir del bloque.
    """

    ofertas: RepositorioOfertas
    zonas: RepositorioZonas
    eventos: RegistroEventosProcesados

    def __enter__(self) -> "UnidadDeTrabajo":
        self._iniciar()
        self._confirmada = False
        return self

    def __exit__(self, tipo, valor, traza) -> None:
        try:
            if not self._confirmada:
                self.rollback()
        finally:
            self._cerrar()

    def commit(self) -> None:
        self._confirmar()
        self._confirmada = True

    @abstractmethod
    def _iniciar(self) -> None: ...

    @abstractmethod
    def _confirmar(self) -> None: ...

    @abstractmethod
    def rollback(self) -> None: ...

    @abstractmethod
    def _cerrar(self) -> None: ...
