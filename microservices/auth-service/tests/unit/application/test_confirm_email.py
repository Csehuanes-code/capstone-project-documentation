import asyncio
import hashlib
from datetime import UTC, datetime

import pytest

from auth_service.application.confirm_email import (
    ConfirmEmail,
    ConfirmEmailCommand,
    InvalidConfirmationToken,
)


class FixedClock:
    def now(self) -> datetime:
        return datetime(2026, 11, 16, tzinfo=UTC)


class MemoryConfirmation:
    def __init__(self, accepted: bool) -> None:
        self.accepted = accepted
        self.confirmed_hash: str | None = None
        self.confirmed_at: datetime | None = None

    async def confirm_email(self, token_hash: str, confirmed_at: datetime) -> bool:
        self.confirmed_hash = token_hash
        self.confirmed_at = confirmed_at
        return self.accepted


def test_confirmation_hashes_token_and_uses_injected_clock() -> None:
    repository = MemoryConfirmation(accepted=True)
    use_case = ConfirmEmail(repository, FixedClock())
    asyncio.run(use_case.execute(ConfirmEmailCommand("opaque-confirmation-token")))

    assert repository.confirmed_hash == hashlib.sha256(
        b"opaque-confirmation-token"
    ).hexdigest()
    assert repository.confirmed_hash != "opaque-confirmation-token"
    assert repository.confirmed_at == FixedClock().now()


def test_confirmation_fails_for_unknown_expired_or_used_token() -> None:
    use_case = ConfirmEmail(MemoryConfirmation(accepted=False), FixedClock())
    with pytest.raises(InvalidConfirmationToken):
        asyncio.run(use_case.execute(ConfirmEmailCommand("opaque-confirmation-token")))


@pytest.mark.parametrize("token", ["", "x" * 257])
def test_confirmation_rejects_invalid_token_length(token: str) -> None:
    repository = MemoryConfirmation(accepted=True)
    with pytest.raises(InvalidConfirmationToken):
        asyncio.run(ConfirmEmail(repository, FixedClock()).execute(ConfirmEmailCommand(token)))
    assert repository.confirmed_hash is None
