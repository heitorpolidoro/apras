"""Assembly voting and poll business logic (APRAS-33).

Module-level functions following the `document_service.py` precedent.

Two invariants drive everything here:

* `Ballot` is append-only. Changing a vote inserts a new row; retracting a
  vote inserts a row with `is_retraction=True`. The "active ballot" of a
  `voter_key` is the last row by `cast_at` (ties broken by `id`), and it
  only counts when that last row is not a retraction.
* Every refusal in `_assert_can_cast` writes a `BallotRejection` row and
  commits it *before* raising, mirroring `visitor_service.py`: the state
  that caused the refusal (delinquency, in particular) may not exist any
  more when someone later contests "I was blocked from voting".
"""

import html
import json
from datetime import datetime, timedelta
from uuid import UUID

from sqlmodel import Session, select

from app.core.exceptions import (
    AnonymousAssemblyError,
    AssemblyNotClosedError,
    AssemblyNotFoundError,
    AssemblyStatusTransitionError,
    DelinquentLotError,
    ForbiddenError,
    LotAlreadyVotedError,
    LotNotFoundError,
    NoActiveBallotError,
    NoActiveLotLinkError,
    NotLotOwnerError,
    TallyNotAvailableError,
    VoteAlreadyClosedError,
    VoteFrozenError,
    VoteNotFoundError,
    VoteNotOpenError,
)
from app.models.document import DocumentFolder
from app.models.enums import (
    AssemblyStatus,
    BallotRejectionReason,
    LotAssociationType,
    UserRole,
    VoteKind,
    VoteStatus,
)
from app.models.lot import Lot, UserLotLink
from app.models.user import User
from app.models.voting import (
    Assembly,
    Ballot,
    BallotRejection,
    LotVoterEligibility,
    Vote,
    VoteOption,
)
from app.schemas.document import AssociationDocumentCreate, DocumentFolderCreate
from app.schemas.voting import (
    AssemblyCreate,
    AssemblyUpdate,
    MyBallotRead,
    TallyAttributionRead,
    TallyRead,
    TallyResultRead,
    VoteCreate,
    VoteUpdate,
)
from app.services import document_service
from app.services.storage_service import BaseStorageProvider, LocalStorageProvider

BOARD_ROLES = (UserRole.ADMINISTRATOR, UserRole.DIRECTOR)
TALLY_STAFF_ROLES = (UserRole.ADMINISTRATOR, UserRole.DIRECTOR, UserRole.MANAGER)
NON_VOTING_ROLES = (UserRole.GUEST, UserRole.PORTEIRO)
MINUTES_FOLDER_NAME = "Atas de Assembleia"


# ---------------------------------------------------------------------------
# RBAC guards
# ---------------------------------------------------------------------------


def _assert_board(user: User) -> None:
    """Only ADMINISTRATOR/DIRECTOR manage assemblies and assembly votes."""
    if user.role not in BOARD_ROLES:
        raise ForbiddenError(
            "Apenas Administrador e Diretor podem gerenciar assembleias"
        )


def _assert_can_create_vote(user: User, kind: VoteKind) -> None:
    """MANAGER may create polls; assembly votes stay with the board."""
    if kind == VoteKind.ENQUETE:
        if user.role not in TALLY_STAFF_ROLES:
            raise ForbiddenError("Você não pode criar enquetes")
        return
    _assert_board(user)


def _assert_can_manage_eligibility(user: User) -> None:
    """ADMINISTRATOR/DIRECTOR/MANAGER curate the extra voter list of a lot."""
    if user.role not in TALLY_STAFF_ROLES:
        raise ForbiddenError("Você não pode gerenciar elegíveis de um lote")


def _assert_can_view_tally(session: Session, user: User, vote: Vote) -> None:
    """Whoever could vote, plus ADMINISTRATOR/DIRECTOR/MANAGER, may read it."""
    if user.role in TALLY_STAFF_ROLES:
        return
    if user.role in NON_VOTING_ROLES:
        raise TallyNotAvailableError
    if vote.kind == VoteKind.ASSEMBLEIA:
        if not get_user_eligible_lot_ids(session, user):
            raise TallyNotAvailableError
    elif not _active_lot_ids(session, user):
        raise TallyNotAvailableError


# ---------------------------------------------------------------------------
# Eligibility helpers
# ---------------------------------------------------------------------------


def _is_link_active(link: UserLotLink, now: datetime) -> bool:
    """A lot link counts while its start/end window contains `now`."""
    if link.start_date is not None and link.start_date > now:
        return False
    return link.end_date is None or link.end_date > now


def _active_lot_ids(session: Session, user: User) -> set[UUID]:
    """Lot ids the user is currently linked to, whatever the association."""
    now = datetime.utcnow()
    links = session.exec(
        select(UserLotLink).where(UserLotLink.user_id == user.id)
    ).all()
    return {link.lot_id for link in links if _is_link_active(link, now)}


