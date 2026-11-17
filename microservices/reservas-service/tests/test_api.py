from datetime import datetime, time, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from comun.eventos import OutboxRegistro
from reservas.dominio.entidades import FranjaDisponibilidad, ZONA_HORARIA_COLOMBIA
from reservas.infraestructura.sql.tablas import (
    EntradaListaEsperaORM,
    FranjaDisponibilidadORM,
    ReservaORM,
)
from reservas.aplicacion.casos_uso import ExpirarOfertasListaEsperaUseCase
from conftest import (
    AHORA,
    FECHA_SERVICIO,
    FRANJA_ID,
    OFERTA_ID,
    PRESTADOR_ID,
    autorizacion,
    crear_reserva,
    emitir_token_prueba,
    generar_par_claves_es256,
    payload_reserva,
    token,
)


def _asientos(app) -> tuple[int, int]:
    with app.state.engine.connect() as conn:
        disponibles = conn.execute(
            select(FranjaDisponibilidadORM.cupo_disponible).where(
                FranjaDisponibilidadORM.id == FRANJA_ID
            )
        ).scalar_one()
        reservas = conn.execute(select(func.count()).select_from(ReservaORM)).scalar_one()
    return disponibles, reservas


def test_reservar_devuelve_comprobante_idempotente_y_un_solo_evento(cliente, app, claves, notificador):
    headers = {**autorizacion(claves), "Idempotency-Key": "misma-clave"}
    primera = cliente.post("/api/v1/reservas", json=payload_reserva(), headers=headers)
    repetida = cliente.post("/api/v1/reservas", json=payload_reserva(), headers=headers)

    assert primera.status_code == 201
    assert primera.json()["estado"] == "confirmada"
    assert primera.json()["pago_aprobado"] is True
    assert primera.json()["codigo"].startswith("SMT-")
    assert repetida.status_code == 201
    assert repetida.json() == primera.json()
    assert _asientos(app) == (3, 1)
    assert len(notificador.enviados) == 1
    with Session(app.state.engine) as session:
        evento = session.execute(select(OutboxRegistro)).scalar_one()
    assert evento.tipo == "reservas.reserva.confirmada"
    assert not ({"turista_id", "correo_turista", "nombre_completo"} & evento.datos.keys())


def test_pago_rechazado_o_vencido_devuelve_cupo(cliente, app, claves):
    for indice, tarjeta in enumerate(("4111111111110002", "4111111111119999")):
        respuesta = crear_reserva(
            cliente, claves, key=f"pago-fallido-{indice}", tarjeta=tarjeta
        )
        assert respuesta.status_code == 402
        assert respuesta.json()["estado"] == "expirada"
        assert respuesta.json()["pago_aprobado"] is False
    assert _asientos(app) == (4, 2)


def test_fallo_catalogo_no_bloquea_y_oferta_no_disponible_es_conflicto(
    cliente, app, claves, catalogo
):
    headers = {**autorizacion(claves), "Idempotency-Key": "fallo-catalogo"}
    catalogo.disponible = False
    caido = cliente.post("/api/v1/reservas", json=payload_reserva(), headers=headers)
    assert caido.status_code == 503
    assert _asientos(app) == (4, 0)

    catalogo.disponible = True
    catalogo.activa = False
    inactiva = cliente.post(
        "/api/v1/reservas",
        json=payload_reserva(),
        headers={**autorizacion(claves), "Idempotency-Key": "oferta-inactiva"},
    )
    assert inactiva.status_code == 409
    catalogo.activa = True
    catalogo.con_tarifa = False
    sin_tarifa = cliente.post(
        "/api/v1/reservas",
        json=payload_reserva(),
        headers={**autorizacion(claves), "Idempotency-Key": "oferta-sin-tarifa"},
    )
    assert sin_tarifa.status_code == 409
    assert _asientos(app) == (4, 0)


def test_sin_cupo_informa_disponibles(cliente, app, claves):
    with app.state.uow_factory() as uow:
        assert uow.franjas.bloquear_cupo_atomico(FRANJA_ID, 4)
        uow.commit()

    respuesta = crear_reserva(cliente, claves)

    assert respuesta.status_code == 409
    assert respuesta.json()["disponibles"] == 0
    assert "disponibles" in respuesta.json()["detail"]


