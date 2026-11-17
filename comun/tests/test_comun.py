import json
import logging
import uuid
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from comun.correlacion import CorrelationIdMiddleware, obtener_correlation_id
from comun.eventos import (
    ConsumidorIdempotente,
    EventoProcesadoRegistro,
    OutboxBase,
    OutboxRegistro,
    ProcesadorOutbox,
    SobreEvento,
    registrar_en_outbox,
)
from comun.logging_json import JsonFormatter, RequestLoggingMiddleware
from comun.salud import crear_router_salud
from comun.seguridad import (
    Identidad,
    ValidadorJWT,
    crear_dependencia_identidad,
    emitir_token_prueba,
    generar_par_claves_es256,
    requiere_rol,
)


class FakeBroker:
    def __init__(self, fallar: bool = False):
        self.fallar = fallar
        self.mensajes: list[tuple[str, str, str]] = []

    def publicar(self, routing_key: str, cuerpo_json: str, message_id: str) -> None:
        if self.fallar:
            raise ConnectionError("RabbitMQ caído")
        self.mensajes.append((routing_key, cuerpo_json, message_id))


def _crear_sesion_sqlite():
    engine = create_engine("sqlite:///:memory:")
    OutboxBase.metadata.create_all(engine)
    return sessionmaker(bind=engine)


def test_jwt_es256_y_roles():
    priv, pub = generar_par_claves_es256()
    validador = ValidadorJWT(clave_publica_pem=pub)
    dep_id = crear_dependencia_identidad(validador)

    app = FastAPI()

    @app.get("/solo-turista")
    def solo_turista(identidad: Identidad = Depends(requiere_rol(dep_id, "turista"))):
        return {"sub": identidad.sub, "rol": identidad.rol}

    client = TestClient(app)

    # Sin token -> 401
    assert client.get("/solo-turista").status_code == 401

    # Token expirado -> 401
    tok_exp = emitir_token_prueba(priv, sub="u-1", rol="turista", minutos_validez=-5)
    assert client.get("/solo-turista", headers={"Authorization": f"Bearer {tok_exp}"}).status_code == 401

    # Rol incorrecto -> 403
    tok_prest = emitir_token_prueba(priv, sub="p-1", rol="prestador")
    assert client.get("/solo-turista", headers={"Authorization": f"Bearer {tok_prest}"}).status_code == 403

    # Rol válido -> 200
    tok_ok = emitir_token_prueba(priv, sub="t-1", rol="turista")
    r = client.get("/solo-turista", headers={"Authorization": f"Bearer {tok_ok}"})
    assert r.status_code == 200
    assert r.json() == {"sub": "t-1", "rol": "turista"}


def test_correlation_id_y_logs_json(caplog):
    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware, nombre_servicio="prueba")
    app.add_middleware(CorrelationIdMiddleware)

    @app.get("/ping")
    def ping():
        return {"cid": obtener_correlation_id()}

    client = TestClient(app)
    r1 = client.get("/ping")
    assert r1.status_code == 200
    cid_generado = r1.headers["X-Correlation-Id"]
    assert uuid.UUID(cid_generado)
    assert r1.json()["cid"] == cid_generado

    r2 = client.get("/ping", headers={"X-Correlation-Id": "mi-cid-123"})
    assert r2.headers["X-Correlation-Id"] == "mi-cid-123"
    assert r2.json()["cid"] == "mi-cid-123"

    # Verificar formato JSON del logger
    record = logging.LogRecord("prueba", logging.INFO, "", 1, "hola mundo", (), None)
    record.correlation_id = "cid-log-1"
    record.ruta = "/ping"
    record.duracion_ms = 12.5
    salida = json.loads(JsonFormatter("prueba").format(record))
    assert salida["servicio"] == "prueba"
    assert salida["correlation_id"] == "cid-log-1"
    assert salida["ruta"] == "/ping"
    assert salida["duracion_ms"] == 12.5


def test_outbox_reenvio_y_tolerancia_caida_broker():
    SessionLocal = _crear_sesion_sqlite()
    with SessionLocal() as s:
        sobre = registrar_en_outbox(
            s,
            tipo="reservas.reserva.confirmada",
            datos={"reserva_id": "SMT-123"},
            correlation_id="cid-99",
        )
        s.commit()

    # Broker caído: no marca publicado_en y no lanza excepción no controlada
    broker_caido = FakeBroker(fallar=True)
    proc_caido = ProcesadorOutbox(SessionLocal, broker_caido)
    assert proc_caido.procesar_pendientes() == 0

    with SessionLocal() as s:
        reg = s.get(OutboxRegistro, sobre.evento_id)
        assert reg.publicado_en is None
        assert reg.intentos == 1

    # Broker recuperado: publica y marca publicado_en
    broker_ok = FakeBroker(fallar=False)
    proc_ok = ProcesadorOutbox(SessionLocal, broker_ok)
    assert proc_ok.procesar_pendientes() == 1
    assert len(broker_ok.mensajes) == 1
    routing_key, cuerpo, msg_id = broker_ok.mensajes[0]
    assert routing_key == "reservas.reserva.confirmada"
    assert msg_id == sobre.evento_id
    parsed = json.loads(cuerpo)
    assert parsed["correlation_id"] == "cid-99"
    assert parsed["datos"] == {"reserva_id": "SMT-123"}

    # Segunda ejecución no duplica
    assert proc_ok.procesar_pendientes() == 0


