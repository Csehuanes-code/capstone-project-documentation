import pytest
from fastapi.testclient import TestClient

from ia.main import crear_app_con_base_de_datos, crear_app_en_memoria


@pytest.fixture(params=["memoria", "sql"])
def cliente(request):
    if request.param == "memoria":
        return TestClient(crear_app_en_memoria())
    return TestClient(
        crear_app_con_base_de_datos("sqlite+pysqlite:///:memory:", sembrar=True, con_esquema=True)
    )


def test_health(cliente):
    assert cliente.get("/health").json() == {"estado": "ok", "servicio": "ia"}


def test_ready(cliente):
    r = cliente.get("/health/ready")
    assert r.status_code == 200
    assert r.json()["estado"] == "listo"


def test_ready_responde_503_si_la_base_no_responde():
    # Carpeta inexistente: la conexión falla al primer uso, no al crear la app.
    app = crear_app_con_base_de_datos("sqlite+pysqlite:///no/existe/esta/carpeta/ia.db")
    r = TestClient(app).get("/health/ready")
    assert r.status_code == 503
    assert r.json()["dependencias"] == {"base_de_datos": False}
    assert TestClient(app).get("/health").status_code == 200  # el proceso sigue vivo


def test_recomendaciones(cliente):
    r = cliente.get("/api/v1/ia/recomendaciones", params={"intereses": "naturaleza,cultura"})
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["version_pesos"] == 1
    assert cuerpo["intereses"] == ["cultura", "naturaleza"]
    item = cuerpo["items"][0]
    assert {a["criterio"] for a in item["desglose"]} == {
        "afinidad", "calidad", "descongestion", "sostenibilidad"
    }
    assert item["explicacion"]
    assert item["puntaje"] == pytest.approx(sum(a["aporte"] for a in item["desglose"]), abs=1e-3)


def test_recomendaciones_en_ingles(cliente):
    r = cliente.get("/api/v1/ia/recomendaciones", params={"intereses": "naturaleza", "idioma": "en"})
    assert r.json()["items"][0]["desglose"][0]["etiqueta"] == "Match with your interests"


def test_por_que_veo_esto(cliente):
    emitida = cliente.get("/api/v1/ia/recomendaciones", params={"intereses": "cultura"}).json()
    consultada = cliente.get(f"/api/v1/ia/recomendaciones/{emitida['id']}").json()
    assert consultada["items"] == emitida["items"]


def test_recomendacion_inexistente(cliente):
    r = cliente.get("/api/v1/ia/recomendaciones/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404


def test_limite_fuera_de_rango(cliente):
    assert cliente.get("/api/v1/ia/recomendaciones", params={"limite": 99}).status_code == 422


def test_criterios(cliente):
    cuerpo = cliente.get("/api/v1/ia/criterios").json()
    assert cuerpo["version"] == 1
    assert sum(p["peso"] for p in cuerpo["pesos"]) == pytest.approx(1)
    assert cliente.get("/api/v1/ia/criterios", params={"version": 9}).status_code == 404


def test_populares(cliente):
    cuerpo = cliente.get("/api/v1/ia/populares", params={"limite": 2}).json()
    assert [p["oferta_id"] for p in cuerpo] == ["playa-cristal", "pueblito-caminata"]


def test_openapi_disponible(cliente):
    rutas = cliente.get("/openapi.json").json()["paths"]
    assert "/api/v1/ia/recomendaciones" in rutas
