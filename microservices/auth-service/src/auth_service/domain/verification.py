"""Solicitud de verificación de prestadores y transiciones permitidas."""

from dataclasses import dataclass, replace
from enum import StrEnum
from uuid import UUID

from auth_service.domain.errors import InvalidVerificationTransition


class VerificationStatus(StrEnum):
    BORRADOR = "borrador"
    ENVIADA = "enviada"
    INFO_REQUERIDA = "info_requerida"
    APROBADA = "aprobada"
    RECHAZADA = "rechazada"


@dataclass(frozen=True, slots=True)
class VerificationRequest:
    id: UUID
    provider_id: UUID
    business_name: str
    nit: str
    rnt: str
    document_keys: tuple[str, ...] = ()
    status: VerificationStatus = VerificationStatus.BORRADOR
    justification: str | None = None

    def __post_init__(self) -> None:
        for field_name in ("business_name", "nit", "rnt"):
            if not getattr(self, field_name).strip():
                raise ValueError(f"{field_name} es obligatorio.")

    def submit(self) -> "VerificationRequest":
        if self.status not in {VerificationStatus.BORRADOR, VerificationStatus.INFO_REQUERIDA}:
            raise InvalidVerificationTransition("Solo un borrador o una solicitud con información pendiente puede enviarse.")
        return replace(self, status=VerificationStatus.ENVIADA, justification=None)

    def request_information(self, justification: str) -> "VerificationRequest":
        return self._decide(VerificationStatus.INFO_REQUERIDA, justification)

    def approve(self, justification: str) -> "VerificationRequest":
        return self._decide(VerificationStatus.APROBADA, justification)

    def reject(self, justification: str) -> "VerificationRequest":
        return self._decide(VerificationStatus.RECHAZADA, justification)

    def _decide(self, status: VerificationStatus, justification: str) -> "VerificationRequest":
        if self.status is not VerificationStatus.ENVIADA:
            raise InvalidVerificationTransition("Solo se puede resolver una solicitud enviada.")
        if not justification.strip():
            raise ValueError("La decisión debe incluir una justificación.")
        return replace(self, status=status, justification=justification.strip())
