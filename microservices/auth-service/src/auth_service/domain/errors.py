"""Errores propios de las reglas del dominio Auth."""


class DomainError(ValueError):
    """Base para errores causados por una operación inválida del dominio."""


class InvalidEmail(DomainError):
    pass


class InvalidUser(DomainError):
    pass


class InvalidVerificationTransition(DomainError):
    pass


class AccountLocked(DomainError):
    pass