def get_lot_eligible_user_ids(session: Session, lot: Lot) -> set[UUID]:
    """Users entitled to cast the assembly ballot of `lot`.

    The union of active `PROPRIETARIO` links (which already covers
    co-ownership: nothing limits a lot to a single owner) with the manually
    curated `LotVoterEligibility` rows.
    """
    now = datetime.utcnow()
    links = session.exec(
        select(UserLotLink).where(UserLotLink.lot_id == lot.id)
    ).all()
    eligible = {
        link.user_id
        for link in links
        if link.association_type == LotAssociationType.PROPRIETARIO
        and _is_link_active(link, now)
    }
    extras = session.exec(
        select(LotVoterEligibility).where(LotVoterEligibility.lot_id == lot.id)
    ).all()
    eligible.update(extra.user_id for extra in extras)
    return eligible


def get_user_eligible_lot_ids(session: Session, user: User) -> set[UUID]:
    """Non-deleted lots the user may cast an assembly ballot for."""
    now = datetime.utcnow()
    links = session.exec(
        select(UserLotLink).where(UserLotLink.user_id == user.id)
    ).all()
    lot_ids = {
        link.lot_id
        for link in links
        if link.association_type == LotAssociationType.PROPRIETARIO
        and _is_link_active(link, now)
    }
    extras = session.exec(
        select(LotVoterEligibility).where(LotVoterEligibility.user_id == user.id)
    ).all()
    lot_ids.update(extra.lot_id for extra in extras)

    active: set[UUID] = set()
    for lot_id in lot_ids:
        lot = session.get(Lot, lot_id)
        if lot and not lot.is_deleted:
            active.add(lot_id)
    return active


def _co_resident_user_ids(session: Session, user: User) -> set[UUID]:
    """Users sharing at least one lot with `user` (any association), plus self."""
    lot_ids = _active_lot_ids(session, user)
    if not lot_ids:
        return {user.id}
    now = datetime.utcnow()
    links = session.exec(
        select(UserLotLink).where(UserLotLink.lot_id.in_(lot_ids))
    ).all()
    peers = {link.user_id for link in links if _is_link_active(link, now)}
    peers.add(user.id)
    return peers


# ---------------------------------------------------------------------------
# Ballot reading helpers
# ---------------------------------------------------------------------------


def _ballot_sort_key(ballot: Ballot) -> tuple[datetime, str]:
    """Ordering used everywhere to find the last row of a `voter_key`."""
    return (ballot.cast_at, str(ballot.id))


def _latest_ballot_for_key(
    session: Session, vote: Vote, voter_key: str
) -> Ballot | None:
    """Last appended row for `voter_key`, retraction or not."""
    rows = session.exec(
        select(Ballot).where(
            Ballot.vote_id == vote.id, Ballot.voter_key == voter_key
        )
    ).all()
    if not rows:
        return None
    return max(rows, key=_ballot_sort_key)


def get_active_ballot_holder(
    session: Session, vote: Vote, lot_id: UUID
) -> UUID | None:
    """Who currently holds the lot's ballot, or `None` if the lot is free.

    Single source of truth for both the per-lot lock (a second eligible
    voter may not overwrite an active ballot) and the retraction check
    (only the holder may withdraw it).
    """
    latest = _latest_ballot_for_key(session, vote, f"lot:{lot_id}")
    if latest is None or latest.is_retraction:
        return None
    return latest.voter_user_id


def get_latest_ballots(session: Session, vote: Vote) -> list[Ballot]:
    """Active ballots of the vote: last row per `voter_key`, retractions out."""
    rows = session.exec(select(Ballot).where(Ballot.vote_id == vote.id)).all()
    latest: dict[str, Ballot] = {}
    for ballot in rows:
        current = latest.get(ballot.voter_key)
        if current is None or _ballot_sort_key(ballot) > _ballot_sort_key(current):
            latest[ballot.voter_key] = ballot
    return sorted(
        (b for b in latest.values() if not b.is_retraction), key=_ballot_sort_key
    )


def _selected_ids(ballot: Ballot) -> list[str]:
    """Distinct option ids of the ballot, in the order they were sent.

    De-duplicated here, at the single point every reader goes through, so a
    row that already carries a repeated id — however it got stored — still
    counts once per option in a recount: one ballot is one vote per option
    ("um voto por lote").
    """
    if not ballot.selected_option_ids_json:
        return []
    return list(
        dict.fromkeys(
            str(value) for value in json.loads(ballot.selected_option_ids_json)
        )
    )


def selected_option_ids(ballot: Ballot) -> list[UUID]:
    """The options the ballot selected, decoded from its JSON column."""
    return [UUID(value) for value in _selected_ids(ballot)]


# ---------------------------------------------------------------------------
# Casting
# ---------------------------------------------------------------------------


def _record_rejection(
    session: Session,
    vote: Vote,
    user: User,
    lot_id: UUID | None,
    reason: BallotRejectionReason,
) -> None:
    """Persist the refusal (own commit) so it survives the aborted request."""
    session.add(
        BallotRejection(
            vote_id=vote.id, user_id=user.id, lot_id=lot_id, reason=reason
        )
    )
    session.commit()


