from datetime import UTC, datetime
from typing import cast
from uuid import uuid4

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient

from auth_service.api.main import create_app
from auth_service.application.authenticate_user import (
    AuthenticateUser,
    AuthenticateUserCommand,
    AuthenticationResult,
)
from auth_service.application.confirm_email import (
    ConfirmEmail,
    ConfirmEmailCommand,
    InvalidConfirmationToken,
)
from auth_service.application.register_user import RegisterUser, RegisterUserCommand
from auth_service.application.resolve_verification import (
    Decision,
    ResolveVerification,
    ResolveVerificationCommand,
)
from auth_service.application.sessions import IssuedSession
from auth_service.application.submit_verification import (
    SubmitVerification,
    SubmitVerificationCommand,
)
from auth_service.domain.email import Email
from auth_service.domain.role import Role
from auth_service.domain.user import User, UserStatus
from auth_service.domain.verification import VerificationRequest
from auth_service.infrastructure.security import ES256AccessTokenIssuer


class FakeRegister:
    async def execute(self, command: RegisterUserCommand) -> User:
        return User(
            uuid4(), Email(command.email), command.role, "secret-hash", UserStatus.PENDIENTE
        )


class FakeAuthenticate:
    async def execute(self, command: AuthenticateUserCommand) -> AuthenticationResult:
        return AuthenticationResult(
            uuid4(), IssuedSession("access-test", "refresh-test", 900)
        )


class FakeConfirmEmail:
    async def execute(self, command: ConfirmEmailCommand) -> None:
        if command.token != "valid-confirmation-token":
            raise InvalidConfirmationToken("invalid")


class FakeJwks:
    def public_jwk(self) -> dict[str, str]:
        return {"kty": "EC", "kid": "test-key"}


class FakeSubmitVerification:
    async def execute(self, command: SubmitVerificationCommand) -> VerificationRequest:
        return VerificationRequest(
            uuid4(), command.actor_id, command.business_name, command.nit, command.rnt,
            command.document_keys,
        ).submit()


class FakeResolveVerification:
    async def execute(self, command: ResolveVerificationCommand) -> VerificationRequest:
        request = VerificationRequest(
            command.request_id,
            uuid4(),
            "Hotel del Mar",
            "900123456",
            "12345",
        ).submit()
        if command.decision is Decision.APROBAR:
            return request.approve(command.justification)
        if command.decision is Decision.RECHAZAR:
            return request.reject(command.justification)
        return request.request_information(command.justification)


def make_issuer() -> ES256AccessTokenIssuer:
    private_key = ec.generate_private_key(ec.SECP256R1())
    private_pem = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode("utf-8")

    class Clock:
        def now(self) -> datetime:
            return datetime.now(UTC)

    return ES256AccessTokenIssuer(private_pem, "test-key", "auth", "platform", Clock())


def make_access_token(issuer: ES256AccessTokenIssuer, role: Role) -> str:
    user = User(uuid4(), Email("person@example.com"), role, "hash", UserStatus.ACTIVO)
    return issuer.issue_access_token(user)


def test_health_is_available_without_auth_adapters() -> None:
    client = TestClient(create_app())
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "auth"}


