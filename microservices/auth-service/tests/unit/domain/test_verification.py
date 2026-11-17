from uuid import uuid4

import pytest

from auth_service.domain.errors import InvalidVerificationTransition
from auth_service.domain.verification import VerificationRequest, VerificationStatus


def draft() -> VerificationRequest:
    return VerificationRequest(uuid4(), uuid4(), "Guías Sierra Viva", "900123456", "12345")


def test_draft_can_be_submitted_and_approved() -> None:
    submitted = draft().submit()
    approved = submitted.approve("RNT verificado por el administrador")
    assert submitted.status is VerificationStatus.ENVIADA
    assert approved.status is VerificationStatus.APROBADA
    assert approved.justification == "RNT verificado por el administrador"


def test_information_request_can_be_resubmitted() -> None:
    needs_info = draft().submit().request_information("Adjunte el certificado vigente")
    resubmitted = needs_info.submit()
    assert resubmitted.status is VerificationStatus.ENVIADA
    assert resubmitted.justification is None


@pytest.mark.parametrize("decision", ["approve", "reject"])
def test_cannot_decide_a_draft(decision: str) -> None:
    with pytest.raises(InvalidVerificationTransition):
        getattr(draft(), decision)("Motivo")


def test_decision_requires_justification() -> None:
    with pytest.raises(ValueError):
        draft().submit().approve(" ")


def test_final_decision_cannot_be_changed() -> None:
    approved = draft().submit().approve("RNT verificado")
    with pytest.raises(InvalidVerificationTransition):
        approved.reject("Cambio de decisión")
