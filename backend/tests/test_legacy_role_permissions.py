"""`LEGACY_ROLE_PERMISSIONS` is derived from the live guards (APRAS-45 §6).

The transitional map must never be a hand copy. Every catalogue permission
declares exactly one **parity source** — a `RoleSet` / `RoleSetComplement`
pointing at the production role-set constant, a `Guard` probing the
production callable, a `Composite` of those, or (only where production offers
neither) an allowlisted `Literal`. The map is then asserted against what the
source says, permission by permission, role by role. Edit a production guard
and this module fails; edit the map alone and it fails too.

Sources are **lazy** (`Callable[[ParityWorld], Source]`): several `Guard`
probes need database rows, so a `Source` cannot be built at import time.

The fixture world is normative (§6.5), not incidental: probe
`ResidentService._check_lot_access` with an unlinked user and `residents:read`
collapses from ALL to `{A, D, M}`; probe
`VisitorService.get_authorization_for_user` with an id that resolves to
nothing and `authorizations:gate_lookup` collapses to the empty set, because
the row lookup runs *before* the role check. `ParityWorld` seeds the most
favourable object situation so the only remaining denial is the
role-dimension denial being measured.
"""

# This module deliberately reaches into production's private guards and
# role-set constants: pointing at the real objects is the entire mechanism
# that makes the map derived rather than typed twice. A probe likewise has to
# treat *any* exception as a denial, because production guards raise a dozen
# different domain errors.
# ruff: noqa: SLF001, BLE001

import inspect
import itertools
import uuid
from collections.abc import Callable, Collection
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from functools import partial

import pytest
from sqlmodel import Session, select

from app.api import deps
from app.api.v1.endpoints import (
    access_logs,
)
from app.api.v1.endpoints import (
    announcements as announcements_endpoint,
)
from app.api.v1.endpoints import (
    authorizations as authorizations_endpoint,
)
from app.api.v1.endpoints import (
    categories as categories_endpoint,
)
from app.api.v1.endpoints import (
    documents as documents_endpoint,
)
from app.api.v1.endpoints import (
    finance as finance_endpoint,
)
from app.api.v1.endpoints import (
    lots as lots_endpoint,
)
from app.api.v1.endpoints import (
    occurrences as occurrences_endpoint,
)
from app.api.v1.endpoints import (
    projects as projects_endpoint,
)
from app.api.v1.endpoints import (
    reservations as reservations_endpoint,
)
from app.api.v1.endpoints import (
    residents as residents_endpoint,
)
from app.api.v1.endpoints import (
    voting as voting_endpoint,
)
from app.core import permissions as permissions_module
from app.core.permissions import (
    LEGACY_MAP_REMOVAL_SLICE,
    LEGACY_ROLE_PERMISSIONS,
    PERMISSIONS,
)
from app.models.enums import (
    AuthorizationStatus,
    EntityType,
    FeedbackCategory,
    PhotoApprovalStatus,
    StorageProvider,
    UserRole,
    VoteKind,
    VoteStatus,
    VoteType,
)
from app.models.feedback import Feedback
from app.models.lot import Lot, UserLotLink
from app.models.media_asset import MediaAsset
from app.models.resident import Resident
from app.models.task import Task
from app.models.tenant import DEFAULT_TENANT_ID, Tenant, UserTenantLink
from app.models.user import User
from app.models.visitor import Visitor, VisitorAuthorization
from app.models.voting import Vote
from app.schemas.feedback import FeedbackRespond
from app.services import (
    access_control_service,
    announcement_service,
    asset_service,
    document_service,
    purchase_service,
    reservation_service,
    voting_service,
)
from app.services.feedback_service import FeedbackService
from app.services.media_service import MediaService
from app.services.package_service import PackageService
from app.services.resident_service import ResidentService
from app.services.storage_service import BaseStorageProvider
from app.services.visitor_service import VisitorService

A = UserRole.ADMINISTRATOR
D = UserRole.DIRECTOR
M = UserRole.MANAGER
G = UserRole.GUEST
R = UserRole.RESIDENT
P = UserRole.PORTEIRO
ALL_SIX = frozenset(UserRole)


# ---------------------------------------------------------------------------
# Source taxonomy (§6.3)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RoleSet:
    """expected == set(roles_obj); `roles_obj` is the PRODUCTION object."""

    roles_obj: Collection[UserRole]


@dataclass(frozen=True)
class RoleSetComplement:
    """expected == set(UserRole) - set(roles_obj), for gates defined by exclusion."""

    roles_obj: Collection[UserRole]


@dataclass(frozen=True)
class Guard:
    """expected == the roles for which the PRODUCTION callable does not raise."""

    probe: Callable[[User], object]


@dataclass(frozen=True)
class Composite:
    """expected == the intersection of the parts' expected sets."""

    parts: tuple[object, ...]


@dataclass(frozen=True)
class Literal:
    """expected == roles. Only where production offers nothing to read."""

    roles: frozenset[UserRole]
    reason: str


