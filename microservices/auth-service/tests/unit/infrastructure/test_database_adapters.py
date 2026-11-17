import asyncio
import hashlib
import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import event, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from auth_service.application.register_user import DuplicateEmail
from auth_service.domain.consent import Consent
from auth_service.domain.email import Email
from auth_service.domain.errors import AccountLocked
from auth_service.domain.role import Role
from auth_service.domain.user import User, UserStatus
from auth_service.infrastructure.database import (
    SqlEmailConfirmationUnitOfWork,
    SqlLoginAttemptGuard,
    SqlOutboxRepository,
    SqlRefreshTokenRepository,
    SqlRegistrationUnitOfWork,
    SqlUserRepository,
)
from auth_service.infrastructure.db_models import (
    Base,
    ConsentRow,
    EmailConfirmationRow,
    LoginAttemptRow,
    OutboxRow,
    RefreshSessionRow,
    UserRow,
)


async def _new_engine():
    database_url = os.environ.get(
        "AUTH_TEST_DATABASE_URL", "sqlite+aiosqlite:///:memory:"
    )
    engine = create_async_engine(database_url)
    if database_url.startswith("sqlite"):
        @event.listens_for(engine.sync_engine, "connect")
        def _enable_foreign_keys(dbapi_connection, _connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    return engine


def test_registration_persists_user_consent_and_outbox_atomically() -> None:
    async def scenario() -> None:
        engine = await _new_engine()
        sessions = async_sessionmaker(engine, expire_on_commit=False)

        user = User(
            uuid4(), Email("person@example.com"), Role.TURISTA,
            "argon-hash", UserStatus.PENDIENTE,
        )
        consent = Consent(user.id, "gestionar_reservas", "v1", datetime.now(UTC))
        unit_of_work = SqlRegistrationUnitOfWork(sessions)
        await unit_of_work.create_user_with_consent_and_event(
            user,
            consent,
            "notificacion.solicitada",
            {"tipo": "confirmacion_registro"},
            hashlib.sha256(b"confirmation-token").hexdigest(),
            datetime.now(UTC) + timedelta(hours=24),
        )

        assert await SqlUserRepository(sessions).find_by_email(user.email) == user
        async with sessions() as session:
            assert await session.scalar(select(func.count()).select_from(ConsentRow)) == 1
            assert await session.scalar(
                select(func.count()).select_from(EmailConfirmationRow)
            ) == 1
            assert await session.scalar(select(func.count()).select_from(OutboxRow)) == 1
        await engine.dispose()

    asyncio.run(scenario())


def test_registration_unique_email_is_translated_to_duplicate_email() -> None:
    async def scenario() -> None:
        engine = await _new_engine()
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        user_id = uuid4()
        first = User(user_id, Email("same@example.com"), Role.TURISTA, "h", UserStatus.PENDIENTE)
        second = User(uuid4(), first.email, Role.TURISTA, "h", UserStatus.PENDIENTE)
        consent = Consent(user_id, "gestionar_reservas", "v1", datetime.now(UTC))
        unit = SqlRegistrationUnitOfWork(sessions)
        expires_at = datetime.now(UTC) + timedelta(hours=24)
        await unit.create_user_with_consent_and_event(
            first, consent, "evt", {}, "hash-first", expires_at
        )
        with pytest.raises(DuplicateEmail):
            await unit.create_user_with_consent_and_event(
                second,
                Consent(second.id, "gestionar_reservas", "v1", datetime.now(UTC)),
                "evt",
                {},
                "hash-second",
                expires_at,
            )
        await engine.dispose()

    asyncio.run(scenario())


def test_registration_other_integrity_errors_are_not_reported_as_duplicate_email() -> None:
    async def scenario() -> None:
        engine = await _new_engine()
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        user = User(
            uuid4(), Email("person@example.com"), Role.TURISTA, "h", UserStatus.PENDIENTE
        )
        invalid_consent = Consent(
            uuid4(), "gestionar_reservas", "v1", datetime.now(UTC)
        )
        unit = SqlRegistrationUnitOfWork(sessions)
        with pytest.raises(IntegrityError):
            await unit.create_user_with_consent_and_event(
                user,
                invalid_consent,
                "evt",
                {},
                "token-hash",
                datetime.now(UTC) + timedelta(hours=24),
            )
        await engine.dispose()

    asyncio.run(scenario())


def test_confirmation_activates_user_once_and_persists_event() -> None:
    async def scenario() -> None:
        engine = await _new_engine()
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        user_id = uuid4()
        now = datetime.now(UTC)
        async with sessions() as session, session.begin():
            session.add(UserRow(
                id=user_id,
                email="person@example.com",
                role=Role.TURISTA.value,
                password_hash="hash",
                status=UserStatus.PENDIENTE.value,
            ))
            await session.flush()
            session.add(EmailConfirmationRow(
                token_hash="one-time-token-hash",
                user_id=user_id,
                expires_at=now + timedelta(hours=1),
            ))

        unit = SqlEmailConfirmationUnitOfWork(sessions)
        assert await unit.confirm_email("one-time-token-hash", now)
        assert not await unit.confirm_email("one-time-token-hash", now)
        async with sessions() as session:
            user = await session.get(UserRow, user_id)
            assert user is not None and user.status == UserStatus.ACTIVO.value
            confirmation = await session.get(EmailConfirmationRow, "one-time-token-hash")
            assert confirmation is not None and confirmation.consumed_at is not None
            assert await session.scalar(select(func.count()).select_from(OutboxRow)) == 1
        await engine.dispose()

    asyncio.run(scenario())


def test_expired_confirmation_does_not_activate_user() -> None:
    async def scenario() -> None:
        engine = await _new_engine()
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        user_id = uuid4()
        now = datetime.now(UTC)
        async with sessions() as session, session.begin():
            session.add(UserRow(
                id=user_id,
                email="expired@example.com",
                role=Role.TURISTA.value,
                password_hash="hash",
                status=UserStatus.PENDIENTE.value,
            ))
            await session.flush()
            session.add(EmailConfirmationRow(
                token_hash="expired-token-hash",
                user_id=user_id,
                expires_at=now - timedelta(seconds=1),
            ))

        assert not await SqlEmailConfirmationUnitOfWork(sessions).confirm_email(
            "expired-token-hash", now
        )
        async with sessions() as session:
            user = await session.get(UserRow, user_id)
            assert user is not None and user.status == UserStatus.PENDIENTE.value
        await engine.dispose()

    asyncio.run(scenario())


def test_refresh_token_rotates_once_and_can_be_revoked() -> None:
    async def scenario() -> None:
        engine = await _new_engine()
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        user_id = uuid4()
        now = datetime.now(UTC)
        async with sessions() as session, session.begin():
            session.add(UserRow(
                id=user_id,
                email="refresh@example.com",
                role=Role.TURISTA.value,
                password_hash="hash",
                status=UserStatus.ACTIVO.value,
            ))
            await session.flush()
            session.add(RefreshSessionRow(
                id=uuid4(),
                user_id=user_id,
                token_hash="old-token-hash",
                expires_at=now + timedelta(days=1),
            ))

        repository = SqlRefreshTokenRepository(sessions)
        user = await repository.rotate_hash(
            "old-token-hash",
            "new-token-hash",
            now,
            now + timedelta(days=7),
        )
        assert user is not None and user.id == user_id
        assert await repository.rotate_hash(
            "old-token-hash", "replay-hash", now, now + timedelta(days=7)
        ) is None
        assert await repository.revoke_hash("new-token-hash", now)
        assert not await repository.revoke_hash("new-token-hash", now)
        assert await repository.rotate_hash(
            "new-token-hash", "after-revoke", now, now + timedelta(days=7)
        ) is None
        await engine.dispose()

    asyncio.run(scenario())


def test_refresh_token_expiry_prevents_rotation() -> None:
    async def scenario() -> None:
        engine = await _new_engine()
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        user_id = uuid4()
        now = datetime.now(UTC)
        async with sessions() as session, session.begin():
            session.add(UserRow(
                id=user_id,
                email="expired-refresh@example.com",
                role=Role.TURISTA.value,
                password_hash="hash",
                status=UserStatus.ACTIVO.value,
            ))
            await session.flush()
            session.add(RefreshSessionRow(
                id=uuid4(),
                user_id=user_id,
                token_hash="expired-refresh-hash",
                expires_at=now - timedelta(seconds=1),
            ))

        assert await SqlRefreshTokenRepository(sessions).rotate_hash(
            "expired-refresh-hash", "replacement", now, now + timedelta(days=7)
        ) is None
        await engine.dispose()

    asyncio.run(scenario())


def test_publishing_outbox_event_removes_confirmation_secret() -> None:
    async def scenario() -> None:
        engine = await _new_engine()
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        event_id = uuid4()
        lease_token = uuid4()
        now = datetime.now(UTC)
        async with sessions() as session, session.begin():
            session.add(OutboxRow(
                id=event_id,
                event_type="notificacion.solicitada",
                payload={"correo": "person@example.com", "token_confirmacion": "secret"},
                locked_until=now + timedelta(minutes=1),
                lease_token=lease_token,
                last_error="ConnectionError",
            ))

        repository = SqlOutboxRepository(sessions)
        assert await repository.mark_published(event_id, lease_token, now)
        assert not await repository.mark_published(event_id, lease_token, now)
        async with sessions() as session:
            row = await session.get(OutboxRow, event_id)
            assert row is not None
            assert row.published_at is not None
            assert "token_confirmacion" not in row.payload
            assert "correo" not in row.payload
            assert row.locked_until is None
            assert row.lease_token is None
            assert row.last_error is None
        await engine.dispose()

    asyncio.run(scenario())


def test_outbox_claim_respects_schedule_lease_and_batch_size() -> None:
    async def scenario() -> None:
        engine = await _new_engine()
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        now = datetime.now(UTC)
        ready_id, leased_id, scheduled_id, published_id = (uuid4() for _ in range(4))
        async with sessions() as session, session.begin():
            session.add_all([
                OutboxRow(
                    id=ready_id,
                    event_type="ready",
                    payload={"ok": True},
                    occurred_at=now,
                    available_at=now - timedelta(seconds=1),
                ),
                OutboxRow(
                    id=leased_id,
                    event_type="leased",
                    payload={},
                    occurred_at=now,
                    available_at=now - timedelta(seconds=1),
                    locked_until=now + timedelta(seconds=30),
                ),
                OutboxRow(
                    id=scheduled_id,
                    event_type="scheduled",
                    payload={},
                    occurred_at=now,
                    available_at=now + timedelta(seconds=30),
                ),
                OutboxRow(
                    id=published_id,
                    event_type="published",
                    payload={},
                    occurred_at=now,
                    available_at=now - timedelta(seconds=1),
                    published_at=now,
                ),
            ])

        repository = SqlOutboxRepository(sessions)
        first_batch = await repository.claim_pending(now, 60, 1)
        assert len(first_batch) == 1
        assert first_batch[0].event.id == ready_id
        assert first_batch[0].attempts == 1
        assert await repository.claim_pending(now, 60, 10) == []

        async with sessions() as session:
            ready = await session.get(OutboxRow, ready_id)
            assert ready is not None
            assert ready.locked_until is not None
            assert ready.attempts == 1
        await engine.dispose()

    asyncio.run(scenario())


def test_outbox_failure_releases_lease_and_applies_exponential_retry() -> None:
    async def scenario() -> None:
        engine = await _new_engine()
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        now = datetime.now(UTC)
        event_id = uuid4()
        async with sessions() as session, session.begin():
            session.add(OutboxRow(
                id=event_id,
                event_type="reliable.event",
                payload={"safe": True},
                occurred_at=now,
                available_at=now - timedelta(seconds=1),
            ))

        repository = SqlOutboxRepository(sessions)
        first_claim = await repository.claim_pending(now, 60, 1)
        assert len(first_claim) == 1 and first_claim[0].attempts == 1
        first_token = first_claim[0].lease_token
        assert await repository.mark_failed(
            event_id, first_token, now, "ConnectionError"
        )
        async with sessions() as session:
            failed = await session.get(OutboxRow, event_id)
            assert failed is not None
            assert failed.last_error == "ConnectionError"
            assert failed.locked_until is None
            assert failed.available_at is not None
            assert failed.available_at.replace(tzinfo=UTC) == now + timedelta(seconds=1)

        assert await repository.claim_pending(now, 60, 1) == []
        retry_claim = await repository.claim_pending(now + timedelta(seconds=1), 60, 1)
        assert len(retry_claim) == 1 and retry_claim[0].attempts == 2
        assert await repository.mark_failed(
            event_id,
            retry_claim[0].lease_token,
            now + timedelta(seconds=1),
            "TimeoutError",
        )
        async with sessions() as session:
            retried = await session.get(OutboxRow, event_id)
            assert retried is not None
            assert retried.last_error == "TimeoutError"
            assert retried.available_at is not None
            assert retried.available_at.replace(tzinfo=UTC) == now + timedelta(seconds=3)
        await engine.dispose()

    asyncio.run(scenario())


def test_outbox_old_lease_cannot_change_event_after_reclaim() -> None:
    async def scenario() -> None:
        engine = await _new_engine()
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        now = datetime.now(UTC)
        event_id = uuid4()
        async with sessions() as session, session.begin():
            session.add(OutboxRow(
                id=event_id,
                event_type="fenced.event",
                payload={"ok": True},
                occurred_at=now,
                available_at=now - timedelta(seconds=1),
            ))

        repository = SqlOutboxRepository(sessions)
        original_claim = (await repository.claim_pending(now, 60, 1))[0]
        async with sessions() as session, session.begin():
            row = await session.get(OutboxRow, event_id)
            assert row is not None
            row.locked_until = now - timedelta(seconds=1)

        replacement_claim = (await repository.claim_pending(now, 60, 1))[0]
        assert replacement_claim.lease_token != original_claim.lease_token
        assert not await repository.mark_published(
            event_id, original_claim.lease_token, now
        )
        assert not await repository.mark_failed(
            event_id, original_claim.lease_token, now, "stale_worker"
        )
        assert await repository.mark_published(
            event_id, replacement_claim.lease_token, now
        )
        await engine.dispose()

    asyncio.run(scenario())


def test_persistent_login_guard_locks_after_five_failures() -> None:
    async def scenario() -> None:
        engine = await _new_engine()
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        now = datetime.now(UTC)
        guard = SqlLoginAttemptGuard(
            sessions,
            block_duration=timedelta(minutes=4),
            clock=lambda: now,
        )
        for _ in range(5):
            await guard.record_failure("person@example.com")
        with pytest.raises(AccountLocked):
            await guard.ensure_allowed("person@example.com")
        await engine.dispose()

    asyncio.run(scenario())


@pytest.mark.skipif(
    not os.environ.get("AUTH_TEST_DATABASE_URL", "").startswith("postgresql+"),
    reason="La prueba concurrente requiere PostgreSQL.",
)
def test_concurrent_first_login_failures_are_counted_atomically() -> None:
    async def scenario() -> None:
        engine = await _new_engine()
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        now = datetime.now(UTC)
        guard = SqlLoginAttemptGuard(
            sessions,
            block_duration=timedelta(minutes=4),
            clock=lambda: now,
        )
        await asyncio.gather(*(
            guard.record_failure("parallel@example.com") for _ in range(12)
        ))
        with pytest.raises(AccountLocked):
            await guard.ensure_allowed("parallel@example.com")
        async with sessions() as session:
            attempts = await session.get(
                LoginAttemptRow,
                SqlLoginAttemptGuard._key("parallel@example.com"),
            )
            assert attempts is not None and attempts.failures == 12
        await engine.dispose()

    asyncio.run(scenario())
