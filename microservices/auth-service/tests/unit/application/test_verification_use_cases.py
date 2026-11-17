import asyncio
from uuid import UUID, uuid4

import pytest

from auth_service.application.resolve_verification import (
    AdministratorRequired,
    Decision,
    ResolveVerification,
    ResolveVerificationCommand,
)
from auth_service.application.submit_verification import (
    ProviderNotAllowed,
    SubmitVerification,
    SubmitVerificationCommand,
)
from auth_service.domain.email import Email
from auth_service.domain.role import Role
from auth_service.domain.user import User, UserStatus
from auth_service.domain.verification import VerificationRequest, VerificationStatus


class MemoryUsers:
    def __init__(self, *users: User) -> None:
        self.users = {user.id: user for user in users}

    async def find_by_email(self, email: Email) -> User | None:
        return next((user for user in self.users.values() if user.email == email), None)

    async def find_by_id(self, user_id: UUID) -> User | None:
        return self.users.get(user_id)

class MemoryVerifications:
    def __init__(self) -> None:
        self.requests: dict[UUID, VerificationRequest] = {}
        self.events: list[tuple[str, dict[str, str]]] = []

    async def find_by_id(self, request_id: UUID) -> VerificationRequest | None:
        return self.requests.get(request_id)

    async def save(self, request: VerificationRequest) -> None:
        self.requests[request.id] = request

    async def save_with_event(
        self,
        request: VerificationRequest,
        event_type: str,
        event_data: dict[str, str],
    ) -> None:
        await self.save(request)
        self.events.append((event_type, event_data))


def active_user(role: Role) -> User:
    return User(uuid4(), Email(f"{role.value}@example.com"), role, "fake-hash", UserStatus.ACTIVO)


def test_provider_can_submit_verification_request() -> None:
    provider = active_user(Role.PRESTADOR)
    users = MemoryUsers(provider)
    verifications = MemoryVerifications()
    result = asyncio.run(SubmitVerification(users, verifications).execute(SubmitVerificationCommand(
        provider.id, "Guías Sierra Viva", "900123456", "12345", ("docs/rnt.pdf",)
    )))
    assert result.provider_id == provider.id
    assert result.status is VerificationStatus.ENVIADA
    assert asyncio.run(verifications.find_by_id(result.id)) == result


def test_tourist_cannot_submit_verification_request() -> None:
    tourist = active_user(Role.TURISTA)
    with pytest.raises(ProviderNotAllowed):
        asyncio.run(SubmitVerification(MemoryUsers(tourist), MemoryVerifications()).execute(
            SubmitVerificationCommand(tourist.id, "Negocio", "900", "123")
        ))


def test_admin_can_resolve_request_and_publish_event() -> None:
    admin = active_user(Role.ADMINISTRADOR)
    provider_id = uuid4()
    request = VerificationRequest(uuid4(), provider_id, "Negocio", "900", "123").submit()
    users = MemoryUsers(admin)
    verifications = MemoryVerifications()
    asyncio.run(verifications.save(request))

    resolved = asyncio.run(ResolveVerification(users, verifications).execute(
        ResolveVerificationCommand(admin.id, request.id, Decision.APROBAR, "RNT verificado")
    ))

    assert resolved.status is VerificationStatus.APROBADA
    assert verifications.events[0][0] == "auth.prestador.verificacion_resuelta"


def test_non_admin_cannot_resolve_request() -> None:
    provider = active_user(Role.PRESTADOR)
    request = VerificationRequest(uuid4(), provider.id, "Negocio", "900", "123").submit()
    with pytest.raises(AdministratorRequired):
        asyncio.run(ResolveVerification(
            MemoryUsers(provider), MemoryVerifications()
        ).execute(ResolveVerificationCommand(
            provider.id, request.id, Decision.RECHAZAR, "Sin registro"
        )))
