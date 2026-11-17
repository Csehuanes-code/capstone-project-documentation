import asyncio
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from auth_service.application.dispatch_outbox import DispatchOutbox
from auth_service.application.outbox import (
    EventPublishError,
    OutboxClaim,
    OutboxEvent,
)


class FixedClock:
    def now(self) -> datetime:
        return datetime(2026, 11, 16, 12, 0, tzinfo=UTC)


class MemoryOutbox:
    def __init__(self, events: list[OutboxClaim]) -> None:
        self.events = list(events)
        self.original = list(events)
        self.published: list[OutboxEvent] = []
        self.failures: list[tuple[OutboxEvent, str]] = []

    async def claim_pending(self, claimed_at, lease_duration_seconds, batch_size):
        del claimed_at, lease_duration_seconds
        claimed = self.events[:batch_size]
        self.events = self.events[batch_size:]
        return claimed

    async def mark_published(self, event_id, lease_token, published_at):
        del published_at
        claim = next(
            claim
            for claim in self.original
            if claim.event.id == event_id and claim.lease_token == lease_token
        )
        self.published.append(claim.event)
        return True

    async def mark_failed(self, event_id, lease_token, failed_at, error_code):
        del failed_at
        claim = next(
            claim
            for claim in self.original
            if claim.event.id == event_id and claim.lease_token == lease_token
        )
        self.failures.append((claim.event, error_code))
        return True


class RecordingPublisher:
    def __init__(self, failing_event_id=None) -> None:
        self.failing_event_id = failing_event_id
        self.published: list[OutboxEvent] = []

    async def publish(self, event: OutboxEvent) -> None:
        if event.id == self.failing_event_id:
            raise EventPublishError("broker_unavailable")
        self.published.append(event)


def test_dispatch_marks_success_and_schedules_failure_without_error_text() -> None:
    async def scenario() -> None:
        successful = OutboxEvent(uuid4(), "auth.usuario.confirmado", {"id": "1"})
        failing = OutboxEvent(uuid4(), "notificacion.solicitada", {"correo": "x"})
        claims = [
            OutboxClaim(successful, uuid4(), 1),
            OutboxClaim(failing, uuid4(), 2),
        ]
        repository = MemoryOutbox(claims)
        publisher = RecordingPublisher(failing.id)

        result = await DispatchOutbox(repository, publisher, FixedClock()).execute()

        assert result.published == 1
        assert result.failed == 1
        assert publisher.published == [successful]
        assert repository.published == [successful]
        assert repository.failures == [(failing, "broker_unavailable")]

    asyncio.run(scenario())


def test_dispatch_requires_positive_batch_and_lease() -> None:
    repository = MemoryOutbox([])
    publisher = RecordingPublisher()
    with pytest.raises(ValueError):
        DispatchOutbox(repository, publisher, FixedClock(), batch_size=0)
    with pytest.raises(ValueError):
        DispatchOutbox(repository, publisher, FixedClock(), lease_duration_seconds=0)


def test_publish_error_discards_untrusted_exception_text() -> None:
    error = EventPublishError("Connection failed: sensitive@example.com")
    assert error.code == "publisher_error"
    assert str(error) == "publisher_error"
