"""API tests for Reviews, Responses, and Moderation (CU-19, CU-20, CU-29)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import AsyncClient

from catalog_service.domain.entities import Oferta
from catalog_service.domain.value_objects import EstadoOferta


@pytest.mark.asyncio
async def test_crear_calificacion_api(
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
        nombre_es="Tour para Reseñar",
        nombre_en="Tour to Review",
        estado=EstadoOferta.PUBLICADA,
    )
    await fake_repos["oferta_repo"].save(oferta)

    reserva_id = uuid4()
    turista_id = uuid4()
    fake_repos["reservas_client"].set_reserva(reserva_id, "completada")

    headers = {
        "X-User-Id": str(turista_id),
        "X-User-Role": "turista",
    }
    payload = {
        "reserva_id": str(reserva_id),
        "puntaje": 5,
        "comentario": "Increíble experiencia, muy recomendado.",
    }

    resp = await async_client.post(
        f"/api/v1/catalogo/ofertas/{oferta.id}/calificaciones",
        json=payload,
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["puntaje"] == 5
    assert data["turista_id"] == str(turista_id)

    # Re-submitting for the same reservation must return 409 Conflict
    resp_dup = await async_client.post(
        f"/api/v1/catalogo/ofertas/{oferta.id}/calificaciones",
        json=payload,
        headers=headers,
    )
    assert resp_dup.status_code == 409
    assert resp_dup.json()["error"]["code"] == "CALIFICACION_DUPLICADA"


@pytest.mark.asyncio
async def test_responder_calificacion_api(
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
        nombre_es="Tour con Reseña",
        nombre_en="Tour With Review",
        estado=EstadoOferta.PUBLICADA,
    )
    await fake_repos["oferta_repo"].save(oferta)

    reserva_id = uuid4()
    turista_id = uuid4()
    fake_repos["reservas_client"].set_reserva(reserva_id, "completada")

    # Tourist creates review
    headers_turista = {"X-User-Id": str(turista_id), "X-User-Role": "turista"}
    calif_resp = await async_client.post(
        f"/api/v1/catalogo/ofertas/{oferta.id}/calificaciones",
        json={"reserva_id": str(reserva_id), "puntaje": 4, "comentario": "Muy buen tour"},
        headers=headers_turista,
    )
    calificacion_id = calif_resp.json()["id"]

    # Provider responds to review
    headers_prestador = {"X-User-Id": str(p.prestador_id), "X-User-Role": "prestador"}
    resp = await async_client.post(
        f"/api/v1/catalogo/calificaciones/{calificacion_id}/respuesta",
        json={"texto": "¡Muchas gracias por visitarnos! Esperamos verte pronto de nuevo."},
        headers=headers_prestador,
    )
    assert resp.status_code == 201
    assert "Muchas gracias" in resp.json()["texto"]


@pytest.mark.asyncio
async def test_moderar_calificacion_admin_solo(
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
        nombre_es="Tour Moderacion",
        nombre_en="Moderation Tour",
        estado=EstadoOferta.PUBLICADA,
    )
    await fake_repos["oferta_repo"].save(oferta)

    reserva_id = uuid4()
    fake_repos["reservas_client"].set_reserva(reserva_id, "completada")

    headers_turista = {"X-User-Id": str(uuid4()), "X-User-Role": "turista"}
    calif_resp = await async_client.post(
        f"/api/v1/catalogo/ofertas/{oferta.id}/calificaciones",
        json={"reserva_id": str(reserva_id), "puntaje": 1, "comentario": "Texto inapropiado"},
        headers=headers_turista,
    )
    calificacion_id = calif_resp.json()["id"]

    # Tourist trying to moderate should be rejected with 403 Forbidden
    resp_forbidden = await async_client.put(
        f"/api/v1/catalogo/calificaciones/{calificacion_id}/moderacion",
        json={"nuevo_estado": "oculta", "justificacion": "No me gusta"},
        headers=headers_turista,
    )
    assert resp_forbidden.status_code == 403

    # Admin moderating should succeed
    headers_admin = {"X-User-Id": str(uuid4()), "X-User-Role": "administrador"}
    resp_ok = await async_client.put(
        f"/api/v1/catalogo/calificaciones/{calificacion_id}/moderacion",
        json={"nuevo_estado": "oculta", "justificacion": "Lenguaje que viola términos"},
        headers=headers_admin,
    )
    assert resp_ok.status_code == 200
    assert resp_ok.json()["estado_moderacion"] == "oculta"