#: Deliberately not a `|` union type alias: the taxonomy is checked with
#: `isinstance` in several assertions and read as data in others.
LIVE_SOURCE_TYPES = (RoleSet, RoleSetComplement, Guard)


# ---------------------------------------------------------------------------
# The fixture world (§6.5)
# ---------------------------------------------------------------------------


class _NullStorage(BaseStorageProvider):
    """The production `MediaService`, with its file system amputated.

    Injected through the constructor parameter that already exists for it
    (`media_service.py:29-30`), so the `Guard` still reads live production
    logic and the parity test touches no disk.
    """

    def save_file(self, file_bytes, filename, mime_type):  # noqa: ARG002
        return f"/dev/null/{filename}", f"http://null/{filename}"

    def delete_file(self, file_path):  # noqa: ARG002
        return None


@dataclass(frozen=True)
class ParityWorld:
    """The most favourable object graph, enumerated by §6.5(b)."""

    session: Session
    tenant: Tenant
    users: dict[UserRole, User]
    lot: Lot
    visitor: Visitor
    authorization: VisitorAuthorization
    vote: Vote
    task: Task
    media: MediaService
    _counter: itertools.count = field(default_factory=lambda: itertools.count(1))

    def new_feedback(self) -> Feedback:
        """A fresh PENDING feedback row: `respond_to_feedback` commits."""
        row = Feedback(
            reporter_user_id=self.users[R].id,
            category=FeedbackCategory.SUGGESTION,
            message=f"parity probe {next(self._counter)}",
        )
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return row

    def new_media_asset(self, role: UserRole) -> MediaAsset:
        """A fresh PENDING photo owned by `role`: the owner branch is the point."""
        row = MediaAsset(
            entity_type=EntityType.RESIDENT,
            storage_provider=StorageProvider.LOCAL_DISK,
            file_path=f"/dev/null/parity-{next(self._counter)}.jpg",
            url="http://null/parity.jpg",
            file_size_bytes=1,
            mime_type="image/jpeg",
            status=PhotoApprovalStatus.PENDING_APPROVAL,
            uploaded_by_id=self.users[role].id,
        )
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return row


def _build_world(session: Session, tenant: Tenant) -> ParityWorld:
    users: dict[UserRole, User] = {}
    for index, role in enumerate(UserRole):
        user = User(
            id=uuid.uuid4(),
            email=f"{role.value.lower()}@parity.test",
            full_name=f"{role.value} Parity",
            hashed_password="hash",
            role=role,
            cpf=str(index + 1).zfill(11),
        )
        session.add(user)
        users[role] = user
    session.commit()

    for user in users.values():
        session.add(
            UserTenantLink(
                user_id=user.id,
                tenant_id=DEFAULT_TENANT_ID,
                is_tenant_admin=False,
            )
        )
    session.commit()

    lot = Lot(block="A", lot_number="1")
    session.add(lot)
    session.commit()
    session.refresh(lot)

    for index, (role, user) in enumerate(users.items()):
        # Open-ended dates are what make `_is_link_active` true *now*.
        session.add(
            UserLotLink(
                user_id=user.id, lot_id=lot.id, start_date=None, end_date=None
            )
        )
        session.add(
            Resident(
                lot_id=lot.id,
                user_id=user.id,
                full_name=f"{role.value} Resident",
                cpf=str(100 + index).zfill(11),
                is_active=True,
            )
        )
    session.commit()

    visitor = Visitor(full_name="Parity Visitor")
    session.add(visitor)
    session.commit()
    session.refresh(visitor)

    authorization = VisitorAuthorization(
        visitor_id=visitor.id,
        lot_id=lot.id,
        authorizer_user_id=users[A].id,
        status=AuthorizationStatus.ACTIVE,
    )
    session.add(authorization)

    vote = Vote(
        kind=VoteKind.ENQUETE,
        title="Parity poll",
        vote_type=VoteType.SINGLE_CHOICE,
        status=VoteStatus.OPEN,
        # Naive UTC, exactly as production writes it (`datetime.utcnow()`
        # throughout `voting_service`); an aware value would not compare.
        closes_at=datetime.utcnow() + timedelta(days=7),  # noqa: DTZ003
        created_by_id=users[A].id,
    )
    session.add(vote)

    # `visible_to=[]` is visible to every MANAGER; `assigned_to_id=None`
    # means a MANAGER may edit it. Any other task silently drops M from
    # tasks:read / tasks:update / tasks:comment.
    task = Task(title="Parity task", created_by_id=users[A].id, assigned_to_id=None)
    session.add(task)
    session.commit()
    session.refresh(authorization)
    session.refresh(vote)
    session.refresh(task)

    return ParityWorld(
        session=session,
        tenant=tenant,
        users=users,
        lot=lot,
        visitor=visitor,
        authorization=authorization,
        vote=vote,
        task=task,
        media=MediaService(storage_provider=_NullStorage()),
    )


