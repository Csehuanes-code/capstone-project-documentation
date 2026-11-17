"""La migración de Alembic crea exactamente el esquema de los modelos y los pesos v1."""

import os
from pathlib import Path

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect

from ia.infraestructura import semilla
from ia.infraestructura.sql.conexion import crear_sesiones
from ia.infraestructura.sql.repositorios import CriteriosSql
from ia.infraestructura.sql.tablas import Base
from ia.main import crear_app_con_base_de_datos

RAIZ = Path(__file__).resolve().parents[1]


@pytest.fixture
def url(tmp_path):
    # Con IA_TEST_DATABASE_URL (en CI) se prueba contra PostgreSQL real.
    externa = os.getenv("IA_TEST_DATABASE_URL")
    if externa:
        motor = create_engine(externa)
        Base.metadata.drop_all(motor)
        with motor.begin() as c:
            c.exec_driver_sql("DROP TABLE IF EXISTS alembic_version")
        motor.dispose()
        return externa
    return f"sqlite+pysqlite:///{(tmp_path / 'ia.db').as_posix()}"


def _config(url: str) -> Config:
    cfg = Config(str(RAIZ / "alembic.ini"))
    cfg.set_main_option("script_location", str(RAIZ / "migraciones"))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


def test_upgrade_crea_el_esquema_de_los_modelos(url):
    command.upgrade(_config(url), "head")
    motor = create_engine(url)
    with motor.connect() as conexion:
        # compare_type=False: PostgreSQL refleja FLOAT como DOUBLE PRECISION y daría falsos avisos.
        contexto = MigrationContext.configure(conexion, opts={"compare_type": False})
        diferencias = compare_metadata(contexto, Base.metadata)
    motor.dispose()
    assert diferencias == [], f"La migración no coincide con tablas.py: {diferencias}"


def test_upgrade_inserta_los_pesos_v1(url):
    command.upgrade(_config(url), "head")
    motor = create_engine(url)
    assert CriteriosSql(crear_sesiones(motor)).vigente() == semilla.CRITERIOS_V1
    motor.dispose()


def test_la_app_funciona_sobre_la_base_migrada(url):
    command.upgrade(_config(url), "head")
    cliente = TestClient(crear_app_con_base_de_datos(url, sembrar=True))
    assert cliente.get("/health/ready").status_code == 200
    r = cliente.get("/api/v1/ia/recomendaciones", params={"intereses": "naturaleza"})
    assert r.status_code == 200 and r.json()["items"]


def test_downgrade_deja_la_base_vacia(url):
    cfg = _config(url)
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "base")
    motor = create_engine(url)
    assert set(inspect(motor).get_table_names()) <= {"alembic_version"}
    motor.dispose()
