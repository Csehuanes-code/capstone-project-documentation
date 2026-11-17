"""Domain-level exceptions for the Catálogo bounded context.

These exceptions represent business-rule violations and are raised by
domain entities and pure rule functions.  They carry NO framework
dependencies (no FastAPI, no SQLAlchemy).
"""

from __future__ import annotations

from uuid import UUID

# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------


class DomainError(Exception):
    """Root exception for all domain errors."""

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        self.code = code or self.__class__.__name__


# ---------------------------------------------------------------------------
# Entity-not-found
# ---------------------------------------------------------------------------


class EntityNotFoundError(DomainError):
    """Raised when a referenced entity does not exist."""

    def __init__(self, entity_type: str, entity_id: UUID | str) -> None:
        super().__init__(
            f"{entity_type} con id={entity_id} no encontrado.",
            code="ENTITY_NOT_FOUND",
        )
        self.entity_type = entity_type
        self.entity_id = entity_id


# ---------------------------------------------------------------------------
# Vocabulary / canonical values
# ---------------------------------------------------------------------------


class CategoriaNoCanonica(DomainError):
    """A provided interest category is not in the canonical vocabulary."""

    def __init__(self, categorias: list[str]) -> None:
        super().__init__(
            f"Categorías no canónicas: {categorias}",
            code="CATEGORIA_NO_CANONICA",
        )
        self.categorias = categorias


class ZonaNoCanonica(DomainError):
    """A provided zone code is not in the canonical vocabulary."""

    def __init__(self, zona: str) -> None:
        super().__init__(
            f"Zona no canónica: {zona!r}",
            code="ZONA_NO_CANONICA",
        )
        self.zona = zona


# ---------------------------------------------------------------------------
# Provider / offers
# ---------------------------------------------------------------------------


class PrestadorNoVerificado(DomainError):
    """A provider attempted a restricted action without being verified."""

    def __init__(self, prestador_id: UUID) -> None:
        super().__init__(
            f"El prestador {prestador_id} no está verificado.",
            code="PRESTADOR_NO_VERIFICADO",
        )
        self.prestador_id = prestador_id


class EstadoOfertaInvalido(DomainError):
    """An offer state transition is not allowed."""

    def __init__(self, actual: str, deseado: str) -> None:
        super().__init__(
            f"Transición de estado inválida: {actual} → {deseado}",
            code="ESTADO_OFERTA_INVALIDO",
        )
        self.actual = actual
        self.deseado = deseado


# ---------------------------------------------------------------------------
# Reviews
# ---------------------------------------------------------------------------


class CalificacionDuplicada(DomainError):
    """A review already exists for the given reservation."""

    def __init__(self, reserva_id: UUID) -> None:
        super().__init__(
            f"Ya existe una calificación para la reserva {reserva_id}.",
            code="CALIFICACION_DUPLICADA",
        )
        self.reserva_id = reserva_id


class PuntajeInvalido(DomainError):
    """Review score is outside the 1-5 range."""

    def __init__(self, puntaje: int) -> None:
        super().__init__(
            f"El puntaje debe estar entre 1 y 5, recibido: {puntaje}",
            code="PUNTAJE_INVALIDO",
        )
        self.puntaje = puntaje


# ---------------------------------------------------------------------------
# Pricing / tariffs
# ---------------------------------------------------------------------------


class TarifaSolapada(DomainError):
    """Two tariffs for the same season overlap in date range."""

    def __init__(self, temporada: str, rango_existente: str, rango_nuevo: str) -> None:
        super().__init__(
            f"La tarifa de temporada {temporada!r} se solapa: {rango_existente} ∩ {rango_nuevo}",
            code="TARIFA_SOLAPADA",
        )
        self.temporada = temporada
        self.rango_existente = rango_existente
        self.rango_nuevo = rango_nuevo


# ---------------------------------------------------------------------------
# Attributes schema validation
# ---------------------------------------------------------------------------


class AtributosInvalidos(DomainError):
    """The offer attributes JSON does not match its service-type schema."""

    def __init__(self, errores: list[str]) -> None:
        super().__init__(
            f"Atributos inválidos: {errores}",
            code="ATRIBUTOS_INVALIDOS",
        )
        self.errores = errores


# ---------------------------------------------------------------------------
# Sustainability index
# ---------------------------------------------------------------------------


class IndiceSostenibilidadInvalido(DomainError):
    """The sustainability index is outside the [0, 1] range."""

    def __init__(self, valor: float) -> None:
        super().__init__(
            f"El índice de sostenibilidad debe estar entre 0.0 y 1.0, recibido: {valor}",
            code="INDICE_SOSTENIBILIDAD_INVALIDO",
        )
        self.valor = valor


# ---------------------------------------------------------------------------
# Batch synchronisation
# ---------------------------------------------------------------------------


class LoteSincronizacionError(DomainError):
    """A batch synchronisation operation failed."""

    def __init__(self, message: str) -> None:
        super().__init__(message, code="LOTE_SINCRONIZACION_ERROR")
