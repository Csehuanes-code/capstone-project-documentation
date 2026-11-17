"""Value objects and enumerations for the Catálogo domain.

All values are immutable and use only stdlib imports.
Canonical vocabulary comes from vocabulario.json (ADR).
"""

from __future__ import annotations

import enum
from dataclasses import dataclass
from decimal import Decimal

# ---------------------------------------------------------------------------
# Enums – Canonical vocabulary
# ---------------------------------------------------------------------------


class CategoriaInteres(str, enum.Enum):
    """Canonical interest categories from vocabulario.json."""

    NATURALEZA = "naturaleza"
    CULTURA = "cultura"
    GASTRONOMIA = "gastronomia"
    HISTORIA = "historia"
    PLAYA = "playa"
    AVENTURA = "aventura"


class ZonaCodigo(str, enum.Enum):
    """Canonical zone codes from vocabulario.json."""

    MINCA = "minca"
    TAYRONA = "tayrona"
    CENTRO = "centro"
    LOS_NARANJOS = "los-naranjos"
    TAGANGA = "taganga"
    RODADERO = "rodadero"


# ---------------------------------------------------------------------------
# Enums – Domain states
# ---------------------------------------------------------------------------


class EstadoOferta(str, enum.Enum):
    """Publication lifecycle of an offer."""

    BORRADOR = "borrador"
    PUBLICADA = "publicada"
    OCULTA = "oculta"
    DADA_DE_BAJA = "dada_de_baja"


class Temporada(str, enum.Enum):
    """Season tiers for pricing."""

    BAJA = "baja"
    MEDIA = "media"
    ALTA = "alta"


class EstadoModeracion(str, enum.Enum):
    """Moderation status for user-generated content from data-model.md §3.2."""

    PUBLICADA = "publicada"
    EN_REVISION = "en_revision"
    OCULTA = "oculta"
    ELIMINADA = "eliminada"


class CategoriaPrestador(str, enum.Enum):
    """Provider category classification from data-model.md §3.2."""

    PEQUENO_MEDIANO = "pequeno_mediano"
    ESTABLECIDO = "establecido"


class TipoFuente(str, enum.Enum):
    """External data-source type."""

    API = "api"
    ARCHIVO = "archivo"


class EstadoLote(str, enum.Enum):
    """Batch synchronisation lifecycle from data-model.md §3.2."""

    RECIBIDO = "recibido"
    PROCESANDO = "procesando"
    COMPLETADO = "completado"
    FALLIDO = "fallido"


# ---------------------------------------------------------------------------
# Value Objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Dinero:
    """Monetary amount with currency (ISO 4217).

    Uses ``Decimal`` to avoid floating-point rounding issues.
    """

    cantidad: Decimal
    moneda: str = "COP"

    def __post_init__(self) -> None:
        if self.cantidad < Decimal(0):
            raise ValueError("La cantidad monetaria no puede ser negativa.")
        if len(self.moneda) != 3:
            raise ValueError(
                f"El código de moneda debe tener 3 caracteres, recibido: {self.moneda!r}"
            )
