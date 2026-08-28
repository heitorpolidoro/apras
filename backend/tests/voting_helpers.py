"""Shared builders for the APRAS-33 voting test modules."""

import uuid
from datetime import date, datetime, timedelta

from app.core.security import get_password_hash
from app.models.enums import (
    AssemblyStatus,
    AssemblyType,
    LotAssociationType,
    UserRole,
    VoteKind,
    VoteStatus,
    VoteType,
)
from app.models.lot import Lot, UserLotLink
from app.models.user import User
from app.models.voting import Assembly, LotVoterEligibility, Vote, VoteOption
from sqlmodel import Session, select

_CPF_POOL = [
    "52998224725",
    "11144477735",
    "39053344705",
    "12345678909",
    "98765432100",
    "15350946056",
    "84515462061",
    "26654108019",
    "70125220096",
    "45317828791",
    "31711446009",
    "63884459038",
]


def _next_cpf(session: Session) -> str:
    """Return an unused CPF from the pool (falls back to a random digit run)."""
    used = {u.cpf for u in session.exec(select(User)).all()}
    for cpf in _CPF_POOL:
        if cpf not in used:
            return cpf
    return str(uuid.uuid4().int)[:11]


def make_user(
    session: Session,
    role: UserRole = UserRole.RESIDENT,
    email: str | None = None,
    full_name: str | None = None,
) -> User:
    """Create and persist a user with the given role."""
    email = email or f"{uuid.uuid4().hex[:8]}@test.com"
    user = User(
        id=uuid.uuid4(),
        email=email,
        full_name=full_name or f"{role.value} {email}",
        hashed_password=get_password_hash("pass"),
        role=role,
        cpf=_next_cpf(session),
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def make_lot(
    session: Session,
    block: str = "A",
    lot_number: str = "1",
    *,
    is_delinquent: bool = False,
    fraction_ideal: float | None = None,
) -> Lot:
    """Create and persist a lot."""
    lot = Lot(
        block=block,
        lot_number=lot_number,
        is_delinquent=is_delinquent,
        fraction_ideal=fraction_ideal,
    )
    session.add(lot)
    session.commit()
    session.refresh(lot)
    return lot


def link_user_to_lot(
    session: Session,
    user: User,
    lot: Lot,
    association_type: LotAssociationType = LotAssociationType.PROPRIETARIO,
    end_date: datetime | None = None,
) -> UserLotLink:
    """Bind a user to a lot with the given association type."""
    link = UserLotLink(
        user_id=user.id,
        lot_id=lot.id,
        association_type=association_type,
        end_date=end_date,
    )
    session.add(link)
    session.commit()
    session.refresh(link)
    return link


def add_extra_eligibility(
    session: Session, user: User, lot: Lot, added_by: User | None = None
) -> LotVoterEligibility:
    """Register a manual extra assembly voter for a lot."""
    eligibility = LotVoterEligibility(
        lot_id=lot.id,
        user_id=user.id,
        added_by_id=added_by.id if added_by else None,
    )
    session.add(eligibility)
    session.commit()
    session.refresh(eligibility)
    return eligibility


def make_assembly(
    session: Session,
    created_by: User,
    *,
    status: AssemblyStatus = AssemblyStatus.OPEN,
    title: str = "AGO 2026",
    assembly_type: AssemblyType = AssemblyType.AGO,
) -> Assembly:
    """Create and persist an assembly (OPEN by default, so votes accept ballots)."""
    assembly = Assembly(
        title=title,
        type=assembly_type,
        held_on=date(2026, 3, 1),
        agenda="1. Orçamento\n2. Obras",
        status=status,
        created_by_id=created_by.id,
    )
    session.add(assembly)
    session.commit()
    session.refresh(assembly)
    return assembly


def make_vote(
    session: Session,
    created_by: User,
    *,
    kind: VoteKind = VoteKind.ASSEMBLEIA,
    assembly: Assembly | None = None,
    title: str = "Aprovação do orçamento",
    vote_type: VoteType = VoteType.SINGLE_CHOICE,
    is_anonymous: bool = False,
    option_labels: tuple[str, ...] = ("Sim", "Não"),
    opens_at: datetime | None = None,
    closes_at: datetime | None = None,
    status: VoteStatus = VoteStatus.OPEN,
) -> Vote:
    """Create and persist a vote with its options."""
    now = datetime.utcnow()
    vote = Vote(
        assembly_id=assembly.id if assembly else None,
        kind=kind,
        title=title,
        description="Descrição",
        vote_type=vote_type,
        status=status,
        is_anonymous=is_anonymous,
        opens_at=opens_at or (now - timedelta(hours=1)),
        closes_at=closes_at or (now + timedelta(days=1)),
        created_by_id=created_by.id,
    )
    session.add(vote)
    session.commit()
    session.refresh(vote)

    for index, label in enumerate(option_labels):
        session.add(VoteOption(vote_id=vote.id, label=label, order_index=index))
    session.commit()
    session.refresh(vote)
    return vote


def option_id(vote: Vote, label: str) -> uuid.UUID:
    """Return the id of the vote option carrying `label`."""
    for opt in vote.options:
        if opt.label == label:
            return opt.id
    raise AssertionError(f"Option {label!r} not found on vote {vote.id}")


def get_token(client, email: str, password: str = "pass") -> str:
    """Log in and return the bearer access token."""
    response = client.post(
        "/api/v1/auth/login", data={"username": email, "password": password}
    )
    return response.json()["access_token"]


def auth_headers(client, user: User) -> dict[str, str]:
    """Return Authorization headers for the given user."""
    return {"Authorization": f"Bearer {get_token(client, user.email)}"}
