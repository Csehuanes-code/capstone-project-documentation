"""Esquemas HTTP de entrada y salida para Auth."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from auth_service.application.resolve_verification import Decision
from auth_service.application.sessions import IssuedSession
from auth_service.domain.role import Role
from auth_service.domain.user import User, UserStatus
from auth_service.domain.verification import VerificationRequest, VerificationStatus


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=1024)
    role: Role
    consent_accepted: bool
    policy_version: str = Field(min_length=1, max_length=100)


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=1024)


class ConfirmEmailRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: str = Field(min_length=16, max_length=256)


class RefreshTokenRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    refresh_token: str = Field(min_length=16, max_length=256)


class UserResponse(BaseModel):
    id: UUID
    email: str
    role: Role
    status: UserStatus

    @classmethod
    def from_domain(cls, user: User) -> "UserResponse":
        return cls(id=user.id, email=user.email.value, role=user.role, status=user.status)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int

    @classmethod
    def from_session(cls, session: IssuedSession) -> "TokenResponse":
        return cls(
            access_token=session.access_token,
            refresh_token=session.refresh_token,
            expires_in=session.access_expires_in,
        )


class SubmitVerificationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    business_name: str = Field(min_length=1, max_length=200)
    nit: str = Field(min_length=1, max_length=32)
    rnt: str = Field(min_length=1, max_length=32)
    document_keys: list[str] = Field(default_factory=list, max_length=20)


class ResolveVerificationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: Decision
    justification: str = Field(min_length=1, max_length=2000)


class VerificationResponse(BaseModel):
    id: UUID
    provider_id: UUID
    business_name: str
    nit: str
    rnt: str
    document_keys: list[str]
    status: VerificationStatus
    justification: str | None

    @classmethod
    def from_domain(cls, request: VerificationRequest) -> "VerificationResponse":
        return cls(
            id=request.id,
            provider_id=request.provider_id,
            business_name=request.business_name,
            nit=request.nit,
            rnt=request.rnt,
            document_keys=list(request.document_keys),
            status=request.status,
            justification=request.justification,
        )