def _assert_window_open(session: Session, vote: Vote, user: User, lot_id) -> None:
    now = datetime.utcnow()
    open_window = (
        vote.status == VoteStatus.OPEN and vote.opens_at <= now < vote.closes_at
    )
    if open_window and vote.kind == VoteKind.ASSEMBLEIA:
        assembly = session.get(Assembly, vote.assembly_id) if vote.assembly_id else None
        open_window = assembly is not None and assembly.status == AssemblyStatus.OPEN
    if not open_window:
        _record_rejection(
            session, vote, user, lot_id, BallotRejectionReason.VOTE_NOT_OPEN
        )
        raise VoteNotOpenError


def _assert_can_cast(
    session: Session,
    user: User,
    vote: Vote,
    lot_id: UUID | None,
    *,
    is_retraction: bool = False,
) -> None:
    """Evaluate the eligibility chain of the spec, in order.

    Retraction chains (3b/4b) are deliberately shorter: they do NOT
    re-evaluate eligibility or delinquency, otherwise a holder who lost
    eligibility after voting could neither withdraw their own ballot nor
    let anyone else vote for that lot — the lot would be locked for the
    rest of the window.
    """
    # 1 — window
    _assert_window_open(session, vote, user, lot_id)

    # 2 — role
    if user.role in NON_VOTING_ROLES:
        _record_rejection(
            session, vote, user, lot_id, BallotRejectionReason.ROLE_FORBIDDEN
        )
        raise ForbiddenError("Este perfil não vota")

    if vote.kind == VoteKind.ASSEMBLEIA:
        if is_retraction:
            _assert_can_retract_assembly(session, user, vote, lot_id)
        else:
            _assert_can_cast_assembly(session, user, vote, lot_id)
        return

    if is_retraction:
        _assert_can_retract_poll(session, user, vote)
        return
    _assert_can_cast_poll(session, user, vote)


def _assert_can_cast_assembly(
    session: Session, user: User, vote: Vote, lot_id: UUID | None
) -> None:
    """Chain 3 — casting or changing an assembly ballot."""
    if lot_id is None:
        raise NotLotOwnerError("É obrigatório informar o lote em uma assembleia.")
    lot = session.get(Lot, lot_id)
    if lot is None:
        raise LotNotFoundError(lot_id)

    if lot.is_deleted or user.id not in get_lot_eligible_user_ids(session, lot):
        _record_rejection(
            session, vote, user, lot_id, BallotRejectionReason.NOT_OWNER
        )
        raise NotLotOwnerError

    if lot.is_delinquent:
        _record_rejection(
            session, vote, user, lot_id, BallotRejectionReason.DELINQUENT_LOT
        )
        raise DelinquentLotError

    holder = get_active_ballot_holder(session, vote, lot_id)
    if holder is not None and holder != user.id:
        _record_rejection(
            session, vote, user, lot_id, BallotRejectionReason.LOT_ALREADY_VOTED
        )
        raise LotAlreadyVotedError


def _assert_can_retract_assembly(
    session: Session, user: User, vote: Vote, lot_id: UUID | None
) -> None:
    """Chain 3b — withdrawing the assembly ballot the caller holds."""
    if lot_id is None:
        raise NoActiveBallotError("Informe o lote cuja cédula será retirada.")
    holder = get_active_ballot_holder(session, vote, lot_id)
    if holder is None:
        raise NoActiveBallotError
    if holder != user.id:
        _record_rejection(
            session, vote, user, lot_id, BallotRejectionReason.LOT_ALREADY_VOTED
        )
        raise LotAlreadyVotedError


def _assert_can_cast_poll(session: Session, user: User, vote: Vote) -> None:
    """Chain 4 — casting or changing a poll ballot."""
    if not _active_lot_ids(session, user):
        _record_rejection(
            session, vote, user, None, BallotRejectionReason.NO_ACTIVE_LOT_LINK
        )
        raise NoActiveLotLinkError


def _assert_can_retract_poll(session: Session, user: User, vote: Vote) -> None:
    """Chain 4b — withdrawing one's own poll ballot; no link re-check."""
    latest = _latest_ballot_for_key(session, vote, f"user:{user.id}")
    if latest is None or latest.is_retraction:
        raise NoActiveBallotError


def _next_cast_at(session: Session, vote: Vote, voter_key: str) -> datetime:
    """Timestamp strictly greater than the voter's previous row.

    `datetime.utcnow()` can repeat inside one request; forcing a strictly
    increasing `cast_at` per `voter_key` keeps "the last row" unambiguous
    without relying on the random-UUID tie-break.
    """
    now = datetime.utcnow()
    latest = _latest_ballot_for_key(session, vote, voter_key)
    if latest is not None and latest.cast_at >= now:
        return latest.cast_at + timedelta(microseconds=1)
    return now


