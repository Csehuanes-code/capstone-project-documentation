"""CU-19 contra Reservas: el token del turista viaja a Reservas y la reserva debe ser de la oferta."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

import pytest

from catalog_service.application.ports import ReservasClient
from catalog_service.application.use_cases import CrearCalificacionUseCase
from catalog_service.domain.entities import Oferta
from catalog_service.domain.exceptions import DomainError
from catalog_service.domain.value_objects import EstadoOferta


class ReservasQueRecuerdaToken(ReservasClient):
    """Responde como Reservas real: {reserva_id, estado, oferta_id}."""

    def __init__(self, oferta_id: UUID | None) -> None:
        self.oferta_id = oferta_id
        self.tokens: list[str | None] = []

    async def get_reserva_estado(
        self, reserva_id: UUID, token_acceso: str | None = None
    ) -> dict[str, Any] | None:
        self.tokens.append(token_acceso)
        if self.oferta_id is None:
            return None  # Reservas respondió 403/404: no es del turista o no existe
        return {"reserva_id": str(reserva_id), "estado": "completada", "oferta_id": str(self.oferta_id)}


async def _preparar(fake_repos: dict[str, Any], cliente: ReservasClient) -> tuple[Oferta, CrearCalificacionUseCase]:
    oferta = Oferta(
        id=uuid4(),
        prestador_id=fake_repos["prestador_verificado"].prestador_id,
        tipo_servicio_id=fake_repos["tipo_tour"].id,
        zona_id=fake_repos["zona_minca"].id,
        nombre_es="Tour",
        nombre_en="Tour",
        estado=EstadoOferta.PUBLICADA,
    )
    await fake_repos["oferta_repo"].save(oferta)
    caso = CrearCalificacionUseCase(
        calificacion_repo=fake_repos["calificacion_repo"],
        oferta_repo=fake_repos["oferta_repo"],
        zona_repo=fake_repos["zona_repo"],
        reservas_client=cliente,
        event_publisher=fake_repos["event_publisher"],
    )
    return oferta, caso


@pytest.mark.asyncio
async def test_reenvia_el_token_y_acepta_reserva_completada_de_la_oferta(
    fake_repos: dict[str, Any],
) -> None:
    cliente = ReservasQueRecuerdaToken(oferta_id=None)
    oferta, caso = await _preparar(fake_repos, cliente)
    cliente.oferta_id = oferta.id
    calif = await caso.execute(
        oferta_id=oferta.id, turista_id=uuid4(), reserva_id=uuid4(), puntaje=5,
        comentario="Excelente", token_acceso="token-del-turista",
    )
    assert calif.puntaje == 5
    assert cliente.tokens == ["token-del-turista"]


@pytest.mark.asyncio
async def test_rechaza_reserva_de_otra_oferta(fake_repos: dict[str, Any]) -> None:
    oferta, caso = await _preparar(fake_repos, ReservasQueRecuerdaToken(oferta_id=uuid4()))
    with pytest.raises(DomainError, match="no corresponde a esta oferta"):
        await caso.execute(
            oferta_id=oferta.id, turista_id=uuid4(), reserva_id=uuid4(), puntaje=4,
            comentario="", token_acceso="t",
        )


@pytest.mark.asyncio
async def test_rechaza_reserva_ajena_que_reservas_no_muestra(fake_repos: dict[str, Any]) -> None:
    oferta, caso = await _preparar(fake_repos, ReservasQueRecuerdaToken(oferta_id=None))
    with pytest.raises(DomainError):
        await caso.execute(
            oferta_id=oferta.id, turista_id=uuid4(), reserva_id=uuid4(), puntaje=4,
            comentario="", token_acceso="t",
        )