@pytest.fixture
def parity_world(session: Session, default_tenant: Tenant):
    """One fresh world per case, asserting its invariant core on teardown.

    The session is the existing `tests/conftest.py::session` fixture, never
    request-scoped and never given an acting tenant. That is load-bearing:
    `deps.is_acting_tenant_admin` has no `DEFAULT_TENANT_ID` fallback, so
    here `has_admin_capability` reduces to `role == ADMINISTRATOR` and
    `get_current_tenant_admin` resolves to `{A}` — the role dimension and
    nothing else.
    """
    world = _build_world(session, default_tenant)
    yield world

    # A probe that mutated the shared graph instead of its own factory row
    # fails the case that caused it, by name.
    session.rollback()
    for role, user in world.users.items():
        assert session.get(User, user.id) is not None, f"{role} user vanished"
        assert (
            session.get(UserLotLink, _link_id(session, user.id, world.lot.id))
            is not None
        ), f"{role} lot link vanished"
    lot = session.get(Lot, world.lot.id)
    task = session.get(Task, world.task.id)
    vote = session.get(Vote, world.vote.id)
    authorization = session.get(VisitorAuthorization, world.authorization.id)
    assert lot is not None
    assert vote is not None
    assert task is not None
    assert task.visible_to == []
    assert task.assigned_to_id is None
    assert authorization is not None
    assert authorization.status != AuthorizationStatus.REVOKED


def _link_id(session: Session, user_id: uuid.UUID, lot_id: uuid.UUID):
    link = session.exec(
        select(UserLotLink).where(
            UserLotLink.user_id == user_id, UserLotLink.lot_id == lot_id
        )
    ).first()
    return link.id if link else None


# ---------------------------------------------------------------------------
# The parity sources — one per catalogue permission (§6.3)
# ---------------------------------------------------------------------------

_NO_ROLE_GATE = "no role gate on {}"

_UNGUARDED_LITERALS: dict[str, str] = {
    "categories:read": "endpoints/categories.py::read_categories",
    "users:read": "endpoints/users.py::read_users",
    "user_types:read": "endpoints/user_types.py::read_user_types",
    "tenants:read": "endpoints/tenants.py::list_tenants / get_tenant",
    "tenants:members_read": "endpoints/tenants.py::list_tenant_members",
    "visitors:read": "endpoints/visitors.py::list_visitors / get_visitor",
    "visitors:create": "endpoints/visitors.py::create_visitor",
    "visitors:update": "endpoints/visitors.py::update_visitor",
    "feedback:read": "endpoints/feedback.py::list_feedback / get_feedback",
    "feedback:create": "endpoints/feedback.py::create_feedback",
    "spaces:read": "endpoints/reservations.py::list_reservable_spaces",
    "uploads:photo_create": "endpoints/uploads.py::upload_photo",
    "uploads:photo_read": "endpoints/uploads.py::get_photo",
}

#: §6.3 — the complete permitted `Literal` list: the 13 unguarded permissions
#: of §11.4 plus the three inline gates named in §4.
LITERAL_ALLOWLIST: frozenset[str] = frozenset(_UNGUARDED_LITERALS) | {
    "tasks:create",
    "tasks:read",
    "announcements:comment",
}

#: §6.2 — the 17 permissions that resolve to all six roles, pinned by exact
#: match so a route that quietly widens, or a §6.5 binding that accidentally
#: narrows one of the two lot-linkage rows, fails CI with a named diff.
ALL_SIX_ROLE_PERMISSIONS: frozenset[str] = frozenset(_UNGUARDED_LITERALS) | {
    "gate:logs_read",
    "uploads:delete",
    "residents:read",
    "authorizations:gate_lookup",
}

#: Permissions ADMINISTRATOR does NOT hold. Every entry needs a comment
#: naming the production gate that excludes it.
ADMIN_GAP_PERMISSIONS: frozenset[str] = frozenset(
    {
        # PackageService.get_my_lots raises for _GATEKEEPER_ROLES (incl.
        # ADMINISTRATOR): staff use GET /packages/queue instead.
        "packages:my_lots_read",
    }
)

#: Every module-level role-set constant a `RoleSet` source may point at,
#: named rather than captured, so `test_role_set_sources_are_production_objects`
#: resolves them live.
PRODUCTION_ROLE_SET_ATTRS: tuple[tuple[object, str], ...] = (
    (categories_endpoint, "_CATEGORY_WRITE_ROLES"),
    (lots_endpoint, "_LOT_READ_ROLES"),
    (lots_endpoint, "_LOT_WRITE_ROLES"),
    (finance_endpoint, "_FINANCE_READ_ROLES"),
    (finance_endpoint, "_FINANCE_ADMIN_ROLES"),
    (finance_endpoint, "_FINANCE_WRITE_ROLES"),
    (projects_endpoint, "_PROJECT_READ_ROLES"),
    (projects_endpoint, "_PROJECT_ADMIN_ROLES"),
    (projects_endpoint, "_PROJECT_UPDATE_ROLES"),
    (reservations_endpoint, "_SPACE_WRITE_ROLES"),
    (reservation_service, "_STAFF_ROLES"),
    (asset_service, "_VIEW_ROLES"),
    (asset_service, "_STAFF_ROLES"),
    (purchase_service, "_VIEW_ROLES"),
    (purchase_service, "_WRITE_ROLES"),
    (purchase_service, "_DECIDE_ROLES"),
    (voting_service, "BOARD_ROLES"),
    (voting_service, "NON_VOTING_ROLES"),
)


