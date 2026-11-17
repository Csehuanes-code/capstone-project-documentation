"""Identidad verificada que las rutas reciben desde el adaptador JWT."""

from dataclasses import dataclass
from uuid import UUID

from auth_service.domain.role import Role


@dataclass(frozen=True, slots=True)
class AuthenticatedIdentity:
    user_id: UUID
    role: Role
