"""Adaptadores criptográficos para contraseñas y tokens de acceso."""

from __future__ import annotations

import base64
from datetime import timedelta
from uuid import UUID, uuid4

import jwt
from argon2 import PasswordHasher, Type
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from auth_service.application.errors import TokenVerificationFailed
from auth_service.application.identity import AuthenticatedIdentity
from auth_service.application.ports import Clock
from auth_service.domain.role import Role
from auth_service.domain.user import User


class Argon2PasswordHasher:
    """Argon2id con los parámetros mínimos establecidos en ADR-06."""

    def __init__(self) -> None:
        self._hasher = PasswordHasher(
            time_cost=2,
            memory_cost=19 * 1024,
            parallelism=1,
            type=Type.ID,
        )

    def hash(self, raw_password: str) -> str:
        return self._hasher.hash(raw_password)

    def verify(self, encoded_hash: str, raw_password: str) -> bool:
        try:
            return self._hasher.verify(encoded_hash, raw_password)
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            return False


class ES256AccessTokenIssuer:
    """Emite JWT ES256; la clave y los identificadores se inyectan al arrancar."""

    def __init__(
        self,
        private_key_pem: str,
        key_id: str,
        issuer: str,
        audience: str,
        clock: Clock,
    ) -> None:
        if not all(value.strip() for value in (private_key_pem, key_id, issuer, audience)):
            raise ValueError("La clave, kid, emisor y audiencia son obligatorios.")
        loaded_key = serialization.load_pem_private_key(
            private_key_pem.encode("utf-8"), password=None
        )
        if not isinstance(loaded_key, ec.EllipticCurvePrivateKey):
            raise TypeError("La clave de firma debe ser una clave EC privada.")
        if not isinstance(loaded_key.curve, ec.SECP256R1):
            raise TypeError("ES256 requiere una clave de curva P-256.")
        self._private_key = loaded_key
        self._key_id = key_id
        self._issuer = issuer
        self._audience = audience
        self._clock = clock
        self._ttl = timedelta(minutes=15)

    def issue_access_token(self, user: User) -> str:
        now = self._clock.now()
        if now.tzinfo is None:
            raise ValueError("El reloj debe producir fechas con zona horaria.")
        issued_at = int(now.timestamp())
        expires_at = int((now + self._ttl).timestamp())
        claims = {
            "sub": str(user.id),
            "rol": Role(user.role).value,
            "iss": self._issuer,
            "aud": self._audience,
            "iat": issued_at,
            "nbf": issued_at,
            "exp": expires_at,
            "jti": str(uuid4()),
        }
        return jwt.encode(
            claims,
            self._private_key,
            algorithm="ES256",
            headers={"kid": self._key_id, "typ": "JWT"},
        )

    def verify_access_token(self, token: str) -> AuthenticatedIdentity:
        try:
            claims = jwt.decode(
                token,
                self._private_key.public_key(),
                algorithms=["ES256"],
                issuer=self._issuer,
                audience=self._audience,
                options={
                    "require": ["sub", "rol", "iss", "aud", "iat", "exp", "jti"]
                },
            )
            return AuthenticatedIdentity(
                user_id=UUID(claims["sub"]),
                role=Role(claims["rol"]),
            )
        except (jwt.InvalidTokenError, TypeError, ValueError, KeyError) as exc:
            raise TokenVerificationFailed("El token de acceso no es válido.") from exc

    def public_jwk(self) -> dict[str, str]:
        public_key = self._private_key.public_key()
        numbers = public_key.public_numbers()
        return {
            "kty": "EC",
            "crv": "P-256",
            "alg": "ES256",
            "use": "sig",
            "kid": self._key_id,
            "x": _base64url_uint(numbers.x),
            "y": _base64url_uint(numbers.y),
        }


def _base64url_uint(value: int) -> str:
    raw = value.to_bytes(32, byteorder="big")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")