def _unguarded(permission: str) -> Callable[[ParityWorld], Literal]:
    where = _UNGUARDED_LITERALS[permission]
    return lambda _w: Literal(ALL_SIX, reason=_NO_ROLE_GATE.format(where))


def _tenant_admin(w: ParityWorld) -> Guard:
    """`deps.get_current_tenant_admin` — `{A}` on a session with no tenant."""
    return Guard(partial(deps.get_current_tenant_admin, w.session, _tenant=w.tenant))


def _tenant_admin_or_manager(w: ParityWorld) -> Guard:
    return Guard(
        partial(deps.get_current_tenant_admin_or_manager, w.session, _tenant=w.tenant)
    )


def _global_admin(_w: ParityWorld) -> Guard:
    return Guard(deps.get_current_active_admin)


PARITY_SOURCES: dict[str, Callable[[ParityWorld], object]] = {
    # ---------------------------------------------------------------- tasks
    "tasks:read": lambda w: Composite(
        (
            Guard(
                partial(
                    deps.assert_manager_can_see_task, task=w.task, session=w.session
                )
            ),
            Literal(
                ALL_SIX - {G},
                reason="inline `role == GUEST` returns [] in endpoints/tasks.py::list_tasks",
            ),
        )
    ),
    "tasks:create": lambda _w: Literal(
        ALL_SIX - {G},
        reason="inline `role == GUEST` in endpoints/tasks.py::create_task",
    ),
    "tasks:update": lambda w: Guard(partial(deps.assert_can_edit_task, task=w.task)),
    "tasks:delete": _tenant_admin,
    "tasks:comment": lambda w: Guard(partial(deps.assert_can_edit_task, task=w.task)),
    # ----------------------------------------------------------- categories
    "categories:read": _unguarded("categories:read"),
    "categories:create": lambda _w: RoleSet(
        categories_endpoint._CATEGORY_WRITE_ROLES
    ),
    "categories:update": lambda _w: RoleSet(
        categories_endpoint._CATEGORY_WRITE_ROLES
    ),
    "categories:delete": lambda _w: RoleSet(
        categories_endpoint._CATEGORY_WRITE_ROLES
    ),
    # ---------------------------------------------------------------- users
    "users:read": _unguarded("users:read"),
    "users:update": _tenant_admin,
    "users:update_contact": _tenant_admin_or_manager,
    # ----------------------------------------------------------- user_types
    "user_types:read": _unguarded("user_types:read"),
    "user_types:create": _tenant_admin,
    "user_types:update": _tenant_admin,
    "user_types:delete": _tenant_admin,
    # -------------------------------------------------------------- tenants
    "tenants:read": _unguarded("tenants:read"),
    "tenants:create": _global_admin,
    "tenants:update": _global_admin,
    "tenants:members_read": _unguarded("tenants:members_read"),
    "tenants:members_manage": _global_admin,
    "tenants:members_set_admin": _global_admin,
    # ----------------------------------------------------------------- lots
    "lots:read": lambda _w: RoleSet(lots_endpoint._LOT_READ_ROLES),
    "lots:create": lambda _w: RoleSet(lots_endpoint._LOT_WRITE_ROLES),
    "lots:update": lambda _w: RoleSet(lots_endpoint._LOT_WRITE_ROLES),
    "lots:delete": _tenant_admin,
    "lots:link_user": lambda _w: RoleSet(lots_endpoint._LOT_WRITE_ROLES),
    "lots:unlink_user": lambda _w: RoleSet(lots_endpoint._LOT_WRITE_ROLES),
    "lots:set_delinquency": lambda _w: RoleSet(voting_service.BOARD_ROLES),
    # ------------------------------------------------------------ residents
    "residents:read": lambda w: Guard(
        partial(ResidentService._check_lot_access, w.session, w.lot.id)
    ),
    "residents:create": lambda _w: Guard(residents_endpoint.assert_admin_or_director),
    "residents:update": lambda _w: Guard(residents_endpoint.assert_admin_or_director),
    "residents:delete": lambda _w: Guard(residents_endpoint.assert_admin_or_director),
    "residents:link_user": lambda _w: Guard(
        residents_endpoint.assert_admin_or_director
    ),
    "residents:unlink_user": lambda _w: Guard(
        residents_endpoint.assert_admin_or_director
    ),
    # ------------------------------------------------------------- visitors
    "visitors:read": _unguarded("visitors:read"),
    "visitors:create": _unguarded("visitors:create"),
    "visitors:update": _unguarded("visitors:update"),
    # ------------------------------------------------------- authorizations
    "authorizations:read": lambda _w: Guard(
        authorizations_endpoint._assert_not_porteiro
    ),
    "authorizations:create": lambda _w: Guard(
        authorizations_endpoint._assert_not_porteiro
    ),
    "authorizations:revoke": lambda _w: Guard(
        authorizations_endpoint._assert_not_porteiro
    ),
    "authorizations:gate_lookup": lambda w: Guard(
        partial(
            VisitorService.get_authorization_for_user, w.session, w.authorization.id
        )
    ),
    # ----------------------------------------------------------------- gate
    "gate:checkin": lambda _w: Guard(access_logs._assert_gatekeeper_access),
    "gate:checkout": lambda _w: Guard(access_logs._assert_gatekeeper_access),
    # `lot_id=None` is the most favourable object situation: the service
    # narrows the query instead of refusing, so no role raises (§4.10).
    "gate:logs_read": lambda w: Guard(
        partial(VisitorService.get_access_logs, w.session, lot_id=None)
    ),
    # ---------------------------------------------------------- occurrences
    "occurrences:read": lambda _w: Guard(occurrences_endpoint._assert_not_porteiro),
    "occurrences:create": lambda _w: Guard(occurrences_endpoint._assert_not_porteiro),
    "occurrences:update_status": lambda _w: Guard(
        occurrences_endpoint._assert_not_porteiro
    ),
    "occurrences:add_note": lambda _w: Guard(
        occurrences_endpoint._assert_not_porteiro
    ),
    # ------------------------------------------------------------ documents
    "documents:read": lambda _w: Guard(documents_endpoint._assert_not_porteiro),
    "documents:create": lambda _w: Guard(document_service._check_admin_or_director),
    "documents:delete": lambda _w: Guard(document_service._check_admin_or_director),
    "documents:download": lambda _w: Guard(documents_endpoint._assert_not_porteiro),
    "documents:version_create": lambda _w: Guard(
        document_service._check_admin_or_director
    ),
    "documents:folder_read": lambda _w: Guard(documents_endpoint._assert_not_porteiro),
    "documents:folder_create": lambda _w: Guard(
        document_service._check_admin_or_director
    ),
    "documents:folder_update": lambda _w: Guard(
        document_service._check_admin_or_director
    ),
    "documents:folder_delete": lambda _w: Guard(
        document_service._check_admin_or_director
    ),
    # ---------------------------------------------------- assemblies & votes
    "assemblies:read": lambda _w: Guard(voting_endpoint._require_voting_access),
    "assemblies:create": lambda _w: Guard(voting_service._assert_board),
    "assemblies:update": lambda _w: Guard(voting_service._assert_board),
    "assemblies:close": lambda _w: Guard(voting_service._assert_board),
    "assemblies:minutes_read": lambda _w: Guard(voting_service._assert_board),
    "assemblies:minutes_save": lambda _w: Guard(voting_service._assert_board),
    "votes:read": lambda _w: Guard(voting_endpoint._require_voting_access),
    "votes:create": lambda _w: Guard(
        partial(voting_service._assert_can_create_vote, kind=VoteKind.ENQUETE)
    ),
    "votes:update": lambda _w: Guard(
        partial(voting_service._assert_can_create_vote, kind=VoteKind.ENQUETE)
    ),
    "votes:close": lambda _w: Guard(
        partial(voting_service._assert_can_create_vote, kind=VoteKind.ENQUETE)
    ),
    "votes:cast": lambda _w: RoleSetComplement(voting_service.NON_VOTING_ROLES),
    "votes:retract": lambda _w: RoleSetComplement(voting_service.NON_VOTING_ROLES),
    "votes:tally_read": lambda w: Guard(
        partial(voting_service._assert_can_view_tally, w.session, vote=w.vote)
    ),
    "votes:my_ballot_read": lambda _w: Guard(voting_endpoint._require_voting_access),
    "votes:eligible_lots_read": lambda _w: Guard(
        voting_endpoint._require_voting_access
    ),
    "votes:eligibility_read": lambda _w: Guard(
        voting_service._assert_can_manage_eligibility
    ),
    "votes:eligibility_manage": lambda _w: Guard(
        voting_service._assert_can_manage_eligibility
    ),
    # -------------------------------------------------------------- finance
    "finance:read": lambda _w: RoleSet(finance_endpoint._FINANCE_READ_ROLES),
    "finance:category_create": lambda _w: RoleSet(
        finance_endpoint._FINANCE_ADMIN_ROLES
    ),
    "finance:category_update": lambda _w: RoleSet(
        finance_endpoint._FINANCE_ADMIN_ROLES
    ),
    "finance:budget_create": lambda _w: RoleSet(finance_endpoint._FINANCE_ADMIN_ROLES),
    "finance:budget_update": lambda _w: RoleSet(finance_endpoint._FINANCE_ADMIN_ROLES),
    "finance:budget_delete": lambda _w: RoleSet(finance_endpoint._FINANCE_ADMIN_ROLES),
    "finance:transaction_create": lambda _w: RoleSet(
        finance_endpoint._FINANCE_WRITE_ROLES
    ),
    "finance:transaction_update": lambda _w: RoleSet(
        finance_endpoint._FINANCE_WRITE_ROLES
    ),
    "finance:transaction_delete": lambda _w: RoleSet(
        finance_endpoint._FINANCE_ADMIN_ROLES
    ),
    "finance:invoice_upload": lambda _w: RoleSet(
        finance_endpoint._FINANCE_WRITE_ROLES
    ),
    "finance:invoice_delete": lambda _w: RoleSet(
        finance_endpoint._FINANCE_WRITE_ROLES
    ),
    # ------------------------------------------------------------- projects
    "projects:read": lambda _w: RoleSet(projects_endpoint._PROJECT_READ_ROLES),
    "projects:create": lambda _w: RoleSet(projects_endpoint._PROJECT_ADMIN_ROLES),
    "projects:update": lambda _w: RoleSet(projects_endpoint._PROJECT_ADMIN_ROLES),
    "projects:delete": lambda _w: RoleSet(projects_endpoint._PROJECT_ADMIN_ROLES),
    "projects:milestone_create": lambda _w: RoleSet(
        projects_endpoint._PROJECT_ADMIN_ROLES
    ),
    "projects:milestone_update": lambda _w: RoleSet(
        projects_endpoint._PROJECT_ADMIN_ROLES
    ),
    "projects:milestone_delete": lambda _w: RoleSet(
        projects_endpoint._PROJECT_ADMIN_ROLES
    ),
    "projects:update_create": lambda _w: RoleSet(
        projects_endpoint._PROJECT_UPDATE_ROLES
    ),
    "projects:update_delete": lambda _w: RoleSet(
        projects_endpoint._PROJECT_ADMIN_ROLES
    ),
    # -------------------------------------------------------- announcements
    "announcements:read": lambda _w: Guard(
        announcements_endpoint._assert_not_porteiro
    ),
    "announcements:create": lambda _w: Guard(announcement_service._check_publisher),
    "announcements:update": lambda _w: Guard(announcement_service._check_publisher),
    "announcements:delete": lambda _w: Guard(announcement_service._check_publisher),
    "announcements:media_upload": lambda _w: Guard(
        announcement_service._check_publisher
    ),
    "announcements:media_delete": lambda _w: Guard(
        announcement_service._check_publisher
    ),
    "announcements:comment": lambda _w: Composite(
        (
            Guard(announcements_endpoint._assert_not_porteiro),
            Literal(
                ALL_SIX - {G},
                reason="inline GUEST rejection in announcement_service.add_comment",
            ),
        )
    ),
    "announcements:comment_delete": lambda _w: Guard(
        announcements_endpoint._assert_not_porteiro
    ),
    "announcements:mark_read": lambda _w: Guard(
        announcements_endpoint._assert_not_porteiro
    ),
    "announcements:read_receipts_read": lambda _w: Guard(
        announcement_service._check_publisher
    ),
    # ------------------------------------------------------------- feedback
    "feedback:read": _unguarded("feedback:read"),
    "feedback:create": _unguarded("feedback:create"),
    "feedback:respond": lambda w: Guard(
        lambda user: FeedbackService.respond_to_feedback(
            w.session,
            user,
            w.new_feedback().id,
            FeedbackRespond(board_response="resposta"),
        )
    ),
    # ------------------------------------------- spaces & reservations
    "spaces:read": _unguarded("spaces:read"),
    "spaces:create": lambda _w: RoleSet(reservations_endpoint._SPACE_WRITE_ROLES),
    "spaces:update": lambda _w: RoleSet(reservations_endpoint._SPACE_WRITE_ROLES),
    "spaces:deactivate": lambda _w: RoleSet(reservations_endpoint._SPACE_WRITE_ROLES),
    "reservations:read": lambda _w: Guard(reservations_endpoint._require_non_guest),
    "reservations:create": lambda _w: Guard(reservations_endpoint._require_non_guest),
    "reservations:approve": lambda _w: RoleSet(reservation_service._STAFF_ROLES),
    "reservations:reject": lambda _w: RoleSet(reservation_service._STAFF_ROLES),
    "reservations:cancel": lambda _w: Guard(reservations_endpoint._require_non_guest),
    # ------------------------------------------------------------- packages
    "packages:read": lambda w: Guard(
        partial(PackageService._assert_lot_access, w.session, w.lot.id)
    ),
    "packages:create": lambda _w: Guard(PackageService._assert_gatekeeper_role),
    "packages:pickup": lambda w: Guard(
        partial(PackageService._assert_lot_access, w.session, w.lot.id)
    ),
    "packages:queue_read": lambda _w: Guard(PackageService._assert_gatekeeper_role),
    # Inverted gate: no favourable binding changes this, the gate reads
    # `role` and nothing else (§4.19).
    "packages:my_lots_read": lambda w: Guard(
        partial(PackageService.get_my_lots, w.session)
    ),
    # --------------------------------------------------- assets & inventory
    "assets:read": lambda _w: RoleSet(asset_service._VIEW_ROLES),
    "assets:summary_read": lambda _w: RoleSet(asset_service._VIEW_ROLES),
    "assets:create": lambda _w: RoleSet(asset_service._STAFF_ROLES),
    "assets:update": lambda _w: RoleSet(asset_service._STAFF_ROLES),
    "assets:delete": lambda _w: RoleSet(asset_service._STAFF_ROLES),
    "assets:movement_record": lambda _w: RoleSet(asset_service._VIEW_ROLES),
    "inventory:movements_read": lambda _w: RoleSet(asset_service._VIEW_ROLES),
    # ------------------------------------------------------------ purchases
    "purchases:read": lambda _w: RoleSet(purchase_service._VIEW_ROLES),
    "purchases:summary_read": lambda _w: RoleSet(purchase_service._VIEW_ROLES),
    "purchases:create": lambda _w: RoleSet(purchase_service._WRITE_ROLES),
    "purchases:update": lambda _w: RoleSet(purchase_service._WRITE_ROLES),
    "purchases:delete": lambda _w: RoleSet(purchase_service._WRITE_ROLES),
    "purchases:quote_create": lambda _w: RoleSet(purchase_service._WRITE_ROLES),
    "purchases:quote_update": lambda _w: RoleSet(purchase_service._WRITE_ROLES),
    "purchases:quote_delete": lambda _w: RoleSet(purchase_service._WRITE_ROLES),
    "purchases:decide": lambda _w: RoleSet(purchase_service._DECIDE_ROLES),
    # Cancel is a decide-level action today, not a write-level one (§11.3).
    "purchases:cancel": lambda _w: RoleSet(purchase_service._DECIDE_ROLES),
    # --- uploads (media) ------------------------------------------------
    "uploads:photo_create": _unguarded("uploads:photo_create"),
    "uploads:photo_read": _unguarded("uploads:photo_read"),
    "uploads:pending_read": lambda w: Guard(
        partial(w.media.list_pending_photos, w.session)
    ),
    "uploads:approve": lambda w: Guard(
        lambda user: w.media.approve_photo(
            w.session, w.new_media_asset(user.role).id, user
        )
    ),
    "uploads:reject": lambda w: Guard(
        lambda user: w.media.reject_photo(
            w.session, w.new_media_asset(user.role).id, user, "motivo"
        )
    ),
    # The owner branch is exactly what makes this permission all-six, so the
    # probed asset must belong to the probed role (§6.5(b)).
    "uploads:delete": lambda w: Guard(
        lambda user: w.media.delete_photo(
            w.session, w.new_media_asset(user.role).id, user
        )
    ),
    # ------------------------------------------------------- access_control
    "access_control:devices_read": lambda _w: Guard(
        access_control_service._assert_admin_director_or_manager
    ),
    "access_control:device_create": lambda _w: Guard(
        access_control_service._assert_admin_or_director
    ),
    "access_control:device_update_status": lambda _w: Guard(
        access_control_service._assert_admin_or_director
    ),
    "access_control:device_regenerate_key": lambda _w: Guard(
        access_control_service._assert_admin_or_director
    ),
    "access_control:facial_template_read": lambda _w: Guard(
        access_control_service._assert_admin_director_or_manager
    ),
    "access_control:facial_template_sync": lambda _w: Guard(
        access_control_service._assert_admin_or_director
    ),
    "access_control:events_read": lambda _w: Guard(
        access_control_service._assert_admin_director_or_manager
    ),
}


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------