def test_readiness_requires_a_successful_database_check() -> None:
    async def database_ready() -> bool:
        return True

    async def database_unavailable() -> bool:
        return False

    ready_client = TestClient(create_app(readiness_check=database_ready))
    response = ready_client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "service": "auth"}

    unavailable_client = TestClient(create_app(readiness_check=database_unavailable))
    response = unavailable_client.get("/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "not_ready", "service": "auth"}
    assert unavailable_client.get("/health").status_code == 200

    no_database_client = TestClient(create_app())
    assert no_database_client.get("/ready").status_code == 503


def test_register_endpoint_returns_user_without_password_hash() -> None:
    client = TestClient(create_app(register_user=cast(RegisterUser, FakeRegister())))
    response = client.post("/api/v1/auth/usuarios", json={
        "email": "person@example.com",
        "password": "secret-password",
        "role": "turista",
        "consent_accepted": True,
        "policy_version": "v1",
    })
    assert response.status_code == 201
    assert response.json()["email"] == "person@example.com"
    assert "password_hash" not in response.json()


def test_login_endpoint_returns_bearer_tokens() -> None:
    client = TestClient(
        create_app(authenticate_user=cast(AuthenticateUser, FakeAuthenticate()))
    )
    response = client.post("/api/v1/auth/sesiones", json={
        "email": "person@example.com",
        "password": "secret-password",
    })
    assert response.status_code == 200
    assert response.json() == {
        "access_token": "access-test",
        "refresh_token": "refresh-test",
        "token_type": "bearer",
        "expires_in": 900,
    }


def test_confirmation_endpoint_accepts_token_once() -> None:
    client = TestClient(
        create_app(confirm_email=cast(ConfirmEmail, FakeConfirmEmail()))
    )
    response = client.post(
        "/api/v1/auth/confirmaciones",
        json={"token": "valid-confirmation-token"},
    )
    assert response.status_code == 204


def test_confirmation_endpoint_returns_generic_error_for_invalid_token() -> None:
    client = TestClient(
        create_app(confirm_email=cast(ConfirmEmail, FakeConfirmEmail()))
    )
    response = client.post(
        "/api/v1/auth/confirmaciones", json={"token": "invalid-token-value"}
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "El enlace de confirmación no es válido o venció."


def test_endpoints_return_service_unavailable_without_composition() -> None:
    client = TestClient(create_app())
    response = client.post("/api/v1/auth/sesiones", json={
        "email": "person@example.com",
        "password": "secret-password",
    })
    assert response.status_code == 503


def test_jwks_exposes_only_public_key_data() -> None:
    client = TestClient(create_app(jwk_provider=cast(ES256AccessTokenIssuer, FakeJwks())))
    response = client.get("/.well-known/jwks.json")
    assert response.status_code == 200
    assert response.json() == {"keys": [{"kty": "EC", "kid": "test-key"}]}


def test_provider_verification_requires_a_bearer_token() -> None:
    client = TestClient(create_app(
        jwk_provider=make_issuer(),
        submit_verification=cast(SubmitVerification, FakeSubmitVerification()),
    ))
    response = client.post("/api/v1/auth/prestadores/verificaciones", json={
        "business_name": "Hotel del Mar",
        "nit": "900123456",
        "rnt": "12345",
    })
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_provider_verification_rejects_an_invalid_token() -> None:
    client = TestClient(create_app(
        jwk_provider=make_issuer(),
        submit_verification=cast(SubmitVerification, FakeSubmitVerification()),
    ))
    response = client.post(
        "/api/v1/auth/prestadores/verificaciones",
        headers={"Authorization": "Bearer invalid-token"},
        json={"business_name": "Hotel del Mar", "nit": "900123456", "rnt": "12345"},
    )
    assert response.status_code == 401


def test_tourist_cannot_submit_provider_verification() -> None:
    issuer = make_issuer()
    client = TestClient(create_app(
        jwk_provider=issuer,
        submit_verification=cast(SubmitVerification, FakeSubmitVerification()),
    ))
    response = client.post(
        "/api/v1/auth/prestadores/verificaciones",
        headers={"Authorization": f"Bearer {make_access_token(issuer, Role.TURISTA)}"},
        json={"business_name": "Hotel del Mar", "nit": "900123456", "rnt": "12345"},
    )
    assert response.status_code == 403


def test_prestador_can_submit_own_verification() -> None:
    issuer = make_issuer()
    client = TestClient(create_app(
        jwk_provider=issuer,
        submit_verification=cast(SubmitVerification, FakeSubmitVerification()),
    ))
    response = client.post(
        "/api/v1/auth/prestadores/verificaciones",
        headers={"Authorization": f"Bearer {make_access_token(issuer, Role.PRESTADOR)}"},
        json={
            "business_name": "Hotel del Mar",
            "nit": "900123456",
            "rnt": "12345",
            "document_keys": ["docs/registro-rnt.pdf"],
        },
    )
    assert response.status_code == 201
    assert response.json()["status"] == "enviada"
    assert response.json()["document_keys"] == ["docs/registro-rnt.pdf"]


def test_only_administrator_can_resolve_verification() -> None:
    issuer = make_issuer()
    request_id = uuid4()
    client = TestClient(create_app(
        jwk_provider=issuer,
        resolve_verification=cast(ResolveVerification, FakeResolveVerification()),
    ))
    response = client.post(
        f"/api/v1/auth/admin/verificaciones/{request_id}/decision",
        headers={"Authorization": f"Bearer {make_access_token(issuer, Role.PRESTADOR)}"},
        json={"decision": "aprobar", "justification": "RNT verificado"},
    )
    assert response.status_code == 403


def test_administrator_can_resolve_verification() -> None:
    issuer = make_issuer()
    request_id = uuid4()
    client = TestClient(create_app(
        jwk_provider=issuer,
        resolve_verification=cast(ResolveVerification, FakeResolveVerification()),
    ))
    response = client.post(
        f"/api/v1/auth/admin/verificaciones/{request_id}/decision",
        headers={
            "Authorization": f"Bearer {make_access_token(issuer, Role.ADMINISTRADOR)}"
        },
        json={"decision": "aprobar", "justification": "RNT verificado"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "aprobada"
    assert response.json()["justification"] == "RNT verificado"
