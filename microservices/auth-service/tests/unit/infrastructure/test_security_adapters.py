import asyncio
import hashlib
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from auth_service.domain.email import Email
from auth_service.domain.role import Role
from auth_service.domain.user import User, UserStatus
from auth_service.infrastructure.security import (
    Argon2PasswordHasher,
    ES256AccessTokenIssuer,
)
from auth_service.infrastructure.sessions import OpaqueRefreshSessionFactory


class FixedClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


def test_argon2id_hashes_and_verifies_passwords() -> None:
    hasher = Argon2PasswordHasher()
    encoded = hasher.hash("correct horse battery")
    assert encoded.startswith("$argon2id$")
    assert hasher.verify(encoded, "correct horse battery")
    assert not hasher.verify(encoded, "wrong password")


def make_issuer() -> tuple[ES256AccessTokenIssuer, ec.EllipticCurvePrivateKey]:
    private_key = ec.generate_private_key(ec.SECP256R1())
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    issuer = ES256AccessTokenIssuer(
        private_pem, "auth-key-01", "auth-service", "tourism-api", FixedClock()
    )
    return issuer, private_key


def test_es256_token_has_required_non_pii_claims_and_jwks() -> None:
    issuer, private_key = make_issuer()
    user = User(
        uuid4(),
        Email("private@example.com"),
        Role.TURISTA,
        "hash-only",
        UserStatus.ACTIVO,
    )

    token = issuer.issue_access_token(user)
    claims = jwt.decode(
        token,
        private_key.public_key(),
        algorithms=["ES256"],
        issuer="auth-service",
        audience="tourism-api",
    )
    assert claims["sub"] == str(user.id)
    assert claims["rol"] == "turista"
    assert claims["exp"] - claims["iat"] == 15 * 60
    assert "email" not in claims
    assert jwt.get_unverified_header(token)["kid"] == "auth-key-01"
    assert issuer.public_jwk()["crv"] == "P-256"


class FakeAccessTokens:
    def issue_access_token(self, user: User) -> str:
        return f"access-for-{user.id}"


class MemoryRefreshTokens:
    def __init__(self) -> None:
        self.records: list[tuple[UUID, str, datetime]] = []

    async def store_hash(self, user_id: UUID, token_hash: str, expires_at: datetime) -> None:
        self.records.append((user_id, token_hash, expires_at))


def test_refresh_token_is_random_and_only_its_hash_is_stored() -> None:
    user = User(
        uuid4(),
        Email("private@example.com"),
        Role.TURISTA,
        "hash-only",
        UserStatus.ACTIVO,
    )
    clock = FixedClock()
    repository = MemoryRefreshTokens()
    session = asyncio.run(OpaqueRefreshSessionFactory(
        FakeAccessTokens(), repository, clock
    ).create(user))

    stored_user_id, stored_hash, expires_at = repository.records[0]
    assert session.access_token == f"access-for-{user.id}"
    assert session.refresh_token != stored_hash
    assert stored_hash == hashlib.sha256(session.refresh_token.encode("utf-8")).hexdigest()
    assert stored_user_id == user.id
    assert expires_at - clock.now() <= timedelta(days=7)
