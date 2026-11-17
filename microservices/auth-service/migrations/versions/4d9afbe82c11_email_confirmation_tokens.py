"""add one-time email confirmation tokens

Revision ID: 4d9afbe82c11
Revises: b18fc3511ef1
Create Date: 2026-11-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "4d9afbe82c11"
down_revision: str | None = "b18fc3511ef1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "confirmacion_correo",
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["usuario.id"]),
        sa.PrimaryKeyConstraint("token_hash"),
    )
    op.create_index(
        "ix_confirmacion_correo_user_id",
        "confirmacion_correo",
        ["user_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_confirmacion_correo_user_id", table_name="confirmacion_correo")
    op.drop_table("confirmacion_correo")
