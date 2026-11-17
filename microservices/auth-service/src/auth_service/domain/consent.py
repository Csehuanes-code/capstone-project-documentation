"""Evidencia de consentimiento de tratamiento de datos personales."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class Consent:
    user_id: UUID
    purpose: str
    policy_version: str
    accepted_at: datetime

    def __post_init__(self) -> None:
        if not self.purpose.strip() or not self.policy_version.strip():
            raise ValueError("La finalidad y versión de la política son obligatorias.")
        if self.accepted_at.tzinfo is None:
            raise ValueError("La fecha del consentimiento debe incluir zona horaria.")
