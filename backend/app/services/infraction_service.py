"""The infraction domain: catalogue, ladder, process, suggestion (APRAS-44).

Everything the module decides lives here, and four of those decisions are
worth naming before the code:

1. **The current stage is derived.** :meth:`InfractionService._current_stage`
   is the only definition, ``(applied_on, created_at, id)``-ordered, and
   ``GET /api/v1/infractions?stage=`` reproduces exactly that ordering as a
   correlated subquery so the list filter creates no stored column (§4.5,
   §7.3).
2. **Recidivism is per ``(rule, responsible)``, never per lot** (§6.2). A sale
   or a tenant change therefore resets the ladder *by construction* -- new
   responsible, new count -- while ``GET /infractions?lot_id=`` still returns
   the lot's whole history. There is no reset code path, and
   ``InfractionCycleClose.lot_id`` is audit context that the predicate
   deliberately ignores.
3. **One linked-lots predicate, used twice.** :meth:`linked_lot_ids` both
   filters ``/my-lots`` and refuses a contestation, so a lot linkage that
   shows a resident an infraction is exactly the linkage that lets them
   contest it. It is deliberately **not**
   ``VisitorService.get_user_linked_lot_ids``, whose
   ``visitors:manage_any_lot`` short-circuit would hand every lot in the
   condominium to anyone holding an unrelated permission -- turning §7.5's
   403 into a no-op for exactly the callers it exists to stop.
4. **Nothing here touches Financeiro.** A ``MULTA`` records a value, a date
   and the person; it creates no ``FinancialTransaction`` and imports no
   finance module. ``tests/test_infraction_isolation.py`` proves it by AST and
   by row count, so the eventual connection has to be a *decision* rather than
   a drift.
"""

from __future__ import annotations

import json
from datetime import date, datetime, time, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import exists
from sqlalchemy.orm import selectinload
from sqlmodel import Session, col, func, select

from app.core.exceptions import (
    InfractionContestationForbiddenError,
    InfractionNotFoundError,
    InfractionRuleConflictError,
    InfractionRuleNotFoundError,
    InfractionStateError,
    InfractionValidationError,
    OccurrenceNotFoundError,
)
from app.models.enums import (
    InfractionFineMode,
    InfractionStageFilter,
    InfractionStepAction,
    NextStepReason,
)
from app.models.infraction import (
    Infraction,
    InfractionContestation,
    InfractionCycleClose,
    InfractionPolicyStep,
    InfractionRule,
    InfractionSettings,
    InfractionStage,
)
from app.models.lot import Lot, UserLotLink
from app.models.occurrence import Occurrence, OccurrenceTimeline
from app.models.resident import Resident
from app.schemas.infraction import (
    ContestationCreate,
    CycleCloseCreate,
    CycleCloseRead,
    InfractionActorRead,
    InfractionCreate,
    InfractionPolicyStepRead,
    InfractionPolicyWrite,
    InfractionPromote,
    InfractionRead,
    InfractionRuleCreate,
    InfractionRuleRead,
    InfractionRuleSummaryRead,
    InfractionRuleUpdate,
    InfractionSettingsRead,
    InfractionSettingsWrite,
    InfractionStageCreate,
    InfractionTimelineEntryRead,
    ResidentSummaryRead,
)
from app.schemas.infraction import NextStepRead as NextStepReadSchema
from app.schemas.package import LotSummaryRead

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Sequence
    from uuid import UUID

    from app.models.user import User

#: The value ``NextStepRead.fine_amount_unavailable_reason`` carries when a
#: ``MULTIPLE`` step cannot be priced. A string rather than an enum because it
#: is a diagnostic the UI renders, not a vocabulary anything branches on.
CONDO_FEE_NOT_SET = "CONDO_FEE_NOT_SET"


def _dump_urls(urls: list[str] | None) -> str | None:
    """Serialise a URL list exactly as ``Occurrence.photo_urls_json`` does."""
    return json.dumps(urls) if urls else None


def _load_urls(raw: str | None) -> list[str]:
    """The inverse, tolerant of a hand-edited row."""
    if not raw:
        return []
    try:
        loaded = json.loads(raw)
    except (TypeError, ValueError):
        return []
    return loaded if isinstance(loaded, list) else []


