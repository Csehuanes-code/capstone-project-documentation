import asyncio
import contextlib
import logging
import os
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from datetime import timedelta
from pathlib import Path

from fastapi import FastAPI

from auth_service.api.routes.auth import router as auth_router
from auth_service.api.routes.health import router as health_router
from auth_service.api.routes.jwks import router as jwks_router
from auth_service.api.routes.verification import router as verification_router
from auth_service.application.authenticate_user import AuthenticateUser
from auth_service.application.confirm_email import ConfirmEmail
from auth_service.application.dispatch_outbox import DispatchOutbox
from auth_service.application.list_verifications import ListVerifications
from auth_service.application.ports import TokenSecurityService
from auth_service.application.refresh_session import RefreshSession
from auth_service.application.register_user import RegisterUser
from auth_service.application.resolve_verification import ResolveVerification
from auth_service.application.submit_verification import SubmitVerification
from auth_service.domain.email import Email
from auth_service.infrastructure.clock import SystemClock
from auth_service.infrastructure.database import (
    SqlAuthenticationAuditRecorder,
    SqlEmailConfirmationUnitOfWork,
    SqlLoginAttemptGuard,
    SqlOutboxRepository,
    SqlRefreshTokenRepository,
    SqlRegistrationUnitOfWork,
    SqlUserRepository,
    SqlVerificationRepository,
    SqlVerificationUnitOfWork,
    create_database,
    ensure_administrator,
)
from auth_service.infrastructure.rabbitmq import RabbitMqEventPublisher
from auth_service.infrastructure.security import (
    Argon2PasswordHasher,
    ES256AccessTokenIssuer,
)
from auth_service.infrastructure.sessions import OpaqueRefreshSessionFactory


def create_app(
    register_user: RegisterUser | None = None,
    authenticate_user: AuthenticateUser | None = None,
    jwk_provider: TokenSecurityService | None = None,
    lifespan: Callable[[FastAPI], AbstractAsyncContextManager[None]] | None = None,
    submit_verification: SubmitVerification | None = None,
    resolve_verification: ResolveVerification | None = None,
    confirm_email: ConfirmEmail | None = None,
    refresh_session: RefreshSession | None = None,
    readiness_check: Callable[[], Awaitable[bool]] | None = None,
    list_verifications: ListVerifications | None = None,
) -> FastAPI:
    app = FastAPI(
        title="Auth - Plataforma de Turismo de Santa Marta",
        version="0.1.0",
        description="Borrador del servicio de usuarios y seguridad.",
        lifespan=lifespan,
    )
    app.state.register_user = register_user
    app.state.authenticate_user = authenticate_user
    app.state.jwk_provider = jwk_provider
    app.state.submit_verification = submit_verification
    app.state.resolve_verification = resolve_verification
    app.state.confirm_email = confirm_email
    app.state.refresh_session = refresh_session
    app.state.readiness_check = readiness_check
    app.state.list_verifications = list_verifications
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(jwks_router)
    app.include_router(verification_router)
    return app


def create_app_from_environment() -> FastAPI:
    database_url = os.environ.get("AUTH_DATABASE_URL")
    if not database_url:
        return create_app()

    required = (
        "AUTH_JWT_KID",
        "AUTH_JWT_ISSUER",
        "AUTH_JWT_AUDIENCE",
        "AUTH_LOGIN_LOCKOUT_SECONDS",
    )
    missing = [name for name in required if not os.environ.get(name)]
    if not (
        os.environ.get("AUTH_JWT_PRIVATE_KEY_PEM")
        or os.environ.get("AUTH_JWT_PRIVATE_KEY_FILE")
    ):
        missing.insert(0, "AUTH_JWT_PRIVATE_KEY_FILE o AUTH_JWT_PRIVATE_KEY_PEM")
    if missing:
        raise RuntimeError(f"Faltan variables de entorno requeridas: {', '.join(missing)}")

    runtime = create_database(database_url)
    sessions = runtime.sessions
    clock = SystemClock()
    private_key_pem = os.environ.get("AUTH_JWT_PRIVATE_KEY_PEM")
    private_key_file = os.environ.get("AUTH_JWT_PRIVATE_KEY_FILE")
    if private_key_file:
        private_key_pem = Path(private_key_file).read_text(encoding="utf-8")
    token_issuer = ES256AccessTokenIssuer(
        private_key_pem=private_key_pem or "",
        key_id=os.environ["AUTH_JWT_KID"],
        issuer=os.environ["AUTH_JWT_ISSUER"],
        audience=os.environ["AUTH_JWT_AUDIENCE"],
        clock=clock,
    )
    user_repository = SqlUserRepository(sessions)
    register_user = RegisterUser(
        user_repository,
        SqlRegistrationUnitOfWork(sessions),
        Argon2PasswordHasher(),
        clock,
    )
    confirm_email = ConfirmEmail(SqlEmailConfirmationUnitOfWork(sessions), clock)
    refresh_session_factory = OpaqueRefreshSessionFactory(
        token_issuer,
        SqlRefreshTokenRepository(sessions),
        clock,
    )
    refresh_session = RefreshSession(refresh_session_factory)
    authenticate_user = AuthenticateUser(
        user_repository,
        Argon2PasswordHasher(),
        SqlLoginAttemptGuard(
            sessions,
            block_duration=timedelta(
                seconds=int(os.environ["AUTH_LOGIN_LOCKOUT_SECONDS"])
            ),
            clock=clock.now,
        ),
        SqlAuthenticationAuditRecorder(sessions),
        refresh_session_factory,
    )
    submit_verification = SubmitVerification(
        user_repository,
        SqlVerificationRepository(sessions),
    )
    resolve_verification = ResolveVerification(
        user_repository,
        SqlVerificationUnitOfWork(sessions),
    )

    hasher = Argon2PasswordHasher()
    admin_email = os.environ.get("AUTH_ADMIN_EMAIL")
    admin_password = os.environ.get("AUTH_ADMIN_PASSWORD")
    rabbitmq_url = os.environ.get("AUTH_RABBITMQ_URL", "")
    publisher = RabbitMqEventPublisher(rabbitmq_url) if rabbitmq_url else None
    dispatch = (
        DispatchOutbox(SqlOutboxRepository(sessions), publisher, clock) if publisher else None
    )

    async def _despachar_outbox() -> None:
        """Publica el outbox en RabbitMQ cada segundo; los fallos se reintentan solos."""
        assert dispatch is not None
        while True:
            try:
                await dispatch.execute()
            except Exception:
                logging.getLogger("auth.outbox").warning("Despacho del outbox falló", exc_info=True)
            await asyncio.sleep(1)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        if admin_email and admin_password:
            await ensure_administrator(sessions, Email(admin_email), hasher.hash(admin_password))
        tarea = asyncio.create_task(_despachar_outbox()) if dispatch else None
        yield
        if tarea is not None:
            tarea.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await tarea
        if publisher is not None:
            await publisher.close()
        await runtime.dispose()

    return create_app(
        register_user,
        authenticate_user,
        token_issuer,
        lifespan=lifespan,
        submit_verification=submit_verification,
        resolve_verification=resolve_verification,
        confirm_email=confirm_email,
        refresh_session=refresh_session,
        readiness_check=runtime.check_ready,
        list_verifications=ListVerifications(SqlVerificationRepository(sessions)),
    )


app = create_app_from_environment()
