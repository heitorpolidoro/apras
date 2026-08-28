"""Assembly and vote API endpoints (APRAS-33).

Two routers in one module, following the `reservations.py` precedent of
`spaces_router`/`reservations_router`.
"""

from typing import Annotated
from uuid import UUID

from app.api import deps as api_deps
from app.db import get_session
from app.models.enums import UserRole, VoteKind, VoteStatus, VoteType
from app.models.lot import Lot
from app.models.user import User
from app.models.voting import Ballot, Vote
from app.schemas.document import AssociationDocumentRead
from app.schemas.voting import (
    AssemblyCreate,
    AssemblyRead,
    AssemblyUpdate,
    BallotCreate,
    BallotRead,
    BallotRetract,
    EligibleLotRead,
    MyBallotRead,
    TallyRead,
    VoteCreate,
    VoteRead,
    VoteUpdate,
)
from app.services import voting_service
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import HTMLResponse
from sqlmodel import Session

assemblies_router = APIRouter()
votes_router = APIRouter()

_NO_ACCESS_ROLES = {UserRole.GUEST, UserRole.PORTEIRO}


def _require_voting_access(current_user: User) -> None:
    """GUEST and PORTEIRO never reach the voting surface, read or write."""
    if current_user.role in _NO_ACCESS_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Este perfil não tem acesso ao módulo de votação",
        )


def _to_ballot_read(session: Session, ballot: Ballot) -> BallotRead:
    lot = session.get(Lot, ballot.lot_id) if ballot.lot_id else None
    return BallotRead(
        id=ballot.id,
        vote_id=ballot.vote_id,
        lot_id=ballot.lot_id,
        lot_label=f"{lot.block}/{lot.lot_number}" if lot else None,
        voter_user_id=ballot.voter_user_id,
        is_retraction=ballot.is_retraction,
        selected_option_ids=voting_service.selected_option_ids(ballot),
        cast_at=ballot.cast_at,
    )


def _validate_selection(vote: Vote, selected_option_ids: list[UUID]) -> None:
    """Boundary validation of the ballot body against the referenced vote.

    Arity and option membership need the vote alongside the payload, so they
    are checked here rather than in the schema (which cannot see the vote)
    or in the service (which raises domain errors, not 422s).
    """
    valid_ids = {option.id for option in vote.options}
    unknown = [oid for oid in selected_option_ids if oid not in valid_ids]
    if unknown:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Opção selecionada não pertence a esta votação",
        )
    if len(set(selected_option_ids)) != len(selected_option_ids):
        # Repeating an id would otherwise let one ballot count several times
        # for the same option in the published result and in the minutes.
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Uma opção não pode ser escolhida mais de uma vez",
        )
    if vote.vote_type == VoteType.SINGLE_CHOICE and len(selected_option_ids) != 1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Escolha exatamente uma opção",
        )


def _validate_retract_body(vote: Vote, payload: BallotRetract) -> None:
    """`lot_id` is required in an assembly and forbidden in a poll."""
    if vote.kind == VoteKind.ASSEMBLEIA and payload.lot_id is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Informe o lote cuja cédula será retirada",
        )
    if vote.kind == VoteKind.ENQUETE and payload.lot_id is not None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Uma enquete não recebe lot_id na retirada",
        )


# ---------------------------------------------------------------------------
# Assemblies
# ---------------------------------------------------------------------------


@assemblies_router.post(
    "/", response_model=AssemblyRead, status_code=status.HTTP_201_CREATED
)
def create_assembly(
    assembly_in: AssemblyCreate,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
) -> AssemblyRead:
    """Create an assembly (AGO/AGE). ADMINISTRATOR/DIRECTOR only."""
    _require_voting_access(current_user)
    assembly = voting_service.create_assembly(session, current_user, assembly_in)
    return AssemblyRead.model_validate(assembly)


@assemblies_router.get("/", response_model=list[AssemblyRead])
def list_assemblies(
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
) -> list[AssemblyRead]:
    """List assemblies, most recent first."""
    _require_voting_access(current_user)
    return [
        AssemblyRead.model_validate(item)
        for item in voting_service.list_assemblies(session)
    ]


@assemblies_router.get("/{assembly_id}", response_model=AssemblyRead)
def get_assembly(
    assembly_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
) -> AssemblyRead:
    """Retrieve a single assembly."""
    _require_voting_access(current_user)
    return AssemblyRead.model_validate(
        voting_service.get_assembly(session, assembly_id)
    )


@assemblies_router.patch("/{assembly_id}", response_model=AssemblyRead)
def update_assembly(
    assembly_id: UUID,
    assembly_in: AssemblyUpdate,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
) -> AssemblyRead:
    """Update an assembly. Blocked once the assembly is CLOSED."""
    _require_voting_access(current_user)
    assembly = voting_service.get_assembly(session, assembly_id)
    return AssemblyRead.model_validate(
        voting_service.update_assembly(session, current_user, assembly, assembly_in)
    )


@assemblies_router.post("/{assembly_id}/close", response_model=AssemblyRead)
def close_assembly(
    assembly_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
) -> AssemblyRead:
    """Close the assembly, cascading into every vote still open."""
    _require_voting_access(current_user)
    assembly = voting_service.get_assembly(session, assembly_id)
    return AssemblyRead.model_validate(
        voting_service.close_assembly(session, current_user, assembly)
    )


@assemblies_router.get("/{assembly_id}/minutes", response_class=HTMLResponse)
def get_assembly_minutes(
    assembly_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
) -> HTMLResponse:
    """Render the minutes as HTML. Only after the assembly is closed."""
    _require_voting_access(current_user)
    assembly = voting_service.get_assembly(session, assembly_id)
    return HTMLResponse(
        content=voting_service.get_minutes_html(session, current_user, assembly)
    )


