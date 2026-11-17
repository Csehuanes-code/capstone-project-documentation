"""Valida tokens ES256 emitidos por Auth (mismo contrato que Catálogo)."""

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
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from analitica.configuracion import config

log = logging.getLogger("analitica.seguridad")
bearer = HTTPBearer(auto_error=False)
ROLES = frozenset({"turista", "prestador", "administrador"})


@dataclass(frozen=True)
class Identidad:
    usuario_id: UUID
    rol: str


class TokenInvalido(ValueError):
    pass


class VerificadorJwt:
    def __init__(self) -> None:
        self._key: ec.EllipticCurvePublicKey | None = None
        self._jwks: jwt.PyJWKClient | None = None
        if config.public_key_file:
            key = serialization.load_pem_public_key(Path(config.public_key_file).read_bytes())
            if not isinstance(key, ec.EllipticCurvePublicKey) or not isinstance(key.curve, ec.SECP256R1):
                raise ValueError("La clave pública Auth debe ser EC P-256 para ES256")
            self._key = key
        elif config.jwks_url:
            self._jwks = jwt.PyJWKClient(config.jwks_url, cache_keys=True, lifespan=300)
        else:
            raise ValueError("Configure JWT_JWKS_URL o JWT_PUBLIC_KEY_FILE")

    def verificar(self, token: str) -> Identidad:
        try:
            key: Any = self._key
            if key is None and self._jwks is not None:
                key = self._jwks.get_signing_key_from_jwt(token).key
            claims = jwt.decode(
                token, key, algorithms=["ES256"], issuer=config.issuer,
                audience=config.audience,
                options={"require": ["sub", "rol", "iss", "aud", "iat", "exp", "jti"]},
            )
            role = claims["rol"]
            if role not in ROLES:
                raise TokenInvalido("Rol no reconocido")
            return Identidad(UUID(claims["sub"]), role)
        except TokenInvalido:
            raise
        except (jwt.PyJWTError, ValueError, TypeError, KeyError) as exc:
            raise TokenInvalido("Token no válido") from exc


@lru_cache(maxsize=1)
def verificador() -> VerificadorJwt | None:
    try:
        return VerificadorJwt()
    except (OSError, ValueError) as exc:
        log.warning("JWT sin configurar; rutas protegidas responderán 401: %s", exc)
        return None


def identidad_actual(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),  # noqa: B008 - patrón FastAPI
) -> Identidad:
    validator = verificador()
    if credentials is None or validator is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Autenticación requerida", headers={"WWW-Authenticate": "Bearer"})
    try:
        return validator.verificar(credentials.credentials)
    except TokenInvalido:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token inválido", headers={"WWW-Authenticate": "Bearer"}) from None


def administrador(identity: Identidad = Depends(identidad_actual)) -> Identidad:  # noqa: B008
    if identity.rol != "administrador":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Se requiere rol administrador")
    return identity
