"""Tablas SQLAlchemy del servicio Auth."""

from datetime import datetime
from typing import Any, ClassVar
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

_JSON_TYPE = JSON().with_variant(JSONB(), "postgresql")


class Base(DeclarativeBase):
    type_annotation_map: ClassVar[dict[Any, Any]] = {
        dict[str, Any]: _JSON_TYPE,
        list[str]: _JSON_TYPE,
    }


class UserRow(Base):
    __tablename__ = "usuario"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    role: Mapped[str] = mapped_column(String(24))
    password_hash: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(24))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ConsentRow(Base):
    __tablename__ = "consentimiento"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    user_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("usuario.id"), index=True)
    purpose: Mapped[str] = mapped_column(String(80))
    policy_version: Mapped[str] = mapped_column(String(100))
    accepted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class EmailConfirmationRow(Base):
    __tablename__ = "confirmacion_correo"

    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("usuario.id"), unique=True, index=True
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consumed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class VerificationRow(Base):
    __tablename__ = "solicitud_verificacion"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    provider_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("usuario.id"), index=True)
    business_name: Mapped[str] = mapped_column(String(200))
    nit: Mapped[str] = mapped_column(String(32))
    rnt: Mapped[str] = mapped_column(String(32))
    document_keys: Mapped[list[str]] = mapped_column(_JSON_TYPE)
    status: Mapped[str] = mapped_column(String(24))
    justification: Mapped[str | None] = mapped_column(Text, nullable=True)


class RefreshSessionRow(Base):
    __tablename__ = "token_sesion"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    user_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("usuario.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class OutboxRow(Base):
    __tablename__ = "outbox"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    event_type: Mapped[str] = mapped_column(String(120))
    payload: Mapped[dict[str, Any]] = mapped_column(_JSON_TYPE)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    locked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    lease_token: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    last_error: Mapped[str | None] = mapped_column(String(120), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AuthAuditRow(Base):
    __tablename__ = "registro_auditoria"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    user_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("usuario.id"), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(80), index=True)
    succeeded: Mapped[bool] = mapped_column(Boolean)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LoginAttemptRow(Base):
    __tablename__ = "login_attempt"

    identifier_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    failures: Mapped[int] = mapped_column(Integer, default=0)
    window_started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    blocked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
