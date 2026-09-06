"""Pydantic schemas for the infraction module (APRAS-44 §4.4).

Three shapes are worth reading before the rest:

* :class:`InfractionRead` carries ``current_stage``, ``current_stage_at`` and
  ``defense_due_on`` and **none of them is a column**. They are derived from
  the append-only ``infraction_stage`` history at serialisation time (§7.3,
  §7.5), which is what lets decision 5 of §2 hold -- no ``status``, no
  ``current_stage`` -- while the UI still shows where a process stands.
* :class:`InfractionTimelineEntryRead` is a flat, discriminated shape, so the
  frontend renders stages and contestations as one list with no client-side
  merge.
* :class:`NextStepRead` is the whole of §6, as data. It is produced by a
  function that is pure with respect to the database: it reads and computes,
  and never writes or advances anything.
"""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import (
    InfractionFineMode,
    InfractionRuleOrigin,
    InfractionStepAction,
    NextStepReason,
)
from app.schemas.package import LotSummaryRead

# ---------------------------------------------------------------------------
# Small shared summaries
# ---------------------------------------------------------------------------


class InfractionActorRead(BaseModel):
    """Who wrote one row: the id and the display name, nothing else.

    Deliberately **not** ``app.schemas.lot.UserSummaryRead``: that shape's
    ``roles`` field means "the user's role names in the acting tenant", and
    this module resolves no role names. Shipping it with ``roles`` permanently
    ``[]`` would be a schema that lies about what it carries.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    full_name: str


class ResidentSummaryRead(BaseModel):
    """The responsible person, as the infraction views need them."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    full_name: str
    lot_id: UUID


# ---------------------------------------------------------------------------
# The rule catalogue and its ladder
# ---------------------------------------------------------------------------


class InfractionRuleBase(BaseModel):
    """The catalogue fields. ``steps`` is deliberately absent (§6.5).

    A rule is created without a ladder and the ladder is written by
    ``PUT .../policy``; forbidding an infraction until that second call
    succeeded would mean a rule that cannot be used until an unrelated request
    lands.
    """

    article: str = Field(min_length=1, max_length=255)
    origin: InfractionRuleOrigin
    description: str = Field(min_length=1)
    recidivism_window_days: int = Field(gt=0)
    is_active: bool = True


class InfractionRuleCreate(InfractionRuleBase):
    """Body of ``POST /api/v1/infraction-rules``."""


class InfractionRuleUpdate(BaseModel):
    """Body of ``PUT /api/v1/infraction-rules/{rule_id}``; every field optional."""

    article: str | None = Field(default=None, min_length=1, max_length=255)
    origin: InfractionRuleOrigin | None = None
    description: str | None = Field(default=None, min_length=1)
    recidivism_window_days: int | None = Field(default=None, gt=0)
    is_active: bool | None = None


class InfractionPolicyStepWrite(BaseModel):
    """One rung, as written. Coherence is validated by the service (§12.1).

    The four conditional requirements -- a deadline iff ``NOTIFICACAO``, a
    ``fine_mode`` iff ``MULTA``, an amount iff ``FIXED``, a multiplier iff
    ``MULTIPLE`` -- are cross-field rules over a *list*, so they are checked
    where the whole ladder is visible and answer **422** with a detail naming
    the offending ``step_order``.
    """

    step_order: int = Field(ge=1)
    action: InfractionStepAction
    defense_deadline_days: int | None = Field(default=None, gt=0)
    fine_mode: InfractionFineMode | None = None
    fine_fixed_amount: float | None = Field(default=None, ge=0)
    fine_fee_multiplier: float | None = Field(default=None, ge=0)
    note: str | None = None


class InfractionPolicyWrite(BaseModel):
    """Body of ``PUT .../policy``. Replaces the ladder whole, never patches it."""

    steps: list[InfractionPolicyStepWrite] = Field(min_length=1, max_length=20)


