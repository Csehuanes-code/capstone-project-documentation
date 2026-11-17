"""Objeto de valor Email: valida y normaliza la dirección."""

import re
from dataclasses import dataclass

from auth_service.domain.errors import InvalidEmail

_EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


@dataclass(frozen=True, slots=True)
class Email:
    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip().lower()
        if len(normalized) > 254 or not _EMAIL_PATTERN.fullmatch(normalized):
            raise InvalidEmail("La dirección de correo no tiene un formato válido.")
        object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        return self.value
