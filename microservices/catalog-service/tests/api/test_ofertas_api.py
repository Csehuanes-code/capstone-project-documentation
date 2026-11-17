"""API tests for Offers endpoints."""

from __future__ import annotations

import datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import AsyncClient

from catalog_service.domain.entities import Oferta, Tarifa
from catalog_service.domain.value_objects import EstadoOferta, Temporada
from tests.auth_util import cabeceras


@pytest.mark.asyncio
async def test_listar_ofertas_publico(
    async_client: AsyncClient, fake_repos: dict[str, object]
) -> None:
    p = fake_repos["prestador_verificado"]
    z = fake_repos["zona_minca"]
    t = fake_repos["tipo_tour"]

    oferta = Oferta(
        id=uuid4(),
        prestador_id=p.prestador_id,
        tipo_servicio_id=t.id,
        zona_id=z.id,
        nombre_es="Paseo de Prueba",
        nombre_en="Test Walk",
        atributos={"categorias": ["naturaleza"]},
        estado=EstadoOferta.PUBLICADA,
    )
    await fake_repos["oferta_repo"].save(oferta)

    resp = await async_client.get("/api/v1/catalogo/ofertas")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert any(item["nombre_es"] == "Paseo de Prueba" for item in data["items"])


@pytest.mark.asyncio
async def test_listar_ofertas_orden_popularidad_ia_fallback(
    async_client: AsyncClient, fake_repos: dict[str, object]
) -> None:
    """Tests RF-IA-04: IA fallback asks Catálogo for offers ordered by popularity."""
    p = fake_repos["prestador_verificado"]
    z = fake_repos["zona_minca"]
    t = fake_repos["tipo_tour"]

    o1 = Oferta(
        id=uuid4(),
        prestador_id=p.prestador_id,
        tipo_servicio_id=t.id,
        zona_id=z.id,
        nombre_es="Oferta Menos Popular",
        nombre_en="Less Popular",
        calificacion_promedio=Decimal("3.50"),
        total_calificaciones=2,
        estado=EstadoOferta.PUBLICADA,
    )
    o2 = Oferta(
        id=uuid4(),
        prestador_id=p.prestador_id,
        tipo_servicio_id=t.id,
        zona_id=z.id,
        nombre_es="Oferta Muy Popular",
        nombre_en="Very Popular",
        calificacion_promedio=Decimal("4.90"),
        total_calificaciones=150,
        estado=EstadoOferta.PUBLICADA,
    )
    await fake_repos["oferta_repo"].save(o1)
    await fake_repos["oferta_repo"].save(o2)

    resp = await async_client.get("/api/v1/catalogo/ofertas?orden=popularidad")
    assert resp.status_code == 200
    items = resp.json()["items"]
    # Most popular should come first
    assert items[0]["nombre_es"] == "Oferta Muy Popular"


@pytest.mark.asyncio
async def test_obtener_condiciones_oferta_sync(
    async_client: AsyncClient, fake_repos: dict[str, object]
) -> None:
    """Tests Reservas → Catálogo: GET /ofertas/{id}/condiciones (ADR-04 §4.2)."""
    p = fake_repos["prestador_verificado"]
    z = fake_repos["zona_minca"]
    t = fake_repos["tipo_tour"]

    oferta = Oferta(
        id=uuid4(),
        prestador_id=p.prestador_id,
        tipo_servicio_id=t.id,
        zona_id=z.id,
        nombre_es="Tour Con Condiciones",
        nombre_en="Tour With Conditions",
        estado=EstadoOferta.PUBLICADA,
    )
    await fake_repos["oferta_repo"].save(oferta)

    tarifa = Tarifa(
        id=uuid4(),
        oferta_id=oferta.id,
        temporada=Temporada.ALTA,
        vigente_desde=datetime.date(2026, 1, 1),
        vigente_hasta=datetime.date(2026, 12, 31),
        precio_por_persona=Decimal("240000.00"),
        moneda="COP",
    )
    await fake_repos["tarifa_repo"].save(tarifa)

    resp = await async_client.get(f"/api/v1/catalogo/ofertas/{oferta.id}/condiciones")
    assert resp.status_code == 200
    data = resp.json()
    assert data["oferta_id"] == str(oferta.id)
    assert data["activa"] is True
    assert data["zona_id"] == "minca"
    assert data["tarifa_vigente"]["precio_por_persona"] == 240000.0


@pytest.mark.asyncio
async def test_crear_oferta_prestador_verificado_api(
    async_client: AsyncClient, fake_repos: dict[str, object]
) -> None:
    p = fake_repos["prestador_verificado"]
    z = fake_repos["zona_minca"]
    t = fake_repos["tipo_tour"]

    headers = cabeceras(str(p.prestador_id), "prestador")
    payload = {
        "tipo_servicio_id": str(t.id),
        "zona_id": str(z.id),
        "nombre_es": "Aventura en Minca",
        "nombre_en": "Minca Adventure",
        "descripcion_es": "Cascadas y café",
        "descripcion_en": "Waterfalls and coffee",
        "atributos": {"duracion_horas": 4.5, "categorias": ["aventura", "naturaleza"]},
        "estado": "publicada",
    }
    resp = await async_client.post("/api/v1/catalogo/ofertas", json=payload, headers=headers)
    assert resp.status_code == 201
    assert resp.json()["nombre_es"] == "Aventura en Minca"


@pytest.mark.asyncio
async def test_crear_oferta_con_categoria_no_canonica_rechazado_400(
    async_client: AsyncClient, fake_repos: dict[str, object]
) -> None:
    p = fake_repos["prestador_verificado"]
    z = fake_repos["zona_minca"]
    t = fake_repos["tipo_tour"]

    headers = cabeceras(str(p.prestador_id), "prestador")
    payload = {
        "tipo_servicio_id": str(t.id),
        "zona_id": str(z.id),
        "nombre_es": "Tour Selva",
        "nombre_en": "Jungle Tour",
        "atributos": {"duracion_horas": 2.0, "categorias": ["selva"]},  # "selva" is non-canonical
        "estado": "borrador",
    }
    resp = await async_client.post("/api/v1/catalogo/ofertas", json=payload, headers=headers)
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "CATEGORIA_NO_CANONICA"


@pytest.mark.asyncio
async def test_crear_oferta_sin_autenticacion_retorna_401(
    async_client: AsyncClient, fake_repos: dict[str, object]
) -> None:
    z = fake_repos["zona_minca"]
    t = fake_repos["tipo_tour"]

    payload = {
        "tipo_servicio_id": str(t.id),
        "zona_id": str(z.id),
        "nombre_es": "Sin Login",
        "nombre_en": "Without Login",
    }
    resp = await async_client.post("/api/v1/catalogo/ofertas", json=payload)
    assert resp.status_code == 401
