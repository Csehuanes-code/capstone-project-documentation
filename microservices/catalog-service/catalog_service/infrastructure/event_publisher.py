"""Event publisher implementing the Transactional Outbox pattern (ADR-04 §4.1)."""

from __future__ import annotations

import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from catalog_service.application.ports import EventPublisher
from catalog_service.infrastructure.models import OutboxModel


class SqlAlchemyOutboxEventPublisher(EventPublisher):
    """Writes domain events to the outbox table in the same database transaction."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def publish(
        self,
        tipo: str,
        datos: dict[str, Any],
        *,
        correlation_id: str | None = None,
    ) -> None:
        cid_uuid: UUID | None = None
        if correlation_id:
            try:
                cid_uuid = UUID(correlation_id)
            except ValueError:
                cid_uuid = None

        outbox_entry = OutboxModel(
            id=uuid4(),
            tipo=tipo,
            version=1,
            correlation_id=cid_uuid,
            datos=datos,
            ocurrido_en=datetime.datetime.now(datetime.UTC),
            publicado_en=None,
            intentos=0,
        )
        self.session.add(outbox_entry)


class InMemoryEventPublisher(EventPublisher):
    """In-memory event publisher for testing and standalone dev mode."""

    def __init__(self) -> None:
        self.published_events: list[dict[str, Any]] = []

    async def publish(
        self,
        tipo: str,
        datos: dict[str, Any],
        *,
        correlation_id: str | None = None,
    ) -> None:
        event = {
            "evento_id": str(uuid4()),
            "tipo": tipo,
            "version": 1,
            "ocurrido_en": datetime.datetime.now(datetime.UTC).isoformat(),
            "correlation_id": correlation_id,
            "datos": datos,
        }
        self.published_events.append(event)
