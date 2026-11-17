"""Listado de solicitudes de verificación para el administrador (CU-28)."""

from auth_service.application.ports import VerificationRepository
from auth_service.domain.verification import VerificationRequest, VerificationStatus


class ListVerifications:
    def __init__(self, verifications: VerificationRepository) -> None:
        self._verifications = verifications

    async def execute(self, status: VerificationStatus | None = None) -> list[VerificationRequest]:
        return await self._verifications.list_by_status(status)
