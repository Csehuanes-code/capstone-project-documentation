"""Caso de uso CU-28: decisión administrativa sobre un prestador."""

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from auth_service.application.ports import UserRepository, VerificationUnitOfWork
from auth_service.domain.errors import DomainError
from auth_service.domain.role import Role
from auth_service.domain.verification import VerificationRequest


class Decision(StrEnum):
    APROBAR = "aprobar"
    RECHAZAR = "rechazar"
    SOLICITAR_INFORMACION = "solicitar_informacion"


class AdministratorRequired(DomainError):
    pass


class VerificationNotFound(DomainError):
    pass


@dataclass(frozen=True, slots=True)
class ResolveVerificationCommand:
    actor_id: UUID
    request_id: UUID
    decision: Decision
    justification: str


class ResolveVerification:
    def __init__(
        self,
        users: UserRepository,
        verifications: VerificationUnitOfWork,
    ) -> None:
        self._users = users
        self._verifications = verifications

    async def execute(self, command: ResolveVerificationCommand) -> VerificationRequest:
        actor = await self._users.find_by_id(command.actor_id)
        if actor is None or actor.role is not Role.ADMINISTRADOR:
            raise AdministratorRequired("Solo un administrador puede resolver verificaciones.")
        request = await self._verifications.find_by_id(command.request_id)
        if request is None:
            raise VerificationNotFound("No se encontró la solicitud de verificación.")

        if command.decision is Decision.APROBAR:
            resolved = request.approve(command.justification)
        elif command.decision is Decision.RECHAZAR:
            resolved = request.reject(command.justification)
        else:
            resolved = request.request_information(command.justification)

        await self._verifications.save_with_event(
            resolved,
            "auth.prestador.verificacion_resuelta",
            {
                "solicitud_id": str(resolved.id),
                "prestador_id": str(resolved.provider_id),
                "estado": resolved.status.value,
                "justificacion": resolved.justification or "",
            },
        )
        return resolved
