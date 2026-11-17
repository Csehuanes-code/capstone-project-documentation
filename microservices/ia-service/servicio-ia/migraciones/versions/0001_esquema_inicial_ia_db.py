"""Esquema inicial de ia_db + pesos versión 1 (ADR-07).

Revision ID: 0001
Revises:
Create Date: 2026-11-14
"""

import json
from datetime import datetime, timezone
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import context, op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

Json = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")
Fecha = sa.DateTime(timezone=True)

# Copiadas aquí (no importadas) para que la migración no cambie si cambia el código.
FUNCION_INMUTABLE = """
CREATE OR REPLACE FUNCTION configuracion_criterios_inmutable() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'configuracion_criterios es inmutable: cree una version nueva';
END;
$$ LANGUAGE plpgsql
"""
TRIGGER_INMUTABLE = """
CREATE TRIGGER tg_configuracion_criterios_inmutable
    BEFORE UPDATE OR DELETE ON configuracion_criterios
    FOR EACH ROW EXECUTE FUNCTION configuracion_criterios_inmutable()
"""


def upgrade() -> None:
    criterios = op.create_table(
        "configuracion_criterios",
        sa.Column("version", sa.Integer(), autoincrement=False, primary_key=True),
        sa.Column("pesos", Json, nullable=False),
        sa.Column("umbral_tranquila", sa.Float(), nullable=False),
        sa.Column("umbral_saturacion", sa.Float(), nullable=False),
        sa.Column("prior_media", sa.Float(), nullable=False),
        sa.Column("prior_peso", sa.Integer(), nullable=False),
        sa.Column("max_por_zona", sa.Integer(), nullable=False),
        sa.Column("creada_en", Fecha, nullable=False),
    )
    op.create_table(
        "estado_zona",
        sa.Column("zona_id", sa.String(64), primary_key=True),
        sa.Column("nombre", sa.String(200), nullable=False),
        sa.Column("ocupacion", sa.Float(), nullable=False),
        sa.Column("actualizado_en", Fecha, nullable=False),
        sa.CheckConstraint("ocupacion >= 0", name="ck_zona_ocupacion"),
    )
    op.create_table(
        "proyeccion_oferta",
        sa.Column("oferta_id", sa.String(64), primary_key=True),
        sa.Column("nombre", sa.String(200), nullable=False),
        sa.Column("zona_id", sa.String(64), nullable=False, index=True),
        sa.Column("categorias", Json, nullable=False),
        sa.Column("calificacion_promedio", sa.Float(), nullable=False),
        sa.Column("numero_resenas", sa.Integer(), nullable=False),
        sa.Column("indice_sostenibilidad", sa.Float(), nullable=False),
        sa.Column("prestador_id", sa.String(64), nullable=False),
        sa.Column("activa", sa.Boolean(), nullable=False, index=True),
        sa.Column("reservas_confirmadas", sa.Integer(), nullable=False),
        sa.CheckConstraint("calificacion_promedio BETWEEN 0 AND 5", name="ck_oferta_calificacion"),
        sa.CheckConstraint("numero_resenas >= 0", name="ck_oferta_resenas"),
        sa.CheckConstraint("indice_sostenibilidad BETWEEN 0 AND 1", name="ck_oferta_sostenibilidad"),
        sa.CheckConstraint("reservas_confirmadas >= 0", name="ck_oferta_reservas"),
    )
    op.create_table(
        "recomendacion",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("turista_id", sa.String(64), nullable=True, index=True),
        sa.Column("intereses", Json, nullable=False),
        sa.Column(
            "version_pesos",
            sa.Integer(),
            sa.ForeignKey("configuracion_criterios.version"),
            nullable=False,
        ),
        sa.Column("generada_en", Fecha, nullable=False),
    )
    op.create_table(
        "item_recomendado",
        sa.Column(
            "recomendacion_id",
            sa.Uuid(),
            sa.ForeignKey("recomendacion.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("posicion", sa.Integer(), primary_key=True),
        sa.Column("oferta_id", sa.String(64), nullable=False, index=True),
        sa.Column("nombre", sa.String(200), nullable=False),
        sa.Column("zona_id", sa.String(64), nullable=False),
        sa.Column("zona_nombre", sa.String(200), nullable=True),
        sa.Column("ocupacion", sa.Float(), nullable=True),
        sa.Column("nivel", sa.String(20), nullable=False),
        sa.Column("calificacion_promedio", sa.Float(), nullable=False),
        sa.Column("numero_resenas", sa.Integer(), nullable=False),
        sa.Column("puntaje", sa.Float(), nullable=False),
        sa.Column("desglose", Json, nullable=False),
        sa.Column("coincidencias", Json, nullable=False),
        sa.Column("motivo", sa.String(40), nullable=False),
        sa.Column("alternativa_de_id", sa.String(64), nullable=True),
        sa.Column("alternativa_de_nombre", sa.String(200), nullable=True),
        sa.Column("alternativa_de_zona", sa.String(200), nullable=True),
    )
    op.create_table(
        "evento_procesado",
        sa.Column("evento_id", sa.String(100), primary_key=True),
        sa.Column("procesado_en", Fecha, nullable=False),
    )
    op.create_table(
        "outbox",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tipo", sa.String(100), nullable=False),
        sa.Column("payload", Json, nullable=False),
        sa.Column("creado_en", Fecha, nullable=False),
        sa.Column("publicado_en", Fecha, nullable=True, index=True),
    )

    # Pesos versión 1: configuración real del producto, no datos de prueba.
    pesos_v1 = {"afinidad": 0.45, "calidad": 0.25, "descongestion": 0.20, "sostenibilidad": 0.10}
    if context.is_offline_mode():
        # En "alembic upgrade head --sql" el JSON va como texto literal (PostgreSQL lo convierte).
        criterios = sa.table(
            "configuracion_criterios",
            *(sa.column(c.name, c.type) for c in criterios.c if c.name != "pesos"),
            sa.column("pesos", sa.Text()),
        )
        pesos_v1 = json.dumps(pesos_v1)
    op.bulk_insert(
        criterios,
        [
            {
                "version": 1,
                "pesos": pesos_v1,
                "umbral_tranquila": 0.5,
                "umbral_saturacion": 0.8,
                "prior_media": 4.3,
                "prior_peso": 10,
                "max_por_zona": 2,
                "creada_en": datetime(2026, 11, 14, 8, 0, tzinfo=timezone.utc),
            }
        ],
    )

    if op.get_context().dialect.name == "postgresql":
        op.execute(FUNCION_INMUTABLE)
        op.execute(TRIGGER_INMUTABLE)


def downgrade() -> None:
    if op.get_context().dialect.name == "postgresql":
        op.execute(
            "DROP TRIGGER IF EXISTS tg_configuracion_criterios_inmutable ON configuracion_criterios"
        )
        op.execute("DROP FUNCTION IF EXISTS configuracion_criterios_inmutable()")
    op.drop_table("outbox")
    op.drop_table("evento_procesado")
    op.drop_table("item_recomendado")
    op.drop_table("recomendacion")
    op.drop_table("proyeccion_oferta")
    op.drop_table("estado_zona")
    op.drop_table("configuracion_criterios")
