from uuid import uuid4

import pytest

from auth_service.domain.email import Email
from auth_service.domain.errors import InvalidUser
from auth_service.domain.role import Role
from auth_service.domain.user import User, UserStatus


def test_user_has_expected_identity_and_status() -> None:
    user = User(uuid4(), Email("user@example.com"), Role.TURISTA, "argon2-hash")
    assert user.status is UserStatus.PENDIENTE


def test_user_rejects_empty_password_hash() -> None:
    with pytest.raises(InvalidUser):
        User(uuid4(), Email("user@example.com"), Role.TURISTA, " ")


def test_admin_cannot_be_registered_as_pending() -> None:
    with pytest.raises(InvalidUser):
        User(uuid4(), Email("admin@example.com"), Role.ADMINISTRADOR, "argon2-hash")
