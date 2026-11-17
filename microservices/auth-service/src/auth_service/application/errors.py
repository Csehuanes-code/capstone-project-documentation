"""Errores de aplicación compartidos entre adaptadores y API."""


class TokenVerificationFailed(Exception):
    """La firma, vigencia o audiencia del token no se pudo validar."""


class InvalidRefreshToken(Exception):
    """Refresh token desconocido, vencido, revocado o ya rotado."""