def _grants(probe: Callable[[User], object], user: User, session: Session) -> bool:
    """Whether the production guard let `user` through. "Did not raise" == granted."""
    try:
        probe(user)
    except Exception:
        return False
    else:
        return True
    finally:
        # Drop whatever uncommitted state a raising probe left behind. The
        # committing probes are isolated by their per-role factory row.
        session.rollback()


def expected_roles(source: object, world: ParityWorld) -> frozenset[UserRole]:
    """The roles the parity source says hold the permission."""
    if isinstance(source, RoleSet):
        return frozenset(source.roles_obj)
    if isinstance(source, RoleSetComplement):
        return frozenset(UserRole) - frozenset(source.roles_obj)
    if isinstance(source, Literal):
        return frozenset(source.roles)
    if isinstance(source, Composite):
        result = frozenset(UserRole)
        for part in source.parts:
            result &= expected_roles(part, world)
        return result
    if isinstance(source, Guard):
        return frozenset(
            role
            for role in UserRole
            if _grants(source.probe, world.users[role], world.session)
        )
    raise TypeError(f"unknown parity source: {source!r}")


def _flatten(source: object) -> list[object]:
    if isinstance(source, Composite):
        return [part for child in source.parts for part in _flatten(child)]
    return [source]


# ---------------------------------------------------------------------------
# Assertions (§6.3)
# ---------------------------------------------------------------------------


