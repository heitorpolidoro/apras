"""Pydantic schemas for assemblies, votes, ballots and tallies (APRAS-33)."""

from datetime import date, datetime
from uuid import UUID

from app.models.enums import (
    AssemblyStatus,
    AssemblyType,
    VoteKind,
    VoteStatus,
    VoteType,
)
from pydantic import BaseModel, ConfigDict, Field, model_validator


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------


class AssemblyCreate(BaseModel):
    title: str = Field(..., min_length=1)
    type: AssemblyType
    held_on: date
    agenda: str | None = None


class AssemblyUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1)
    type: AssemblyType | None = None
    held_on: date | None = None
    agenda: str | None = None
    status: AssemblyStatus | None = None


class AssemblyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    type: AssemblyType
    held_on: date
    agenda: str | None = None
    status: AssemblyStatus
    created_by_id: UUID
    created_at: datetime
    updated_at: datetime
    closed_at: datetime | None = None


# ---------------------------------------------------------------------------
# Vote / VoteOption
# ---------------------------------------------------------------------------


class VoteOptionCreate(BaseModel):
    label: str = Field(..., min_length=1)
    order_index: int = 0


class VoteOptionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    vote_id: UUID
    label: str
    order_index: int


class VoteCreate(BaseModel):
    assembly_id: UUID | None = None
    kind: VoteKind
    title: str = Field(..., min_length=1)
    description: str | None = None
    vote_type: VoteType
    is_anonymous: bool = False
    opens_at: datetime | None = None
    closes_at: datetime
    options: list[VoteOptionCreate] = Field(..., min_length=2)

    @model_validator(mode="after")
    def check_assembly_binding(self) -> "VoteCreate":
        """An ASSEMBLEIA vote belongs to an assembly; an ENQUETE never does."""
        if self.kind == VoteKind.ASSEMBLEIA and self.assembly_id is None:
            raise ValueError("assembly_id is required for ASSEMBLEIA votes")
        if self.kind == VoteKind.ENQUETE and self.assembly_id is not None:
            raise ValueError("assembly_id must be null for ENQUETE votes")
        return self


class VoteUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1)
    description: str | None = None
    vote_type: VoteType | None = None
    is_anonymous: bool | None = None
    opens_at: datetime | None = None
    closes_at: datetime | None = None
    options: list[VoteOptionCreate] | None = Field(default=None, min_length=2)


class VoteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    assembly_id: UUID | None = None
    kind: VoteKind
    title: str
    description: str | None = None
    vote_type: VoteType
    status: VoteStatus
    is_anonymous: bool
    opens_at: datetime
    closes_at: datetime
    created_by_id: UUID
    created_at: datetime
    updated_at: datetime
    closed_at: datetime | None = None
    options: list[VoteOptionRead] = []


# ---------------------------------------------------------------------------
# Lot voter eligibility
# ---------------------------------------------------------------------------


class EligibleLotRead(BaseModel):
    """A lot the caller may cast the assembly ballot for.

    Needed by the ballot UI: a RESIDENT cannot list lots, so the vote
    screen has no other way to offer the right Bloco/Lote to vote for.
    """

    id: UUID
    label: str


class LotVoterEligibilityCreate(BaseModel):
    user_id: UUID


class LotVoterEligibilityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    lot_id: UUID
    user_id: UUID
    user_name: str | None = None
    added_by_id: UUID | None = None
    added_at: datetime


# ---------------------------------------------------------------------------
# Ballots
# ---------------------------------------------------------------------------


class BallotCreate(BaseModel):
    lot_id: UUID | None = None
    selected_option_ids: list[UUID] = Field(..., min_length=1)


class BallotRetract(BaseModel):
    """Body of ``POST /votes/{id}/ballots/retract``.

    Carries the lot whose active ballot is being withdrawn: required in
    ``ASSEMBLEIA`` (a user may hold ballots for several lots in the same
    vote), and must be null/absent in ``ENQUETE``.
    """

    lot_id: UUID | None = None


class BallotRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    vote_id: UUID
    lot_id: UUID | None = None
    lot_label: str | None = None
    voter_user_id: UUID | None = None
    voter_name: str | None = None
    is_retraction: bool = False
    selected_option_ids: list[UUID] = []
    cast_at: datetime


class MyBallotRead(BallotRead):
    """One ballot the caller is entitled to see (see spec Visibilidade, Regra 3).

    ``can_edit`` is true only for the person who cast that specific ballot —
    only the holder may change or retract it.
    """

    can_edit: bool = False


# ---------------------------------------------------------------------------
# Tally
# ---------------------------------------------------------------------------


class TallyResultRead(BaseModel):
    option_id: UUID
    label: str
    count: int


class TallyAttributionRead(BaseModel):
    lot_id: UUID | None = None
    lot_label: str | None = None
    voter_user_id: UUID | None = None
    voter_name: str | None = None
    selected_labels: list[str] = []
    cast_at: datetime


class TallyRead(BaseModel):
    """Two-mode tally payload.

    While the vote is open only ``voters_count`` (plus ``total_lots`` in an
    assembly) is filled; ``results`` and ``attributions`` stay ``None`` and
    are dropped from the JSON response by ``response_model_exclude_none``.
    """

    vote_id: UUID
    kind: VoteKind
    status: VoteStatus
    is_anonymous: bool
    voters_count: int
    total_lots: int | None = None
    results: list[TallyResultRead] | None = None
    attributions: list[TallyAttributionRead] | None = None
