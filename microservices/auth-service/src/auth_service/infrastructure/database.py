"""Conexión asíncrona y adaptadores SQLAlchemy para PostgreSQL."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import or_, select, text
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.sql import Executable

from auth_service.application.outbox import OutboxClaim, OutboxEvent
from auth_service.application.ports import (
    AuthenticationAuditRecorder,
    EmailConfirmationUnitOfWork,
    LoginAttemptGuard,
    OutboxRepository,
    RefreshTokenRepository,
    RegistrationUnitOfWork,
    UserRepository,
    VerificationRepository,
    VerificationUnitOfWork,
)
from auth_service.application.register_user import DuplicateEmail
from auth_service.domain.consent import Consent
from auth_service.domain.email import Email
from auth_service.domain.errors import AccountLocked
from auth_service.domain.role import Role
from auth_service.domain.user import User, UserStatus
from auth_service.domain.verification import VerificationRequest, VerificationStatus
from auth_service.infrastructure.db_models import (
    AuthAuditRow,
    ConsentRow,
    EmailConfirmationRow,
    LoginAttemptRow,
    OutboxRow,
    RefreshSessionRow,
    UserRow,
    VerificationRow,
)

SessionFactory = async_sessionmaker[AsyncSession]
ClockFunction = Callable[[], datetime]


class DatabaseRuntime:
    def __init__(self, engine: AsyncEngine, sessions: SessionFactory) -> None:
        self.engine = engine
        self.sessions = sessions

    async def check_ready(self) -> bool:
        try:
            async with self.engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
        except SQLAlchemyError:
            return False
        return True

    async def dispose(self) -> None:
        await self.engine.dispose()


def create_database(database_url: str) -> DatabaseRuntime:
    engine = create_async_engine(database_url, pool_pre_ping=True)
    return DatabaseRuntime(engine, async_sessionmaker(engine, expire_on_commit=False))


def _to_user(row: UserRow) -> User:
    return User(
        id=row.id,
        email=Email(row.email),
        role=Role(row.role),
        password_hash=row.password_hash,
        status=UserStatus(row.status),
    )


def _to_verification(row: VerificationRow) -> VerificationRequest:
    return VerificationRequest(
        id=row.id,
        provider_id=row.provider_id,
        business_name=row.business_name,
        nit=row.nit,
        rnt=row.rnt,
        document_keys=tuple(row.document_keys),
        status=VerificationStatus(row.status),
        justification=row.justification,
    )


class SqlUserRepository(UserRepository):
    def __init__(self, sessions: SessionFactory) -> None:
        self._sessions = sessions

    async def find_by_email(self, email: Email) -> User | None:
        async with self._sessions() as session:
            result = await session.execute(select(UserRow).where(UserRow.email == email.value))
            row = result.scalar_one_or_none()
            return _to_user(row) if row else None

    async def find_by_id(self, user_id: UUID) -> User | None:
        async with self._sessions() as session:
            row = await session.get(UserRow, user_id)
            return _to_user(row) if row else None


class SqlRegistrationUnitOfWork(RegistrationUnitOfWork):
    def __init__(self, sessions: SessionFactory) -> None:
        self._sessions = sessions

    async def create_user_with_consent_and_event(
        self,
        user: User,
        consent: Consent,
        event_type: str,
        event_data: dict[str, str],
        confirmation_token_hash: str,
        confirmation_expires_at: datetime,
    ) -> None:
        try:
            async with self._sessions() as session, session.begin():
                session.add(UserRow(
                    id=user.id,
                    email=user.email.value,
                    role=user.role.value,
                    password_hash=user.password_hash,
                    status=user.status.value,
                ))
                await session.flush()
                session.add(ConsentRow(
                    id=uuid4(),
                    user_id=consent.user_id,
                    purpose=consent.purpose,
                    policy_version=consent.policy_version,
                    accepted_at=consent.accepted_at,
                ))
                session.add(EmailConfirmationRow(
                    token_hash=confirmation_token_hash,
                    user_id=user.id,
                    expires_at=confirmation_expires_at,
                ))
                session.add(OutboxRow(id=uuid4(), event_type=event_type, payload=event_data))
        except IntegrityError as exc:
            message = str(exc.orig).lower()
            if any(
                marker in message
                for marker in (
                    "ix_usuario_email",
                    "usuario_email_key",
                    "usuario.email",
                )
            ):
                raise DuplicateEmail("Ya existe una cuenta con ese correo.") from exc
            raise


class SqlEmailConfirmationUnitOfWork(EmailConfirmationUnitOfWork):
    def __init__(self, sessions: SessionFactory) -> None:
        self._sessions = sessions

    async def confirm_email(self, token_hash: str, confirmed_at: datetime) -> bool:
        async with self._sessions() as session, session.begin():
            result = await session.execute(
                select(EmailConfirmationRow)
                .where(EmailConfirmationRow.token_hash == token_hash)
                .with_for_update()
            )
            confirmation = result.scalar_one_or_none()
            if (
                confirmation is None
                or confirmation.consumed_at is not None
                or _as_utc(confirmation.expires_at) <= _as_utc(confirmed_at)
            ):
                return False

            user = await session.get(UserRow, confirmation.user_id, with_for_update=True)
            if user is None or user.status != UserStatus.PENDIENTE.value:
                return False

            user.status = _to_user(user).activate().status.value
            confirmation.consumed_at = confirmed_at
            session.add(OutboxRow(
                id=uuid4(),
                event_type="auth.usuario.confirmado",
                payload={"usuario_id": str(user.id)},
            ))
            return True


class SqlVerificationRepository(VerificationRepository):
    def __init__(self, sessions: SessionFactory) -> None:
        self._sessions = sessions

    async def find_by_id(self, request_id: UUID) -> VerificationRequest | None:
        async with self._sessions() as session:
            row = await session.get(VerificationRow, request_id)
            return _to_verification(row) if row else None

    async def save(self, request: VerificationRequest) -> None:
        async with self._sessions() as session, session.begin():
            row = await session.get(VerificationRow, request.id)
            if row is None:
                row = VerificationRow(id=request.id, provider_id=request.provider_id)
                session.add(row)
            row.business_name = request.business_name
            row.nit = request.nit
            row.rnt = request.rnt
            row.document_keys = list(request.document_keys)
            row.status = request.status.value
            row.justification = request.justification


class SqlVerificationUnitOfWork(VerificationUnitOfWork):
    def __init__(self, sessions: SessionFactory) -> None:
        self._sessions = sessions

    async def find_by_id(self, request_id: UUID) -> VerificationRequest | None:
        return await SqlVerificationRepository(self._sessions).find_by_id(request_id)

    async def save_with_event(
        self,
        request: VerificationRequest,
        event_type: str,
        event_data: dict[str, str],
    ) -> None:
        async with self._sessions() as session, session.begin():
            row = await session.get(VerificationRow, request.id)
            if row is None:
                raise LookupError("La solicitud de verificación no existe.")
            row.status = request.status.value
            row.justification = request.justification
            session.add(OutboxRow(id=uuid4(), event_type=event_type, payload=event_data))


class SqlOutboxRepository(OutboxRepository):
    """Reclama eventos con lease y minimiza el payload después de publicarlo."""

    def __init__(self, sessions: SessionFactory) -> None:
        self._sessions = sessions

    async def claim_pending(
        self,
        claimed_at: datetime,
        lease_duration_seconds: int,
        batch_size: int,
    ) -> list[OutboxClaim]:
        if lease_duration_seconds < 1 or batch_size < 1:
            raise ValueError("El lote y la duración del lease deben ser positivos.")
        claim_time = _as_utc(claimed_at)
        lease_end = claim_time + timedelta(seconds=lease_duration_seconds)
        async with self._sessions() as session, session.begin():
            result = await session.execute(
                select(OutboxRow)
                .where(
                    OutboxRow.published_at.is_(None),
                    OutboxRow.available_at <= claim_time,
                    or_(
                        OutboxRow.locked_until.is_(None),
                        OutboxRow.locked_until <= claim_time,
                    ),
                )
                .order_by(OutboxRow.occurred_at, OutboxRow.id)
                .limit(batch_size)
                .with_for_update(skip_locked=True)
            )
            rows = result.scalars().all()
            claims: list[OutboxClaim] = []
            for row in rows:
                lease_token = uuid4()
                row.locked_until = lease_end
                row.lease_token = lease_token
                row.attempts += 1
                claims.append(
                    OutboxClaim(
                        event=OutboxEvent(
                            id=row.id,
                            event_type=row.event_type,
                            payload=dict(row.payload),
                        ),
                        lease_token=lease_token,
                        attempts=row.attempts,
                    )
                )
            return claims

    async def mark_failed(
        self,
        event_id: UUID,
        lease_token: UUID,
        failed_at: datetime,
        error_code: str,
    ) -> bool:
        async with self._sessions() as session, session.begin():
            row = await session.get(OutboxRow, event_id, with_for_update=True)
            if (
                row is None
                or row.published_at is not None
                or row.lease_token != lease_token
            ):
                return False
            retry_seconds = min(2 ** min(max(row.attempts - 1, 0), 12), 3600)
            row.available_at = _as_utc(failed_at) + timedelta(seconds=retry_seconds)
            row.locked_until = None
            row.lease_token = None
            row.last_error = error_code[:120]
            return True

    async def mark_published(
        self, event_id: UUID, lease_token: UUID, published_at: datetime
    ) -> bool:
        async with self._sessions() as session, session.begin():
            row = await session.get(OutboxRow, event_id, with_for_update=True)
            if (
                row is None
                or row.published_at is not None
                or row.lease_token != lease_token
            ):
                return False
            safe_payload = dict(row.payload)
            safe_payload.pop("token_confirmacion", None)
            safe_payload.pop("correo", None)
            row.payload = safe_payload
            row.published_at = published_at
            row.locked_until = None
            row.lease_token = None
            row.last_error = None
            return True


class SqlRefreshTokenRepository(RefreshTokenRepository):
    def __init__(self, sessions: SessionFactory) -> None:
        self._sessions = sessions

    async def store_hash(self, user_id: UUID, token_hash: str, expires_at: datetime) -> None:
        async with self._sessions() as session, session.begin():
            session.add(RefreshSessionRow(
                id=uuid4(),
                user_id=user_id,
                token_hash=token_hash,
                expires_at=expires_at,
            ))

    async def rotate_hash(
        self,
        token_hash: str,
        replacement_hash: str,
        now: datetime,
        expires_at: datetime,
    ) -> User | None:
        async with self._sessions() as session, session.begin():
            result = await session.execute(
                select(RefreshSessionRow)
                .where(RefreshSessionRow.token_hash == token_hash)
                .with_for_update()
            )
            refresh = result.scalar_one_or_none()
            if (
                refresh is None
                or refresh.revoked_at is not None
                or _as_utc(refresh.expires_at) <= _as_utc(now)
            ):
                return None
            user_row = await session.get(UserRow, refresh.user_id, with_for_update=True)
            if user_row is None or user_row.status != UserStatus.ACTIVO.value:
                refresh.revoked_at = now
                return None
            refresh.token_hash = replacement_hash
            refresh.expires_at = expires_at
            return _to_user(user_row)

    async def revoke_hash(self, token_hash: str, revoked_at: datetime) -> bool:
        async with self._sessions() as session, session.begin():
            result = await session.execute(
                select(RefreshSessionRow)
                .where(RefreshSessionRow.token_hash == token_hash)
                .with_for_update()
            )
            refresh = result.scalar_one_or_none()
            if refresh is None or refresh.revoked_at is not None:
                return False
            refresh.revoked_at = revoked_at
            return True


class SqlAuthenticationAuditRecorder(AuthenticationAuditRecorder):
    def __init__(self, sessions: SessionFactory) -> None:
        self._sessions = sessions

    async def record_attempt(self, user_id: UUID | None, succeeded: bool) -> None:
        async with self._sessions() as session, session.begin():
            session.add(AuthAuditRow(
                id=uuid4(),
                user_id=user_id,
                event_type="auth.login",
                succeeded=succeeded,
            ))


class SqlLoginAttemptGuard(LoginAttemptGuard):
    """Bloqueo persistente por identificador seudonimizado.

    Mantiene 5 intentos dentro de 60 segundos. La duración de bloqueo sigue
    siendo configurable porque el ADR no fija ese valor.
    """

    def __init__(
        self,
        sessions: SessionFactory,
        block_duration: timedelta,
        clock: ClockFunction = lambda: datetime.now(UTC),
    ) -> None:
        if block_duration <= timedelta(0):
            raise ValueError("La duración del bloqueo debe ser positiva.")
        self._sessions = sessions
        self._block_duration = block_duration
        self._clock = clock

    @staticmethod
    def _key(identifier: str) -> str:
        return hashlib.sha256(identifier.encode("utf-8")).hexdigest()

    async def ensure_allowed(self, identifier: str) -> None:
        async with self._sessions() as session:
            row = await session.get(LoginAttemptRow, self._key(identifier))
            now = self._clock()
            if row and row.blocked_until and _as_utc(row.blocked_until) > now:
                raise AccountLocked("La cuenta está bloqueada temporalmente.")

    async def record_failure(self, identifier: str) -> None:
        key = self._key(identifier)
        now = self._clock()
        async with self._sessions() as session, session.begin():
            values = {
                "identifier_hash": key,
                "failures": 0,
                "window_started_at": now,
                "blocked_until": None,
            }
            dialect = session.sync_session.get_bind().dialect.name
            if dialect == "postgresql":
                statement: Executable = (
                    postgresql_insert(LoginAttemptRow)
                    .values(**values)
                    .on_conflict_do_nothing(
                        index_elements=[LoginAttemptRow.identifier_hash]
                    )
                )
            elif dialect == "sqlite":
                statement = (
                    sqlite_insert(LoginAttemptRow)
                    .values(**values)
                    .on_conflict_do_nothing(
                        index_elements=[LoginAttemptRow.identifier_hash]
                    )
                )
            else:
                raise RuntimeError(f"Dialecto de base de datos no soportado: {dialect}")
            await session.execute(statement)
            row = await session.get(LoginAttemptRow, key, with_for_update=True)
            if row is None:
                raise RuntimeError("No se pudo inicializar el registro de intentos de login.")
            if now - _as_utc(row.window_started_at) >= timedelta(seconds=60):
                row.failures = 0
                row.window_started_at = now
            row.failures += 1
            if row.failures >= 5:
                row.blocked_until = now + self._block_duration

    async def record_success(self, identifier: str) -> None:
        key = self._key(identifier)
        async with self._sessions() as session, session.begin():
            row = await session.get(LoginAttemptRow, key)
            if row is not None:
                await session.delete(row)


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
