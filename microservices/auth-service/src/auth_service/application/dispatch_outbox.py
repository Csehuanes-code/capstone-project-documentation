"""Despacha eventos del outbox con entrega al menos una vez."""

from dataclasses import dataclass

from auth_service.application.outbox import EventPublisher, EventPublishError
from auth_service.application.ports import Clock, OutboxRepository


@dataclass(frozen=True, slots=True)
class DispatchResult:
    published: int
    failed: int


class DispatchOutbox:
    def __init__(
        self,
        repository: OutboxRepository,
        publisher: EventPublisher,
        clock: Clock,
        *,
        batch_size: int = 50,
        lease_duration_seconds: int = 60,
    ) -> None:
        if batch_size < 1 or lease_duration_seconds < 1:
            raise ValueError("El lote y la duración del lease deben ser positivos.")
        self._repository = repository
        self._publisher = publisher
        self._clock = clock
        self._batch_size = batch_size
        self._lease_duration_seconds = lease_duration_seconds

    async def execute(self) -> DispatchResult:
        events = await self._repository.claim_pending(
            self._clock.now(), self._lease_duration_seconds, self._batch_size
        )
        published = 0
        failed = 0
        for claim in events:
            try:
                await self._publisher.publish(claim.event)
            except EventPublishError as exc:
                if await self._repository.mark_failed(
                    claim.event.id, claim.lease_token, self._clock.now(), exc.code
                ):
                    failed += 1
            else:
                if await self._repository.mark_published(
                    claim.event.id, claim.lease_token, self._clock.now()
                ):
                    published += 1
        return DispatchResult(published=published, failed=failed)