def test_every_permission_has_a_parity_source():
    assert set(PARITY_SOURCES) == set(PERMISSIONS)


@pytest.mark.parametrize("permission", sorted(PARITY_SOURCES))
def test_legacy_map_matches_the_live_guards(parity_world: ParityWorld, permission):
    """For every role: `perm in LEGACY_ROLE_PERMISSIONS[role]` iff production grants it."""
    source = PARITY_SOURCES[permission](parity_world)
    expected = expected_roles(source, parity_world)
    recorded = frozenset(
        role for role in UserRole if permission in LEGACY_ROLE_PERMISSIONS[role]
    )

    mismatches = sorted(
        (permission, role.value, role in expected, role in recorded)
        for role in UserRole
        if (role in expected) != (role in recorded)
    )
    assert not mismatches, (
        f"{permission}: production grants {sorted(r.value for r in expected)} but "
        f"the map records {sorted(r.value for r in recorded)}; "
        f"(permission, role, live, mapped) diffs: {mismatches}"
    )


def test_role_set_sources_are_production_objects(parity_world: ParityWorld):
    """A `RoleSet` must point at the live constant, never a copied literal."""
    live = [getattr(module, name) for module, name in PRODUCTION_ROLE_SET_ATTRS]
    detached = sorted(
        permission
        for permission, builder in PARITY_SOURCES.items()
        for part in _flatten(builder(parity_world))
        if isinstance(part, RoleSet | RoleSetComplement)
        and not any(part.roles_obj is obj for obj in live)
    )
    assert not detached, f"role-set sources not reading production: {detached}"


