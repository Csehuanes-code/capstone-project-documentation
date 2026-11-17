import os
from pathlib import Path
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from reservas.infraestructura.sql.tablas import BaseReservas

RAIZ = Path(__file__).resolve().parents[1]


def _aplicar_y_comparar(url: str) -> None:
    config = Config(str(RAIZ / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    command.upgrade(config, "head")
    command.check(config)
    engine = create_engine(url)
    inspector = inspect(engine)
    tablas_migradas = set(inspector.get_table_names()) - {"alembic_version"}
    tablas_modelos = set(BaseReservas.metadata.tables)
    assert tablas_migradas == tablas_modelos
    for tabla in tablas_modelos:
        columnas_db = {columna["name"] for columna in inspector.get_columns(tabla)}
        columnas_modelo = set(BaseReservas.metadata.tables[tabla].columns.keys())
        assert columnas_db == columnas_modelo, tabla
    engine.dispose()


def test_migracion_inicial_equivale_a_modelos_en_sqlite(tmp_path):
    _aplicar_y_comparar(f"sqlite:///{tmp_path / 'migracion.sqlite'}")


def test_migracion_inicial_equivale_a_modelos_en_postgresql_si_configurado():
    url = os.getenv("RESERVAS_TEST_DATABASE_URL")
    if not url:
        import pytest

        pytest.skip("RESERVAS_TEST_DATABASE_URL no está configurada")
    _aplicar_y_comparar(url)
