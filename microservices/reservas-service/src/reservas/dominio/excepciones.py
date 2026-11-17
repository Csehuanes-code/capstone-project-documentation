"""Excepciones de dominio puras (sin dependencias de frameworks HTTP ni ORM).

La capa api/ las traduce a códigos HTTP (app.py). Cualquier otra excepción es un error
inesperado y responde 500 sin exponer detalles internos.
"""


class ErrorDominio(Exception):
    """Clase base para errores de reglas de negocio."""


class CupoInsuficienteError(ErrorDominio):
    """No quedan cupos suficientes en la franja seleccionada (409).

    `disponibles` informa el máximo que sí se puede reservar (CU-12 3a) para ofrecer dividir
    la reserva o unirse a la lista de espera (CU-13).
    """

    def __init__(self, mensaje: str, disponibles: int | None = None):
        super().__init__(mensaje)
        self.disponibles = disponibles


class OfertaNoDisponibleError(ErrorDominio):
    """La oferta no existe, no está activa o no tiene tarifa vigente (409)."""


class TransicionEstadoInvalidaError(ErrorDominio):
    """El cambio de estado viola el ciclo de vida de la entidad (409)."""


class ReservaNoCancelableError(ErrorDominio):
    """La reserva no se puede cancelar en su estado actual o el servicio ya comenzó (409)."""


class ListaEsperaInvalidaError(ErrorDominio):
    """No se puede unir o usar la lista de espera (ej. aún hay cupo, ya está inscrito) (409)."""


class DisputaInvalidaError(ErrorDominio):
    """La disputa no cumple las reglas de CU-17 (422)."""


class AccesoDenegadoDominioError(ErrorDominio):
    """El usuario autenticado no es propietario ni tiene permiso sobre el recurso (403)."""


class RecursoNoEncontradoError(ErrorDominio):
    """La entidad solicitada no existe en Reservas (404)."""


class ServicioCatalogoNoDisponibleError(ErrorDominio):
    """El servicio Catálogo no respondió a tiempo o tiene el circuit breaker abierto (503)."""


class ReembolsoFallidoError(ErrorDominio):
    """La pasarela rechazó o no respondió un reembolso (502)."""


class ClaveIdempotenciaDuplicadaError(ErrorDominio):
    """Otra petición con la misma Idempotency-Key creó la reserva al mismo tiempo.

    La lanza el repositorio al chocar con la restricción única; el caso de uso responde con la
    reserva que ganó (misma respuesta, una sola reserva).
    """
