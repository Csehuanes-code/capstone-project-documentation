"""API tests for Favorites, Itineraries, and Batch Sync (CU-09, CU-10, CU-23)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import AsyncClient

from catalog_service.domain.entities import Oferta
from catalog_service.domain.value_objects import EstadoOferta
from tests.auth_util import cabeceras


@pytest.mark.asyncio
async def test_favoritos_flujo_completo(
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
        nombre_es="Cascadas Favoritas",
        nombre_en="Favorite Waterfalls",
        estado=EstadoOferta.PUBLICADA,
    )
    await fake_repos["oferta_repo"].save(oferta)

    turista_id = uuid4()
    headers = cabeceras(str(turista_id), "turista")

    # 1. Add favorite
    resp_add = await async_client.post(f"/api/v1/catalogo/favoritos/{oferta.id}", headers=headers)
    assert resp_add.status_code == 204

    # 2. List favorites
    resp_list = await async_client.get("/api/v1/catalogo/favoritos", headers=headers)
    assert resp_list.status_code == 200
    favs = resp_list.json()
    assert len(favs) == 1
    assert favs[0]["id"] == str(oferta.id)

    # 3. Remove favorite
    resp_rem = await async_client.delete(f"/api/v1/catalogo/favoritos/{oferta.id}", headers=headers)
    assert resp_rem.status_code == 204

    # 4. List again (empty)
    resp_list2 = await async_client.get("/api/v1/catalogo/favoritos", headers=headers)
    assert resp_list2.status_code == 200
    assert len(resp_list2.json()) == 0


@pytest.mark.asyncio
async def test_itinerarios_con_advertencia_solapamiento(
    async_client: AsyncClient, fake_repos: dict[str, object]
) -> None:
    p = fake_repos["prestador_verificado"]
    z = fake_repos["zona_minca"]
    t = fake_repos["tipo_tour"]

    of1 = Oferta(
        id=uuid4(),
        prestador_id=p.prestador_id,
        tipo_servicio_id=t.id,
        zona_id=z.id,
        nombre_es="Actividad 1",
        nombre_en="Activity 1",
    )
    of2 = Oferta(
        id=uuid4(),
        prestador_id=p.prestador_id,
        tipo_servicio_id=t.id,
        zona_id=z.id,
        nombre_es="Actividad 2",
        nombre_en="Activity 2",
    )
    await fake_repos["oferta_repo"].save(of1)
    await fake_repos["oferta_repo"].save(of2)

    turista_id = uuid4()
    headers = cabeceras(str(turista_id), "turista")

    # 1. Create itinerary
    resp_it = await async_client.post(
        "/api/v1/catalogo/itinerarios",
        json={
            "nombre": "Vacaciones Diciembre 2026",
            "fecha_inicio": "2026-12-15",
            "fecha_fin": "2026-12-20",
        },
        headers=headers,
    )
    assert resp_it.status_code == 201
    itinerario_id = resp_it.json()["id"]

    # 2. Add first item: 09:00 to 12:00
    resp_item1 = await async_client.post(
        f"/api/v1/catalogo/itinerarios/{itinerario_id}/items",
        json={
            "oferta_id": str(of1.id),
            "dia": "2026-12-16",
            "orden": 1,
            "hora_inicio": "09:00:00",
            "hora_fin": "12:00:00",
        },
        headers=headers,
    )
    assert resp_item1.status_code == 201
    assert len(resp_item1.json()["advertencias"]) == 0

    # 3. Add second item overlapping: 11:00 to 14:00 (RF-CAT-07: warn but do NOT block)
    resp_item2 = await async_client.post(
        f"/api/v1/catalogo/itinerarios/{itinerario_id}/items",
        json={
            "oferta_id": str(of2.id),
            "dia": "2026-12-16",
            "orden": 2,
            "hora_inicio": "11:00:00",
            "hora_fin": "14:00:00",
        },
        headers=headers,
    )
    assert resp_item2.status_code == 201
    data2 = resp_item2.json()
    assert len(data2["advertencias"]) > 0
    assert "solapamiento" in data2["advertencias"][0].lower()


@pytest.mark.asyncio
async def test_sincronizacion_lote_202_accepted(
    async_client: AsyncClient, fake_repos: dict[str, object]
) -> None:
    """Tests CU-23 & ADR-04 §4.4: POST /api/v1/catalogo/lotes responds 202 Accepted with lote_id."""
    p = fake_repos["prestador_verificado"]
    fuente_id = uuid4()
    headers = cabeceras(str(p.prestador_id), "prestador")

    payload = {
        "fuente_id": str(fuente_id),
        "registros": [
            {
                "nombre_es": "Hotel Minca Eco",
                "nombre_en": "Hotel Minca Eco",
                "tipo_codigo": "tour",
                "zona_codigo": "minca",
                "atributos": {"duracion_horas": 3.0},
            }
        ],
    }

    resp = await async_client.post("/api/v1/catalogo/lotes", json=payload, headers=headers)
    assert resp.status_code == 202
    data = resp.json()
    assert "lote_id" in data
    assert data["aceptados"] == 1
