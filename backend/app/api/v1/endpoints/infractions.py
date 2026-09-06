"""API endpoints for the infraction module (APRAS-44 §4).

Three routers in one file, all mounted ``TENANT_SCOPED``: the rule catalogue,
the module-settings singleton, and the infraction process. The settings
singleton gets its own mount because its two routes hang off the collection
path itself, which a prefix cannot express twice.

**Route declaration order is a correctness requirement, not style.**
``/my-lots``, ``/cycles``, ``/cycles/close`` and
``/from-occurrence/{occurrence_id}`` are declared *before* ``/{infraction_id}``
and its children, or FastAPI matches the literal segment as a UUID path
parameter and answers 422. This is the ``packages.py`` precedent, where
``/queue`` and ``/my-lots`` precede ``/{package_id}``, and a test pins it.

Every handler carries the route-level guard of **its own** permission. There
is no shared helper collapsing several permissions into one, and no role
comparison anywhere. The only object-dimension narrowing is in the service:
``/my-lots`` filters, the contestation refuses, and the cross-tenant case is
``tenant_context``'s loader criteria doing its job for free.
"""

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session

from app.api import deps
from app.models.enums import InfractionStageFilter
from app.models.user import User
from app.schemas.infraction import (
    ContestationCreate,
    CycleCloseCreate,
    CycleCloseRead,
    InfractionCreate,
    InfractionPolicyWrite,
    InfractionPromote,
    InfractionRead,
    InfractionRuleCreate,
    InfractionRuleRead,
    InfractionRuleUpdate,
    InfractionSettingsRead,
    InfractionSettingsWrite,
    InfractionStageCreate,
    NextStepRead,
    PaginatedInfractionRead,
)
from app.services.infraction_service import InfractionService

rules_router = APIRouter()
settings_router = APIRouter()
router = APIRouter()


# ---------------------------------------------------------------------------
# The rule catalogue -- /api/v1/infraction-rules
# ---------------------------------------------------------------------------


@rules_router.get("", response_model=list[InfractionRuleRead])
def list_infraction_rules(
    session: Annotated[Session, Depends(deps.get_session)],
    _guard: Annotated[User, Depends(deps.require_permission("infractions:rule_read"))],
) -> list[InfractionRuleRead]:
    """The tenant's catalogue, each rule with its ordered ladder.

    Deactivated rules are listed too, and deliberately: §4.5 makes the
    management list the *only* route in this module with query parameters, and
    the catalogue screen has to show what was withdrawn or the síndico cannot
    tell an absent article from a retired one.
    """
    return InfractionService.list_rules(session)


@rules_router.get("/{rule_id}", response_model=InfractionRuleRead)
def get_infraction_rule(
    rule_id: UUID,
    session: Annotated[Session, Depends(deps.get_session)],
    _guard: Annotated[User, Depends(deps.require_permission("infractions:rule_read"))],
) -> InfractionRuleRead:
    """One rule, deactivated ones included -- ER-4's navigable history."""
    return InfractionService.get_rule(session, rule_id)


@rules_router.post(
    "", response_model=InfractionRuleRead, status_code=status.HTTP_201_CREATED
)
def create_infraction_rule(
    rule_in: InfractionRuleCreate,
    session: Annotated[Session, Depends(deps.get_session)],
    _guard: Annotated[
        User, Depends(deps.require_permission("infractions:rule_create"))
    ],
) -> InfractionRuleRead:
    """Register an article. `(origin, article)` twice in one tenant is 409."""
    return InfractionService.create_rule(session, rule_in)


@rules_router.put("/{rule_id}", response_model=InfractionRuleRead)
def update_infraction_rule(
    rule_id: UUID,
    rule_in: InfractionRuleUpdate,
    session: Annotated[Session, Depends(deps.get_session)],
    _guard: Annotated[
        User, Depends(deps.require_permission("infractions:rule_update"))
    ],
) -> InfractionRuleRead:
    """Edit the catalogue entry. The ladder is written by its own route."""
    return InfractionService.update_rule(session, rule_id, rule_in)


