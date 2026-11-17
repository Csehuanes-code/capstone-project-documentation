"""Rutas protegidas para solicitudes y decisiones de verificación."""

from typing import Annotated, cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from auth_service.api.schemas import (
    ResolveVerificationRequest,
    SubmitVerificationRequest,
    VerificationResponse,
)
from auth_service.application.errors import TokenVerificationFailed
from auth_service.application.identity import AuthenticatedIdentity
from auth_service.application.ports import TokenSecurityService
from auth_service.application.resolve_verification import (
    AdministratorRequired,
    ResolveVerification,
    ResolveVerificationCommand,
    VerificationNotFound,
)
from auth_service.application.submit_verification import (
    ProviderNotAllowed,
    SubmitVerification,
    SubmitVerificationCommand,
)
from auth_service.domain.errors import InvalidVerificationTransition
from auth_service.domain.role import Role

router = APIRouter(prefix="/api/v1/auth", tags=["Verificación de prestadores"])
bearer_scheme = HTTPBearer(auto_error=False)


def _submit_use_case(request: Request) -> SubmitVerification:
    use_case = request.app.state.submit_verification
    if use_case is None:
        raise HTTPException(status_code=503, detail="Verificación no está configurada.")
    return cast(SubmitVerification, use_case)


def _resolve_use_case(request: Request) -> ResolveVerification:
    use_case = request.app.state.resolve_verification
    if use_case is None:
        raise HTTPException(status_code=503, detail="Verificación no está configurada.")
    return cast(ResolveVerification, use_case)


def _identity(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None,
) -> AuthenticatedIdentity:
    token_service = request.app.state.jwk_provider
    if token_service is None:
        raise HTTPException(status_code=503, detail="Autorización no está configurada.")
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Se requiere un token de acceso.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        return cast(TokenSecurityService, token_service).verify_access_token(
            credentials.credentials
        )
    except TokenVerificationFailed as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El token de acceso no es válido.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def _provider_identity(
    request: Request,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer_scheme)
    ],
) -> AuthenticatedIdentity:
    identity = _identity(request, credentials)
    if identity.role is not Role.PRESTADOR:
        raise HTTPException(status_code=403, detail="Se requiere el rol prestador.")
    return identity


def _administrator_identity(
    request: Request,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer_scheme)
    ],
) -> AuthenticatedIdentity:
    identity = _identity(request, credentials)
    if identity.role is not Role.ADMINISTRADOR:
        raise HTTPException(status_code=403, detail="Se requiere el rol administrador.")
    return identity


@router.post(
    "/prestadores/verificaciones",
    response_model=VerificationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_verification(
    body: SubmitVerificationRequest,
    use_case: Annotated[SubmitVerification, Depends(_submit_use_case)],
    identity: Annotated[AuthenticatedIdentity, Depends(_provider_identity)],
) -> VerificationResponse:
    try:
        request = await use_case.execute(
            SubmitVerificationCommand(
                actor_id=identity.user_id,
                business_name=body.business_name,
                nit=body.nit,
                rnt=body.rnt,
                document_keys=tuple(body.document_keys),
            )
        )
    except ProviderNotAllowed as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return VerificationResponse.from_domain(request)


@router.post(
    "/admin/verificaciones/{request_id}/decision",
    response_model=VerificationResponse,
)
async def resolve_verification(
    request_id: UUID,
    body: ResolveVerificationRequest,
    use_case: Annotated[ResolveVerification, Depends(_resolve_use_case)],
    identity: Annotated[AuthenticatedIdentity, Depends(_administrator_identity)],
) -> VerificationResponse:
    try:
        request = await use_case.execute(
            ResolveVerificationCommand(
                actor_id=identity.user_id,
                request_id=request_id,
                decision=body.decision,
                justification=body.justification,
            )
        )
    except AdministratorRequired as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except VerificationNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidVerificationTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return VerificationResponse.from_domain(request)