def cast_ballot(
    session: Session,
    user: User,
    vote: Vote,
    *,
    lot_id: UUID | None = None,
    selected_option_ids: list[UUID] | None = None,
    is_retraction: bool = False,
) -> Ballot:
    """Append a ballot row — a vote, a vote change, or a retraction.

    Never updates or deletes: the audit trail is the row sequence.
    Option membership/arity is validated at the API boundary, where the
    vote type is known alongside the request body.
    """
    _assert_can_cast(session, user, vote, lot_id, is_retraction=is_retraction)

    if vote.kind == VoteKind.ASSEMBLEIA:
        lot = session.get(Lot, lot_id)
        voter_key = f"lot:{lot_id}"
        fraction = lot.fraction_ideal if lot else None
        ballot_lot_id = lot_id
    else:
        voter_key = f"user:{user.id}"
        fraction = None
        ballot_lot_id = None

    ballot = Ballot(
        vote_id=vote.id,
        voter_key=voter_key,
        lot_id=ballot_lot_id,
        voter_user_id=user.id,
        fraction_ideal_at_cast=fraction,
        is_retraction=is_retraction,
        selected_option_ids_json=(
            None
            if is_retraction
            else json.dumps([str(oid) for oid in (selected_option_ids or [])])
        ),
        cast_at=_next_cast_at(session, vote, voter_key),
    )
    session.add(ballot)
    session.commit()
    session.refresh(ballot)
    return ballot


# ---------------------------------------------------------------------------
# Tally
# ---------------------------------------------------------------------------


def _lot_label(lot: Lot | None) -> str | None:
    return f"{lot.block}/{lot.lot_number}" if lot else None


def count_active_lots(session: Session) -> int:
    """Assembly denominator: every lot that has not been soft-deleted."""
    return len(session.exec(select(Lot).where(Lot.is_deleted == False)).all())  # noqa: E712


def compute_tally(session: Session, vote: Vote) -> dict:
    """Compute the tally from the ballot rows (never from the snapshot).

    Anonymous polls are aggregated with no attribution list at all — the
    masking happens here, before anything is stored or serialised, so the
    identity is not merely hidden by the frontend.
    """
    latest = get_latest_ballots(session, vote)
    options = sorted(vote.options, key=lambda opt: (opt.order_index, opt.label))
    counts = {str(opt.id): 0 for opt in options}
    for ballot in latest:
        for option_id in _selected_ids(ballot):
            if option_id in counts:
                counts[option_id] += 1

    labels = {str(opt.id): opt.label for opt in options}
    data: dict = {
        "voters_count": len(latest),
        "total_lots": None,
        "results": [
            {
                "option_id": str(opt.id),
                "label": opt.label,
                "count": counts[str(opt.id)],
            }
            for opt in options
        ],
        "attributions": None,
    }

    if vote.kind == VoteKind.ASSEMBLEIA:
        data["total_lots"] = count_active_lots(session)

    if vote.kind == VoteKind.ENQUETE and vote.is_anonymous:
        return data

    attributions = []
    for ballot in latest:
        selected = [labels[oid] for oid in _selected_ids(ballot) if oid in labels]
        entry: dict = {
            "lot_id": None,
            "lot_label": None,
            "voter_user_id": None,
            "voter_name": None,
            "selected_labels": selected,
            "cast_at": ballot.cast_at.isoformat(),
        }
        if vote.kind == VoteKind.ASSEMBLEIA:
            # The vote belongs to the unit, so it is attributed by Bloco/Lote
            # and never by the name of the person who cast it.
            lot = session.get(Lot, ballot.lot_id) if ballot.lot_id else None
            entry["lot_id"] = str(ballot.lot_id) if ballot.lot_id else None
            entry["lot_label"] = _lot_label(lot)
        else:
            voter = (
                session.get(User, ballot.voter_user_id)
                if ballot.voter_user_id
                else None
            )
            entry["voter_user_id"] = (
                str(ballot.voter_user_id) if ballot.voter_user_id else None
            )
            entry["voter_name"] = voter.full_name if voter else None
        attributions.append(entry)
    data["attributions"] = attributions
    return data


def materialize_snapshot(session: Session, vote: Vote) -> Vote:
    """Freeze the tally once and mark the vote closed. Idempotent."""
    if vote.tally_snapshot_json is None:
        vote.tally_snapshot_json = json.dumps(compute_tally(session, vote))
    if vote.status != VoteStatus.CLOSED:
        vote.status = VoteStatus.CLOSED
        vote.closed_at = vote.closed_at or datetime.utcnow()
    vote.updated_at = datetime.utcnow()
    session.add(vote)
    session.commit()
    session.refresh(vote)
    return vote


def materialize_if_due(session: Session, vote: Vote) -> Vote:
    """Lazy close: the first read past `closes_at` freezes the tally.

    Deliberately not wired into the list endpoint, so one listing request
    cannot write N snapshots.
    """
    if vote.status == VoteStatus.OPEN and datetime.utcnow() >= vote.closes_at:
        return materialize_snapshot(session, vote)
    return vote


