import json
from pathlib import Path

import jsonschema
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from comun.eventos import ConsumidorIdempotente, OutboxRegistro, SobreEvento
from reservas.infraestructura.rabbitmq import (
    TIPOS_OFERTA,
    manejar_evento_oferta_catalogo,
)
from reservas.infraestructura.sql.tablas import BaseReservas, ProyeccionOfertaORM


RAIZ_REPO = Path(__file__).resolve().parents[3]


def test_evento_confirmacion_cumple_contratos_y_no_expone_datos_personales(
    cliente, claves, app
):
    from conftest import crear_reserva

    reserva = crear_reserva(cliente, claves).json()
    with Session(app.state.engine) as session:
        evento = session.execute(select(OutboxRegistro)).scalar_one()
    sobre = {
        "evento_id": evento.evento_id,
        "tipo": evento.tipo,
        "version": evento.version,
        "ocurrido_en": evento.ocurrido_en,
        "correlation_id": evento.correlation_id,
        "datos": evento.datos,
    }
    contratos = RAIZ_REPO / "contratos" / "eventos"
    schema_sobre = json.loads((contratos / "sobre-evento.schema.json").read_text())
    schema_datos = json.loads(
        (contratos / "reservas.reserva.confirmada.schema.json").read_text()
    )
    jsonschema.validate(sobre, schema_sobre)
    jsonschema.validate(sobre["datos"], schema_datos)
    assert sobre["tipo"] == "reservas.reserva.confirmada"
    assert sobre["datos"]["reserva_id"] == reserva["codigo"]
    assert not {
        "turista_id",
        "correo_turista",
        "nombre_completo",
        "documento",
    }.intersection(sobre["datos"])


def test_consumidor_proyecta_evento_una_sola_vez_y_rechaza_datos_invalidos(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'eventos.sqlite'}")
    BaseReservas.metadata.create_all(engine)
    sesiones = sessionmaker(engine, expire_on_commit=False)
    consumidor = ConsumidorIdempotente(
        sesiones,
        manejadores={tipo: manejar_evento_oferta_catalogo for tipo in TIPOS_OFERTA},
    )
    sobre = SobreEvento(
        tipo="catalogo.oferta.publicada",
        datos={
            "oferta_id": "oferta-1",
            "nombre": "Tour",
            "zona_id": "tayrona",
            "prestador_id": "prestador-1",
            "activa": True,
        },
    )

    assert consumidor.procesar_mensaje_raw(sobre.model_dump_json()) is True
    assert consumidor.procesar_mensaje_raw(sobre.model_dump_json()) is False
    with sesiones() as session:
        proyeccion = session.get(ProyeccionOfertaORM, "oferta-1")
        assert proyeccion is not None
        assert proyeccion.activa is True

    invalido = SobreEvento(
        tipo="catalogo.oferta.actualizada",
        datos={"oferta_id": "oferta-2", "nombre": "Tour", "activa": "si"},
    )
    with pytest.raises(ValueError, match="zona_id"):
        consumidor.procesar_mensaje_raw(invalido.model_dump_json())
    engine.dispose()


def test_solicitud_de_correo_de_auth_queda_como_notificacion(tmp_path):
    from reservas.infraestructura.rabbitmq import (
        TIPO_NOTIFICACION_AUTH,
        crear_manejador_notificacion_auth,
    )
    from reservas.infraestructura.sql.tablas import NotificacionORM

    engine = create_engine(f"sqlite:///{tmp_path / 'auth.sqlite'}")
    BaseReservas.metadata.create_all(engine)
    sesiones = sessionmaker(engine, expire_on_commit=False)
    consumidor = ConsumidorIdempotente(
        sesiones,
        manejadores={TIPO_NOTIFICACION_AUTH: crear_manejador_notificacion_auth("http://front")},
    )
    # Lo que escribe auth-service en su outbox al registrar un usuario.
    sobre = SobreEvento(
        tipo=TIPO_NOTIFICACION_AUTH,
        datos={
            "tipo": "confirmacion_registro",
            "destinatario_id": "u-1",
            "correo": "nuevo@ejemplo.com",
            "token_confirmacion": "tok-123",
            "expira_en": "2026-11-18T00:00:00+00:00",
            "idioma": "es",
        },
    )
    assert consumidor.procesar_mensaje_raw(sobre.model_dump_json()) is True
    assert consumidor.procesar_mensaje_raw(sobre.model_dump_json()) is False
    with sesiones() as session:
        (notificacion,) = session.query(NotificacionORM).all()
    assert notificacion.correo_destino == "nuevo@ejemplo.com"
    assert "http://front/confirmar?token=tok-123" in notificacion.cuerpo_texto
    assert notificacion.enviada is False  # la envía el proceso de fondo
