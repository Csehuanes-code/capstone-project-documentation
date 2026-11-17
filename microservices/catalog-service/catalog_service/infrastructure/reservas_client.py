"""HTTP client for communicating synchronously with Reservas service (ADR-04 §4.2)."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

import httpx

from catalog_service.application.ports import ReservasClient
from catalog_service.infrastructure.config import settings

logger = logging.getLogger(__name__)


class HttpReservasClient(ReservasClient):
    """Production HTTP client calling GET /reservas/{id}/estado with strict 1s timeout (ADR-04 §4.2)."""

    def __init__(
        self,
        base_url: str = settings.RESERVAS_SERVICE_URL,
        timeout: float = settings.RESERVAS_TIMEOUT_SECONDS,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def get_reserva_estado(
        self, reserva_id: UUID, token_acceso: str | None = None
    ) -> dict[str, Any] | None:
        url = f"{self.base_url}/api/v1/reservas/{reserva_id}/estado"
        headers = {"Authorization": f"Bearer {token_acceso}"} if token_acceso else {}
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    return data if isinstance(data, dict) else None
                logger.warning(
                    "Reservas service responded with status %s for reservation %s",
                    response.status_code,
                    reserva_id,
                )
                return None
        except httpx.TimeoutException:
            logger.error("Timeout connecting to Reservas service for reservation %s", reserva_id)
            return None
        except Exception as exc:
            logger.error("Error communicating with Reservas service: %s", exc)
            return None


class MockReservasClient(ReservasClient):
    """Configurable mock client for tests and standalone mode."""

    def __init__(self, default_estado: str = "completada") -> None:
        self.default_estado = default_estado
        self.reservas: dict[UUID, dict[str, Any]] = {}

    def set_reserva(self, reserva_id: UUID, estado: str) -> None:
        self.reservas[reserva_id] = {"id": str(reserva_id), "estado": estado}

    async def get_reserva_estado(
        self, reserva_id: UUID, token_acceso: str | None = None
    ) -> dict[str, Any] | None:
        if reserva_id in self.reservas:
            return self.reservas[reserva_id]
        # Fallback to configured default
        return {"id": str(reserva_id), "estado": self.default_estado}