def _tally_from_data(vote: Vote, data: dict, *, closed: bool) -> TallyRead:
    tally = TallyRead(
        vote_id=vote.id,
        kind=vote.kind,
        status=vote.status,
        is_anonymous=vote.is_anonymous,
        voters_count=data["voters_count"],
        total_lots=data.get("total_lots"),
    )
    if not closed:
        return tally
    tally.results = [TallyResultRead(**row) for row in data["results"]]
    if data.get("attributions") is not None:
        tally.attributions = [
            TallyAttributionRead(**row) for row in data["attributions"]
        ]
    return tally


def get_tally(session: Session, user: User, vote: Vote) -> TallyRead:
    """Participation count while open; full tally only once closed.

    The gate is server-side and has no carve-out for the board: an
    ADMINISTRATOR calling this endpoint mid-window gets the same reduced
    payload as anybody else.
    """
    _assert_can_view_tally(session, user, vote)
    materialize_if_due(session, vote)

    if vote.status == VoteStatus.CLOSED:
        if vote.tally_snapshot_json is None:
            materialize_snapshot(session, vote)
        return _tally_from_data(
            vote, json.loads(vote.tally_snapshot_json), closed=True
        )
    return _tally_from_data(vote, compute_tally(session, vote), closed=False)


# ---------------------------------------------------------------------------
# My ballot (visibility rule 3)
# ---------------------------------------------------------------------------


def _to_my_ballot(
    session: Session, vote: Vote, ballot: Ballot, user: User
) -> MyBallotRead:
    can_edit = ballot.voter_user_id == user.id
    anonymous = vote.kind == VoteKind.ENQUETE and vote.is_anonymous
    lot = session.get(Lot, ballot.lot_id) if ballot.lot_id else None
    voter = (
        session.get(User, ballot.voter_user_id) if ballot.voter_user_id else None
    )
    return MyBallotRead(
        id=ballot.id,
        vote_id=ballot.vote_id,
        lot_id=None if anonymous else ballot.lot_id,
        lot_label=None if anonymous else _lot_label(lot),
        voter_user_id=None if anonymous else ballot.voter_user_id,
        voter_name=None if anonymous else (voter.full_name if voter else None),
        is_retraction=ballot.is_retraction,
        selected_option_ids=[UUID(oid) for oid in _selected_ids(ballot)],
        cast_at=ballot.cast_at,
        can_edit=can_edit,
    )


def get_eligible_lots(session: Session, user: User, vote: Vote) -> list[Lot]:
    """Lots the caller may cast this vote's ballot for, ordered by unit.

    Empty for a poll, where the ballot belongs to the person and carries
    no lot at all.
    """
    if vote.kind != VoteKind.ASSEMBLEIA:
        return []
    lots = [
        session.get(Lot, lot_id)
        for lot_id in get_user_eligible_lot_ids(session, user)
    ]
    return sorted(
        (lot for lot in lots if lot is not None),
        key=lambda lot: (lot.block, lot.lot_number),
    )


def get_my_ballots(session: Session, user: User, vote: Vote) -> list[MyBallotRead]:
    """The ballots the caller is entitled to see.

    ASSEMBLEIA: the active ballot of every lot the caller is eligible for,
    even when someone else cast it (`can_edit=False`).
    ENQUETE, non-anonymous: the caller's ballot plus those of everyone who
    shares a lot with them.
    ENQUETE, anonymous: only the caller's own, with identity stripped.
    """
    ballots: list[Ballot] = []

    if vote.kind == VoteKind.ASSEMBLEIA:
        for lot_id in get_user_eligible_lot_ids(session, user):
            latest = _latest_ballot_for_key(session, vote, f"lot:{lot_id}")
            if latest is not None and not latest.is_retraction:
                ballots.append(latest)
    elif vote.is_anonymous:
        latest = _latest_ballot_for_key(session, vote, f"user:{user.id}")
        if latest is not None and not latest.is_retraction:
            ballots.append(latest)
    else:
        for user_id in _co_resident_user_ids(session, user):
            latest = _latest_ballot_for_key(session, vote, f"user:{user_id}")
            if latest is not None and not latest.is_retraction:
                ballots.append(latest)

    ballots.sort(key=_ballot_sort_key)
    return [_to_my_ballot(session, vote, ballot, user) for ballot in ballots]


# ---------------------------------------------------------------------------
# Assemblies
# ---------------------------------------------------------------------------


def get_assembly(session: Session, assembly_id: UUID) -> Assembly:
    assembly = session.get(Assembly, assembly_id)
    if assembly is None:
        raise AssemblyNotFoundError(assembly_id)
    return assembly


def create_assembly(
    session: Session, user: User, assembly_in: AssemblyCreate
) -> Assembly:
    _assert_board(user)
    assembly = Assembly(
        title=assembly_in.title,
        type=assembly_in.type,
        held_on=assembly_in.held_on,
        agenda=assembly_in.agenda,
        status=AssemblyStatus.DRAFT,
        created_by_id=user.id,
    )
    session.add(assembly)
    session.commit()
    session.refresh(assembly)
    return assembly


