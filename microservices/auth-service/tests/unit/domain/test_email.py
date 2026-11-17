import pytest

from auth_service.domain.email import Email
from auth_service.domain.errors import InvalidEmail


def test_email_is_trimmed_and_lowercased() -> None:
    assert Email("  David.Hasbum@Example.COM ").value == "david.hasbum@example.com"


@pytest.mark.parametrize("value", ["", "no-es-correo", "a@b", "a b@example.com"])
def test_email_rejects_invalid_values(value: str) -> None:
    with pytest.raises(InvalidEmail):
        Email(value)
