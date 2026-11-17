"""Repositorios abstractos (ABC). La infraestructura los implementa (infraestructura/sql/)."""

from abc import ABC, abstractmethod
from datetime import date, datetime

from reservas.dominio.entidades import (
    Disputa,
    EntradaListaEspera,
    EstadoDisputa,
    EstadoListaEspera,
    EstadoReserva,
    FranjaDisponibilidad,
    Notificacion,
    Pago,
    ProyeccionOfertaLocal,
    Reserva,
)


class FranjaRepository(ABC):
    @abstractmethod
    def guardar(self, franja: FranjaDisponibilidad) -> FranjaDisponibilidad: ...

    @abstractmethod
    def obtener_por_id(self, franja_id: str) -> FranjaDisponibilidad | None: ...

    @abstractmethod
    def buscar_disponibles(
        self,
        oferta_id: str,
        desde: date | None = None,
        hasta: date | None = None,
        personas: int = 1,
    ) -> list[FranjaDisponibilidad]:
        """Franjas con cupo_disponible >= personas, opcionalmente entre dos fechas (inclusive)."""

    @abstractmethod
    def bloquear_cupo_atomico(self, franja_id: str, personas: int) -> bool:
        """UPDATE ... SET cupo_disponible = cupo_disponible - :n WHERE id = :f AND cupo_disponible >= :n.

        Devuelve True si bloqueó y False si no había cupo. De dos peticiones simultáneas por el
        último cupo, solo una obtiene True (sección 3.2)."""

    @abstractmethod
    def devolver_cupo_atomico(self, franja_id: str, personas: int) -> None:
        """Suma el cupo de vuelta sin pasar de cupo_total."""


class ReservaRepository(ABC):
    @abstractmethod
    def obtener_por_id(self, reserva_id: str) -> Reserva | None: ...

    @abstractmethod
    def obtener_por_idempotencia(self, turista_id: str, clave_idempotencia: str) -> Reserva | None: ...

    @abstractmethod
    def listar_por_turista(self, turista_id: str) -> list[Reserva]: ...

    @abstractmethod
    def listar_por_prestador(self, prestador_id: str) -> list[Reserva]: ...

    @abstractmethod
    def guardar_nueva(self, reserva: Reserva) -> Reserva:
        """Lanza ClaveIdempotenciaDuplicadaError si (turista, clave) ya existe."""

    @abstractmethod
    def actualizar_si_estado(self, reserva: Reserva, estado_esperado: EstadoReserva) -> bool:
        """Guarda estado y fechas de la reserva SOLO si en la base sigue en `estado_esperado`.

        Es un UPDATE condicional atómico: evita que dos procesos cambien la misma reserva a la
        vez (doble cancelación, o el expirador y la confirmación del pago). Devuelve si guardó."""

    @abstractmethod
    def listar_pendientes_vencidas(self, corte: datetime) -> list[Reserva]: ...


class PagoRepository(ABC):
    @abstractmethod
    def guardar(self, pago: Pago) -> Pago: ...

    @abstractmethod
    def obtener_cobro(self, reserva_id: str) -> Pago | None:
        """El cobro aprobado de la reserva (no los reembolsos)."""

    @abstractmethod
    def listar_por_reserva(self, reserva_id: str) -> list[Pago]: ...


class NotificacionRepository(ABC):
    @abstractmethod
    def guardar(self, notificacion: Notificacion) -> Notificacion: ...

    @abstractmethod
    def marcar_enviada(self, notificacion_id: str) -> None: ...

    @abstractmethod
    def registrar_intento_fallido(self, notificacion_id: str) -> None: ...

    @abstractmethod
    def listar_pendientes(self, limite: int, max_intentos: int) -> list[Notificacion]: ...


class ListaEsperaRepository(ABC):
    @abstractmethod
    def guardar(self, entrada: EntradaListaEspera) -> EntradaListaEspera: ...

    @abstractmethod
    def actualizar_si_estado(self, entrada: EntradaListaEspera, estado_esperado: EstadoListaEspera) -> bool:
        """Guarda estado y plazo SOLO si en la base sigue en `estado_esperado` (UPDATE condicional).

        Evita que el expirador y la confirmación del turista actúen a la vez sobre la misma
        oferta (lo que liberaría un cupo ya usado)."""

    @abstractmethod
    def obtener_por_id(self, entrada_id: str) -> EntradaListaEspera | None: ...

    @abstractmethod
    def obtener_primera_esperando(self, franja_id: str) -> EntradaListaEspera | None:
        """La entrada más antigua en estado 'esperando' (orden estricto de llegada, CU-13)."""

    @abstractmethod
    def posicion(self, entrada: EntradaListaEspera) -> int:
        """1 + cuántos siguen esperando en esa franja desde antes (trazabilidad del orden)."""

    @abstractmethod
    def existe_activa(self, franja_id: str, turista_id: str) -> bool:
        """Si el turista ya está esperando u ofrecido en esa franja."""

    @abstractmethod
    def listar_ofertas_vencidas(self, ahora: datetime) -> list[EntradaListaEspera]: ...

    @abstractmethod
    def listar_por_turista(self, turista_id: str) -> list[EntradaListaEspera]: ...


class DisputaRepository(ABC):
    @abstractmethod
    def guardar(self, disputa: Disputa) -> Disputa: ...

    @abstractmethod
    def resolver_si_en_revision(self, disputa: Disputa) -> bool:
        """Guarda la resolución SOLO si en la base sigue 'en_revision' (UPDATE condicional)."""

    @abstractmethod
    def revertir_a_revision(self, disputa_id: str) -> None:
        """Deshace la resolución si el reembolso falló (CU-17 4a: gestión manual)."""

    @abstractmethod
    def obtener_por_id(self, disputa_id: str) -> Disputa | None: ...

    @abstractmethod
    def listar(self, estado: EstadoDisputa | None = None) -> list[Disputa]: ...

    @abstractmethod
    def existe_en_revision(self, reserva_id: str) -> bool: ...


class ProyeccionOfertaRepository(ABC):
    @abstractmethod
    def guardar_o_actualizar(self, proyeccion: ProyeccionOfertaLocal) -> None: ...

    @abstractmethod
    def obtener(self, oferta_id: str) -> ProyeccionOfertaLocal | None: ...
