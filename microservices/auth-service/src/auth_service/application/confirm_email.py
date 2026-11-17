"""Confirma una dirección y activa la cuenta una sola vez."""

import hashlib
from dataclasses import dataclass

from auth_service.application.ports import Clock, EmailConfirmationUnitOfWork
from auth_service.domain.errors import DomainError


class InvalidConfirmationToken(DomainError):
    """Token inexistente, expirado o ya utilizado."""


@dataclass(frozen=True, slots=True)
class ConfirmEmailCommand:
    token: str


class ConfirmEmail:
    def __init__(self, unit_of_work: EmailConfirmationUnitOfWork, clock: Clock) -> None:
        self._unit_of_work = unit_of_work
        self._clock = clock

    async def execute(self, command: ConfirmEmailCommand) -> None:
        if not command.token or len(command.token) > 256:
            raise InvalidConfirmationToken("El enlace de confirmación no es válido o venció.")
        token_hash = hashlib.sha256(command.token.encode("utf-8")).hexdigest()
        confirmed = await self._unit_of_work.confirm_email(token_hash, self._clock.now())
        if not confirmed:
            raise InvalidConfirmationToken("El enlace de confirmación no es válido o venció.")
