"""Unit tests for Application layer use cases."""

from __future__ import annotations

import datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from catalog_service.application.use_cases import (
    CrearCalificacionUseCase,
    GestionarOfertaUseCase,
    ObtenerCondicionesOfertaUseCase,
    SincronizarLoteUseCase,
)
from catalog_service.domain.entities import Oferta, Tarifa
from catalog_service.domain.exceptions import (
    CalificacionDuplicada,
    DomainError,
    PrestadorNoVerificado,
)
from catalog_service.domain.value_objects import (
    EstadoLote,
    EstadoOferta,
    Temporada,
)


@pytest.mark.asyncio
async def test_crear_oferta_prestador_verificado(fake_repos: dict[str, object]) -> None:
    use_case = GestionarOfertaUseCase(
        oferta_repo=fake_repos["oferta_repo"],
        zona_repo=fake_repos["zona_repo"],
        tipo_repo=fake_repos["tipo_repo"],
        prestador_repo=fake_repos["prestador_repo"],
        event_publisher=fake_repos["event_publisher"],
    )
    p_verificado = fake_repos["prestador_verificado"]
    z_minca = fake_repos["zona_minca"]
    t_tour = fake_repos["tipo_tour"]

    oferta = await use_case.crear_oferta(
        prestador_id=p_verificado.prestador_id,
        tipo_servicio_id=t_tour.id,
        zona_id=z_minca.id,
        nombre_es="Tour cascadas de Minca",
        nombre_en="Minca Waterfalls Tour",
        descripcion_es="Paseo por la naturaleza",
        descripcion_en="Walk through nature",
        atributos={"duracion_horas": 4.0, "categorias": ["naturaleza"]},
        estado=EstadoOferta.PUBLICADA,
    )
    assert oferta.id is not None
    assert oferta.estado == EstadoOferta.PUBLICADA
    assert oferta.nombre_es == "Tour cascadas de Minca"

    # Verify event was published
    publisher = fake_repos["event_publisher"]
    assert len(publisher.published_events) == 1
    event = publisher.published_events[0]
    assert event["tipo"] == "catalogo.oferta.publicada"
    assert event["datos"]["nombre"] == "Tour cascadas de Minca"
    assert event["datos"]["zona_id"] == "minca"
    assert event["datos"]["activa"] is True


@pytest.mark.asyncio
async def test_crear_oferta_publicada_prestador_no_verificado_falla(
    fake_repos: dict[str, object],
) -> None:
    use_case = GestionarOfertaUseCase(
        oferta_repo=fake_repos["oferta_repo"],
        zona_repo=fake_repos["zona_repo"],
        tipo_repo=fake_repos["tipo_repo"],
        prestador_repo=fake_repos["prestador_repo"],
        event_publisher=fake_repos["event_publisher"],
    )
    p_no_verificado = fake_repos["prestador_no_verificado"]
    z_minca = fake_repos["zona_minca"]
    t_tour = fake_repos["tipo_tour"]

    # Trying to publish directly without being verified must raise PrestadorNoVerificado (RF-USR-19)
    with pytest.raises(PrestadorNoVerificado):
        await use_case.crear_oferta(
            prestador_id=p_no_verificado.prestador_id,
            tipo_servicio_id=t_tour.id,
            zona_id=z_minca.id,
            nombre_es="Tour no permitido",
            nombre_en="Disallowed tour",
            atributos={"duracion_horas": 2.0},
            estado=EstadoOferta.PUBLICADA,
        )


@pytest.mark.asyncio
async def test_retirar_oferta(fake_repos: dict[str, object]) -> None:
    use_case = GestionarOfertaUseCase(
        oferta_repo=fake_repos["oferta_repo"],
        zona_repo=fake_repos["zona_repo"],
        tipo_repo=fake_repos["tipo_repo"],
        prestador_repo=fake_repos["prestador_repo"],
        event_publisher=fake_repos["event_publisher"],
    )
    p = fake_repos["prestador_verificado"]
    z = fake_repos["zona_minca"]
    t = fake_repos["tipo_tour"]

    oferta = await use_case.crear_oferta(
        prestador_id=p.prestador_id,
        tipo_servicio_id=t.id,
        zona_id=z.id,
        nombre_es="Oferta temporal",
        nombre_en="Temporary offer",
        atributos={"duracion_horas": 3.0},
        estado=EstadoOferta.PUBLICADA,
    )

    retirada = await use_case.retirar_oferta(oferta.id, p.prestador_id)
    assert retirada.estado == EstadoOferta.DADA_DE_BAJA

    publisher = fake_repos["event_publisher"]
    last_event = publisher.published_events[-1]
    assert last_event["tipo"] == "catalogo.oferta.retirada"
    assert last_event["datos"]["activa"] is False


@pytest.mark.asyncio
async def test_obtener_condiciones_oferta(fake_repos: dict[str, object]) -> None:
    use_case = ObtenerCondicionesOfertaUseCase(
        oferta_repo=fake_repos["oferta_repo"],
        tarifa_repo=fake_repos["tarifa_repo"],
        politica_repo=fake_repos["politica_repo"],
        zona_repo=fake_repos["zona_repo"],
    )
    p = fake_repos["prestador_verificado"]
    z = fake_repos["zona_minca"]
    t = fake_repos["tipo_tour"]

    oferta = Oferta(
        id=uuid4(),
        prestador_id=p.prestador_id,
        tipo_servicio_id=t.id,
        zona_id=z.id,
        nombre_es="Tour Minca Cascadas",
        nombre_en="Minca Waterfalls Tour",
        estado=EstadoOferta.PUBLICADA,
    )
    await fake_repos["oferta_repo"].save(oferta)

    tarifa = Tarifa(
        id=uuid4(),
        oferta_id=oferta.id,
        temporada=Temporada.MEDIA,
        vigente_desde=datetime.date(2026, 1, 1),
        vigente_hasta=datetime.date(2026, 12, 31),
        precio_por_persona=Decimal("120000.00"),
        moneda="COP",
    )
    await fake_repos["tarifa_repo"].save(tarifa)

    condiciones = await use_case.execute(oferta.id, datetime.date(2026, 6, 15))
    assert condiciones["activa"] is True
    assert condiciones["zona_id"] == "minca"
    assert condiciones["tarifa_vigente"]["precio_por_persona"] == 120000.0


