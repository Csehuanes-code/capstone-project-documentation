"""Creación de sesiones con refresh token opaco guardado como hash."""

import hashlib
import secrets
from datetime import datetime, timedelta

from auth_service.application.errors import InvalidRefreshToken
from auth_service.application.ports import (
    AccessTokenIssuer,
    Clock,
    RefreshTokenRepository,
)
from auth_service.application.sessions import IssuedSession
from auth_service.domain.user import User


class OpaqueRefreshSessionFactory:
    """Emite refresh aleatorio; persiste únicamente SHA-256(token) y expiración."""

    def __init__(
        self,
        access_tokens: AccessTokenIssuer,
        refresh_tokens: RefreshTokenRepository,
        clock: Clock,
        refresh_token_ttl: timedelta = timedelta(days=7),
    ) -> None:
        if refresh_token_ttl <= timedelta(0):
            raise ValueError("La duración del refresh token debe ser positiva.")
        self._access_tokens = access_tokens
        self._refresh_tokens = refresh_tokens
        self._clock = clock
        self._refresh_ttl = refresh_token_ttl

    async def create(self, user: User) -> IssuedSession:
        now: datetime = self._clock.now()
        if now.tzinfo is None:
            raise ValueError("El reloj debe producir fechas con zona horaria.")
        raw_refresh_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_refresh_token.encode("utf-8")).hexdigest()
        access_token = self._access_tokens.issue_access_token(user)
        await self._refresh_tokens.store_hash(
            user.id,
            token_hash,
            now + self._refresh_ttl,
        )
        return IssuedSession(
            access_token=access_token,
            refresh_token=raw_refresh_token,
            access_expires_in=900,
        )

    async def rotate(self, raw_token: str) -> IssuedSession:
        now = self._clock.now()
        if now.tzinfo is None:
            raise ValueError("El reloj debe producir fechas con zona horaria.")
        replacement_token = secrets.token_urlsafe(32)
        user = await self._refresh_tokens.rotate_hash(
            self._hash(raw_token),
            self._hash(replacement_token),
            now,
            now + self._refresh_ttl,
        )
        if user is None:
            raise InvalidRefreshToken("El refresh token no es válido.")
        return IssuedSession(
            access_token=self._access_tokens.issue_access_token(user),
            refresh_token=replacement_token,
            access_expires_in=900,
        )

    async def revoke(self, raw_token: str) -> bool:
        now = self._clock.now()
        if now.tzinfo is None:
            raise ValueError("El reloj debe producir fechas con zona horaria.")
        return await self._refresh_tokens.revoke_hash(self._hash(raw_token), now)

    @staticmethod
    def _hash(raw_token: str) -> str:
        return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
