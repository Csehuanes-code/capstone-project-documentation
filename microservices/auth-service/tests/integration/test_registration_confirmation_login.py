"""Prueba de extremo a extremo opcional contra una base de prueba vacía."""

import asyncio
import os
from uuid import uuid4

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from auth_service.api.main import create_app_from_environment
from auth_service.infrastructure.db_models import OutboxRow


@pytest.mark.skipif(
    not os.environ.get("AUTH_INTEGRATION_DATABASE_URL"),
    reason="Define AUTH_INTEGRATION_DATABASE_URL con una base vacía y desechable.",
)
def test_register_confirm_and_login(monkeypatch: pytest.MonkeyPatch) -> None:
    database_url = os.environ["AUTH_INTEGRATION_DATABASE_URL"]
    private_key = ec.generate_private_key(ec.SECP256R1())
    private_pem = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode("utf-8")
    monkeypatch.setenv("AUTH_DATABASE_URL", database_url)
    monkeypatch.setenv("AUTH_JWT_PRIVATE_KEY_PEM", private_pem)
    monkeypatch.setenv("AUTH_JWT_KID", "integration-test")
    monkeypatch.setenv("AUTH_JWT_ISSUER", "auth-integration-test")
    monkeypatch.setenv("AUTH_JWT_AUDIENCE", "platform-integration-test")
    monkeypatch.setenv("AUTH_LOGIN_LOCKOUT_SECONDS", "60")

    app = create_app_from_environment()
    email = f"integration-{uuid4().hex}@example.com"
    with TestClient(app) as client:
        readiness = client.get("/ready")
        assert readiness.status_code == 200
        assert readiness.json() == {"status": "ready", "service": "auth"}

        registration = client.post(
            "/api/v1/auth/usuarios",
            json={
                "email": email,
                "password": "a-long-enough-integration-password",
                "role": "turista",
                "consent_accepted": True,
                "policy_version": "test-v1",
            },
        )
        assert registration.status_code == 201
        assert registration.json()["status"] == "pendiente"

        async def find_confirmation_token() -> str:
            engine = create_async_engine(database_url)
            sessions = async_sessionmaker(engine, expire_on_commit=False)
            try:
                async with sessions() as session:
                    events = (
                        await session.scalars(
                        select(OutboxRow)
                        .where(OutboxRow.event_type == "notificacion.solicitada")
                        )
                    ).all()
                    event = next(
                        (
                            candidate
                            for candidate in events
                            if candidate.payload.get("correo") == email
                        ),
                        None,
                    )
                    assert event is not None
                    return event.payload["token_confirmacion"]
            finally:
                await engine.dispose()

        token = asyncio.run(find_confirmation_token())
        confirmation = client.post("/api/v1/auth/confirmaciones", json={"token": token})
        assert confirmation.status_code == 204

        login = client.post(
            "/api/v1/auth/sesiones",
            json={
                "email": email,
                "password": "a-long-enough-integration-password",
            },
        )
        assert login.status_code == 200
        assert login.json()["token_type"] == "bearer"
        original_refresh = login.json()["refresh_token"]
        rotated = client.post(
            "/api/v1/auth/sesiones/refresh",
            json={"refresh_token": original_refresh},
        )
        assert rotated.status_code == 200
        replacement_refresh = rotated.json()["refresh_token"]
        assert replacement_refresh != original_refresh
        assert client.post(
            "/api/v1/auth/sesiones/refresh",
            json={"refresh_token": original_refresh},
        ).status_code == 401
        assert client.post(
            "/api/v1/auth/sesiones/revocar",
            json={"refresh_token": replacement_refresh},
        ).status_code == 204
        assert client.post(
            "/api/v1/auth/sesiones/refresh",
            json={"refresh_token": replacement_refresh},
        ).status_code == 401
        assert client.post(
            "/api/v1/auth/confirmaciones", json={"token": token}
        ).status_code == 400
