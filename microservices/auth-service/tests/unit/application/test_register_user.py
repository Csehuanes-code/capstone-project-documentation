import asyncio
import hashlib
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from auth_service.application.register_user import (
    ConsentRequired,
    DuplicateEmail,
    RegisterUser,
    RegisterUserCommand,
)
from auth_service.domain.consent import Consent
from auth_service.domain.email import Email
from auth_service.domain.role import Role
from auth_service.domain.user import User


class MemoryUsers:
    def __init__(self) -> None:
        self.users: dict[str, User] = {}
        self.consents: list[Consent] = []
        self.events: list[tuple[str, dict[str, str]]] = []

    async def find_by_email(self, email: Email) -> User | None:
        return self.users.get(email.value)

    async def find_by_id(self, user_id: UUID) -> User | None:
        return next((user for user in self.users.values() if user.id == user_id), None)

    async def create_user_with_consent_and_event(
        self,
        user: User,
        consent: Consent,
        event_type: str,
        event_data: dict[str, str],
        confirmation_token_hash: str,
        confirmation_expires_at: datetime,
    ) -> None:
        self.users[user.email.value] = user
        self.consents.append(consent)
        self.events.append((event_type, event_data))
        self.confirmation_token_hash = confirmation_token_hash
        self.confirmation_expires_at = confirmation_expires_at


class FakeHasher:
    def hash(self, raw_password: str) -> str:
        return f"fake:{raw_password}"

    def verify(self, encoded_hash: str, raw_password: str) -> bool:
        return encoded_hash == f"fake:{raw_password}"


class FixedClock:
    def now(self) -> datetime:
        return datetime(2026, 11, 16, tzinfo=UTC)


def make_use_case() -> tuple[RegisterUser, MemoryUsers]:
    users = MemoryUsers()
    use_case = RegisterUser(users, users, FakeHasher(), FixedClock())
    return use_case, users


def test_registers_user_with_normalized_email_consent_and_notification() -> None:
    use_case, users = make_use_case()
    user = asyncio.run(use_case.execute(RegisterUserCommand(
        " David@Example.com ", "test-password", Role.TURISTA, True, "v1"
    )))

    assert user.email.value == "david@example.com"
    assert user.password_hash == "fake:test-password"
    assert len(users.consents) == 1
    assert users.consents[0].user_id == user.id
    assert users.events[0][0] == "notificacion.solicitada"
    event_data = users.events[0][1]
    token = event_data["token_confirmacion"]
    assert users.confirmation_token_hash == hashlib.sha256(token.encode()).hexdigest()
    assert users.confirmation_token_hash != token
    assert users.confirmation_expires_at == FixedClock().now() + timedelta(hours=24)
    assert event_data["correo"] == user.email.value


def test_does_not_create_account_without_consent() -> None:
    use_case, users = make_use_case()
    with pytest.raises(ConsentRequired):
        asyncio.run(use_case.execute(RegisterUserCommand(
            "user@example.com", "password", Role.TURISTA, False, "v1"
        )))
    assert users.users == {}
    assert users.events == []


def test_rejects_duplicate_email() -> None:
    use_case, _ = make_use_case()
    command = RegisterUserCommand("user@example.com", "password", Role.TURISTA, True, "v1")
    asyncio.run(use_case.execute(command))
    with pytest.raises(DuplicateEmail):
        asyncio.run(use_case.execute(command))
