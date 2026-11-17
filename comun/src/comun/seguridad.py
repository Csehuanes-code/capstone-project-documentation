"""Validación de los JWT que emite el servicio Auth (ADR-06).

Auth (microservices/auth-service) firma los tokens de acceso con ES256 (curva P-256). Cada
servicio los valida por su cuenta con la clave PÚBLICA, sin llamar a Auth en cada petición.

Claims que emite Auth: sub, rol, iss, aud, iat, nbf, exp, jti. Aquí se exige firma ES256,
emisor, audiencia, expiración, los claims obligatorios y que el rol sea uno de los tres.

Configuración (variables de entorno; los parámetros explícitos tienen prioridad):
  JWT_CLAVE_PUBLICA        PEM de la clave pública de Auth
  JWT_CLAVE_PUBLICA_FILE   o la ruta a ese PEM
  JWT_ISSUER               emisor (por defecto el de Auth en local: http://localhost:8001)
  JWT_AUDIENCE             audiencia (por defecto santa-marta-platform, igual que Auth)
Sin clave configurada, ningún token es válido (falla cerrado: 401).
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
from typing import Callable, Literal
import uuid

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt

RolUsuario = Literal["turista", "prestador", "administrador"]
ROLES_VALIDOS: set[str] = {"turista", "prestador", "administrador"}
CLAIMS_OBLIGATORIOS = ["sub", "rol", "iss", "aud", "iat", "exp", "jti"]

ISSUER_POR_DEFECTO = "http://localhost:8001"
AUDIENCE_POR_DEFECTO = "santa-marta-platform"

_bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class Identidad:
    """Identidad autenticada extraída del JWT ES256 (ADR-06)."""
    sub: str
    rol: RolUsuario


def _no_autorizado(detalle: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detalle,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _leer_clave_de_entorno() -> str:
    pem = os.getenv("JWT_CLAVE_PUBLICA", "")
    archivo = os.getenv("JWT_CLAVE_PUBLICA_FILE", "")
    if not pem and archivo:
        try:
            pem = Path(archivo).read_text(encoding="utf-8")
        except OSError:
            pem = ""
    return pem


class ValidadorJWT:
    """Valida tokens JWT firmados con ES256 (ECDSA P-256) usando la clave pública PEM de Auth."""

    def __init__(
        self,
        clave_publica_pem: str | None = None,
        issuer: str | None = None,
        audience: str | None = None,
    ):
        self.clave_publica_pem = clave_publica_pem or _leer_clave_de_entorno()
        self.issuer = issuer or os.getenv("JWT_ISSUER") or ISSUER_POR_DEFECTO
        self.audience = audience or os.getenv("JWT_AUDIENCE") or AUDIENCE_POR_DEFECTO

    def validar(self, token: str) -> Identidad:
        if not self.clave_publica_pem:
            raise _no_autorizado("El servicio no tiene configurada la clave pública de Auth.")
        try:
            payload = jwt.decode(
                token,
                self.clave_publica_pem,
                algorithms=["ES256"],
                issuer=self.issuer,
                audience=self.audience,
                options={"require": CLAIMS_OBLIGATORIOS},
            )
        except (jwt.PyJWTError, ValueError, TypeError) as exc:
            # No se devuelve el detalle de la excepción: no se da pistas a quien prueba tokens.
            raise _no_autorizado("Token inválido o expirado.") from exc

        rol = payload.get("rol")
        sub = str(payload.get("sub") or "").strip()
        if rol not in ROLES_VALIDOS or not sub:
            raise _no_autorizado("Token inválido o expirado.")
        return Identidad(sub=sub, rol=rol)


def crear_dependencia_identidad(validador: ValidadorJWT) -> Callable[..., Identidad]:
    """Devuelve una dependencia FastAPI que exige Bearer token ES256 válido (401 si falla)."""

    def _obtener_identidad(
        credenciales: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    ) -> Identidad:
        if credenciales is None or credenciales.scheme.lower() != "bearer":
            raise _no_autorizado("Falta cabecera Authorization: Bearer <token>.")
        return validador.validar(credenciales.credentials)

    return _obtener_identidad


def requiere_rol(
    obtener_identidad: Callable[..., Identidad],
    *roles_permitidos: RolUsuario,
) -> Callable[..., Identidad]:
    """Dependencia FastAPI que verifica que la identidad tenga uno de los roles permitidos (403 si no)."""

    def _verificar_rol(identidad: Identidad = Depends(obtener_identidad)) -> Identidad:
        if identidad.rol not in roles_permitidos:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Acceso denegado: se requiere rol {' o '.join(roles_permitidos)}.",
            )
        return identidad

    return _verificar_rol


# --- Utilidades para pruebas automatizadas ---

def generar_par_claves_es256() -> tuple[str, str]:
    """Genera un par de claves (privada_pem, publica_pem) ES256 (P-256) para pruebas."""
    privada = ec.generate_private_key(ec.SECP256R1())
    privada_pem = privada.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    publica_pem = privada.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")
    return privada_pem, publica_pem


def emitir_token_prueba(
    privada_pem: str,
    sub: str,
    rol: RolUsuario,
    minutos_validez: int = 15,
    issuer: str = ISSUER_POR_DEFECTO,
    audience: str = AUDIENCE_POR_DEFECTO,
) -> str:
    """Emite un JWT ES256 con los mismos claims que Auth, firmado con la clave de prueba."""
    ahora = datetime.now(timezone.utc)
    claims = {
        "sub": sub,
        "rol": rol,
        "iss": issuer,
        "aud": audience,
        "iat": ahora,
        "nbf": ahora,
        "exp": ahora + timedelta(minutes=minutos_validez),
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(claims, privada_pem, algorithm="ES256", headers={"typ": "JWT"})