class InfractionService:
    """Service class for the infraction domain."""

    # ------------------------------------------------------------------
    # The linked-lots predicate (§7.6)
    # ------------------------------------------------------------------

    @staticmethod
    def linked_lot_ids(session: Session, user: User) -> set[UUID]:
        """Lots this user *is the unit for*. No permission short-circuit.

        Both branches of the union are kept -- an explicit ``UserLotLink`` and
        an active ``Resident`` row -- because that is what "the unit" means in
        this codebase and it is what ``tests/matrix_world.py`` seeds.
        """
        links = session.exec(
            select(UserLotLink.lot_id).where(UserLotLink.user_id == user.id)
        ).all()
        residents = session.exec(
            select(Resident.lot_id).where(
                Resident.user_id == user.id,
                col(Resident.is_active).is_(True),
            )
        ).all()
        return set(links) | set(residents)

    # ------------------------------------------------------------------
    # The rule catalogue
    # ------------------------------------------------------------------

    @staticmethod
    def _get_rule(session: Session, rule_id: UUID) -> InfractionRule:
        rule = session.get(InfractionRule, rule_id)
        if rule is None:
            raise InfractionRuleNotFoundError(rule_id)
        return rule

    @classmethod
    def _rule_read(cls, rule: InfractionRule) -> InfractionRuleRead:
        return InfractionRuleRead(
            id=rule.id,
            article=rule.article,
            origin=rule.origin,
            description=rule.description,
            recidivism_window_days=rule.recidivism_window_days,
            is_active=rule.is_active,
            steps=[
                InfractionPolicyStepRead.model_validate(step)
                for step in sorted(rule.steps, key=lambda s: s.step_order)
            ],
            created_at=rule.created_at,
            updated_at=rule.updated_at,
        )

    @classmethod
    def list_rules(cls, session: Session) -> list[InfractionRuleRead]:
        """The tenant's catalogue, oldest article first, ladders included.

        Deactivated rules are returned too, deliberately: §4.5 makes the
        management list the only route in this module with query parameters,
        and the catalogue screen has to show what was withdrawn or the síndico
        cannot tell an absent article from a retired one.
        """
        rules = session.exec(
            select(InfractionRule).order_by(col(InfractionRule.created_at).asc())
        ).all()
        return [cls._rule_read(rule) for rule in rules]

    @classmethod
    def get_rule(cls, session: Session, rule_id: UUID) -> InfractionRuleRead:
        return cls._rule_read(cls._get_rule(session, rule_id))

    @classmethod
    def create_rule(
        cls, session: Session, rule_in: InfractionRuleCreate
    ) -> InfractionRuleRead:
        """409 on ``(origin, article)`` twice **in the same tenant** only.

        The uniqueness is per tenant because two condominiums may both cite
        "art. 12 do Regimento Interno"; one may not cite it twice.
        """
        cls._assert_article_is_free(session, rule_in.origin, rule_in.article)
        rule = InfractionRule(
            article=rule_in.article,
            origin=rule_in.origin,
            description=rule_in.description,
            recidivism_window_days=rule_in.recidivism_window_days,
            is_active=rule_in.is_active,
        )
        session.add(rule)
        session.commit()
        session.refresh(rule)
        return cls._rule_read(rule)

    @staticmethod
    def _assert_article_is_free(
        session: Session, origin, article: str, *, exclude_id: UUID | None = None
    ) -> None:
        statement = select(InfractionRule).where(
            InfractionRule.origin == origin, InfractionRule.article == article
        )
        if exclude_id is not None:
            statement = statement.where(InfractionRule.id != exclude_id)
        if session.exec(statement).first() is not None:
            raise InfractionRuleConflictError(article)

    @classmethod
    def update_rule(
        cls, session: Session, rule_id: UUID, rule_in: InfractionRuleUpdate
    ) -> InfractionRuleRead:
        rule = cls._get_rule(session, rule_id)
        data = rule_in.model_dump(exclude_unset=True)
        origin = data.get("origin", rule.origin)
        article = data.get("article", rule.article)
        if (origin, article) != (rule.origin, rule.article):
            cls._assert_article_is_free(
                session, origin, article, exclude_id=rule.id
            )
        for field, value in data.items():
            setattr(rule, field, value)
        rule.updated_at = datetime.utcnow()
        session.add(rule)
        session.commit()
        session.refresh(rule)
        return cls._rule_read(rule)

    @classmethod
    def deactivate_rule(cls, session: Session, rule_id: UUID) -> None:
        """``DELETE`` soft-deactivates, on the ``spaces:deactivate`` precedent.

        Infractions reference rules and ER-4 requires the lot's history to
        stay whole and navigable, so the row survives, still reads back, and
        still resolves for every existing process. Only a *new* infraction of
        it is refused (§7.7).
        """
        rule = cls._get_rule(session, rule_id)
        rule.is_active = False
        rule.updated_at = datetime.utcnow()
        session.add(rule)
        session.commit()

    # ------------------------------------------------------------------
    # The escalation ladder
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_policy(policy_in: InfractionPolicyWrite) -> None:
        """Contiguity and per-action coherence, both **422** (§12.1).

        The spec's `422/400` either-or is resolved to 422: this is validation
        of the submitted body, the same class as an unparseable UUID, and one
        status code per failure class is what keeps a client's error handling
        writable.
        """
        orders = [step.step_order for step in policy_in.steps]
        if len(set(orders)) != len(orders):
            raise InfractionValidationError(
                "step_order must be unique; duplicates: "
                + ", ".join(
                    str(order)
                    for order in sorted({o for o in orders if orders.count(o) > 1})
                )
            )
        expected = list(range(1, len(orders) + 1))
        if sorted(orders) != expected:
            missing = sorted(set(expected) - set(orders))
            raise InfractionValidationError(
                "step_order must be contiguous from 1; the gap is at "
                + ", ".join(str(order) for order in missing)
            )

        for step in policy_in.steps:
            if step.action is InfractionStepAction.NOTIFICACAO:
                if step.defense_deadline_days is None:
                    raise InfractionValidationError(
                        f"step {step.step_order}: NOTIFICACAO requires "
                        "defense_deadline_days"
                    )
            elif step.defense_deadline_days is not None:
                raise InfractionValidationError(
                    f"step {step.step_order}: defense_deadline_days is only "
                    "meaningful on a NOTIFICACAO step"
                )

            if step.action is InfractionStepAction.MULTA:
                if step.fine_mode is None:
                    raise InfractionValidationError(
                        f"step {step.step_order}: MULTA requires fine_mode"
                    )
                if (
                    step.fine_mode is InfractionFineMode.FIXED
                    and step.fine_fixed_amount is None
                ):
                    raise InfractionValidationError(
                        f"step {step.step_order}: a FIXED fine requires "
                        "fine_fixed_amount"
                    )
                if (
                    step.fine_mode is InfractionFineMode.MULTIPLE
                    and step.fine_fee_multiplier is None
                ):
                    raise InfractionValidationError(
                        f"step {step.step_order}: a MULTIPLE fine requires "
                        "fine_fee_multiplier"
                    )
            elif step.fine_mode is not None:
                raise InfractionValidationError(
                    f"step {step.step_order}: fine_mode is only meaningful on "
                    "a MULTA step"
                )

    @classmethod
    def write_policy(
        cls, session: Session, rule_id: UUID, policy_in: InfractionPolicyWrite
    ) -> InfractionRuleRead:
        """Replace the ladder **whole**. A patch would need a merge rule.

        Replacing is what makes "three steps then two steps leaves exactly
        two" the obvious behaviour, and it is why the frontend ladder editor
        is a list with add/remove/reorder rather than a per-row form.
        """
        rule = cls._get_rule(session, rule_id)
        cls._validate_policy(policy_in)

        # Cleared through the relationship, so `delete-orphan` issues the
        # DELETEs, and flushed before the inserts, so the replacement rungs
        # cannot collide with the old ones on
        # `uq_infraction_policy_step_rule_order`.
        rule.steps.clear()
        session.flush()

        for step in policy_in.steps:
            session.add(
                InfractionPolicyStep(
                    rule_id=rule.id,
                    step_order=step.step_order,
                    action=step.action,
                    defense_deadline_days=step.defense_deadline_days,
                    fine_mode=step.fine_mode,
                    fine_fixed_amount=step.fine_fixed_amount,
                    fine_fee_multiplier=step.fine_fee_multiplier,
                    note=step.note,
                )
            )
        rule.updated_at = datetime.utcnow()
        session.add(rule)
        session.commit()
        session.refresh(rule)
        return cls._rule_read(rule)

    # ------------------------------------------------------------------
    # The module settings singleton (§5)
    # ------------------------------------------------------------------

    @staticmethod
    def _settings_row(session: Session) -> InfractionSettings | None:
        return session.exec(select(InfractionSettings)).first()

    @classmethod
    def _condo_fee(cls, session: Session) -> float | None:
        row = cls._settings_row(session)
        return row.condo_fee_amount if row is not None else None

    @classmethod
    def read_settings(cls, session: Session) -> InfractionSettingsRead:
        """Never 404s: an absent row reads as ``{null, null, null}``."""
        row = cls._settings_row(session)
        if row is None:
            return InfractionSettingsRead()
        return InfractionSettingsRead(
            condo_fee_amount=row.condo_fee_amount,
            updated_at=row.updated_at,
            updated_by=(
                InfractionActorRead(
                    id=row.updated_by.id,
                    full_name=row.updated_by.full_name or row.updated_by.email,
                )
                if row.updated_by is not None
                else None
            ),
        )

    @classmethod
    def write_settings(
        cls,
        session: Session,
        current_user: User,
        settings_in: InfractionSettingsWrite,
    ) -> InfractionSettingsRead:
        """Upsert, answering 200. The row is materialised lazily on first PUT.

        Which is why migration ``0036`` has no data step and the no-seeds
        doctrine survives intact: a fresh tenant has no settings row and reads
        nulls until somebody sets a fee.
        """
        row = cls._settings_row(session)
        if row is None:
            row = InfractionSettings()
        row.condo_fee_amount = settings_in.condo_fee_amount
        row.updated_by_id = current_user.id
        row.updated_at = datetime.utcnow()
        session.add(row)
        session.commit()
        session.refresh(row)
        return cls.read_settings(session)

    # ------------------------------------------------------------------
    # Reading one infraction
    # ------------------------------------------------------------------

    @staticmethod
    def _stage_sort_key(stage: InfractionStage) -> tuple:
        return (stage.applied_on, stage.created_at, str(stage.id))

    @classmethod
    def _ordered_stages(cls, infraction: Infraction) -> list[InfractionStage]:
        return sorted(infraction.stages, key=cls._stage_sort_key)

    @classmethod
    def _current_stage(cls, infraction: Infraction) -> InfractionStage | None:
        """The last row of the history. **The only definition of "current".**"""
        stages = cls._ordered_stages(infraction)
        return stages[-1] if stages else None

    @classmethod
    def _defense_due_on(cls, infraction: Infraction) -> date | None:
        """The frozen deadline of the **most recent** ``NOTIFICACAO`` stage."""
        for stage in reversed(cls._ordered_stages(infraction)):
            if stage.action is InfractionStepAction.NOTIFICACAO:
                return stage.defense_due_on
        return None

    @staticmethod
    def _actor(user: User) -> InfractionActorRead:
        """Who wrote a row. Never optional: every actor FK here is NOT NULL.

        ``infraction_settings.updated_by_id`` is the one nullable actor in the
        module, and :meth:`read_settings` handles its `None` at the call site
        rather than making this helper defensive about a case its own callers
        cannot produce.
        """
        return InfractionActorRead(
            id=user.id, full_name=user.full_name or user.email
        )

    @classmethod
    def _timeline(
        cls, infraction: Infraction
    ) -> list[InfractionTimelineEntryRead]:
        """Stages and contestations, merged and ordered by ``at``.

        One flat, discriminated list, so the frontend renders the history with
        no client-side merge and no second fetch.
        """
        entries: list[InfractionTimelineEntryRead] = [
            InfractionTimelineEntryRead(
                kind="STAGE",
                id=stage.id,
                at=stage.created_at,
                actor=cls._actor(stage.actor),
                action=stage.action,
                note=stage.note,
                fine_amount=stage.fine_amount,
                fine_amount_overridden=stage.fine_amount_overridden,
                defense_due_on=stage.defense_due_on,
                defense_deadline_overridden=stage.defense_deadline_overridden,
                policy_step_order=stage.policy_step_order,
                suggestion_followed=stage.suggestion_followed,
                attachment_urls=_load_urls(stage.evidence_urls_json),
            )
            for stage in cls._ordered_stages(infraction)
        ]
        entries.extend(
            InfractionTimelineEntryRead(
                kind="CONTESTATION",
                id=contestation.id,
                at=contestation.created_at,
                actor=cls._actor(contestation.submitted_by),
                note=contestation.body,
                attachment_urls=_load_urls(contestation.attachment_urls_json),
            )
            for contestation in infraction.contestations
        )
        entries.sort(key=lambda entry: (entry.at, entry.kind, str(entry.id)))
        return entries

    @classmethod
    def _source_protocols(
        cls, session: Session, infractions: Sequence[Infraction]
    ) -> dict[UUID, str]:
        """``occurrence_id -> protocol_number`` for a whole page, in one query.

        The list paths pass this to :meth:`_infraction_read` so the promotion
        protocol costs **one** statement per page instead of one per promoted
        row. Without it `_EAGER_RELATIONS` fixes five fan-outs and leaves a
        sixth, which is `9 + N` rather than the flat `9` the constant's own
        docstring claims.
        """
        wanted = {
            infraction.source_occurrence_id
            for infraction in infractions
            if infraction.source_occurrence_id is not None
        }
        if not wanted:
            return {}
        rows = session.exec(
            select(Occurrence.id, Occurrence.protocol_number).where(
                col(Occurrence.id).in_(wanted)
            )
        ).all()
        return dict(rows)

    @classmethod
    def _infraction_read(
        cls,
        session: Session,
        infraction: Infraction,
        protocols: dict[UUID, str] | None = None,
    ) -> InfractionRead:
        """One row, rendered.

        ``protocols`` is the page-wide map :meth:`_source_protocols` builds; the
        per-row ``session.get`` below is the **detail** path's answer, where one
        lookup for one row saves nothing worth batching.
        """
        current = cls._current_stage(infraction)
        protocol = None
        if infraction.source_occurrence_id is not None:
            if protocols is not None:
                protocol = protocols.get(infraction.source_occurrence_id)
            else:
                occurrence = session.get(
                    Occurrence, infraction.source_occurrence_id
                )
                if occurrence is not None:
                    protocol = occurrence.protocol_number
        return InfractionRead(
            id=infraction.id,
            rule=InfractionRuleSummaryRead.model_validate(infraction.rule),
            lot=LotSummaryRead.model_validate(infraction.lot),
            responsible=ResidentSummaryRead.model_validate(infraction.responsible),
            occurred_on=infraction.occurred_on,
            description=infraction.description,
            evidence_urls=_load_urls(infraction.evidence_urls_json),
            source_occurrence_id=infraction.source_occurrence_id,
            source_occurrence_protocol=protocol,
            current_stage=current.action if current is not None else None,
            current_stage_at=current.created_at if current is not None else None,
            defense_due_on=cls._defense_due_on(infraction),
            timeline=cls._timeline(infraction),
            created_at=infraction.created_at,
        )

    @staticmethod
    def _get_infraction(session: Session, infraction_id: UUID) -> Infraction:
        infraction = session.get(Infraction, infraction_id)
        if infraction is None:
            raise InfractionNotFoundError(infraction_id)
        return infraction

    @classmethod
    def get_infraction(
        cls, session: Session, infraction_id: UUID
    ) -> InfractionRead:
        return cls._infraction_read(
            session, cls._get_infraction(session, infraction_id)
        )

    # ------------------------------------------------------------------
    # Listing (§4.5)
    # ------------------------------------------------------------------

    #: The five relations :meth:`_infraction_read` reads for every row.
    #: Eager-loaded on the two list paths, because lazy-loading them is a
    #: fan-out: at ``limit=50`` they are 250 round trips for one page, and
    #: `selectinload` turns **these five** into five regardless of page size.
    #:
    #: They are not the whole list path, and the previous wording implied they
    #: were: the promotion protocol is a sixth read, batched separately by
    #: :meth:`_source_protocols`. Five relations plus one protocol query is
    #: what makes the page count flat in `N`;
    #: ``test_a_page_costs_a_constant_number_of_queries`` measures it rather
    #: than asserting it here.
    #:
    #: The detail path leaves all of them lazy on purpose -- one row, one
    #: relation each, and no query saved.
    _EAGER_RELATIONS = (
        selectinload(Infraction.rule),  # type: ignore[arg-type]
        selectinload(Infraction.lot),  # type: ignore[arg-type]
        selectinload(Infraction.responsible),  # type: ignore[arg-type]
        selectinload(Infraction.stages).selectinload(  # type: ignore[arg-type]
            InfractionStage.actor  # type: ignore[arg-type]
        ),
        selectinload(Infraction.contestations).selectinload(  # type: ignore[arg-type]
            InfractionContestation.submitted_by  # type: ignore[arg-type]
        ),
    )

    @staticmethod
    def _latest_stage_id_subquery():
        """The id of the latest stage of the correlated ``Infraction`` row.

        Ordered **exactly** as :meth:`_current_stage` orders it, because a
        filter that disagreed with the field it filters on would be worse than
        no filter. Evaluated by the database: neither branch materialises a
        Python list of ids and neither writes anything.
        """
        return (
            select(InfractionStage.id)
            .where(InfractionStage.infraction_id == Infraction.id)
            .order_by(
                col(InfractionStage.applied_on).desc(),
                col(InfractionStage.created_at).desc(),
                col(InfractionStage.id).desc(),
            )
            .limit(1)
            .correlate(Infraction)
            .scalar_subquery()
        )

    @classmethod
    def list_infractions(
        cls,
        session: Session,
        *,
        rule_id: UUID | None = None,
        lot_id: UUID | None = None,
        responsible_id: UUID | None = None,
        stage: InfractionStageFilter | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[InfractionRead], int]:
        """The management list. Present filters compose with ``AND``.

        ``total`` counts **after** every filter and **before** ``skip`` /
        ``limit``, and the order is ``created_at DESC, id DESC`` -- stable, so
        paging can neither skip nor repeat a row.
        """
        statement = select(Infraction)
        if rule_id is not None:
            statement = statement.where(Infraction.rule_id == rule_id)
        if lot_id is not None:
            statement = statement.where(Infraction.lot_id == lot_id)
        if responsible_id is not None:
            statement = statement.where(
                Infraction.responsible_resident_id == responsible_id
            )
        if date_from is not None:
            statement = statement.where(
                Infraction.created_at >= datetime.combine(date_from, time.min)
            )
        if date_to is not None:
            statement = statement.where(
                Infraction.created_at
                < datetime.combine(date_to + timedelta(days=1), time.min)
            )
        if stage is InfractionStageFilter.NONE:
            statement = statement.where(
                ~exists().where(InfractionStage.infraction_id == Infraction.id)
            )
        elif stage is not None:
            statement = statement.where(
                select(InfractionStage.action)
                .where(InfractionStage.id == cls._latest_stage_id_subquery())
                .scalar_subquery()
                == stage.value
            )

        total = session.exec(
            select(func.count()).select_from(statement.subquery())
        ).one()
        rows = session.exec(
            statement.order_by(
                col(Infraction.created_at).desc(), col(Infraction.id).desc()
            )
            .offset(skip)
            .limit(limit)
            .options(*cls._EAGER_RELATIONS)
        ).all()
        protocols = cls._source_protocols(session, rows)
        return (
            [cls._infraction_read(session, row, protocols) for row in rows],
            total,
        )

    @classmethod
    def list_my_lots_infractions(
        cls, session: Session, current_user: User
    ) -> list[InfractionRead]:
        """A **filter, never a refusal**: an unlinked caller gets ``[]``.

        The mirror is the *route shape* of ``GET /packages/my-lots``, not its
        inversion: ``PackageService.get_my_lots`` actively refuses the
        gatekeeper tiers, which is why ``packages:my_lots_read`` sits in
        ``ADMIN_GAP_PERMISSIONS``. This one narrows, so
        ``ADMIN_GAP_PERMISSIONS`` stays a one-element set and the matrix cell
        for the ADMINISTRATOR profile is a plain 200.
        """
        lot_ids = cls.linked_lot_ids(session, current_user)
        if not lot_ids:
            return []
        rows = session.exec(
            select(Infraction)
            .where(col(Infraction.lot_id).in_(lot_ids))
            .order_by(
                col(Infraction.created_at).desc(), col(Infraction.id).desc()
            )
            .options(*cls._EAGER_RELATIONS)
        ).all()
        protocols = cls._source_protocols(session, rows)
        return [cls._infraction_read(session, row, protocols) for row in rows]

    # ------------------------------------------------------------------
    # Creating (§7.7) and promoting (§7.4)
    # ------------------------------------------------------------------

    @classmethod
    def _assert_create_references(
        cls, session: Session, rule: InfractionRule, lot_id: UUID, resident_id: UUID
    ) -> Resident:
        """§7.7's two validations, in order, both 422.

        Two distinct details for the responsible check, not one: "belongs to
        another lot" and "is no longer an active resident" are different
        corrections for the person reading the message, and collapsing them
        would make the form say the wrong thing half the time.
        """
        if not rule.is_active:
            raise InfractionValidationError("The rule is not active")
        if session.get(Lot, lot_id) is None:
            raise InfractionValidationError("The lot does not exist")
        resident = session.get(Resident, resident_id)
        if resident is None or resident.lot_id != lot_id:
            raise InfractionValidationError(
                "The responsible resident does not belong to this lot"
            )
        if not resident.is_active:
            raise InfractionValidationError(
                "The responsible resident is not active on this lot"
            )
        return resident

    @classmethod
    def create_infraction(
        cls, session: Session, current_user: User, infraction_in: InfractionCreate
    ) -> InfractionRead:
        rule = cls._get_rule(session, infraction_in.rule_id)
        cls._assert_create_references(
            session,
            rule,
            infraction_in.lot_id,
            infraction_in.responsible_resident_id,
        )
        infraction = Infraction(
            rule_id=rule.id,
            lot_id=infraction_in.lot_id,
            responsible_resident_id=infraction_in.responsible_resident_id,
            registered_by_id=current_user.id,
            occurred_on=infraction_in.occurred_on,
            description=infraction_in.description,
            evidence_urls_json=_dump_urls(infraction_in.evidence_urls),
        )
        session.add(infraction)
        session.commit()
        session.refresh(infraction)
        return cls._infraction_read(session, infraction)

    @staticmethod
    def _effective_lot_id(
        occurrence: Occurrence, body_lot_id: UUID | None
    ) -> UUID:
        """§7.4's five-row table, as three branches.

        Both mismatches are **422 and not a silent override**: the promotion
        is an attribution of responsibility to a unit, and a caller who names
        a different unit from the one the occurrence records has either
        mis-clicked or is correcting the occurrence -- and correcting the
        occurrence is the occurrence module's job, not this route's.
        """
        if body_lot_id is None:
            if occurrence.lot_id is None:
                raise InfractionValidationError(
                    "The occurrence has no lot; lot_id is required"
                )
            return occurrence.lot_id
        if occurrence.lot_id is not None and occurrence.lot_id != body_lot_id:
            raise InfractionValidationError(
                "lot_id does not match the occurrence's lot"
            )
        return body_lot_id

    @classmethod
    def promote_occurrence(
        cls,
        session: Session,
        current_user: User,
        occurrence_id: UUID,
        promote_in: InfractionPromote,
    ) -> InfractionRead:
        """Turn an occurrence into an infraction, both ways navigable.

        The **same** occurrence may be promoted more than once -- one incident
        can breach two rules -- so the link is 1:N from the occurrence's side
        and nothing here refuses a second promotion.
        """
        occurrence = session.get(Occurrence, occurrence_id)
        if occurrence is None:
            raise OccurrenceNotFoundError(occurrence_id)

        rule = cls._get_rule(session, promote_in.rule_id)
        lot_id = cls._effective_lot_id(occurrence, promote_in.lot_id)
        cls._assert_create_references(
            session, rule, lot_id, promote_in.responsible_resident_id
        )

        infraction = Infraction(
            rule_id=rule.id,
            lot_id=lot_id,
            responsible_resident_id=promote_in.responsible_resident_id,
            source_occurrence_id=occurrence.id,
            registered_by_id=current_user.id,
            occurred_on=promote_in.occurred_on or occurrence.created_at.date(),
            description=promote_in.description or occurrence.description,
        )
        session.add(infraction)
        session.flush()

        # The occurrence module's own timeline shape, so the promotion is
        # visible where an occurrence's history already is.
        session.add(
            OccurrenceTimeline(
                occurrence_id=occurrence.id,
                actor_id=current_user.id,
                note=(
                    "Ocorrência promovida a infração "
                    f"({rule.origin.value}, {rule.article})"
                ),
                is_internal_only=False,
            )
        )
        occurrence.updated_at = datetime.utcnow()
        session.add(occurrence)
        session.commit()
        session.refresh(infraction)
        return cls._infraction_read(session, infraction)

    @staticmethod
    def infraction_ids_of_occurrence(
        session: Session, occurrence_id: UUID
    ) -> list[UUID]:
        """The occurrence side of the bidirectional link (ER-6).

        Read-only and additive, so no existing occurrence test changes.
        """
        return list(
            session.exec(
                select(Infraction.id)
                .where(Infraction.source_occurrence_id == occurrence_id)
                .order_by(col(Infraction.created_at).asc())
            ).all()
        )

    # ------------------------------------------------------------------
    # The suggestion algorithm (§6)
    # ------------------------------------------------------------------

    @classmethod
    def _cycle_closed_at(
        cls, session: Session, infraction: Infraction
    ) -> datetime | None:
        """The latest close of this ``(rule, responsible)`` **at or before**
        the infraction's own registration.

        The second half is what makes a close a cutoff going forward rather
        than a retroactive rewrite: an infraction that already existed when
        the cycle was closed keeps its count, its stages and its ladder index.
        ``lot_id`` is deliberately absent from the match (§6.2 property 5).
        """
        closes = session.exec(
            select(InfractionCycleClose).where(
                InfractionCycleClose.rule_id == infraction.rule_id,
                InfractionCycleClose.responsible_resident_id
                == infraction.responsible_resident_id,
                InfractionCycleClose.closed_at <= infraction.created_at,
            )
        ).all()
        return max((close.closed_at for close in closes), default=None)

    @classmethod
    def _recidivism_count(
        cls,
        session: Session,
        infraction: Infraction,
        window_start: date,
        cycle_closed_at: datetime | None,
    ) -> int:
        """§6.2's predicate, verbatim. ``lot_id`` is **absent** from it.

        The strict ``<`` on the date is symmetric on purpose: two infractions
        with the same ``occurred_on`` do not count each other, in either
        ordering. And every prior infraction counts regardless of how far its
        own process advanced -- requiring it to have reached some stage would
        make the count depend on staff diligence rather than on facts.
        """
        statement = select(func.count()).select_from(Infraction).where(
            Infraction.rule_id == infraction.rule_id,
            Infraction.responsible_resident_id
            == infraction.responsible_resident_id,
            Infraction.id != infraction.id,
            Infraction.occurred_on >= window_start,
            Infraction.occurred_on < infraction.occurred_on,
        )
        if cycle_closed_at is not None:
            statement = statement.where(Infraction.created_at > cycle_closed_at)
        return session.exec(statement).one()

    @classmethod
    def _price(
        cls, session: Session, step: InfractionPolicyStep | None
    ) -> tuple[float | None, str | None]:
        """``(amount, unavailable_reason)`` for one step (§6.3)."""
        if step is None or step.action is not InfractionStepAction.MULTA:
            return None, None
        if step.fine_mode is InfractionFineMode.FIXED:
            return step.fine_fixed_amount, None
        fee = cls._condo_fee(session)
        if fee is None:
            return None, CONDO_FEE_NOT_SET
        return round((step.fine_fee_multiplier or 0.0) * fee, 2), None

    @classmethod
    def suggest_next_step(
        cls, session: Session, infraction: Infraction
    ) -> NextStepReadSchema:
        """The whole of §6. Pure with respect to the database.

        ``ladder_index = recidivism_count + stages_applied + 1`` collapses the
        two escalations -- across infractions and within one process -- into
        one 1-based ordinal, and ``min(ladder_index, n)`` saturates it at the
        last step, because a condominium cannot run out of sanctions.
        """
        rule = infraction.rule
        steps = sorted(rule.steps, key=lambda step: step.step_order)
        steps_by_order = {step.step_order: step for step in steps}
        n = len(steps)

        window_start = infraction.occurred_on - timedelta(
            days=rule.recidivism_window_days
        )
        cycle_closed_at = cls._cycle_closed_at(session, infraction)
        recidivism_count = cls._recidivism_count(
            session, infraction, window_start, cycle_closed_at
        )
        stages_applied = len(infraction.stages)
        ladder_index = recidivism_count + stages_applied + 1

        if n == 0:
            return NextStepReadSchema(
                recidivism_count=recidivism_count,
                window_start=window_start,
                cycle_closed_at=cycle_closed_at,
                stages_applied=stages_applied,
                ladder_index=ladder_index,
                suggested_step_order=None,
                suggested_action=None,
                reason=NextStepReason.NO_POLICY,
                defense_deadline_days=None,
                fine_amount=None,
                # Not `CONDO_FEE_NOT_SET`: the fee is not the reason, there is
                # simply no step to price.
                fine_amount_unavailable_reason=None,
                # An absent ladder is not an exhausted one.
                is_saturated=False,
            )

        step = steps_by_order[min(ladder_index, n)]
        fine_amount, unavailable = cls._price(session, step)
        return NextStepReadSchema(
            recidivism_count=recidivism_count,
            window_start=window_start,
            cycle_closed_at=cycle_closed_at,
            stages_applied=stages_applied,
            ladder_index=ladder_index,
            suggested_step_order=step.step_order,
            suggested_action=step.action,
            # `CLAMPED` and `is_saturated` disagree at exactly
            # `ladder_index == n`: the last step *is* the suggestion --
            # saturated, but nothing was truncated.
            reason=(
                NextStepReason.CLAMPED
                if ladder_index > n
                else NextStepReason.SUGGESTED
            ),
            defense_deadline_days=step.defense_deadline_days,
            fine_amount=fine_amount,
            fine_amount_unavailable_reason=unavailable,
            is_saturated=ladder_index >= n,
        )

    @classmethod
    def next_step(
        cls, session: Session, infraction_id: UUID
    ) -> NextStepReadSchema:
        return cls.suggest_next_step(
            session, cls._get_infraction(session, infraction_id)
        )

    # ------------------------------------------------------------------
    # Advancing the process (§6.4, §6.5)
    # ------------------------------------------------------------------

    @staticmethod
    def _step_for_explicit_action(
        rule: InfractionRule, action: InfractionStepAction
    ) -> InfractionPolicyStep | None:
        """The rung an *off-ladder* action borrows its terms from.

        The spec leaves the pricing of an explicit action undeclared; this is
        the decision. An explicit ``MULTA`` or ``NOTIFICACAO`` that is not the
        suggestion still needs a value or a deadline, and there are only two
        honest sources: the request body, or the ladder's own **last** rung of
        the same action. The body wins; this is the fallback; when neither
        exists the field is simply ``null``, because ER-4 requires an explicit
        action to be **always accepted** -- a fine the policy never priced is a
        recorded fact, not a validation failure.
        """
        candidates = [step for step in rule.steps if step.action is action]
        if not candidates:
            return None
        return max(candidates, key=lambda step: step.step_order)

    @classmethod
    def add_stage(
        cls,
        session: Session,
        current_user: User,
        infraction_id: UUID,
        stage_in: InfractionStageCreate,
    ) -> InfractionRead:
        """Append one stage. Never edits, never deletes, never auto-advances."""
        infraction = cls._get_infraction(session, infraction_id)
        suggestion = cls.suggest_next_step(session, infraction)

        suggested_step = next(
            (
                step
                for step in infraction.rule.steps
                if step.step_order == suggestion.suggested_step_order
            ),
            None,
        )

        if stage_in.action is None:
            # "Apply the suggestion" -- and with no ladder there is none. 409
            # and not 422: the body is shape-valid, it is the world that has
            # no answer, exactly as the MULTA-without-a-fee case is a 409.
            if suggestion.suggested_action is None:
                raise InfractionStateError("Rule has no escalation policy")
            action = suggestion.suggested_action
            step = suggested_step
            # ER-4: only the accepted suggestion is a followed one.
            suggestion_followed = True
        else:
            # ER-4 and §6.5, read literally: **any** explicit action records
            # `suggestion_followed = False` and `policy_step_order = null`,
            # even when it happens to coincide with the suggestion. The point
            # of the field is "a human named this", not "the string differed".
            action = stage_in.action
            suggestion_followed = False
            # Where the terms come from, which is a separate question from
            # whether a human named the action. If the explicit action
            # **coincides** with the suggestion, the suggested rung is the
            # policy's own terms *for this position* and is the right source;
            # only a genuinely off-ladder action falls back to the last rung of
            # its own kind. A ladder with two MULTA rungs at different prices is
            # the shape where the difference is visible, and
            # `test_an_off_ladder_action_borrows_the_last_rung_of_its_own_kind`
            # is built on exactly that shape.
            step = (
                suggested_step
                if action is suggestion.suggested_action
                else cls._step_for_explicit_action(infraction.rule, action)
            )

        applied_on = date.today()
        fine_amount = None
        overridden = False
        if action is InfractionStepAction.MULTA:
            if stage_in.fine_amount is not None:
                fine_amount, overridden = stage_in.fine_amount, True
            else:
                fine_amount, unavailable = cls._price(session, step)
                if unavailable == CONDO_FEE_NOT_SET:
                    raise InfractionStateError(
                        "The condominium fee reference is not set"
                    )

        defense_due_on = None
        deadline_overridden = False
        if action is InfractionStepAction.NOTIFICACAO:
            if stage_in.defense_deadline_days is not None:
                days, deadline_overridden = stage_in.defense_deadline_days, True
            else:
                days = step.defense_deadline_days if step is not None else None
            if days is not None:
                defense_due_on = applied_on + timedelta(days=days)

        session.add(
            InfractionStage(
                infraction_id=infraction.id,
                action=action,
                applied_on=applied_on,
                note=stage_in.note,
                actor_id=current_user.id,
                fine_amount=fine_amount,
                fine_amount_overridden=overridden,
                defense_due_on=defense_due_on,
                defense_deadline_overridden=deadline_overridden,
                policy_step_order=(
                    step.step_order
                    if step is not None and suggestion_followed
                    else None
                ),
                suggestion_followed=suggestion_followed,
                evidence_urls_json=_dump_urls(stage_in.evidence_urls),
            )
        )
        infraction.updated_at = datetime.utcnow()
        session.add(infraction)
        session.commit()
        session.refresh(infraction)
        return cls._infraction_read(session, infraction)

    # ------------------------------------------------------------------
    # Contestation (§7.5)
    # ------------------------------------------------------------------

    @classmethod
    def add_contestation(
        cls,
        session: Session,
        current_user: User,
        infraction_id: UUID,
        contestation_in: ContestationCreate,
    ) -> InfractionRead:
        """404, then **403**, then 409, then 201 -- in that order.

        The order is the contract: an unlinked caller gets 403 even when the
        deadline has also passed, so the answer never leaks whether a
        neighbour's process has an open deadline.
        """
        infraction = cls._get_infraction(session, infraction_id)

        if infraction.lot_id not in cls.linked_lot_ids(session, current_user):
            raise InfractionContestationForbiddenError

        notification = next(
            (
                stage
                for stage in reversed(cls._ordered_stages(infraction))
                if stage.action is InfractionStepAction.NOTIFICACAO
            ),
            None,
        )
        if notification is None or notification.defense_due_on is None:
            raise InfractionStateError("No open defense deadline")
        if date.today() > notification.defense_due_on:
            raise InfractionStateError("The defense deadline has passed")

        session.add(
            InfractionContestation(
                infraction_id=infraction.id,
                stage_id=notification.id,
                body=contestation_in.body,
                attachment_urls_json=_dump_urls(contestation_in.attachment_urls),
                submitted_by_id=current_user.id,
            )
        )
        session.commit()
        session.refresh(infraction)
        return cls._infraction_read(session, infraction)

    # ------------------------------------------------------------------
    # Recidivism cycles (§6.2, ER-9)
    # ------------------------------------------------------------------

    @classmethod
    def list_cycle_closes(cls, session: Session) -> list[CycleCloseRead]:
        rows = session.exec(
            select(InfractionCycleClose).order_by(
                col(InfractionCycleClose.closed_at).desc()
            )
        ).all()
        return [
            CycleCloseRead(
                id=row.id,
                rule=InfractionRuleSummaryRead.model_validate(row.rule),
                responsible=ResidentSummaryRead.model_validate(row.responsible),
                lot_id=row.lot_id,
                justification=row.justification,
                closed_by=cls._actor(row.closed_by),
                closed_at=row.closed_at,
            )
            for row in rows
        ]

    @classmethod
    def close_cycle(
        cls, session: Session, current_user: User, close_in: CycleCloseCreate
    ) -> CycleCloseRead:
        """Record the cut. **Deletes nothing**, and there is no reset button.

        The legal addendum makes a reset unnecessary -- the count is personal,
        so a change of responsible resets it by construction -- and this route
        covers only the case the addendum names: a resident change not
        reflected in the cadastre in time.
        """
        if not close_in.justification.strip():
            raise InfractionValidationError("justification must not be empty")

        rule = cls._get_rule(session, close_in.rule_id)
        resident = session.get(Resident, close_in.responsible_resident_id)
        if resident is None:
            raise InfractionValidationError("The responsible resident does not exist")
        if close_in.lot_id is not None and session.get(Lot, close_in.lot_id) is None:
            raise InfractionValidationError("The lot does not exist")

        close = InfractionCycleClose(
            rule_id=rule.id,
            lot_id=close_in.lot_id,
            responsible_resident_id=resident.id,
            justification=close_in.justification,
            closed_by_id=current_user.id,
        )
        session.add(close)
        session.commit()
        session.refresh(close)
        return CycleCloseRead(
            id=close.id,
            rule=InfractionRuleSummaryRead.model_validate(rule),
            responsible=ResidentSummaryRead.model_validate(resident),
            lot_id=close.lot_id,
            justification=close.justification,
            closed_by=cls._actor(current_user),
            closed_at=close.closed_at,
        )