def test_literal_sources_carry_a_reason(parity_world: ParityWorld):
    for permission, builder in PARITY_SOURCES.items():
        for part in _flatten(builder(parity_world)):
            if isinstance(part, Literal):
                assert part.reason.strip(), f"{permission}: empty Literal reason"


def test_every_role_has_an_entry():
    assert set(LEGACY_ROLE_PERMISSIONS) == set(UserRole)
    for role, granted in LEGACY_ROLE_PERMISSIONS.items():
        assert granted <= PERMISSIONS, f"{role} holds unknown permissions"


def test_administrator_is_a_superset_of_every_other_role_except_the_documented_gaps():
    """The unqualified superset claim is false against production (§11.5)."""
    admin = LEGACY_ROLE_PERMISSIONS[A]
    missing = sorted(
        permission
        for permission in PERMISSIONS
        if permission not in ADMIN_GAP_PERMISSIONS
        and permission not in admin
        and any(permission in LEGACY_ROLE_PERMISSIONS[role] for role in UserRole)
    )
    assert not missing, f"undocumented admin gaps: {missing}"


def test_admin_gap_list_is_exact():
    """A new admin gap, or a closed one, fails CI until the constant moves."""
    admin = LEGACY_ROLE_PERMISSIONS[A]
    live_gaps = {
        permission
        for permission in PERMISSIONS
        if permission not in admin
        and any(permission in LEGACY_ROLE_PERMISSIONS[role] for role in UserRole)
    }
    assert live_gaps == ADMIN_GAP_PERMISSIONS


