"""Validación de los JWT que emite el servicio Auth (ADR-06).

Auth firma los tokens de acceso con ES256 (curva P-256) y su clave privada; cada servicio los
valida por su cuenta con la clave PÚBLICA, sin llamar a Auth en cada petición.

Se comprueba: firma ES256, emisor (`iss`), audiencia (`aud`), expiración (`exp`) y que el rol
(`rol`) sea uno de los tres de la plataforma. Claims que exige Auth: sub, rol, iss, aud, iat,
exp, jti (auth-service/src/auth_service/infrastructure/security.py).

La clave pública se configura de una de dos formas:
  - JWT_PUBLIC_KEY / JWT_PUBLIC_KEY_FILE: el PEM de la clave pública (recomendado: no depende
    de que Auth esté arriba).
  - JWT_JWKS_URL: la URL del endpoint /jwks de Auth (se descarga y se guarda en caché).
Si no hay ninguna configurada, ningún token es válido (falla cerrado): las rutas protegidas
responden 401.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any
from uuid import UUID

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from catalog_service.infrastructure.config import settings

log = logging.getLogger("catalog_service.security")

ROLES_PLATAFORMA = frozenset({"turista", "prestador", "administrador"})
CLAIMS_OBLIGATORIOS = ["sub", "rol", "iss", "aud", "iat", "exp", "jti"]


class TokenInvalido(Exception):
    """El token no se pudo validar (firma, emisor, audiencia, expiración o rol)."""


@dataclass(frozen=True)
class IdentidadToken:
    user_id: UUID
    rol: str


class VerificadorJwt:
    def __init__(
        self,
        issuer: str,
        audience: str,
        public_key_pem: str | None = None,
        jwks_url: str | None = None,
    ) -> None:
        if not issuer.strip() or not audience.strip():
            raise ValueError("JWT_ISSUER y JWT_AUDIENCE son obligatorios.")
        self._issuer = issuer
        self._audience = audience
        self._clave: ec.EllipticCurvePublicKey | None = None
        self._jwks: jwt.PyJWKClient | None = None
        if public_key_pem:
            clave = serialization.load_pem_public_key(public_key_pem.encode("utf-8"))
            if not isinstance(clave, ec.EllipticCurvePublicKey) or not isinstance(
                clave.curve, ec.SECP256R1
            ):
                raise ValueError("La clave pública debe ser EC P-256 (ES256).")
            self._clave = clave
        elif jwks_url:
            self._jwks = jwt.PyJWKClient(jwks_url, cache_keys=True, lifespan=300)
        else:
            raise ValueError("Configure JWT_PUBLIC_KEY, JWT_PUBLIC_KEY_FILE o JWT_JWKS_URL.")

    def verificar(self, token: str) -> IdentidadToken:
        try:
            clave: Any = self._clave
            if clave is None and self._jwks is not None:
                clave = self._jwks.get_signing_key_from_jwt(token).key
            claims = jwt.decode(
                token,
                clave,
                algorithms=["ES256"],
                issuer=self._issuer,
                audience=self._audience,
                options={"require": CLAIMS_OBLIGATORIOS},
            )
            rol = claims["rol"]
            if rol not in ROLES_PLATAFORMA:
                raise TokenInvalido(f"Rol desconocido: {rol!r}")
            return IdentidadToken(user_id=UUID(claims["sub"]), rol=rol)
        except TokenInvalido:
            raise
        except (jwt.PyJWTError, ValueError, TypeError, KeyError) as exc:
            raise TokenInvalido("El token de acceso no es válido.") from exc


@lru_cache(maxsize=1)
def obtener_verificador() -> VerificadorJwt | None:
    """Verificador construido desde la configuración.

    Devuelve None (y ninguna ruta protegida acepta tokens) si no hay clave configurada o si
    la configuración es inválida; en ese caso queda registrado en el log.
    """
    try:
        pem = settings.JWT_PUBLIC_KEY
        if not pem and settings.JWT_PUBLIC_KEY_FILE:
            pem = Path(settings.JWT_PUBLIC_KEY_FILE).read_text(encoding="utf-8")
        if not pem and not settings.JWT_JWKS_URL:
            log.warning("Sin clave pública de Auth configurada: las rutas protegidas darán 401.")
            return None
        return VerificadorJwt(
            issuer=settings.JWT_ISSUER,
            audience=settings.JWT_AUDIENCE,
            public_key_pem=pem or None,
            jwks_url=settings.JWT_JWKS_URL or None,
        )
    except (OSError, ValueError, TypeError) as exc:
        log.error("Configuración JWT inválida (las rutas protegidas darán 401): %s", exc)
        return None