def test_reserva_grupal_guarda_acompanantes_en_un_comprobante(cliente, app, claves):
    respuesta = crear_reserva(
        cliente, claves, personas=3, acompanantes=["Ana Pérez", "Luis Díaz"]
    )

    assert respuesta.status_code == 201
    assert respuesta.json()["personas"] == 3
    assert respuesta.json()["acompanantes"] == ["Ana Pérez", "Luis Díaz"]
    assert _asientos(app)[0] == 1


def test_cancelacion_aplica_reembolso_total_parcial_y_cero(cliente, claves, reloj):
    for indice, horas, porcentaje in ((0, 72, "100000.00"), (1, 36, "50000.00"), (2, 12, "0.00")):
        reserva = crear_reserva(cliente, claves, key=f"cancelar-{indice}").json()
        inicio = datetime.combine(
            FECHA_SERVICIO, time(10), tzinfo=ZONA_HORARIA_COLOMBIA
        )
        reloj[0] = inicio - timedelta(hours=horas)

        respuesta = cliente.post(
            f"/api/v1/reservas/{reserva['reserva_id']}/cancelar",
            headers=autorizacion(claves),
        )

        assert respuesta.status_code == 200
        assert respuesta.json()["estado"] == "cancelada"
        assert Decimal(str(respuesta.json()["monto_reembolso"])) == Decimal(porcentaje)
        reloj[0] = AHORA


