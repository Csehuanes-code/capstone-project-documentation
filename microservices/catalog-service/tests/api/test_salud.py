"""/health (vivo) y /health/ready (503 si PostgreSQL no responde, para el Gateway)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from catalog_service.api import main as modulo_main


@pytest.mark.asyncio
async def test_health_responde(async_client: AsyncClient) -> None:
    resp = await async_client.get("/health")
    assert resp.status_code == 200 and resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_ready_listo_con_base_disponible(async_client: AsyncClient) -> None:
    resp = await async_client.get("/health/ready")
    assert resp.status_code == 200
    assert resp.json()["dependencias"]["base_de_datos"] is True


@pytest.mark.asyncio
async def test_ready_503_si_la_base_no_responde(
    async_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def base_caida() -> bool:
        return False

    monkeypatch.setattr(modulo_main, "verificar_base_datos", base_caida)
    resp = await async_client.get("/health/ready")
    assert resp.status_code == 503
    assert resp.json()["estado"] == "no_listo"
