"""Hechos de reservas, umbrales, alertas y outbox."""

import sqlalchemy as sa
from alembic import op

revision = "0001_analitica"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reserva_hecho",
        sa.Column("evento_id", sa.String(36), primary_key=True),
        sa.Column("reserva_id", sa.String(100), nullable=False, unique=True),
        sa.Column("oferta_id", sa.String(100), nullable=False),
        sa.Column("zona_id", sa.String(40), nullable=False),
        sa.Column("personas", sa.Integer(), nullable=False),
        sa.Column("fecha_servicio", sa.Date(), nullable=False),
        sa.Column("total", sa.Numeric(14, 2), nullable=False),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_reserva_hecho_zona_id", "reserva_hecho", ["zona_id"])
    op.create_index("ix_reserva_hecho_fecha_servicio", "reserva_hecho", ["fecha_servicio"])
    op.create_table(
        "evento_procesado",
        sa.Column("evento_id", sa.String(36), primary_key=True),
        sa.Column("tipo", sa.String(100), nullable=False),
        sa.Column("procesado_en", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "umbral_zona",
        sa.Column("zona_id", sa.String(40), primary_key=True),
        sa.Column("visitantes_maximos", sa.Integer(), nullable=False),
        sa.Column("periodo_dias", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "alerta_capacidad",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("zona_id", sa.String(40), nullable=False),
        sa.Column("ocupacion", sa.Numeric(10, 4), nullable=False),
        sa.Column("visitantes", sa.Integer(), nullable=False),
        sa.Column("umbral", sa.Integer(), nullable=False),
        sa.Column("creada_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resuelta_en", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_alerta_capacidad_zona_id", "alerta_capacidad", ["zona_id"])
    op.create_table(
        "outbox_evento",
        sa.Column("evento_id", sa.String(36), primary_key=True),
        sa.Column("tipo", sa.String(100), nullable=False),
        sa.Column("datos", sa.JSON(), nullable=False),
        sa.Column("ocurrido_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("publicado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("intentos", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("disponible_en", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("outbox_evento")
    op.drop_index("ix_alerta_capacidad_zona_id", table_name="alerta_capacidad")
    op.drop_table("alerta_capacidad")
    op.drop_table("umbral_zona")
    op.drop_table("evento_procesado")
    op.drop_index("ix_reserva_hecho_fecha_servicio", table_name="reserva_hecho")
    op.drop_index("ix_reserva_hecho_zona_id", table_name="reserva_hecho")
    op.drop_table("reserva_hecho")