@rules_router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_infraction_rule(
    rule_id: UUID,
    session: Annotated[Session, Depends(deps.get_session)],
    _guard: Annotated[
        User, Depends(deps.require_permission("infractions:rule_deactivate"))
    ],
) -> None:
    """Soft-deactivate. `rule_deactivate`, not `rule_delete`: infractions
    reference rules and the lot's history must stay whole and navigable."""
    InfractionService.deactivate_rule(session, rule_id)


@rules_router.put("/{rule_id}/policy", response_model=InfractionRuleRead)
def write_infraction_policy(
    rule_id: UUID,
    policy_in: InfractionPolicyWrite,
    session: Annotated[Session, Depends(deps.get_session)],
    _guard: Annotated[
        User, Depends(deps.require_permission("infractions:policy_update"))
    ],
) -> InfractionRuleRead:
    """Replace the escalation ladder whole (§4.4)."""
    return InfractionService.write_policy(session, rule_id, policy_in)


# ---------------------------------------------------------------------------
# The module settings singleton -- /api/v1/infraction-settings
# ---------------------------------------------------------------------------


@settings_router.get("", response_model=InfractionSettingsRead)
def read_infraction_settings(
    session: Annotated[Session, Depends(deps.get_session)],
    _guard: Annotated[User, Depends(deps.require_permission("infractions:rule_read"))],
) -> InfractionSettingsRead:
    """The condominium-fee reference. **Never 404s** (§5)."""
    return InfractionService.read_settings(session)


@settings_router.put("", response_model=InfractionSettingsRead)
def write_infraction_settings(
    settings_in: InfractionSettingsWrite,
    session: Annotated[Session, Depends(deps.get_session)],
    current_user: Annotated[
        User, Depends(deps.require_permission("infractions:settings_update"))
    ],
) -> InfractionSettingsRead:
    """Upsert the fee reference. `null` clears it."""
    return InfractionService.write_settings(session, current_user, settings_in)


# ---------------------------------------------------------------------------
# The process -- /api/v1/infractions
# ---------------------------------------------------------------------------
#
# The four literal-segment routes come first. See the module docstring.


@router.get("/my-lots", response_model=list[InfractionRead])
def list_my_lots_infractions(
    session: Annotated[Session, Depends(deps.get_session)],
    current_user: Annotated[
        User, Depends(deps.require_permission("infractions:my_lots_read"))
    ],
) -> list[InfractionRead]:
    """The resident's own short list. A filter, never a refusal: a caller with
    no linked lot gets `[]`, never a 403."""
    return InfractionService.list_my_lots_infractions(session, current_user)


@router.get("/cycles", response_model=list[CycleCloseRead])
def list_cycle_closes(
    session: Annotated[Session, Depends(deps.get_session)],
    _guard: Annotated[User, Depends(deps.require_permission("infractions:read"))],
) -> list[CycleCloseRead]:
    """The audit list of recidivism-cycle closes (ER-9)."""
    return InfractionService.list_cycle_closes(session)


@router.post(
    "/cycles/close",
    response_model=CycleCloseRead,
    status_code=status.HTTP_201_CREATED,
)
def close_cycle(
    close_in: CycleCloseCreate,
    session: Annotated[Session, Depends(deps.get_session)],
    current_user: Annotated[
        User, Depends(deps.require_permission("infractions:cycle_close"))
    ],
) -> CycleCloseRead:
    """Cut a `(rule, responsible)` cycle going forward. Deletes nothing."""
    return InfractionService.close_cycle(session, current_user, close_in)


