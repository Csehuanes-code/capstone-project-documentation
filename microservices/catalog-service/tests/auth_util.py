"""Tokens JWT de prueba firmados igual que los emite Auth (ES256, mismos claims).

Al importarse genera un par de claves P-256 de prueba y configura el servicio para validar con
la pública. Así las pruebas recorren la validación real (firma, emisor, audiencia, expiración),
sin atajos que luego queden abiertos en producción.
"""

from __future__ import annotations

import datetime
from typing import Any
from uuid import UUID, uuid4

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from catalog_service.infrastructure.config import settings
from catalog_service.infrastructure.security import obtener_verificador

ISSUER = "http://auth-de-prueba"
AUDIENCE = "santa-marta-platform"
KID = "clave-de-prueba"

_CLAVE_PRIVADA = ec.generate_private_key(ec.SECP256R1())
CLAVE_PUBLICA_PEM = (
    _CLAVE_PRIVADA.public_key()
    .public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    .decode("ascii")
)


def configurar_servicio() -> None:
    settings.JWT_PUBLIC_KEY = CLAVE_PUBLICA_PEM
    settings.JWT_PUBLIC_KEY_FILE = ""
    settings.JWT_JWKS_URL = ""
    settings.JWT_ISSUER = ISSUER
    settings.JWT_AUDIENCE = AUDIENCE
    obtener_verificador.cache_clear()


def token(
    user_id: UUID | str,
    rol: str,
    *,
    clave: ec.EllipticCurvePrivateKey | None = None,
    expira_en: datetime.timedelta = datetime.timedelta(minutes=15),
    **cambios: Any,
) -> str:
    ahora = datetime.datetime.now(datetime.UTC)
    claims: dict[str, Any] = {
        "sub": str(user_id),
        "rol": rol,
        "iss": ISSUER,
        "aud": AUDIENCE,
        "iat": int(ahora.timestamp()),
        "nbf": int(ahora.timestamp()),
        "exp": int((ahora + expira_en).timestamp()),
        "jti": str(uuid4()),
    }
    claims.update(cambios)
    return jwt.encode(
        claims, clave or _CLAVE_PRIVADA, algorithm="ES256", headers={"kid": KID, "typ": "JWT"}
    )


def cabeceras(user_id: UUID | str, rol: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token(user_id, rol)}"}
