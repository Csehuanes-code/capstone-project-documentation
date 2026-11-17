"""Configuración de pruebas de Analítica.

`analitica.configuracion` lee el entorno al importarse, así que aquí se fijan ANTES de importar
el servicio: una clave pública de prueba para los JWT y, si existe ANALITICA_TEST_DATABASE_URL,
la base PostgreSQL de pruebas.
"""

from __future__ import annotations

import os
import tempfile
import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

_CLAVE = ec.generate_private_key(ec.SECP256R1())
with tempfile.NamedTemporaryFile("wb", suffix=".pem", delete=False) as _PUBLICA:
    _PUBLICA.write(
        _CLAVE.public_key().public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
        )
    )

ISSUER = "http://localhost:8001"
AUDIENCE = "santa-marta-platform"
os.environ["JWT_PUBLIC_KEY_FILE"] = _PUBLICA.name
os.environ["JWT_JWKS_URL"] = ""
os.environ["JWT_ISSUER"] = ISSUER
os.environ["JWT_AUDIENCE"] = AUDIENCE
os.environ["ANALITICA_RABBITMQ_URL"] = ""  # sin hilos de RabbitMQ en las pruebas
DB_URL = os.getenv("ANALITICA_TEST_DATABASE_URL")
if DB_URL:
    os.environ["ANALITICA_DATABASE_URL"] = DB_URL


def token(rol: str, sub: str | None = None, **cambios: object) -> str:
    """JWT con los mismos claims que emite Auth."""
    ahora = datetime.now(UTC)
    claims: dict[str, object] = {
        "sub": sub or str(uuid.uuid4()), "rol": rol, "iss": ISSUER, "aud": AUDIENCE,
        "iat": ahora, "nbf": ahora, "exp": ahora + timedelta(minutes=15), "jti": str(uuid.uuid4()),
    }
    claims.update(cambios)
    return jwt.encode(claims, _CLAVE, algorithm="ES256")


def cabeceras(rol: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token(rol)}"}


requiere_postgres = pytest.mark.skipif(not DB_URL, reason="requiere ANALITICA_TEST_DATABASE_URL")
