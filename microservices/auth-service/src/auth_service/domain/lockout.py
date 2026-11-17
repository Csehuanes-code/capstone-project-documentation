"""Regla de bloqueo tras intentos fallidos, con reloj y duración configurables."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Protocol

from auth_service.domain.errors import AccountLocked


class Clock(Protocol):
    def now(self) -> datetime: ...


@dataclass(slots=True)
class FailedLoginTracker:
    """Cuenta fallos dentro de una ventana y bloquea temporalmente.

    El diseño fija 5 fallos en 60 segundos, pero no la duración del bloqueo.
    Por eso esta última es obligatoria y debe configurarla el equipo.
    """

    clock: Clock
    block_duration: timedelta
    threshold: int = 5
    window: timedelta = timedelta(seconds=60)
    _failures: list[datetime] = field(default_factory=list, init=False)
    _blocked_until: datetime | None = field(default=None, init=False)

    def __post_init__(self) -> None:
        if self.threshold < 1 or self.window <= timedelta(0):
            raise ValueError("El umbral y la ventana deben ser positivos.")
        if self.block_duration <= timedelta(0):
            raise ValueError("La duración del bloqueo debe ser positiva.")

    @property
    def blocked_until(self) -> datetime | None:
        if self._blocked_until is not None and self.clock.now() >= self._blocked_until:
            self._blocked_until = None
            self._failures.clear()
        return self._blocked_until

    def ensure_unlocked(self) -> None:
        if self.blocked_until is not None:
            raise AccountLocked("La cuenta está bloqueada temporalmente.")

    def record_failure(self) -> bool:
        """Registra un fallo; retorna True si con este fallo se activa el bloqueo."""
        self.ensure_unlocked()
        now = self.clock.now()
        cutoff = now - self.window
        self._failures = [failed_at for failed_at in self._failures if failed_at > cutoff]
        self._failures.append(now)
        if len(self._failures) >= self.threshold:
            self._blocked_until = now + self.block_duration
            return True
        return False

    def record_success(self) -> None:
        self.ensure_unlocked()
        self._failures.clear()