def test_fallo_de_reembolso_deja_cancelacion_pendiente_y_emite_evento(
    cliente, app, claves
):
    reserva = crear_reserva(cliente, claves, tarjeta="4111111111110019").json()

    respuesta = cliente.post(
        f"/api/v1/reservas/{reserva['reserva_id']}/cancelar",
        headers=autorizacion(claves),
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "cancelacion_pendiente"
    with Session(app.state.engine) as session:
        eventos = session.execute(select(OutboxRegistro)).scalars().all()
    assert [evento.tipo for evento in eventos] == [
        "reservas.reserva.confirmada",
        "reservas.cancelacion.pendiente",
    ]
    assert _asientos(app)[0] == 4
    doble = cliente.post(
        f"/api/v1/reservas/{reserva['reserva_id']}/cancelar",
        headers=autorizacion(claves),
    )
    assert doble.status_code == 409


def test_seguridad_token_rol_y_acceso_a_comprobante(cliente, claves):
    assert cliente.get("/api/v1/reservas/mias").status_code == 401
    expirado = cliente.get(
        "/api/v1/reservas/mias",
        headers={"Authorization": f"Bearer {token(claves, minutos=-1)}"},
    )
    assert expirado.status_code == 401
    otra_clave = generar_par_claves_es256()
    token_no_confiable = emitir_token_prueba(otra_clave[0], "turista-1", "turista")
    firma_invalida = cliente.get(
        "/api/v1/reservas/mias",
        headers={"Authorization": f"Bearer {token_no_confiable}"},
    )
    assert firma_invalida.status_code == 401
    rol_incorrecto = cliente.post(
        "/api/v1/reservas",
        json=payload_reserva(),
        headers={**autorizacion(claves, rol="prestador"), "Idempotency-Key": "sin-permiso"},
    )
    assert rol_incorrecto.status_code == 403

    reserva = crear_reserva(cliente, claves).json()
    ajeno = cliente.get(
        f"/api/v1/reservas/{reserva['reserva_id']}",
        headers=autorizacion(claves, sujeto="turista-ajeno"),
    )
    assert ajeno.status_code == 403
    dueno = cliente.get(
        f"/api/v1/reservas/{reserva['reserva_id']}",
        headers=autorizacion(claves),
    )
    prestador = cliente.get(
        f"/api/v1/reservas/{reserva['reserva_id']}",
        headers=autorizacion(claves, PRESTADOR_ID, "prestador"),
    )
    admin = cliente.get(
        f"/api/v1/reservas/{reserva['reserva_id']}",
        headers=autorizacion(claves, "admin-1", "administrador"),
    )
    assert (dueno.status_code, prestador.status_code, admin.status_code) == (200, 200, 200)


def test_prestador_no_consulta_reservas_ajenas_ni_crea_franja_ajena(cliente, claves):
    consulta = cliente.get(
        "/api/v1/prestador/reservas?prestador_id=otro-prestador",
        headers=autorizacion(claves, PRESTADOR_ID, "prestador"),
    )
    assert consulta.status_code == 403
    franja = cliente.post(
        "/api/v1/prestador/franjas",
        json={
            "oferta_id": OFERTA_ID,
            "fecha": (FECHA_SERVICIO + timedelta(days=1)).isoformat(),
            "hora_inicio": "10:00:00",
            "cupo_total": 3,
        },
        headers=autorizacion(claves, "otro-prestador", "prestador"),
    )
    assert franja.status_code == 403


def _limitar_a_un_cupo(app) -> None:
    with app.state.engine.begin() as conn:
        conn.execute(
            update(FranjaDisponibilidadORM)
            .where(FranjaDisponibilidadORM.id == FRANJA_ID)
            .values(cupo_total=1, cupo_disponible=1)
        )


def _entrar_lista(cliente, claves, turista):
    return cliente.post(
        f"/api/v1/franjas/{FRANJA_ID}/lista-espera",
        json={"personas": 1, "correo_turista": f"{turista}@example.com"},
        headers=autorizacion(claves, turista),
    )


def _ocupar_y_formar_lista(cliente, claves, app, reloj):
    _limitar_a_un_cupo(app)
    reserva = crear_reserva(cliente, claves, key="ocupar-cupo").json()
    primero = _entrar_lista(cliente, claves, "turista-primero").json()
    reloj[0] += timedelta(microseconds=1)
    segundo = _entrar_lista(cliente, claves, "turista-segundo").json()
    assert primero["posicion"] == 1
    assert segundo["posicion"] == 2
    return reserva, primero, segundo


def test_lista_espera_solo_agotado_y_ofrece_al_primero(cliente, claves, app, reloj):
    hay_cupo = _entrar_lista(cliente, claves, "turista-primero")
    assert hay_cupo.status_code == 409
    reserva, primero, segundo = _ocupar_y_formar_lista(cliente, claves, app, reloj)
    cancelada = cliente.post(
        f"/api/v1/reservas/{reserva['reserva_id']}/cancelar",
        headers=autorizacion(claves),
    )
    assert cancelada.status_code == 200
    with app.state.engine.connect() as conn:
        estados = dict(
            conn.execute(
                select(EntradaListaEsperaORM.id, EntradaListaEsperaORM.estado)
            ).all()
        )
        cupo = conn.execute(
            select(FranjaDisponibilidadORM.cupo_disponible)
        ).scalar_one()
    assert estados[primero["entrada_id"]] == "ofrecida"
    assert estados[segundo["entrada_id"]] == "esperando"
    assert cupo == 0
    confirmada = cliente.post(
        "/api/v1/reservas",
        json=payload_reserva(entrada_lista_espera_id=primero["entrada_id"]),
        headers={
            **autorizacion(claves, "turista-primero"),
            "Idempotency-Key": "confirmar-lista",
        },
    )
    assert confirmada.status_code == 201
    assert confirmada.json()["estado"] == "confirmada"
    assert _asientos(app)[0] == 0


def test_oferta_vencida_pasa_al_siguiente_en_la_lista(cliente, claves, app, reloj):
    reserva, primero, segundo = _ocupar_y_formar_lista(cliente, claves, app, reloj)
    cliente.post(
        f"/api/v1/reservas/{reserva['reserva_id']}/cancelar",
        headers=autorizacion(claves),
    )
    reloj[0] += timedelta(minutes=31)

    expiradas = ExpirarOfertasListaEsperaUseCase(
        app.state.uow_factory, reloj=lambda: reloj[0]
    ).ejecutar()

    assert expiradas == 1
    with app.state.engine.connect() as conn:
        estados = dict(
            conn.execute(
                select(EntradaListaEsperaORM.id, EntradaListaEsperaORM.estado)
            ).all()
        )
        cupo = conn.execute(
            select(FranjaDisponibilidadORM.cupo_disponible)
        ).scalar_one()
    assert estados[primero["entrada_id"]] == "expirada"
    assert estados[segundo["entrada_id"]] == "ofrecida"
    assert cupo == 0


def test_retirarse_de_oferta_libera_y_ofrece_al_siguiente(cliente, claves, app, reloj):
    reserva, primero, segundo = _ocupar_y_formar_lista(cliente, claves, app, reloj)
    cliente.post(
        f"/api/v1/reservas/{reserva['reserva_id']}/cancelar",
        headers=autorizacion(claves),
    )
    retiro = cliente.delete(
        f"/api/v1/lista-espera/{primero['entrada_id']}",
        headers=autorizacion(claves, "turista-primero"),
    )
    assert retiro.status_code == 200
    assert retiro.json()["estado"] == "retirada"
    with app.state.engine.connect() as conn:
        estado = conn.execute(
            select(EntradaListaEsperaORM.estado).where(
                EntradaListaEsperaORM.id == segundo["entrada_id"]
            )
        ).scalar_one()
    assert estado == "ofrecida"


def test_disputa_aprobada_reembolsa_y_rechazo_de_pasarela_sigue_en_revision(
    cliente, claves
):
    for indice, tarjeta, esperado in (
        (0, "4111111111111111", 200),
        (1, "4111111111110019", 502),
    ):
        reserva = crear_reserva(
            cliente, claves, key=f"disputa-reserva-{indice}", tarjeta=tarjeta
        ).json()
        disputa = cliente.post(
            f"/api/v1/reservas/{reserva['reserva_id']}/disputas",
            json={"motivo": "El cobro no coincide con lo acordado"},
            headers=autorizacion(claves),
        )
        assert disputa.status_code == 201
        resuelta = cliente.post(
            f"/api/v1/admin/disputas/{disputa.json()['disputa_id']}/resolver",
            json={"decision": "aprobada", "justificacion": "Se verificó el cobro reportado"},
            headers=autorizacion(claves, "admin-1", "administrador"),
        )
        assert resuelta.status_code == esperado
        if esperado == 502:
            pendientes = cliente.get(
                "/api/v1/admin/disputas?estado=en_revision",
                headers=autorizacion(claves, "admin-1", "administrador"),
            )
            assert any(d["disputa_id"] == disputa.json()["disputa_id"] for d in pendientes.json())


def test_fechas_cercanas_y_filtros_de_historial(cliente, claves, app):
    with app.state.engine.begin() as conn:
        conn.execute(
            update(FranjaDisponibilidadORM)
            .where(FranjaDisponibilidadORM.id == FRANJA_ID)
            .values(cupo_disponible=0)
        )
    otra_fecha = FECHA_SERVICIO + timedelta(days=1)
    with app.state.uow_factory() as uow:
        uow.franjas.guardar(
            FranjaDisponibilidad(
                "franja-cercana", OFERTA_ID, "tayrona", PRESTADOR_ID, otra_fecha,
                time(10), 2, 2,
            )
        )
        uow.commit()
    cercanas = cliente.get(
        f"/api/v1/ofertas/{OFERTA_ID}/disponibilidad/cercanas",
        params={"fecha": FECHA_SERVICIO.isoformat()},
    )
    assert cercanas.status_code == 200
    assert [f["id"] for f in cercanas.json()] == ["franja-cercana"]

    crear_reserva(cliente, claves, franja_id="franja-cercana", key="filtro-confirmada")
    confirmadas = cliente.get(
        "/api/v1/reservas/mias?estado=confirmada",
        headers=autorizacion(claves),
    )
    assert confirmadas.status_code == 200
    assert len(confirmadas.json()) == 1
    por_fecha = cliente.get(
        f"/api/v1/reservas/mias?desde={otra_fecha.isoformat()}&hasta={otra_fecha.isoformat()}",
        headers=autorizacion(claves),
    )
    assert len(por_fecha.json()) == 1
    por_prestador = cliente.get(
        "/api/v1/reservas/mias?prestador_id=prestador-ajeno",
        headers=autorizacion(claves),
    )
    assert por_prestador.status_code == 200
    assert por_prestador.json() == []
