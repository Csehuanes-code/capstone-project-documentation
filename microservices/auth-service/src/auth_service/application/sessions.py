"""Resultado de inicio de sesión entregado por la aplicación a la API."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class IssuedSession:
    access_token: str
    refresh_token: str
    access_expires_in: int