def list_assemblies(session: Session) -> list[Assembly]:
    return list(
        session.exec(select(Assembly).order_by(Assembly.held_on.desc())).all()
    )


def update_assembly(
    session: Session, user: User, assembly: Assembly, assembly_in: AssemblyUpdate
) -> Assembly:
    _assert_board(user)
    if assembly.status == AssemblyStatus.CLOSED:
        raise VoteAlreadyClosedError("Assembleia fechada não pode ser editada.")
    if assembly_in.status == AssemblyStatus.CLOSED:
        # Closing has to cascade into the open votes and freeze every
        # snapshot; letting an edit set the flag would hand the board the
        # full tally of a still-open vote through the minutes.
        raise AssemblyStatusTransitionError

    for field, value in assembly_in.model_dump(exclude_unset=True).items():
        setattr(assembly, field, value)
    assembly.updated_at = datetime.utcnow()
    session.add(assembly)
    session.commit()
    session.refresh(assembly)
    return assembly


def close_assembly(session: Session, user: User, assembly: Assembly) -> Assembly:
    """Close the assembly, cascading into every vote still open.

    This is what makes the minutes available.
    """
    _assert_board(user)
    if assembly.status == AssemblyStatus.CLOSED:
        raise VoteAlreadyClosedError("Assembleia já está fechada.")

    for vote in assembly.votes:
        materialize_snapshot(session, vote)

    assembly.status = AssemblyStatus.CLOSED
    assembly.closed_at = datetime.utcnow()
    assembly.updated_at = assembly.closed_at
    session.add(assembly)
    session.commit()
    session.refresh(assembly)
    return assembly


# ---------------------------------------------------------------------------
# Votes
# ---------------------------------------------------------------------------


def get_vote(session: Session, vote_id: UUID) -> Vote:
    vote = session.get(Vote, vote_id)
    if vote is None:
        raise VoteNotFoundError(vote_id)
    return vote


def create_vote(session: Session, user: User, vote_in: VoteCreate) -> Vote:
    _assert_can_create_vote(user, vote_in.kind)

    if vote_in.kind == VoteKind.ASSEMBLEIA:
        if vote_in.is_anonymous:
            raise AnonymousAssemblyError
        get_assembly(session, vote_in.assembly_id)

    vote = Vote(
        assembly_id=vote_in.assembly_id,
        kind=vote_in.kind,
        title=vote_in.title,
        description=vote_in.description,
        vote_type=vote_in.vote_type,
        is_anonymous=vote_in.is_anonymous,
        opens_at=vote_in.opens_at or datetime.utcnow(),
        closes_at=vote_in.closes_at,
        created_by_id=user.id,
    )
    session.add(vote)
    session.commit()
    session.refresh(vote)

    for index, option_in in enumerate(vote_in.options):
        session.add(
            VoteOption(
                vote_id=vote.id,
                label=option_in.label,
                order_index=option_in.order_index or index,
            )
        )
    session.commit()
    session.refresh(vote)
    return vote


def list_votes(
    session: Session,
    kind: VoteKind | None = None,
    status: VoteStatus | None = None,
    assembly_id: UUID | None = None,
) -> list[Vote]:
    """List votes. Deliberately does NOT lazily materialise snapshots."""
    query = select(Vote)
    if kind is not None:
        query = query.where(Vote.kind == kind)
    if status is not None:
        query = query.where(Vote.status == status)
    if assembly_id is not None:
        query = query.where(Vote.assembly_id == assembly_id)
    return list(session.exec(query.order_by(Vote.created_at.desc())).all())


def has_ballots(session: Session, vote: Vote) -> bool:
    """True once the vote received at least one ballot row (it is then frozen)."""
    first = session.exec(select(Ballot).where(Ballot.vote_id == vote.id)).first()
    return first is not None


def update_vote(
    session: Session, user: User, vote: Vote, vote_in: VoteUpdate
) -> Vote:
    """Edit a vote — only while it has not received a single ballot."""
    _assert_can_create_vote(user, vote.kind)
    if vote.status == VoteStatus.CLOSED:
        raise VoteAlreadyClosedError
    if has_ballots(session, vote):
        raise VoteFrozenError

    payload = vote_in.model_dump(exclude_unset=True)
    options = payload.pop("options", None)
    if payload.get("is_anonymous") and vote.kind == VoteKind.ASSEMBLEIA:
        raise AnonymousAssemblyError

    for field, value in payload.items():
        setattr(vote, field, value)
    vote.updated_at = datetime.utcnow()
    session.add(vote)

    if options is not None:
        for option in list(vote.options):
            session.delete(option)
        session.commit()
        for index, option_in in enumerate(options):
            session.add(
                VoteOption(
                    vote_id=vote.id,
                    label=option_in["label"],
                    order_index=option_in.get("order_index") or index,
                )
            )
    session.commit()
    session.refresh(vote)
    return vote


def close_vote(session: Session, user: User, vote: Vote) -> Vote:
    _assert_can_create_vote(user, vote.kind)
    if vote.status == VoteStatus.CLOSED:
        raise VoteAlreadyClosedError
    return materialize_snapshot(session, vote)


