"""Caso de uso CU-26: guardar y enviar una solicitud de verificación."""

from dataclasses import dataclass
from uuid import UUID, uuid4

from auth_service.application.ports import UserRepository, VerificationRepository
from auth_service.domain.errors import DomainError
from auth_service.domain.role import Role
from auth_service.domain.user import UserStatus
from auth_service.domain.verification import VerificationRequest


class ProviderNotAllowed(DomainError):
    pass


@dataclass(frozen=True, slots=True)
class SubmitVerificationCommand:
    actor_id: UUID
    business_name: str
    nit: str
    rnt: str
    document_keys: tuple[str, ...] = ()


class SubmitVerification:
    def __init__(self, users: UserRepository, verifications: VerificationRepository) -> None:
        self._users = users
        self._verifications = verifications

    async def execute(self, command: SubmitVerificationCommand) -> VerificationRequest:
        actor = await self._users.find_by_id(command.actor_id)
        if actor is None or actor.role is not Role.PRESTADOR or actor.status is UserStatus.BLOQUEADO:
            raise ProviderNotAllowed("Solo un prestador habilitado puede enviar esta solicitud.")
        request = VerificationRequest(
            id=uuid4(),
            provider_id=actor.id,
            business_name=command.business_name,
            nit=command.nit,
            rnt=command.rnt,
            document_keys=command.document_keys,
        ).submit()
        await self._verifications.save(request)
        return request
