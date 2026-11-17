"""Entidad Usuario y estados mínimos del ciclo de cuenta."""

from dataclasses import dataclass, replace
from enum import StrEnum
from uuid import UUID

from auth_service.domain.email import Email
from auth_service.domain.errors import InvalidUser
from auth_service.domain.role import Role


class UserStatus(StrEnum):
    PENDIENTE = "pendiente"
    ACTIVO = "activo"
    BLOQUEADO = "bloqueado"


@dataclass(frozen=True, slots=True)
class User:
    id: UUID
    email: Email
    role: Role
    password_hash: str
    status: UserStatus = UserStatus.PENDIENTE

    def __post_init__(self) -> None:
        if not self.password_hash.strip():
            raise InvalidUser("El usuario debe tener un hash de contraseña.")
        if self.role is Role.ADMINISTRADOR and self.status is UserStatus.PENDIENTE:
            raise InvalidUser("Una cuenta administradora no puede registrarse como pendiente.")

    def activate(self) -> "User":
        if self.status is not UserStatus.PENDIENTE:
            raise InvalidUser("Solo se puede activar una cuenta pendiente.")
        return replace(self, status=UserStatus.ACTIVO)
