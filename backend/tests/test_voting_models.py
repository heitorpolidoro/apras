"""Model/enum level tests for the assembly voting feature (APRAS-33)."""

import uuid
from datetime import date, datetime, timedelta

from app.models.enums import (
    AssemblyStatus,
    AssemblyType,
    BallotRejectionReason,
    VoteKind,
    VoteStatus,
    VoteType,
)
from app.models.lot import Lot
from app.models.user import User
from app.models.voting import (
    Assembly,
    Ballot,
    BallotRejection,
    LotVoterEligibility,
    Vote,
    VoteOption,
)
from app.core.security import get_password_hash
from sqlmodel import Session, select


def test_enums_have_expected_members():
    assert AssemblyType.AGO == "AGO"
    assert AssemblyType.AGE == "AGE"
    assert {s.value for s in AssemblyStatus} == {"DRAFT", "OPEN", "CLOSED"}
    assert {k.value for k in VoteKind} == {"ASSEMBLEIA", "ENQUETE"}
    assert {t.value for t in VoteType} == {"SINGLE_CHOICE", "MULTIPLE_CHOICE"}
    assert {s.value for s in VoteStatus} == {"OPEN", "CLOSED"}
    assert {r.value for r in BallotRejectionReason} == {
        "DELINQUENT_LOT",
        "NOT_OWNER",
        "NO_ACTIVE_LOT_LINK",
        "VOTE_NOT_OPEN",
        "ROLE_FORBIDDEN",
        "LOT_ALREADY_VOTED",
    }


def test_vote_type_has_no_free_text():
    """FREE_TEXT was deliberately cut from the spec; no hook must exist."""
    assert not hasattr(VoteType, "FREE_TEXT")
    assert not hasattr(Ballot, "free_text_response")


def test_lot_delinquency_fields_default_to_false(session: Session):
    lot = Lot(block="A", lot_number="1")
    session.add(lot)
    session.commit()
    session.refresh(lot)

    assert lot.is_delinquent is False
    assert lot.delinquency_updated_at is None
    assert lot.delinquency_updated_by_id is None


def test_voting_models_persist(session: Session):
    user = User(
        id=uuid.uuid4(),
        email="board@test.com",
        full_name="Board",
        hashed_password=get_password_hash("pass"),
        cpf="52998224725",
    )
    lot = Lot(block="A", lot_number="1")
    session.add(user)
    session.add(lot)
    session.commit()

    assembly = Assembly(
        title="AGO 2026",
        type=AssemblyType.AGO,
        held_on=date(2026, 3, 1),
        created_by_id=user.id,
    )
    session.add(assembly)
    session.commit()
    assert assembly.status == AssemblyStatus.DRAFT

    vote = Vote(
        assembly_id=assembly.id,
        kind=VoteKind.ASSEMBLEIA,
        title="Aprovação do orçamento",
        vote_type=VoteType.SINGLE_CHOICE,
        closes_at=datetime.utcnow() + timedelta(days=1),
        created_by_id=user.id,
    )
    session.add(vote)
    session.commit()

    option = VoteOption(vote_id=vote.id, label="Sim", order_index=0)
    session.add(option)
    session.commit()

    ballot = Ballot(
        vote_id=vote.id,
        voter_key=f"lot:{lot.id}",
        lot_id=lot.id,
        voter_user_id=user.id,
        fraction_ideal_at_cast=0.25,
        selected_option_ids_json=f'["{option.id}"]',
    )
    session.add(ballot)

    eligibility = LotVoterEligibility(
        lot_id=lot.id, user_id=user.id, added_by_id=user.id
    )
    session.add(eligibility)

    rejection = BallotRejection(
        vote_id=vote.id,
        user_id=user.id,
        lot_id=lot.id,
        reason=BallotRejectionReason.DELINQUENT_LOT,
    )
    session.add(rejection)
    session.commit()

    assert vote.status == VoteStatus.OPEN
    assert vote.is_anonymous is False
    assert ballot.is_retraction is False
    assert session.exec(select(Assembly)).one().votes[0].id == vote.id
    assert session.exec(select(BallotRejection)).one().reason == (
        BallotRejectionReason.DELINQUENT_LOT
    )
    assert session.exec(select(LotVoterEligibility)).one().lot_id == lot.id
