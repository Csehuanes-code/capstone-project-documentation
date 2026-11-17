"""Interfaces que la capa de aplicación necesita de los adaptadores."""

from datetime import datetime
from typing import Protocol
from uuid import UUID

from auth_service.application.identity import AuthenticatedIdentity
from auth_service.application.outbox import OutboxClaim
from auth_service.application.sessions import IssuedSession
from auth_service.domain.consent import Consent
from auth_service.domain.email import Email
from auth_service.domain.user import User
from auth_service.domain.verification import VerificationRequest


class UserRepository(Protocol):
    async def find_by_email(self, email: Email) -> User | None: ...

    async def find_by_id(self, user_id: UUID) -> User | None: ...


class RegistrationUnitOfWork(Protocol):
    async def create_user_with_consent_and_event(
        self,
        user: User,
        consent: Consent,
        event_type: str,
        event_data: dict[str, str],
        confirmation_token_hash: str,
        confirmation_expires_at: datetime,
    ) -> None: ...


class EmailConfirmationUnitOfWork(Protocol):
    async def confirm_email(self, token_hash: str, confirmed_at: datetime) -> bool: ...


class VerificationRepository(Protocol):
    async def find_by_id(self, request_id: UUID) -> VerificationRequest | None: ...

    async def save(self, request: VerificationRequest) -> None: ...


class VerificationUnitOfWork(Protocol):
    async def find_by_id(self, request_id: UUID) -> VerificationRequest | None: ...

    async def save_with_event(
        self,
        request: VerificationRequest,
        event_type: str,
        event_data: dict[str, str],
    ) -> None: ...


class OutboxRepository(Protocol):
    async def claim_pending(
        self,
        claimed_at: datetime,
        lease_duration_seconds: int,
        batch_size: int,
    ) -> list[OutboxClaim]: ...

    async def mark_published(
        self, event_id: UUID, lease_token: UUID, published_at: datetime
    ) -> bool: ...

    async def mark_failed(
        self,
        event_id: UUID,
        lease_token: UUID,
        failed_at: datetime,
        error_code: str,
    ) -> bool: ...


class PasswordHasher(Protocol):
    def hash(self, raw_password: str) -> str: ...

    def verify(self, encoded_hash: str, raw_password: str) -> bool: ...


class Clock(Protocol):
    def now(self) -> datetime: ...


class LoginAttemptGuard(Protocol):
    async def ensure_allowed(self, identifier: str) -> None: ...

    async def record_failure(self, identifier: str) -> None: ...

    async def record_success(self, identifier: str) -> None: ...


class AuthenticationAuditRecorder(Protocol):
    async def record_attempt(self, user_id: UUID | None, succeeded: bool) -> None: ...


class AuthenticationSessionFactory(Protocol):
    async def create(self, user: User) -> IssuedSession: ...


class AccessTokenIssuer(Protocol):
    def issue_access_token(self, user: User) -> str: ...


class AccessTokenVerifier(Protocol):
    def verify_access_token(self, token: str) -> AuthenticatedIdentity: ...


class JwkProvider(Protocol):
    def public_jwk(self) -> dict[str, str]: ...


class TokenSecurityService(AccessTokenVerifier, JwkProvider, Protocol):
    """Verifica tokens de acceso y publica la clave que los valida."""


class RefreshTokenRepository(Protocol):
    async def store_hash(self, user_id: UUID, token_hash: str, expires_at: datetime) -> None: ...

    async def rotate_hash(
        self,
        token_hash: str,
        replacement_hash: str,
        now: datetime,
        expires_at: datetime,
    ) -> User | None: ...

    async def revoke_hash(self, token_hash: str, revoked_at: datetime) -> bool: ...


class RefreshTokenManager(AuthenticationSessionFactory, Protocol):
    async def rotate(self, raw_token: str) -> IssuedSession: ...

    async def revoke(self, raw_token: str) -> bool: ...