class InfractionPolicyStepRead(InfractionPolicyStepWrite):
    """One persisted rung."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID


class InfractionRuleRead(InfractionRuleBase):
    """One rule with its ladder, ordered by ``step_order``."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    steps: list[InfractionPolicyStepRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class InfractionRuleSummaryRead(BaseModel):
    """The rule as an infraction refers to it."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    article: str
    origin: InfractionRuleOrigin
    description: str


# ---------------------------------------------------------------------------
# The module settings singleton (§5)
# ---------------------------------------------------------------------------


class InfractionSettingsRead(BaseModel):
    """``GET /api/v1/infraction-settings``. Never 404s: an absent row is nulls."""

    condo_fee_amount: float | None = None
    updated_at: datetime | None = None
    updated_by: InfractionActorRead | None = None


class InfractionSettingsWrite(BaseModel):
    """``PUT /api/v1/infraction-settings``. ``None`` clears the reference."""

    condo_fee_amount: float | None = Field(default=None, ge=0)


# ---------------------------------------------------------------------------
# The process
# ---------------------------------------------------------------------------


class InfractionCreate(BaseModel):
    """Body of ``POST /api/v1/infractions``.

    ``source_occurrence_id`` is **absent on purpose**. The spec's draft carried
    it as "accepted and ignored", which is a silent lie to the caller: an
    infraction born of an occurrence is created by
    ``POST /api/v1/infractions/from-occurrence/{occurrence_id}``, which is the
    route that resolves the effective lot, defaults the description and writes
    the ``OccurrenceTimeline`` note. Accepting the field here and dropping it
    would let a client believe it had linked the two.
    """

    rule_id: UUID
    lot_id: UUID
    responsible_resident_id: UUID
    occurred_on: date
    description: str = Field(min_length=1)
    evidence_urls: list[str] = Field(default_factory=list)


class InfractionPromote(BaseModel):
    """Body of ``POST /api/v1/infractions/from-occurrence/{occurrence_id}``.

    ``lot_id`` is optional because ``Occurrence.lot_id`` is nullable while
    ``infraction.lot_id`` is not: §7.4's effective-lot rule resolves the two.
    ``responsible_resident_id`` stays required either way -- an occurrence
    names no responsible person.
    """

    rule_id: UUID
    responsible_resident_id: UUID
    lot_id: UUID | None = None
    description: str | None = Field(default=None, min_length=1)
    occurred_on: date | None = None


class InfractionStageCreate(BaseModel):
    """Body of ``POST /api/v1/infractions/{id}/stages``.

    ``action = null`` means *apply the suggestion*; an explicit ``action`` is
    always accepted and records ``suggestion_followed = False``, so a deviation
    from policy is itself auditable (§6.4).
    """

    action: InfractionStepAction | None = None
    note: str = Field(min_length=1)
    fine_amount: float | None = Field(default=None, ge=0)
    defense_deadline_days: int | None = Field(default=None, gt=0)
    evidence_urls: list[str] = Field(default_factory=list)


class ContestationCreate(BaseModel):
    """Body of ``POST /api/v1/infractions/{id}/contestation``."""

    body: str = Field(min_length=1)
    attachment_urls: list[str] = Field(default_factory=list)


class CycleCloseCreate(BaseModel):
    """Body of ``POST /api/v1/infractions/cycles/close``.

    ``lot_id`` is optional **audit context** and is never part of the
    recidivism predicate (§6.2 property 5). ``justification`` is required and
    non-empty (ER-9); a whitespace-only string is 422.
    """

    rule_id: UUID
    responsible_resident_id: UUID
    lot_id: UUID | None = None
    justification: str = Field(min_length=1)


class CycleCloseRead(BaseModel):
    """One recorded cycle close, as ``GET /api/v1/infractions/cycles`` lists it."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    rule: InfractionRuleSummaryRead
    responsible: ResidentSummaryRead
    lot_id: UUID | None = None
    justification: str
    closed_by: InfractionActorRead
    closed_at: datetime


class NextStepRead(BaseModel):
    """``GET /api/v1/infractions/{id}/next-step`` -- the whole of §6, as data.

    ``reason`` and ``is_saturated`` are **not** the same predicate and neither
    replaces the other: they disagree at exactly ``ladder_index == n``, where
    the last step *is* the suggestion -- saturated, because nothing is above
    it, but not clamped, because nothing was truncated.
    """

    recidivism_count: int
    window_start: date
    cycle_closed_at: datetime | None = None
    stages_applied: int
    ladder_index: int
    suggested_step_order: int | None = None
    suggested_action: InfractionStepAction | None = None
    reason: NextStepReason
    defense_deadline_days: int | None = None
    fine_amount: float | None = None
    fine_amount_unavailable_reason: str | None = None
    is_saturated: bool


class InfractionTimelineEntryRead(BaseModel):
    """One row of the merged history: a stage or a contestation.

    Flat and discriminated by ``kind`` rather than a union of two models, so
    the frontend timeline is one ordered list and never a client-side merge.
    """

    kind: str
    id: UUID
    at: datetime
    actor: InfractionActorRead | None = None
    action: InfractionStepAction | None = None
    note: str | None = None
    fine_amount: float | None = None
    fine_amount_overridden: bool | None = None
    defense_due_on: date | None = None
    defense_deadline_overridden: bool | None = None
    policy_step_order: int | None = None
    suggestion_followed: bool | None = None
    attachment_urls: list[str] = Field(default_factory=list)


class InfractionRead(BaseModel):
    """One infraction. ``current_stage`` and friends are derived, never stored."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    rule: InfractionRuleSummaryRead
    lot: LotSummaryRead
    responsible: ResidentSummaryRead
    occurred_on: date
    description: str
    evidence_urls: list[str] = Field(default_factory=list)
    source_occurrence_id: UUID | None = None
    source_occurrence_protocol: str | None = None
    current_stage: InfractionStepAction | None = None
    current_stage_at: datetime | None = None
    defense_due_on: date | None = None
    timeline: list[InfractionTimelineEntryRead] = Field(default_factory=list)
    created_at: datetime


class PaginatedInfractionRead(BaseModel):
    """``GET /api/v1/infractions``, shaped exactly like ``PaginatedPackageRead``.

    ``GET /api/v1/infractions/my-lots`` is deliberately a **bare list**: it is
    the resident's own short list, bounded by their lot links, and the
    ``GET /api/v1/packages/my-lots`` precedent returns a bare list too.
    """

    items: list[InfractionRead]
    total: int
    skip: int
    limit: int