def test_literal_sources_are_allowlisted(parity_world: ParityWorld):
    """`Literal` is bounded, not a general escape hatch (§6.3)."""
    using_literal = {
        permission
        for permission, builder in PARITY_SOURCES.items()
        if any(isinstance(part, Literal) for part in _flatten(builder(parity_world)))
    }
    assert using_literal == LITERAL_ALLOWLIST


def test_composite_sources_have_a_live_part(parity_world: ParityWorld):
    """A `Composite` of only `Literal`s is a hand copy wearing a costume."""
    composites = {
        permission
        for permission, builder in PARITY_SOURCES.items()
        if isinstance(builder(parity_world), Composite)
    }
    assert composites == {"tasks:read", "announcements:comment"}
    for permission in composites:
        parts = _flatten(PARITY_SOURCES[permission](parity_world))
        assert any(isinstance(part, LIVE_SOURCE_TYPES) for part in parts), (
            f"{permission}: Composite with no live part"
        )


def test_all_six_role_permissions_are_the_documented_seventeen():
    live = {
        permission
        for permission in PERMISSIONS
        if all(permission in LEGACY_ROLE_PERMISSIONS[role] for role in UserRole)
    }
    assert len(ALL_SIX_ROLE_PERMISSIONS) == 17
    assert live == ALL_SIX_ROLE_PERMISSIONS


def test_legacy_map_is_marked_transitional():
    assert LEGACY_MAP_REMOVAL_SLICE == "IAM F5"

    source = inspect.getsource(permissions_module)
    assignment = source.index("LEGACY_ROLE_PERMISSIONS: dict[UserRole, frozenset[str]] =")
    banner = source.rindex("TRANSITIONAL", 0, assignment)
    assert banner < assignment
