"""Alinea índices y unicidad de la base con los modelos (alembic check sin diferencias).

La 001 creó restricciones UNIQUE (zona_codigo_key, tipo_servicio_codigo_key,
calificacion_reserva_id_key) más índices normales; los modelos declaran índices ÚNICOS
(`unique=True, index=True`). Ambas formas impiden duplicados, pero no coincidían, y además
faltaba el índice de calificacion.turista_id que el modelo declara.

Revision ID: 002_alinear_indices
Revises: 001_initial
"""

from collections.abc import Sequence

from alembic import op

revision: str = "002_alinear_indices"
down_revision: str | None = "001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# (tabla, columna, restricción UNIQUE creada por la 001, índice)
_UNICOS = [
    ("zona", "codigo", "zona_codigo_key", "ix_zona_codigo"),
    ("tipo_servicio", "codigo", "tipo_servicio_codigo_key", "ix_tipo_servicio_codigo"),
    ("calificacion", "reserva_id", "calificacion_reserva_id_key", "ix_calificacion_reserva_id"),
]


def upgrade() -> None:
    for tabla, columna, restriccion, indice in _UNICOS:
        # Primero el índice único (la unicidad nunca deja de estar garantizada), luego se
        # quitan la restricción y el índice normal que lo duplicaban.
        op.drop_index(indice, table_name=tabla)
        op.create_index(indice, tabla, [columna], unique=True)
        op.drop_constraint(restriccion, tabla, type_="unique")
    op.create_index("ix_calificacion_turista_id", "calificacion", ["turista_id"])


def downgrade() -> None:
    op.drop_index("ix_calificacion_turista_id", table_name="calificacion")
    for tabla, columna, restriccion, indice in _UNICOS:
        op.create_unique_constraint(restriccion, tabla, [columna])
        op.drop_index(indice, table_name=tabla)
        op.create_index(indice, tabla, [columna])