@pytest.mark.asyncio
async def test_crear_calificacion_reserva_completada(fake_repos: dict[str, object]) -> None:
    use_case = CrearCalificacionUseCase(
        calificacion_repo=fake_repos["calificacion_repo"],
        oferta_repo=fake_repos["oferta_repo"],
        zona_repo=fake_repos["zona_repo"],
        reservas_client=fake_repos["reservas_client"],
        event_publisher=fake_repos["event_publisher"],
    )
    p = fake_repos["prestador_verificado"]
    z = fake_repos["zona_minca"]
    t = fake_repos["tipo_tour"]

    oferta = Oferta(
        id=uuid4(),
        prestador_id=p.prestador_id,
        tipo_servicio_id=t.id,
        zona_id=z.id,
        nombre_es="Tour a Calificar",
        nombre_en="Tour to Rate",
        estado=EstadoOferta.PUBLICADA,
    )
    await fake_repos["oferta_repo"].save(oferta)

    reserva_id = uuid4()
    turista_id = uuid4()

    # Configure mock reservas client to return "completada"
    fake_repos["reservas_client"].set_reserva(reserva_id, "completada")

    calif = await use_case.execute(
        oferta_id=oferta.id,
        turista_id=turista_id,
        reserva_id=reserva_id,
        puntaje=5,
        comentario="Excelente guía y hermosa cascada.",
    )
    assert calif.puntaje == 5

    # Check updated offer rating
    oferta_updated = await fake_repos["oferta_repo"].get_by_id(oferta.id)
    assert oferta_updated.total_calificaciones == 1
    assert oferta_updated.calificacion_promedio == Decimal("5.00")

    # Trying to review same reservation again must fail (RF-CAT-15)
    with pytest.raises(CalificacionDuplicada):
        await use_case.execute(
            oferta_id=oferta.id,
            turista_id=turista_id,
            reserva_id=reserva_id,
            puntaje=4,
        )


@pytest.mark.asyncio
async def test_crear_calificacion_reserva_no_completada_rechazada(
    fake_repos: dict[str, object],
) -> None:
    use_case = CrearCalificacionUseCase(
        calificacion_repo=fake_repos["calificacion_repo"],
        oferta_repo=fake_repos["oferta_repo"],
        zona_repo=fake_repos["zona_repo"],
        reservas_client=fake_repos["reservas_client"],
        event_publisher=fake_repos["event_publisher"],
    )
    p = fake_repos["prestador_verificado"]
    z = fake_repos["zona_minca"]
    t = fake_repos["tipo_tour"]

    oferta = Oferta(
        id=uuid4(),
        prestador_id=p.prestador_id,
        tipo_servicio_id=t.id,
        zona_id=z.id,
        nombre_es="Tour Pendiente",
        nombre_en="Pending Tour",
    )
    await fake_repos["oferta_repo"].save(oferta)

    reserva_id = uuid4()
    # Reservation is only "confirmada", not completed yet
    fake_repos["reservas_client"].set_reserva(reserva_id, "confirmada")

    with pytest.raises(DomainError) as exc_info:
        await use_case.execute(
            oferta_id=oferta.id,
            turista_id=uuid4(),
            reserva_id=reserva_id,
            puntaje=5,
        )
    assert "completadas" in str(exc_info.value)


@pytest.mark.asyncio
async def test_sincronizar_lote_todo_o_nada(fake_repos: dict[str, object]) -> None:
    use_case = SincronizarLoteUseCase(
        lote_repo=fake_repos["lote_repo"],
        oferta_repo=fake_repos["oferta_repo"],
        zona_repo=fake_repos["zona_repo"],
        tipo_repo=fake_repos["tipo_repo"],
    )
    p = fake_repos["prestador_verificado"]
    fuente_id = uuid4()

    # Batch with 1 valid row and 1 invalid row (unknown zone)
    registros = [
        {
            "nombre_es": "Hotel Sierra Minca",
            "nombre_en": "Hotel Sierra Minca",
            "tipo_codigo": "tour",
            "zona_codigo": "minca",
            "atributos": {"duracion_horas": 5.0},
        },
        {
            "nombre_es": "Hotel Invalido",
            "nombre_en": "Invalid Hotel",
            "tipo_codigo": "tour",
            "zona_codigo": "zona_inexistente",  # Non-canonical zone
            "atributos": {"duracion_horas": 2.0},
        },
    ]

    lote = await use_case.execute(
        prestador_id=p.prestador_id,
        fuente_id=fuente_id,
        registros=registros,
    )

    # Invariant: all-or-nothing (lotes todo o nada, RF-CAT-12, EC-INTEROP-01)
    assert lote.estado == EstadoLote.FALLIDO
    assert lote.aceptados == 0
    assert len(lote.rechazados) == 1
    assert lote.rechazados[0]["fila"] == 2