# ---------------------------------------------------------------------------
# Lot voter eligibility
# ---------------------------------------------------------------------------


def set_lot_voter_eligibility(
    session: Session, user: User, lot_id: UUID, target_user_id: UUID
) -> LotVoterEligibility:
    """Register an extra assembly voter for a lot (idempotent)."""
    _assert_can_manage_eligibility(user)
    lot = session.get(Lot, lot_id)
    if lot is None or lot.is_deleted:
        raise LotNotFoundError(lot_id)
    if session.get(User, target_user_id) is None:
        raise ForbiddenError("Usuário não encontrado")

    existing = session.exec(
        select(LotVoterEligibility).where(
            LotVoterEligibility.lot_id == lot_id,
            LotVoterEligibility.user_id == target_user_id,
        )
    ).first()
    if existing:
        return existing

    eligibility = LotVoterEligibility(
        lot_id=lot_id, user_id=target_user_id, added_by_id=user.id
    )
    session.add(eligibility)
    session.commit()
    session.refresh(eligibility)
    return eligibility


def remove_lot_voter_eligibility(
    session: Session, user: User, lot_id: UUID, target_user_id: UUID
) -> None:
    _assert_can_manage_eligibility(user)
    existing = session.exec(
        select(LotVoterEligibility).where(
            LotVoterEligibility.lot_id == lot_id,
            LotVoterEligibility.user_id == target_user_id,
        )
    ).first()
    if existing is None:
        raise LotNotFoundError(lot_id)
    session.delete(existing)
    session.commit()


def list_lot_voter_eligibility(
    session: Session, user: User, lot_id: UUID
) -> list[LotVoterEligibility]:
    _assert_can_manage_eligibility(user)
    return list(
        session.exec(
            select(LotVoterEligibility).where(LotVoterEligibility.lot_id == lot_id)
        ).all()
    )


def set_lot_delinquency(
    session: Session, user: User, lot: Lot, is_delinquent: bool
) -> Lot:
    """Flip the manual delinquency flag that suspends the lot's voting right."""
    _assert_board(user)
    lot.is_delinquent = is_delinquent
    lot.delinquency_updated_at = datetime.utcnow()
    lot.delinquency_updated_by_id = user.id
    lot.updated_at = lot.delinquency_updated_at
    session.add(lot)
    session.commit()
    session.refresh(lot)
    return lot


# ---------------------------------------------------------------------------
# Minutes
# ---------------------------------------------------------------------------


def _fmt_date(value) -> str:
    return value.strftime("%d/%m/%Y") if value else "—"


def _fmt_datetime(value) -> str:
    return value.strftime("%d/%m/%Y %H:%M") if value else "—"


def get_delinquency_barred_lots(session: Session, assembly: Assembly) -> list[str]:
    """Bloco/Lote labels refused for delinquency across the assembly.

    Mandatory in the minutes: without it the document looks like it lost
    people, and it is what answers "why is unit 12 missing?".
    """
    vote_ids = [vote.id for vote in assembly.votes]
    if not vote_ids:
        return []
    rejections = session.exec(
        select(BallotRejection).where(
            BallotRejection.vote_id.in_(vote_ids),
            BallotRejection.reason == BallotRejectionReason.DELINQUENT_LOT,
        )
    ).all()
    labels = set()
    for rejection in rejections:
        lot = session.get(Lot, rejection.lot_id) if rejection.lot_id else None
        label = _lot_label(lot)
        if label:
            labels.add(label)
    return sorted(labels)


def _render_vote_section(session: Session, vote: Vote, index: int) -> str:
    # The minutes are always read from the frozen snapshot, never from a live
    # recount: the assembly is CLOSED by the time we get here, so any vote
    # still missing its snapshot is materialised now (idempotent).
    if vote.tally_snapshot_json is None:
        materialize_snapshot(session, vote)
    data = json.loads(vote.tally_snapshot_json)
    rows = "".join(
        f"<tr><td>{html.escape(row['label'])}</td>"
        f"<td>{row['count']}</td></tr>"
        for row in data["results"]
    )
    attributions = data.get("attributions") or []
    attribution_rows = "".join(
        f"<tr><td>{html.escape(entry.get('lot_label') or '—')}</td>"
        f"<td>{html.escape(', '.join(entry.get('selected_labels') or []))}</td>"
        f"<td>{html.escape(entry.get('cast_at') or '')}</td></tr>"
        for entry in attributions
    )
    total_lots = data.get("total_lots") or 0
    voted = data["voters_count"]
    denominator = (
        f"<p class='denominator'>Denominador: {total_lots} lotes ativos · "
        f"{voted} votaram · {max(total_lots - voted, 0)} não votaram.</p>"
    )
    return (
        f"<section class='vote'>"
        f"<h2>{index}. {html.escape(vote.title)}</h2>"
        f"<p>{html.escape(vote.description or '')}</p>"
        f"<h3>Resultado por opção</h3>"
        f"<table><thead><tr><th>Opção</th><th>Votos</th></tr></thead>"
        f"<tbody>{rows}</tbody></table>"
        f"<h3>Votos por unidade</h3>"
        f"<table><thead><tr><th>Bloco/Lote</th><th>Escolha</th>"
        f"<th>Data-hora</th></tr></thead>"
        f"<tbody>{attribution_rows}</tbody></table>"
        f"{denominator}"
        f"</section>"
    )