@assemblies_router.post(
    "/{assembly_id}/minutes/save",
    response_model=AssociationDocumentRead,
    status_code=status.HTTP_201_CREATED,
)
def save_assembly_minutes(
    assembly_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
) -> AssociationDocumentRead:
    """Store the rendered minutes in the Document Center."""
    _require_voting_access(current_user)
    assembly = voting_service.get_assembly(session, assembly_id)
    return voting_service.save_minutes(session, current_user, assembly)


# ---------------------------------------------------------------------------
# Votes
# ---------------------------------------------------------------------------


@votes_router.post("/", response_model=VoteRead, status_code=status.HTTP_201_CREATED)
def create_vote(
    vote_in: VoteCreate,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
) -> VoteRead:
    """Create an agenda vote or a standalone poll."""
    _require_voting_access(current_user)
    return VoteRead.model_validate(
        voting_service.create_vote(session, current_user, vote_in)
    )


@votes_router.get("/", response_model=list[VoteRead])
def list_votes(
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
    kind: VoteKind | None = Query(default=None),
    status_filter: VoteStatus | None = Query(default=None, alias="status"),
    assembly_id: UUID | None = Query(default=None),
) -> list[VoteRead]:
    """List votes. Never materialises snapshots (see the lazy-close rule)."""
    _require_voting_access(current_user)
    votes = voting_service.list_votes(
        session, kind=kind, status=status_filter, assembly_id=assembly_id
    )
    return [VoteRead.model_validate(vote) for vote in votes]


@votes_router.get("/{vote_id}", response_model=VoteRead)
def get_vote(
    vote_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
) -> VoteRead:
    """Retrieve one vote, lazily closing it if the window has elapsed."""
    _require_voting_access(current_user)
    vote = voting_service.get_vote(session, vote_id)
    voting_service.materialize_if_due(session, vote)
    return VoteRead.model_validate(vote)


@votes_router.patch("/{vote_id}", response_model=VoteRead)
def update_vote(
    vote_id: UUID,
    vote_in: VoteUpdate,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
) -> VoteRead:
    """Update a vote — only while it has received no ballot at all."""
    _require_voting_access(current_user)
    vote = voting_service.get_vote(session, vote_id)
    return VoteRead.model_validate(
        voting_service.update_vote(session, current_user, vote, vote_in)
    )


@votes_router.post("/{vote_id}/close", response_model=VoteRead)
def close_vote(
    vote_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
) -> VoteRead:
    """Close a vote early, materialising its tally snapshot."""
    _require_voting_access(current_user)
    vote = voting_service.get_vote(session, vote_id)
    return VoteRead.model_validate(
        voting_service.close_vote(session, current_user, vote)
    )


@votes_router.post(
    "/{vote_id}/ballots", response_model=BallotRead, status_code=status.HTTP_201_CREATED
)
def cast_ballot(
    vote_id: UUID,
    ballot_in: BallotCreate,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
) -> BallotRead:
    """Cast a ballot, or replace the one the caller already holds.

    No role pre-filter here on purpose: the service chain must run so a
    refused attempt is written to `BallotRejection` before the 403.
    """
    vote = voting_service.get_vote(session, vote_id)
    _validate_selection(vote, ballot_in.selected_option_ids)
    ballot = voting_service.cast_ballot(
        session,
        current_user,
        vote,
        lot_id=ballot_in.lot_id,
        selected_option_ids=ballot_in.selected_option_ids,
    )
    return _to_ballot_read(session, ballot)


@votes_router.post(
    "/{vote_id}/ballots/retract",
    response_model=BallotRead,
    status_code=status.HTTP_201_CREATED,
)
def retract_ballot(
    vote_id: UUID,
    payload: BallotRetract,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
) -> BallotRead:
    """Withdraw the active ballot the caller holds (appends a retraction row).

    As with casting, the role check lives in the service chain so the
    refusal is logged.
    """
    vote = voting_service.get_vote(session, vote_id)
    _validate_retract_body(vote, payload)
    ballot = voting_service.cast_ballot(
        session, current_user, vote, lot_id=payload.lot_id, is_retraction=True
    )
    return _to_ballot_read(session, ballot)


@votes_router.get("/{vote_id}/my-ballot", response_model=list[MyBallotRead])
def get_my_ballot(
    vote_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
) -> list[MyBallotRead]:
    """The ballots the caller may see (own, lot-mates', or only own if anonymous)."""
    _require_voting_access(current_user)
    vote = voting_service.get_vote(session, vote_id)
    return voting_service.get_my_ballots(session, current_user, vote)


@votes_router.get("/{vote_id}/eligible-lots", response_model=list[EligibleLotRead])
def list_eligible_lots(
    vote_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
) -> list[EligibleLotRead]:
    """Lots the caller may cast this vote's ballot for (empty for a poll)."""
    _require_voting_access(current_user)
    vote = voting_service.get_vote(session, vote_id)
    return [
        EligibleLotRead(id=lot.id, label=f"{lot.block}/{lot.lot_number}")
        for lot in voting_service.get_eligible_lots(session, current_user, vote)
    ]


@votes_router.get(
    "/{vote_id}/tally", response_model=TallyRead, response_model_exclude_none=True
)
def get_tally(
    vote_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
) -> TallyRead:
    """Participation count while open; full tally only once closed."""
    vote = voting_service.get_vote(session, vote_id)
    return voting_service.get_tally(session, current_user, vote)
