"""Infraction rules, escalation policy and the infraction process (APRAS-44).

Seven tables, and the partition between them is the whole design:

* ``infraction_rule`` is the per-tenant catalogue of the articles a
  condominium enforces, and ``infraction_policy_step`` is the *ordered
  escalation ladder* of one rule. A rule with **zero** steps is a normal,
  reachable state (§6.5), never an error.
* ``infraction`` is one process and ``infraction_stage`` is its **append-only**
  history. :class:`Infraction` carries no ``status`` and no ``current_stage``
  column, and no route updates or deletes a stage: the current stage is the
  last row of ``infraction_stage``, derived at serialisation time (§7.3).
  ``tests/test_infractions.py`` pins the absence of both columns, because a
  convenience column added later is exactly how an append-only history stops
  being the truth.
* ``infraction_contestation`` is the notified unit's written defense.
  Registration only: there is no accept/reject, no adjudicator, and nothing
  about it moves the process (§2 decision 3).
* ``infraction_cycle_close`` is the auditable, justified event that cuts a
  ``(rule, responsible)`` recidivism cycle **going forward**. Its ``lot_id``
  is optional audit context and is deliberately absent from §6.2's predicate.
* ``infraction_settings`` is the tenant-scoped singleton holding the
  condominium-fee reference a ``MULTIPLE`` fine multiplies (§5). There is no
  condominium fee anywhere else in this codebase, and ``tenant`` is a global,
  superuser-managed table, so the value lives here -- owned by the module,
  toggled off with it, written by the síndico.

Scoping follows the rule ``app/models/tenant.py`` states: a table carries its
own ``tenant_id`` when a route lists it or fetches it by its own id **without**
a scoped parent's id in the path. ``GET /api/v1/infractions/cycles`` and
``GET /api/v1/infraction-settings`` are exactly that, so those two are directly
scoped alongside ``infraction_rule`` and ``infraction``.
``infraction_policy_step``, ``infraction_stage`` and
``infraction_contestation`` are reached only through their parent's id and
therefore carry **no** ``tenant_id``: duplicating it would create a second,
forgeable source of truth that can disagree with the parent.

Money is ``float`` (``FinancialTransaction.amount``'s type) and enums are
``sa.String()``, never a Postgres ``ENUM`` type -- migration ``0027``'s
convention. They carry **no** ``server_default``, and deliberately: none of
the three has a Python-side default either, and migration ``0035``'s precedent
is to add one only where the model has one. That is what keeps the schema
Alembic builds identical to the one ``SQLModel.metadata.create_all()`` builds
for the test suite, an equality
``test_0036_matches_the_model_metadata`` asserts against real Postgres.

Nothing here imports, names or points at a finance table -- ER-5, proved
mechanically by ``tests/test_infraction_isolation.py``.
"""

from datetime import date, datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4

from sqlalchemy import Index, UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel

from app.models.enums import (
    InfractionFineMode,
    InfractionRuleOrigin,
    InfractionStepAction,
)
from app.models.tenant import tenant_id_field

if TYPE_CHECKING:  # pragma: no cover
    from app.models.lot import Lot
    from app.models.occurrence import Occurrence
    from app.models.resident import Resident
    from app.models.user import User