@router.post(
    "/from-occurrence/{occurrence_id}",
    response_model=InfractionRead,
    status_code=status.HTTP_201_CREATED,
)
def promote_occurrence(
    occurrence_id: UUID,
    promote_in: InfractionPromote,
    session: Annotated[Session, Depends(deps.get_session)],
    current_user: Annotated[
        User, Depends(deps.require_permission("infractions:promote"))
    ],
) -> InfractionRead:
    """Promote an occurrence, resolving the effective lot (§7.4)."""
    return InfractionService.promote_occurrence(
        session, current_user, occurrence_id, promote_in
    )


@router.get("", response_model=PaginatedInfractionRead)
def list_infractions(
    session: Annotated[Session, Depends(deps.get_session)],
    _guard: Annotated[User, Depends(deps.require_permission("infractions:read"))],
    rule_id: UUID | None = Query(default=None),
    lot_id: UUID | None = Query(default=None),
    responsible_id: UUID | None = Query(default=None),
    stage: InfractionStageFilter | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> PaginatedInfractionRead:
    """The management list. Every parameter is optional; `stage` reads the
    **derived** current stage through a correlated subquery (§4.5)."""
    items, total = InfractionService.list_infractions(
        session,
        rule_id=rule_id,
        lot_id=lot_id,
        responsible_id=responsible_id,
        stage=stage,
        date_from=date_from,
        date_to=date_to,
        skip=skip,
        limit=limit,
    )
    return PaginatedInfractionRead(items=items, total=total, skip=skip, limit=limit)


@router.post(
    "", response_model=InfractionRead, status_code=status.HTTP_201_CREATED
)
def create_infraction(
    infraction_in: InfractionCreate,
    session: Annotated[Session, Depends(deps.get_session)],
    current_user: Annotated[
        User, Depends(deps.require_permission("infractions:create"))
    ],
) -> InfractionRead:
    """Register an infraction directly. `source_occurrence_id` stays `None`."""
    return InfractionService.create_infraction(session, current_user, infraction_in)


@router.get("/{infraction_id}", response_model=InfractionRead)
def get_infraction(
    infraction_id: UUID,
    session: Annotated[Session, Depends(deps.get_session)],
    _guard: Annotated[User, Depends(deps.require_permission("infractions:read"))],
) -> InfractionRead:
    """One process, with its merged timeline and its derived current stage."""
    return InfractionService.get_infraction(session, infraction_id)


@router.get("/{infraction_id}/next-step", response_model=NextStepRead)
def get_next_step(
    infraction_id: UUID,
    session: Annotated[Session, Depends(deps.get_session)],
    _guard: Annotated[User, Depends(deps.require_permission("infractions:read"))],
) -> NextStepRead:
    """The suggestion. A read: it never writes and never advances anything.
    An empty ladder answers **200** with `reason == "NO_POLICY"` (§6.5)."""
    return InfractionService.next_step(session, infraction_id)


@router.post(
    "/{infraction_id}/stages",
    response_model=InfractionRead,
    status_code=status.HTTP_201_CREATED,
)
def add_stage(
    infraction_id: UUID,
    stage_in: InfractionStageCreate,
    session: Annotated[Session, Depends(deps.get_session)],
    current_user: Annotated[
        User, Depends(deps.require_permission("infractions:advance"))
    ],
) -> InfractionRead:
    """Append one stage. `action = null` applies the suggestion; an explicit
    `action` is always accepted and records the deviation."""
    return InfractionService.add_stage(
        session, current_user, infraction_id, stage_in
    )


@router.post(
    "/{infraction_id}/contestation",
    response_model=InfractionRead,
    status_code=status.HTTP_201_CREATED,
)
def add_contestation(
    infraction_id: UUID,
    contestation_in: ContestationCreate,
    session: Annotated[Session, Depends(deps.get_session)],
    current_user: Annotated[
        User, Depends(deps.require_permission("infractions:contest"))
    ],
) -> InfractionRead:
    """The notified unit's written defense. Holding the permission gets you to
    the route; being linked to the lot gets you past it (§7.5)."""
    return InfractionService.add_contestation(
        session, current_user, infraction_id, contestation_in
    )