def render_minutes_html(session: Session, assembly: Assembly) -> str:
    """Render the assembly minutes as standalone HTML.

    A draft, not a registered ata: APRAS has no digital signature, so the
    document explicitly says it does not replace a registered ata. HTML is
    printed to PDF by the browser — no server-side PDF dependency.
    """
    if assembly.status != AssemblyStatus.CLOSED:
        raise AssemblyNotClosedError

    votes = sorted(assembly.votes, key=lambda vote: vote.created_at)
    opens = min((vote.opens_at for vote in votes), default=None)
    closes = max((vote.closes_at for vote in votes), default=None)
    sections = "".join(
        _render_vote_section(session, vote, index)
        for index, vote in enumerate(votes, start=1)
    )
    barred = get_delinquency_barred_lots(session, assembly)
    barred_html = (
        "<ul>" + "".join(f"<li>{html.escape(label)}</li>" for label in barred) + "</ul>"
        if barred
        else "<p>Nenhum lote foi impedido de votar por inadimplência.</p>"
    )
    type_label = "Assembleia Geral Ordinária (AGO)" if assembly.type == "AGO" else (
        "Assembleia Geral Extraordinária (AGE)"
    )

    return (
        "<!DOCTYPE html>"
        "<html lang='pt-BR'><head><meta charset='utf-8'>"
        f"<title>Minuta de Ata — {html.escape(assembly.title)}</title>"
        "<style>body{font-family:Arial,Helvetica,sans-serif;margin:2rem;}"
        "table{border-collapse:collapse;margin-bottom:1rem;}"
        "th,td{border:1px solid #999;padding:4px 8px;text-align:left;}"
        ".footer{margin-top:3rem;font-size:0.85rem;color:#444;}</style>"
        "</head><body>"
        f"<h1>Minuta de Ata — {html.escape(assembly.title)}</h1>"
        f"<p><strong>Tipo:</strong> {type_label}</p>"
        f"<p><strong>Realizada em:</strong> {_fmt_date(assembly.held_on)}</p>"
        f"<p><strong>Janela de votação:</strong> {_fmt_datetime(opens)} até "
        f"{_fmt_datetime(closes)}</p>"
        "<h2>Pauta</h2>"
        f"<pre>{html.escape(assembly.agenda or '—')}</pre>"
        f"{sections}"
        "<h2>Lotes impedidos por inadimplência</h2>"
        f"{barred_html}"
        "<div class='footer'>"
        "<p>_________________________________<br>Síndico(a)</p>"
        "<p>_________________________________<br>Secretário(a)</p>"
        "<p>Documento gerado automaticamente pelo APRAS. Esta é uma minuta e "
        "não substitui a ata registrada e assinada.</p>"
        "</div></body></html>"
    )


def get_minutes_html(session: Session, user: User, assembly: Assembly) -> str:
    """Board-only entry point for the rendered minutes."""
    _assert_board(user)
    return render_minutes_html(session, assembly)


def _find_or_create_minutes_folder(session: Session, user: User) -> UUID:
    """Resolve the fixed "Atas de Assembleia" root folder, creating it once."""
    folder = session.exec(
        select(DocumentFolder).where(
            DocumentFolder.name == MINUTES_FOLDER_NAME,
            DocumentFolder.parent_id == None,  # noqa: E711
        )
    ).first()
    if folder is not None:
        return folder.id
    created = document_service.create_folder(
        session,
        user,
        DocumentFolderCreate(
            name=MINUTES_FOLDER_NAME,
            description="Minutas de ata geradas pelo módulo de assembleias.",
        ),
    )
    return created.id


def save_minutes(
    session: Session,
    user: User,
    assembly: Assembly,
    storage_provider: BaseStorageProvider | None = None,
):
    """Render the minutes and file them in the Document Center."""
    _assert_board(user)
    minutes_html = render_minutes_html(session, assembly)
    payload = minutes_html.encode("utf-8")

    provider = storage_provider or LocalStorageProvider()
    _file_path, url = provider.save_file(
        payload, f"minuta-{assembly.id}.html", "text/html"
    )

    folder_id = _find_or_create_minutes_folder(session, user)
    return document_service.create_document(
        session,
        user,
        AssociationDocumentCreate(
            folder_id=folder_id,
            title=f"Minuta de Ata — {assembly.title}",
            description=(
                f"Minuta gerada automaticamente em {_fmt_date(assembly.held_on)}."
            ),
            file_url=url,
            file_size_bytes=len(payload),
            mime_type="text/html",
            publication_year=assembly.held_on.year,
            publication_month=assembly.held_on.month,
        ),
    )