class InfractionRule(SQLModel, table=True):
    """One article of the estatuto / regimento / convenção, per tenant.

    ``DELETE /api/v1/infraction-rules/{id}`` **soft-deactivates** (sets
    ``is_active = False``) on the ``spaces:deactivate`` precedent: infractions
    reference rules, and ER-4 requires the lot's history to stay whole and
    navigable. Deactivation is forward-looking only -- a deactivated rule
    refuses to start a *new* infraction (§7.7) while every existing process
    still resolves it and still advances along its ladder.
    """

    __tablename__ = "infraction_rule"
    # Two condominiums may both cite "art. 12 do Regimento Interno"; one may
    # not cite it twice. Per-tenant, the AGENTS.md convention for every scoped
    # unique constraint.
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "origin",
            "article",
            name="uq_infraction_rule_tenant_origin_article",
        ),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    tenant_id: UUID = tenant_id_field()
    article: str = Field(nullable=False)
    origin: InfractionRuleOrigin = Field(nullable=False, index=True)
    description: str = Field(nullable=False)
    recidivism_window_days: int = Field(nullable=False)
    is_active: bool = Field(default=True, nullable=False, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    steps: list["InfractionPolicyStep"] = Relationship(
        back_populates="rule",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class InfractionPolicyStep(SQLModel, table=True):
    """One rung of one rule's ladder. Scope inherited through ``rule_id``.

    ``step_order`` is 1-based and contiguous from 1, validated on write, which
    is what lets §6.1 index the ladder by ``step_order`` rather than by a
    Python list position -- the dict spelling exists precisely so the
    off-by-one cannot be introduced.
    """

    __tablename__ = "infraction_policy_step"
    __table_args__ = (
        UniqueConstraint(
            "rule_id", "step_order", name="uq_infraction_policy_step_rule_order"
        ),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    rule_id: UUID = Field(
        foreign_key="infraction_rule.id",
        ondelete="CASCADE",
        nullable=False,
        index=True,
    )
    step_order: int = Field(nullable=False)
    action: InfractionStepAction = Field(nullable=False)
    defense_deadline_days: int | None = Field(default=None, nullable=True)
    fine_mode: InfractionFineMode | None = Field(default=None, nullable=True)
    fine_fixed_amount: float | None = Field(default=None, nullable=True)
    fine_fee_multiplier: float | None = Field(default=None, nullable=True)
    note: str | None = Field(default=None, nullable=True)

    rule: "InfractionRule" = Relationship(back_populates="steps")


class Infraction(SQLModel, table=True):
    """One infraction process. **No ``status``, no ``current_stage``.**

    Decision 5 of §2: the current stage is the last row of
    ``infraction_stage``, ordered by ``(applied_on, created_at, id)``, computed
    at serialisation time. ``GET /api/v1/infractions?stage=`` filters on that
    derivation with a correlated subquery, so even the list filter creates no
    stored column.

    ``lot_id`` is **NOT NULL** while ``Occurrence.lot_id`` is nullable: an
    infraction is always against a unit, a common-area occurrence legitimately
    has no lot. That asymmetry is what §7.4's effective-lot rule exists for,
    and it is pinned by a test so a later "fix" to either column cannot
    silently break promotion.
    """

    __tablename__ = "infraction"
    __table_args__ = (
        # What §6.2's recidivism count reads, in the order it reads it.
        Index(
            "ix_infraction_recidivism",
            "tenant_id",
            "rule_id",
            "responsible_resident_id",
            "occurred_on",
        ),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    tenant_id: UUID = tenant_id_field()
    rule_id: UUID = Field(
        foreign_key="infraction_rule.id",
        ondelete="RESTRICT",
        nullable=False,
        index=True,
    )
    lot_id: UUID = Field(
        foreign_key="lot.id", ondelete="RESTRICT", nullable=False, index=True
    )
    responsible_resident_id: UUID = Field(
        foreign_key="resident.id", ondelete="RESTRICT", nullable=False, index=True
    )
    source_occurrence_id: UUID | None = Field(
        default=None,
        foreign_key="occurrence.id",
        ondelete="SET NULL",
        nullable=True,
        index=True,
    )
    registered_by_id: UUID = Field(
        foreign_key="user.id", ondelete="RESTRICT", nullable=False, index=True
    )
    occurred_on: date = Field(nullable=False, index=True)
    description: str = Field(nullable=False)
    evidence_urls_json: str | None = Field(default=None, nullable=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    rule: "InfractionRule" = Relationship()
    lot: "Lot" = Relationship()
    responsible: "Resident" = Relationship()
    source_occurrence: Optional["Occurrence"] = Relationship()
    stages: list["InfractionStage"] = Relationship(
        back_populates="infraction",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    contestations: list["InfractionContestation"] = Relationship(
        back_populates="infraction",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class InfractionStage(SQLModel, table=True):
    """One applied step. Append-only **in the schema**, not only in handlers.

    There is deliberately **no ``updated_at``** and no update or delete route:
    a mistaken stage is corrected by a subsequent stage whose note says so.

    ``fine_amount`` and ``defense_due_on`` are **frozen** here at application
    time, so a later change to ``condo_fee_amount`` or to the rule's deadline
    never rewrites history.

    Both frozen values carry a matching ``*_overridden`` flag, and the pair is
    deliberately symmetric: the audit trail has to distinguish "the policy
    priced this" from "a human typed it" for a **deadline** exactly as it does
    for a value. ``suggestion_followed`` cannot stand in for either -- it says
    a human named the *action*, not that they named its terms.
    """

    __tablename__ = "infraction_stage"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    infraction_id: UUID = Field(
        foreign_key="infraction.id",
        ondelete="CASCADE",
        nullable=False,
        index=True,
    )
    action: InfractionStepAction = Field(nullable=False, index=True)
    applied_on: date = Field(nullable=False)
    note: str = Field(nullable=False)
    actor_id: UUID = Field(
        foreign_key="user.id", ondelete="RESTRICT", nullable=False, index=True
    )
    fine_amount: float | None = Field(default=None, nullable=True)
    fine_amount_overridden: bool = Field(default=False, nullable=False)
    defense_due_on: date | None = Field(default=None, nullable=True)
    defense_deadline_overridden: bool = Field(default=False, nullable=False)
    policy_step_order: int | None = Field(default=None, nullable=True)
    suggestion_followed: bool = Field(default=True, nullable=False)
    evidence_urls_json: str | None = Field(default=None, nullable=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    infraction: "Infraction" = Relationship(back_populates="stages")
    actor: "User" = Relationship()


class InfractionContestation(SQLModel, table=True):
    """The notified unit's written defense. Registration only.

    ``stage_id`` is **nullable** and always points at the ``NOTIFICACAO`` the
    defense answers. Nullable rather than NOT NULL for one reason and it is a
    FK-lifetime one: ``infraction_stage.infraction_id`` is ``CASCADE`` while
    this column is ``RESTRICT``, so deleting an infraction would try to cascade
    the stages out from under a restricting child. ``SET NULL`` on a nullable
    column resolves that collision without weakening the contestation's own
    guarantee -- the row survives, attached to its infraction, and the
    ``NOTIFICACAO`` it answered is still in the same timeline.
    """

    __tablename__ = "infraction_contestation"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    infraction_id: UUID = Field(
        foreign_key="infraction.id",
        ondelete="CASCADE",
        nullable=False,
        index=True,
    )
    stage_id: UUID | None = Field(
        default=None,
        foreign_key="infraction_stage.id",
        ondelete="SET NULL",
        nullable=True,
        index=True,
    )
    body: str = Field(nullable=False)
    attachment_urls_json: str | None = Field(default=None, nullable=True)
    submitted_by_id: UUID = Field(
        foreign_key="user.id", ondelete="RESTRICT", nullable=False, index=True
    )
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    infraction: "Infraction" = Relationship(back_populates="contestations")
    submitted_by: "User" = Relationship()


class InfractionCycleClose(SQLModel, table=True):
    """A justified, auditable cut of one ``(rule, responsible)`` cycle.

    ``lot_id`` is **optional and is audit context only** (§6.2 property 5): it
    records where the síndico observed the change of responsible. Matching on
    it in the recidivism predicate would silently make the count *propter rem*
    again for anyone who moved, which is the opposite of decision 4 of §2.
    Nothing but ``GET /api/v1/infractions/cycles`` reads it.

    Closing deletes nothing. It is a cutoff on infractions registered
    **after** it, and ``justification`` is NOT NULL and non-empty (ER-9).
    """

    __tablename__ = "infraction_cycle_close"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    tenant_id: UUID = tenant_id_field()
    rule_id: UUID = Field(
        foreign_key="infraction_rule.id",
        ondelete="RESTRICT",
        nullable=False,
        index=True,
    )
    lot_id: UUID | None = Field(
        default=None,
        foreign_key="lot.id",
        ondelete="RESTRICT",
        nullable=True,
        index=True,
    )
    responsible_resident_id: UUID = Field(
        foreign_key="resident.id", ondelete="RESTRICT", nullable=False, index=True
    )
    justification: str = Field(nullable=False)
    closed_by_id: UUID = Field(
        foreign_key="user.id", ondelete="RESTRICT", nullable=False, index=True
    )
    closed_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    rule: "InfractionRule" = Relationship()
    responsible: "Resident" = Relationship()
    closed_by: "User" = Relationship()


class InfractionSettings(SQLModel, table=True):
    """The tenant's condominium-fee reference, one row per tenant (§5).

    Materialised lazily on the first ``PUT``, so there is no seed and no data
    step in migration ``0036``. ``GET /api/v1/infraction-settings`` never 404s:
    an absent row reads as all nulls.
    """

    __tablename__ = "infraction_settings"
    __table_args__ = (
        UniqueConstraint("tenant_id", name="uq_infraction_settings_tenant"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    tenant_id: UUID = tenant_id_field()
    condo_fee_amount: float | None = Field(default=None, nullable=True)
    updated_by_id: UUID | None = Field(
        default=None,
        foreign_key="user.id",
        ondelete="SET NULL",
        nullable=True,
        index=True,
    )
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    updated_by: Optional["User"] = Relationship()
