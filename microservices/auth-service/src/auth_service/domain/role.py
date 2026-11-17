"""Roles de usuario acordes con ADR-06."""

from enum import StrEnum


class Role(StrEnum):
    TURISTA = "turista"
    PRESTADOR = "prestador"
    ADMINISTRADOR = "administrador"
