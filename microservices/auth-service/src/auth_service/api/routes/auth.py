"""Rutas HTTP para registro e inicio de sesión."""

from typing import Annotated, cast

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from auth_service.api.schemas import (
    ConfirmEmailRequest,
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from auth_service.application.authenticate_user import (
    AuthenticateUser,
    AuthenticateUserCommand,
    InvalidCredentials,
)
from auth_service.application.confirm_email import (
    ConfirmEmail,
    ConfirmEmailCommand,
    InvalidConfirmationToken,
)
from auth_service.application.errors import InvalidRefreshToken
from auth_service.application.refresh_session import (
    RefreshSession,
    RefreshSessionCommand,
)
from auth_service.application.register_user import (
    ConsentRequired,
    DuplicateEmail,
    RegisterUser,
    RegisterUserCommand,
    RegistrationRoleNotAllowed,
)
from auth_service.domain.errors import AccountLocked, InvalidEmail

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])


def _register_user(request: Request) -> RegisterUser:
    use_case = request.app.state.register_user
    if use_case is None:
        raise HTTPException(status_code=503, detail="Registro no está configurado.")
    return cast(RegisterUser, use_case)


def _authenticate_user(request: Request) -> AuthenticateUser:
    use_case = request.app.state.authenticate_user
    if use_case is None:
        raise HTTPException(status_code=503, detail="Autenticación no está configurada.")
    return cast(AuthenticateUser, use_case)


def _confirm_email(request: Request) -> ConfirmEmail:
    use_case = request.app.state.confirm_email
    if use_case is None:
        raise HTTPException(status_code=503, detail="Confirmación de correo no está configurada.")
    return cast(ConfirmEmail, use_case)


def _refresh_session(request: Request) -> RefreshSession:
    use_case = request.app.state.refresh_session
    if use_case is None:
        raise HTTPException(status_code=503, detail="Sesiones no están configuradas.")
    return cast(RefreshSession, use_case)


@router.post("/usuarios", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    use_case: Annotated[RegisterUser, Depends(_register_user)],
) -> UserResponse:
    try:
        user = await use_case.execute(RegisterUserCommand(**body.model_dump()))
    except ConsentRequired as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except DuplicateEmail as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except (RegistrationRoleNotAllowed, InvalidEmail, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return UserResponse.from_domain(user)


@router.post("/sesiones", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    use_case: Annotated[AuthenticateUser, Depends(_authenticate_user)],
) -> TokenResponse:
    try:
        result = await use_case.execute(AuthenticateUserCommand(**body.model_dump()))
    except AccountLocked as exc:
        raise HTTPException(status_code=429, detail="Correo o contraseña incorrectos.") from exc
    except (InvalidCredentials, InvalidEmail) as exc:
        raise HTTPException(status_code=401, detail="Correo o contraseña incorrectos.") from exc
    return TokenResponse.from_session(result.session)


@router.post("/confirmaciones", status_code=status.HTTP_204_NO_CONTENT)
async def confirm_email(
    body: ConfirmEmailRequest,
    use_case: Annotated[ConfirmEmail, Depends(_confirm_email)],
) -> Response:
    try:
        await use_case.execute(ConfirmEmailCommand(body.token))
    except InvalidConfirmationToken as exc:
        raise HTTPException(
            status_code=400,
            detail="El enlace de confirmación no es válido o venció.",
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/sesiones/refresh", response_model=TokenResponse)
async def refresh_session(
    body: RefreshTokenRequest,
    use_case: Annotated[RefreshSession, Depends(_refresh_session)],
) -> TokenResponse:
    try:
        session = await use_case.execute(RefreshSessionCommand(body.refresh_token))
    except InvalidRefreshToken as exc:
        raise HTTPException(
            status_code=401,
            detail="El refresh token no es válido.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    return TokenResponse.from_session(session)


@router.post("/sesiones/revocar", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_session(
    body: RefreshTokenRequest,
    use_case: Annotated[RefreshSession, Depends(_refresh_session)],
) -> Response:
    await use_case.revoke(RefreshSessionCommand(body.refresh_token))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
