"""add outbox leases and retry scheduling

Revision ID: 7a6dc0c93b20
Revises: 4d9afbe82c11
Create Date: 2026-11-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "7a6dc0c93b20"
down_revision: str | None = "4d9afbe82c11"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "outbox",
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "outbox",
        sa.Column(
            "available_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.add_column(
        "outbox",
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("outbox", sa.Column("lease_token", sa.Uuid(), nullable=True))
    op.add_column("outbox", sa.Column("last_error", sa.String(length=120), nullable=True))
    op.create_index("ix_outbox_available_at", "outbox", ["available_at"])
    op.create_index("ix_outbox_locked_until", "outbox", ["locked_until"])


def downgrade() -> None:
    op.drop_index("ix_outbox_locked_until", table_name="outbox")
    op.drop_index("ix_outbox_available_at", table_name="outbox")
    op.drop_column("outbox", "last_error")
    op.drop_column("outbox", "lease_token")
    op.drop_column("outbox", "locked_until")
    op.drop_column("outbox", "available_at")
    op.drop_column("outbox", "attempts")
