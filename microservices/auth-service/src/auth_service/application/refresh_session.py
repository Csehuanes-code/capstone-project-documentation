"""Rotación y revocación de refresh tokens."""

from dataclasses import dataclass

from auth_service.application.errors import InvalidRefreshToken
from auth_service.application.ports import RefreshTokenManager
from auth_service.application.sessions import IssuedSession


@dataclass(frozen=True, slots=True)
class RefreshSessionCommand:
    refresh_token: str


class RefreshSession:
    def __init__(self, tokens: RefreshTokenManager) -> None:
        self._tokens = tokens

    async def execute(self, command: RefreshSessionCommand) -> IssuedSession:
        if not command.refresh_token or len(command.refresh_token) > 256:
            raise InvalidRefreshToken("El refresh token no es válido.")
        return await self._tokens.rotate(command.refresh_token)

    async def revoke(self, command: RefreshSessionCommand) -> bool:
        if not command.refresh_token or len(command.refresh_token) > 256:
            return False
        return await self._tokens.revoke(command.refresh_token)