def test_consumidor_idempotente():
    SessionLocal = _crear_sesion_sqlite()
    ejecuciones = []

    def manejar_oferta(sesion, sobre: SobreEvento):
        ejecuciones.append(sobre.datos["oferta_id"])

    consumidor = ConsumidorIdempotente(
        SessionLocal,
        manejadores={"catalogo.oferta.publicada": manejar_oferta},
    )
    sobre = SobreEvento(
        tipo="catalogo.oferta.publicada",
        datos={"oferta_id": "minca-cascadas"},
    )
    raw = sobre.model_dump_json()

    assert consumidor.procesar_mensaje_raw(raw) is True
    assert consumidor.procesar_mensaje_raw(raw) is False  # Duplicado descartado
    assert ejecuciones == ["minca-cascadas"]


def test_healthcheck_endpoints():
    estado = {"db": True, "mq": True}
    app = FastAPI()
    app.include_router(
        crear_router_salud(
            "reservas",
            verificar_db=lambda: estado["db"],
            verificar_broker=lambda: estado["mq"],
        )
    )
    client = TestClient(app)

    assert client.get("/health").status_code == 200
    assert client.get("/health/ready").status_code == 200

    estado["mq"] = False
    r_503 = client.get("/health/ready")
    assert r_503.status_code == 503
    assert r_503.json()["dependencias"]["rabbitmq"] == "error"


# --- Compatibilidad con los tokens de Auth (ADR-06) --------------------------------------

def _app_protegida(validador: ValidadorJWT) -> TestClient:
    dep_id = crear_dependencia_identidad(validador)
    app = FastAPI()

    @app.get("/yo")
    def yo(identidad: Identidad = Depends(dep_id)):
        return {"sub": identidad.sub, "rol": identidad.rol}

    return TestClient(app)


def test_acepta_token_con_los_claims_y_valores_de_auth():
    """Mismos claims y valores por defecto que auth-service (iss localhost:8001, aud santa-marta-platform)."""
    import jwt as pyjwt
    from datetime import datetime, timedelta, timezone

    priv, pub = generar_par_claves_es256()
    ahora = datetime.now(timezone.utc)
    token_como_auth = pyjwt.encode(
        {
            "sub": str(uuid.uuid4()), "rol": "prestador", "iss": "http://localhost:8001",
            "aud": "santa-marta-platform", "iat": int(ahora.timestamp()), "nbf": int(ahora.timestamp()),
            "exp": int((ahora + timedelta(minutes=15)).timestamp()), "jti": str(uuid.uuid4()),
        },
        priv, algorithm="ES256", headers={"kid": "auth-local-1", "typ": "JWT"},
    )
    r = _app_protegida(ValidadorJWT(clave_publica_pem=pub)).get(
        "/yo", headers={"Authorization": f"Bearer {token_como_auth}"}
    )
    assert r.status_code == 200 and r.json()["rol"] == "prestador"


@pytest.mark.parametrize(
    "cambios",
    [
        pytest.param({"issuer": "otro-emisor"}, id="otro-emisor"),
        pytest.param({"audience": "otra-audiencia"}, id="otra-audiencia"),
    ],
)
def test_rechaza_otro_emisor_o_audiencia(cambios):
    priv, pub = generar_par_claves_es256()
    token = emitir_token_prueba(priv, sub="t-1", rol="turista", **cambios)
    r = _app_protegida(ValidadorJWT(clave_publica_pem=pub)).get(
        "/yo", headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 401


def test_rechaza_firma_de_otra_clave_hs256_y_sin_jti():
    import jwt as pyjwt
    from datetime import datetime, timedelta, timezone

    priv, pub = generar_par_claves_es256()
    otra_priv, _ = generar_par_claves_es256()
    cliente = _app_protegida(ValidadorJWT(clave_publica_pem=pub))
    ahora = datetime.now(timezone.utc)
    base = {"sub": "t-1", "rol": "administrador", "iss": "http://localhost:8001",
            "aud": "santa-marta-platform", "iat": ahora, "exp": ahora + timedelta(minutes=5)}
    malos = [
        emitir_token_prueba(otra_priv, sub="t-1", rol="administrador"),
        pyjwt.encode({**base, "jti": "x"}, "clave-compartida-de-al-menos-32-bytes!!", algorithm="HS256"),
        pyjwt.encode(base, priv, algorithm="ES256"),  # falta jti
    ]
    for token in malos:
        assert cliente.get("/yo", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_sin_clave_configurada_falla_cerrado(monkeypatch):
    monkeypatch.delenv("JWT_CLAVE_PUBLICA", raising=False)
    monkeypatch.delenv("JWT_CLAVE_PUBLICA_FILE", raising=False)
    priv, _ = generar_par_claves_es256()
    token = emitir_token_prueba(priv, sub="t-1", rol="turista")
    r = _app_protegida(ValidadorJWT()).get("/yo", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401


def test_lee_clave_e_issuer_desde_entorno(monkeypatch, tmp_path):
    priv, pub = generar_par_claves_es256()
    archivo = tmp_path / "auth-publica.pem"
    archivo.write_text(pub, encoding="utf-8")
    monkeypatch.delenv("JWT_CLAVE_PUBLICA", raising=False)
    monkeypatch.setenv("JWT_CLAVE_PUBLICA_FILE", str(archivo))
    monkeypatch.setenv("JWT_ISSUER", "http://auth:8001")
    token = emitir_token_prueba(priv, sub="t-1", rol="turista", issuer="http://auth:8001")
    r = _app_protegida(ValidadorJWT()).get("/yo", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
