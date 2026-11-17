"""Caso de uso CU-02: valida credenciales y crea una sesión."""

from dataclasses import dataclass
from uuid import UUID

from auth_service.application.ports import (
    AuthenticationAuditRecorder,
    AuthenticationSessionFactory,
    LoginAttemptGuard,
    PasswordHasher,
    UserRepository,
)
from auth_service.application.sessions import IssuedSession
from auth_service.domain.email import Email
from auth_service.domain.errors import AccountLocked, DomainError
from auth_service.domain.user import UserStatus


class InvalidCredentials(DomainError):
    """Error genérico para no revelar si existe una cuenta o está activa."""


@dataclass(frozen=True, slots=True)
class AuthenticateUserCommand:
    email: str
    password: str


@dataclass(frozen=True, slots=True)
class AuthenticationResult:
    user_id: UUID
    session: IssuedSession


class AuthenticateUser:
    def __init__(
        self,
        users: UserRepository,
        hasher: PasswordHasher,
        attempts: LoginAttemptGuard,
        audit: AuthenticationAuditRecorder,
        sessions: AuthenticationSessionFactory,
    ) -> None:
        self._users = users
        self._hasher = hasher
        self._attempts = attempts
        self._audit = audit
        self._sessions = sessions

    async def execute(self, command: AuthenticateUserCommand) -> AuthenticationResult:
        email = Email(command.email)
        identifier = email.value
        user = await self._users.find_by_email(email)
        try:
            await self._attempts.ensure_allowed(identifier)
        except AccountLocked:
            await self._audit.record_attempt(user.id if user else None, succeeded=False)
            raise

        if user is None:
            await self._attempts.record_failure(identifier)
            await self._audit.record_attempt(None, succeeded=False)
            raise InvalidCredentials("Correo o contraseña incorrectos.")

        if user.status is not UserStatus.ACTIVO or not self._hasher.verify(
            user.password_hash, command.password
        ):
            await self._attempts.record_failure(identifier)
            await self._audit.record_attempt(user.id, succeeded=False)
            raise InvalidCredentials("Correo o contraseña incorrectos.")

        await self._attempts.record_success(identifier)
        session = await self._sessions.create(user)
        await self._audit.record_attempt(user.id, succeeded=True)
        return AuthenticationResult(user.id, session)
