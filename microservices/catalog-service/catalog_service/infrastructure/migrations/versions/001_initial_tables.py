"""Initial migration creating all 12 tables + outbox + evento_procesado for catalogo_db.

Revision ID: 001_initial
Revises:
Create Date: 2026-11-16 15:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. zona
    op.create_table(
        "zona",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("codigo", sa.String(20), nullable=False, unique=True),
        sa.Column("nombre_es", sa.String(120), nullable=False),
        sa.Column("nombre_en", sa.String(120), nullable=False),
        sa.Column(
            "ecosistema_sensible", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column("latitud", sa.Float(), nullable=True),
        sa.Column("longitud", sa.Float(), nullable=True),
    )
    op.create_index("ix_zona_codigo", "zona", ["codigo"])

    # 2. tipo_servicio
    op.create_table(
        "tipo_servicio",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("codigo", sa.String(40), nullable=False, unique=True),
        sa.Column("nombre_es", sa.String(80), nullable=False),
        sa.Column("nombre_en", sa.String(80), nullable=False),
        sa.Column("reservable", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("esquema_atributos", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.create_index("ix_tipo_servicio_codigo", "tipo_servicio", ["codigo"])

    # 3. perfil_prestador
    op.create_table(
        "perfil_prestador",
        sa.Column("prestador_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("nombre_comercial", sa.String(160), nullable=False),
        sa.Column("numero_rnt", sa.String(20), nullable=True),
        sa.Column("verificado", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("categoria", sa.String(30), nullable=False, server_default="pequeno_mediano"),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), nullable=True),
    )

    # 4. fuente_externa
    op.create_table(
        "fuente_externa",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("nombre", sa.String(120), nullable=False),
        sa.Column("tipo", sa.String(20), nullable=False, server_default="api"),
        sa.Column("integracion_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("activa", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )

    # 5. oferta
    op.create_table(
        "oferta",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "prestador_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("perfil_prestador.prestador_id"),
            nullable=True,
        ),
        sa.Column(
            "tipo_servicio_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tipo_servicio.id"),
            nullable=False,
        ),
        sa.Column(
            "zona_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("zona.id"), nullable=False
        ),
        sa.Column("nombre_es", sa.String(160), nullable=False),
        sa.Column("nombre_en", sa.String(160), nullable=False),
        sa.Column("descripcion_es", sa.Text(), nullable=False, server_default=""),
        sa.Column("descripcion_en", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "atributos",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("estado", sa.String(30), nullable=False, server_default="borrador"),
        sa.Column(
            "fuente_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("fuente_externa.id"),
            nullable=True,
        ),
        sa.Column("actualizado_fuente_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "calificacion_promedio",
            sa.Numeric(3, 2),
            nullable=False,
            server_default=sa.text("0.00"),
        ),
        sa.Column(
            "total_calificaciones", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column(
            "creado_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "actualizado_en",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_oferta_estado", "oferta", ["estado"])
    op.create_index("ix_oferta_zona_id", "oferta", ["zona_id"])
    op.create_index("ix_oferta_tipo_servicio_id", "oferta", ["tipo_servicio_id"])
    op.create_index("ix_oferta_prestador_id", "oferta", ["prestador_id"])

    # 6. imagen_oferta
    op.create_table(
        "imagen_oferta",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "oferta_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("oferta.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("clave_objeto", sa.Text(), nullable=False),
        sa.Column("orden", sa.SmallInteger(), nullable=False, server_default=sa.text("0")),
        sa.Column("texto_alternativo_es", sa.String(250), nullable=False, server_default=""),
        sa.Column("texto_alternativo_en", sa.String(250), nullable=False, server_default=""),
    )
    op.create_index("ix_imagen_oferta_oferta_id", "imagen_oferta", ["oferta_id"])

    # 7. tarifa
    op.create_table(
        "tarifa",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "oferta_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("oferta.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("temporada", sa.String(20), nullable=False),
        sa.Column("vigente_desde", sa.Date(), nullable=False),
        sa.Column("vigente_hasta", sa.Date(), nullable=False),
        sa.Column("precio_por_persona", sa.Numeric(12, 2), nullable=False),
        sa.Column("moneda", sa.String(3), nullable=False, server_default="COP"),
    )
    op.create_index("ix_tarifa_oferta_id", "tarifa", ["oferta_id"])

    # 8. politica_cancelacion
    op.create_table(
        "politica_cancelacion",
        sa.Column(
            "oferta_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("oferta.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("horas_reembolso_total", sa.SmallInteger(), nullable=False),
        sa.Column("horas_reembolso_parcial", sa.SmallInteger(), nullable=False),
        sa.Column("porcentaje_reembolso_parcial", sa.SmallInteger(), nullable=False),
    )

    # 9. calificacion
    op.create_table(
        "calificacion",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "oferta_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("oferta.id"), nullable=False
        ),
        sa.Column("turista_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reserva_id", postgresql.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column("puntaje", sa.SmallInteger(), nullable=False),
        sa.Column("comentario", sa.Text(), nullable=False, server_default=""),
        sa.Column("estado_moderacion", sa.String(30), nullable=False, server_default="publicada"),
        sa.Column(
            "creada_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_calificacion_oferta_id", "calificacion", ["oferta_id"])
    op.create_index("ix_calificacion_reserva_id", "calificacion", ["reserva_id"])

    # 10. respuesta_calificacion
    op.create_table(
        "respuesta_calificacion",
        sa.Column(
            "calificacion_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("calificacion.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("prestador_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("texto", sa.Text(), nullable=False),
        sa.Column("estado_moderacion", sa.String(30), nullable=False, server_default="publicada"),
        sa.Column(
            "creada_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )

    # 11. favorito
    op.create_table(
        "favorito",
        sa.Column("turista_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "oferta_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("oferta.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "creado_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.PrimaryKeyConstraint("turista_id", "oferta_id"),
    )

    # 12. itinerario
    op.create_table(
        "itinerario",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("turista_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("nombre", sa.String(120), nullable=False),
        sa.Column("fecha_inicio", sa.Date(), nullable=True),
        sa.Column("fecha_fin", sa.Date(), nullable=True),
    )
    op.create_index("ix_itinerario_turista_id", "itinerario", ["turista_id"])

    # 13. item_itinerario
    op.create_table(
        "item_itinerario",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "itinerario_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("itinerario.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "oferta_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("oferta.id"), nullable=False
        ),
        sa.Column("dia", sa.Date(), nullable=False),
        sa.Column("orden", sa.SmallInteger(), nullable=False, server_default=sa.text("0")),
        sa.Column("hora_inicio", sa.Time(), nullable=True),
        sa.Column("hora_fin", sa.Time(), nullable=True),
    )

    # 14. lote_sincronizacion
    op.create_table(
        "lote_sincronizacion",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "prestador_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("perfil_prestador.prestador_id"),
            nullable=False,
        ),
        sa.Column(
            "fuente_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("fuente_externa.id"),
            nullable=False,
        ),
        sa.Column("estado", sa.String(30), nullable=False, server_default="recibido"),
        sa.Column("total_registros", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("aceptados", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "rechazados",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "recibido_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("finalizado_en", sa.DateTime(timezone=True), nullable=True),
    )

    # 15. outbox (ADR-04)
    op.create_table(
        "outbox",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tipo", sa.String(80), nullable=False),
        sa.Column("version", sa.SmallInteger(), nullable=False, server_default=sa.text("1")),
        sa.Column("correlation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("datos", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "ocurrido_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("publicado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("intentos", sa.SmallInteger(), nullable=False, server_default=sa.text("0")),
    )
    op.create_index("ix_outbox_tipo", "outbox", ["tipo"])

    # 16. evento_procesado
    op.create_table(
        "evento_procesado",
        sa.Column("evento_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tipo", sa.String(80), nullable=False),
        sa.Column(
            "procesado_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )


def downgrade() -> None:
    op.drop_table("evento_procesado")
    op.drop_table("outbox")
    op.drop_table("lote_sincronizacion")
    op.drop_table("item_itinerario")
    op.drop_table("itinerario")
    op.drop_table("favorito")
    op.drop_table("respuesta_calificacion")
    op.drop_table("calificacion")
    op.drop_table("politica_cancelacion")
    op.drop_table("tarifa")
    op.drop_table("imagen_oferta")
    op.drop_table("oferta")
    op.drop_table("fuente_externa")
    op.drop_table("perfil_prestador")
    op.drop_table("tipo_servicio")
    op.drop_table("zona")
