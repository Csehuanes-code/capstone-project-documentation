import asyncio
from uuid import UUID, uuid4

import pytest

from auth_service.application.authenticate_user import (
    AuthenticateUser,
    AuthenticateUserCommand,
    InvalidCredentials,
)
from auth_service.application.sessions import IssuedSession
from auth_service.domain.email import Email
from auth_service.domain.errors import AccountLocked
from auth_service.domain.role import Role
from auth_service.domain.user import User, UserStatus


class MemoryUsers:
    def __init__(self, *users: User) -> None:
        self.users = {user.email.value: user for user in users}

    async def find_by_email(self, email: Email) -> User | None:
        return self.users.get(email.value)

    async def find_by_id(self, user_id: UUID) -> User | None:
        return next((user for user in self.users.values() if user.id == user_id), None)


class FakeHasher:
    def hash(self, raw_password: str) -> str:
        return f"fake:{raw_password}"

    def verify(self, encoded_hash: str, raw_password: str) -> bool:
        return encoded_hash == f"fake:{raw_password}"


class MemoryAttempts:
    def __init__(self) -> None:
        self.failures: dict[str, int] = {}
        self.locked: set[str] = set()

    async def ensure_allowed(self, identifier: str) -> None:
        if identifier in self.locked:
            raise AccountLocked("La cuenta está bloqueada temporalmente.")

    async def record_failure(self, identifier: str) -> None:
        self.failures[identifier] = self.failures.get(identifier, 0) + 1
        if self.failures[identifier] >= 5:
            self.locked.add(identifier)

    async def record_success(self, identifier: str) -> None:
        self.failures.pop(identifier, None)


class MemoryAudit:
    def __init__(self) -> None:
        self.records: list[tuple[UUID | None, bool]] = []

    async def record_attempt(self, user_id: UUID | None, succeeded: bool) -> None:
        self.records.append((user_id, succeeded))


class FakeSessions:
    def __init__(self) -> None:
        self.created_for: list[UUID] = []

    async def create(self, user: User) -> IssuedSession:
        self.created_for.append(user.id)
        return IssuedSession("test-access", "test-refresh", 900)


def active_user(password: str = "correct") -> User:
    return User(
        uuid4(), Email("person@example.com"), Role.TURISTA,
        FakeHasher().hash(password), UserStatus.ACTIVO,
    )


def test_valid_credentials_create_session_and_clear_failures() -> None:
    user = active_user()
    attempts = MemoryAttempts()
    audit = MemoryAudit()
    sessions = FakeSessions()
    result = asyncio.run(AuthenticateUser(MemoryUsers(user), FakeHasher(), attempts, audit, sessions).execute(
        AuthenticateUserCommand("PERSON@example.com", "correct")
    ))
    assert result.user_id == user.id
    assert result.session.access_expires_in == 900
    assert sessions.created_for == [user.id]
    assert audit.records == [(user.id, True)]


def test_wrong_password_returns_generic_error_and_records_failure() -> None:
    user = active_user()
    attempts = MemoryAttempts()
    audit = MemoryAudit()
    with pytest.raises(InvalidCredentials, match="Correo o contraseña incorrectos"):
        asyncio.run(AuthenticateUser(MemoryUsers(user), FakeHasher(), attempts, audit, FakeSessions()).execute(
            AuthenticateUserCommand("person@example.com", "wrong")
        ))
    assert attempts.failures["person@example.com"] == 1
    assert audit.records == [(user.id, False)]


def test_unknown_account_returns_same_generic_error() -> None:
    attempts = MemoryAttempts()
    audit = MemoryAudit()
    with pytest.raises(InvalidCredentials, match="Correo o contraseña incorrectos"):
        asyncio.run(AuthenticateUser(MemoryUsers(), FakeHasher(), attempts, audit, FakeSessions()).execute(
            AuthenticateUserCommand("unknown@example.com", "wrong")
        ))
    assert attempts.failures["unknown@example.com"] == 1
    assert audit.records == [(None, False)]


def test_inactive_account_is_not_issued_a_session() -> None:
    user = User(
        uuid4(), Email("person@example.com"), Role.TURISTA,
        FakeHasher().hash("correct"), UserStatus.PENDIENTE,
    )
    sessions = FakeSessions()
    audit = MemoryAudit()
    with pytest.raises(InvalidCredentials):
        asyncio.run(AuthenticateUser(MemoryUsers(user), FakeHasher(), MemoryAttempts(), audit, sessions).execute(
            AuthenticateUserCommand("person@example.com", "correct")
        ))
    assert sessions.created_for == []
    assert audit.records == [(user.id, False)]


def test_locked_identifier_is_rejected_before_password_check() -> None:
    attempts = MemoryAttempts()
    attempts.locked.add("person@example.com")
    audit = MemoryAudit()
    with pytest.raises(AccountLocked):
        asyncio.run(AuthenticateUser(
            MemoryUsers(active_user()), FakeHasher(), attempts, audit, FakeSessions()
        ).execute(AuthenticateUserCommand("person@example.com", "correct")))
    assert audit.records[0][1] is False
