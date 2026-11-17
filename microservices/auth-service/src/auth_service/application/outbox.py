"""Contrato neutral para eventos pendientes de integración."""

import re
from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID


class EventPublishError(Exception):
    """Fallo de transporte con código breve, sin datos del mensaje ni del broker."""

    def __init__(self, code: str) -> None:
        self.code = code if re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", code) else "publisher_error"
        super().__init__(self.code)


@dataclass(frozen=True, slots=True)
class OutboxEvent:
    id: UUID
    event_type: str
    payload: dict[str, Any]


@dataclass(frozen=True, slots=True)
class OutboxClaim:
    event: OutboxEvent
    lease_token: UUID
    attempts: int


class EventPublisher(Protocol):
    """Transporte que confirma cuando el broker acepta el evento."""

    async def publish(self, event: OutboxEvent) -> None: ...
