"""Caso de uso CU-01: registro de turista o prestador."""

import hashlib
import secrets
from dataclasses import dataclass
from datetime import timedelta
from uuid import uuid4

from auth_service.application.ports import (
    Clock,
    PasswordHasher,
    RegistrationUnitOfWork,
    UserRepository,
)
from auth_service.domain.consent import Consent
from auth_service.domain.email import Email
from auth_service.domain.errors import DomainError
from auth_service.domain.role import Role
from auth_service.domain.user import User, UserStatus


class ConsentRequired(DomainError):
    pass


class DuplicateEmail(DomainError):
    pass


class RegistrationRoleNotAllowed(DomainError):
    pass


@dataclass(frozen=True, slots=True)
class RegisterUserCommand:
    email: str
    password: str
    role: Role
    consent_accepted: bool
    policy_version: str


class RegisterUser:
    def __init__(
        self,
        users: UserRepository,
        registration: RegistrationUnitOfWork,
        hasher: PasswordHasher,
        clock: Clock,
    ) -> None:
        self._users = users
        self._registration = registration
        self._hasher = hasher
        self._clock = clock

    async def execute(self, command: RegisterUserCommand) -> User:
        if not command.consent_accepted:
            raise ConsentRequired("Se debe aceptar la política de datos para crear la cuenta.")
        if command.role not in {Role.TURISTA, Role.PRESTADOR}:
            raise RegistrationRoleNotAllowed("El registro público solo admite turista o prestador.")
        if not command.policy_version.strip():
            raise ValueError("La versión de la política de datos es obligatoria.")
        if not command.password:
            raise ValueError("La contraseña no puede estar vacía.")

        email = Email(command.email)
        if await self._users.find_by_email(email) is not None:
            raise DuplicateEmail("Ya existe una cuenta con ese correo.")

        user = User(
            id=uuid4(),
            email=email,
            role=command.role,
            password_hash=self._hasher.hash(command.password),
            status=UserStatus.PENDIENTE,
        )
        now = self._clock.now()
        consent = Consent(
            user_id=user.id,
            purpose="gestionar_reservas",
            policy_version=command.policy_version,
            accepted_at=now,
        )
        confirmation_token = secrets.token_urlsafe(32)
        confirmation_expires_at = now + timedelta(hours=24)
        await self._registration.create_user_with_consent_and_event(
            user,
            consent,
            "notificacion.solicitada",
            {
                "tipo": "confirmacion_registro",
                "destinatario_id": str(user.id),
                "correo": user.email.value,
                "token_confirmacion": confirmation_token,
                "expira_en": confirmation_expires_at.isoformat(),
                "idioma": "es",
            },
            hashlib.sha256(confirmation_token.encode("utf-8")).hexdigest(),
            confirmation_expires_at,
        )
        return user
