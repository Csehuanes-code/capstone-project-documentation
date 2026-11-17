"""ADR-06: solo los JWT ES256 emitidos por Auth abren las rutas protegidas.

Antes se aceptaban cabeceras X-User-Id / X-User-Role sin verificar, tokens "test-<rol>-<id>"
y, en desarrollo, tokens sin verificar la firma: cualquiera podía hacerse pasar por
administrador. Estas pruebas evitan que esos atajos vuelvan.
"""

from __future__ import annotations

import datetime
from uuid import uuid4

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from httpx import AsyncClient

from catalog_service.infrastructure.config import settings
from catalog_service.infrastructure.security import obtener_verificador
from tests.auth_util import cabeceras, configurar_servicio, token

FAVORITOS = "/api/v1/catalogo/favoritos"
MODERACION = f"/api/v1/catalogo/calificaciones/{uuid4()}/moderacion"
CUERPO_MODERACION = {"nuevo_estado": "oculto", "justificacion": "prueba"}


def bearer(valor: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {valor}"}


@pytest.mark.asyncio
async def test_token_valido_de_auth_entra(async_client: AsyncClient) -> None:
    resp = await async_client.get(FAVORITOS, headers=cabeceras(uuid4(), "turista"))
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_sin_token_401(async_client: AsyncClient) -> None:
    assert (await async_client.get(FAVORITOS)).status_code == 401


@pytest.mark.asyncio
async def test_cabeceras_de_simulacion_ya_no_autentican(async_client: AsyncClient) -> None:
    falsas = {"X-User-Id": str(uuid4()), "X-User-Role": "administrador"}
    assert (await async_client.get(FAVORITOS, headers=falsas)).status_code == 401
    resp = await async_client.put(MODERACION, json=CUERPO_MODERACION, headers=falsas)
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_token_de_prueba_inventado_no_sirve(async_client: AsyncClient) -> None:
    resp = await async_client.get(FAVORITOS, headers=bearer(f"test-administrador-{uuid4()}"))
    assert resp.status_code == 401


@pytest.mark.parametrize(
    "malo",
    [
        pytest.param(
            lambda: token(uuid4(), "turista", clave=ec.generate_private_key(ec.SECP256R1())),
            id="firmado-con-otra-clave",
        ),
        pytest.param(
            lambda: token(uuid4(), "turista", expira_en=datetime.timedelta(minutes=-1)),
            id="expirado",
        ),
        pytest.param(lambda: token(uuid4(), "turista", iss="http://otro-emisor"), id="otro-emisor"),
        pytest.param(lambda: token(uuid4(), "turista", aud="otra-audiencia"), id="otra-audiencia"),
        pytest.param(lambda: token(uuid4(), "superusuario"), id="rol-desconocido"),
        pytest.param(lambda: token("no-es-uuid", "turista"), id="sub-no-uuid"),
        pytest.param(
            lambda: jwt.encode(
                {"sub": str(uuid4()), "rol": "administrador"},
                "clave-compartida-cualquiera-de-32-bytes!!",
                algorithm="HS256",
            ),
            id="hs256-con-clave-compartida",
        ),
        pytest.param(
            lambda: jwt.encode({"sub": str(uuid4()), "rol": "administrador"}, None, algorithm="none"),
            id="alg-none-sin-firma",
        ),
    ],
)
@pytest.mark.asyncio
async def test_tokens_invalidos_401(async_client: AsyncClient, malo) -> None:  # type: ignore[no-untyped-def]
    assert (await async_client.get(FAVORITOS, headers=bearer(malo()))).status_code == 401


@pytest.mark.asyncio
async def test_rol_sin_permiso_403(async_client: AsyncClient) -> None:
    resp = await async_client.put(
        MODERACION, json=CUERPO_MODERACION, headers=cabeceras(uuid4(), "prestador")
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_sin_clave_configurada_nadie_entra(async_client: AsyncClient) -> None:
    """Falla cerrado: si se olvida configurar la clave pública, no se abre la puerta."""
    settings.JWT_PUBLIC_KEY = ""
    obtener_verificador.cache_clear()
    try:
        resp = await async_client.get(FAVORITOS, headers=cabeceras(uuid4(), "turista"))
        assert resp.status_code == 401
    finally:
        configurar_servicio()


@pytest.mark.asyncio
async def test_archivo_de_clave_inexistente_da_401_no_500(async_client: AsyncClient) -> None:
    settings.JWT_PUBLIC_KEY = ""
    settings.JWT_PUBLIC_KEY_FILE = "no/existe/auth-es256-public.pem"
    obtener_verificador.cache_clear()
    try:
        resp = await async_client.get(FAVORITOS, headers=cabeceras(uuid4(), "turista"))
        assert resp.status_code == 401
    finally:
        configurar_servicio()
