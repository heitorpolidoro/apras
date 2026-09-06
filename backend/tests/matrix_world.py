"""The `role x route x verb` parity harness (IAM F2, APRAS-46 §6.2).

**Not a test module.** Pytest does not collect it (no `test_` prefix), which
is the whole point: `tests/test_permission_parity_matrix.py` and
`tests/tools/record_parity_baseline.py` import the *same* objects from here,
so the committed baseline and the assertions that read it are produced by one
implementation of the world. A baseline recorded by a second implementation
would prove nothing.

What it provides
----------------

* :data:`CELLS` -- ``(profile, method, path)`` for every
  ``ROUTE_PERMISSIONS`` key and every :data:`PARITY_PROFILES` entry:
  ``6 x 201 == 1206``. 1080 of them are recorded in the frozen IAM F2
  baseline; the 18 APRAS-40 adds live in the additive
  ``tests/data/parity_matrix_baseline_40.json`` (APRAS-40 §9.2) and the 108
  APRAS-44 adds in ``tests/data/parity_matrix_baseline_44.json``
  (APRAS-44 §8.5), which is what keeps the F2 file byte-identical.
  The twenty-two ``UNGUARDED_ROUTES`` are excluded because none of them makes
  a **role-dimension, catalogue-permission** authorization decision: eight are
  unauthenticated (``/``, ``/api/v1/health``, login, signup,
  forgot/reset-password and the two dev helpers), ``GET /api/v1/auth/me`` and
  ``GET /api/v1/permissions/me`` are strictly self-scoped, ``GET
  /api/v1/permissions/`` is a static vocabulary, the device webhook
  authenticates an ``X-Device-Key`` and no user at all, and ``PATCH
  /api/v1/users/{user_id}/superuser`` (IAM F5, APRAS-49 §8.4) *does* make an
  authorization decision -- it simply makes it on ``is_superuser``, a column
  no role bundle can carry, so no profile dimension could move its answer.
* :class:`MatrixWorld` -- one row of every object a matrix path parameter
  names, so the only reason a cell can be refused is the authorization
  decision under measurement.
* :data:`PATH_PARAMS` -- ``(path, name) -> callable(world) -> str``. Keyed by
  the *path* as well as the name because ``{id}``, ``{user_id}`` and
  ``{category_id}`` name different objects on different routes.
* :data:`REQUEST_BODIES` -- ``(method, path) -> body spec`` for every
  POST/PUT/PATCH route. A missing entry is never allowed to default to
  ``{}``: an invalid body answers ``422`` and would mask the authorization
  answer for the roles that hold the permission.
* :func:`run_cell` -- issues exactly one real HTTP request and returns the
  status code.

Time
----

Every datetime written into the world or into a request body is an offset
from ``datetime.utcnow()`` computed at build time. No absolute date is
hard-coded anywhere in this module: the baseline is a committed golden file,
and at least one production path branches on wall-clock time
(``reservation_service`` compares ``start_time`` to now), so an absolute date
would rot the file into a red CI run that has nothing to do with permissions.
``tests/test_permission_parity_matrix.py::test_no_absolute_datetime_in_the_harness``
parses this module and enforces it.

Isolation
---------

One mechanism, no fallback (§6.2): one SQLite *file* database, one engine,
the world seeded exactly once and committed, and then every cell inside its
own connection-level transaction with a
``join_transaction_mode="create_savepoint"`` session, so a handler's
``commit()`` releases a savepoint and the cell's closing ``rollback()`` undoes
every write. The world is never rebuilt.
"""

from __future__ import annotations

import json
import re
import uuid
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from fastapi.testclient import TestClient
from sqlalchemy import Engine, event
from sqlmodel import Session, SQLModel, create_engine

from app.core.permissions import ROUTE_PERMISSIONS
from app.core.security import create_access_token
from app.core.tenant_context import REQUEST_SCOPED_KEY
from app.db import get_session
from app.main import app
from app.models.access_control import AccessDevice
from app.models.announcement import (
    Announcement,
    AnnouncementComment,
    AnnouncementMedia,
)
from app.models.asset import Asset, InventoryMovement
from app.models.category import Category
from app.models.document import AssociationDocument, DocumentFolder
from app.models.enums import (
    AnnouncementMediaType,
    AssemblyType,
    AssetCategory,
    AuthorizationStatus,
    EntityType,
    FeedbackCategory,
    InfractionFineMode,
    InfractionRuleOrigin,
    InfractionStepAction,
    MovementType,
    OccurrenceCategory,
    PhotoApprovalStatus,
    StorageProvider,
    TransactionType,
    VoteKind,
    VoteStatus,
    VoteType,
)
from app.models.feedback import Feedback
from app.models.finance import BudgetLine, FinanceCategory, FinancialTransaction
from app.models.infraction import (
    Infraction,
    InfractionPolicyStep,
    InfractionRule,
    InfractionStage,
)
from app.models.lot import Lot, UserLotLink
from app.models.media_asset import MediaAsset
from app.models.occurrence import Occurrence
from app.models.package import Package
from app.models.project import ConstructionProject, ProjectMilestone, ProjectUpdate
from app.models.purchase import PurchaseQuote, PurchaseRequest
from app.models.reservation import ReservableSpace, SpaceReservation
from app.models.resident import Resident
from app.models.role import Role
from app.models.task import Task, TaskComment
from app.models.tenant import (
    DEFAULT_TENANT_ID,
    DEFAULT_TENANT_NAME,
    Tenant,
    UserTenantLink,
)
from app.models.visitor import AccessLog, Visitor, VisitorAuthorization
from app.models.voting import Assembly, LotVoterEligibility, Vote, VoteOption
from app.services import announcement_service, finance_service
from app.services.media_service import media_service
from app.services.storage_service import BaseStorageProvider
from tests.conftest import make_user, profile_role

if TYPE_CHECKING:  # pragma: no cover
    from app.models.user import User

# ---------------------------------------------------------------------------
# The cell grid (§6.1)
# ---------------------------------------------------------------------------

#: What the retired role enum leaves behind in the test tree, and nothing
#: else (IAM F5, APRAS-49 §11.1): the six **legacy profiles**, spelled as the
#: enum's value strings, **verbatim** and in the same sorted order.
#:
#: Verbatim is not a style point. `tests/data/parity_matrix_baseline.json`'s
#: top-level keys *are* those strings, so the golden file's byte-identity
#: depends on them surviving the enum's death unchanged while the actor
#: behind each becomes a role membership.
PARITY_PROFILES: tuple[str, ...] = (
    "ADMINISTRATOR",
    "DIRECTOR",
    "GUEST",
    "MANAGER",
    "PORTEIRO",
    "RESIDENT",
)

#: `(profile, method, path)` for every permission-mapped route and profile.
CELLS: list[tuple[str, str, str]] = [
    (profile, method, path)
    for (method, path) in sorted(ROUTE_PERMISSIONS)
    for profile in PARITY_PROFILES
]


# ---------------------------------------------------------------------------
# Small deterministic helpers
# ---------------------------------------------------------------------------


def _now() -> datetime:
    """Naive UTC now, exactly as production writes it."""
    return datetime.utcnow()  # noqa: DTZ003


def _cpf(seed: int) -> str:
    """A check-digit-valid CPF derived from `seed`, so no literal is needed.

    `ResidentCreate` validates the check digits, and `User.cpf` is globally
    unique, so the world needs a handful of distinct valid numbers. Deriving
    them keeps the module free of magic strings and free of collisions.
    """
    base = f"{seed:09d}"
    total = sum(int(base[i]) * (10 - i) for i in range(9))
    d1 = 0 if (total % 11) < 2 else 11 - (total % 11)
    nine = base + str(d1)
    total = sum(int(nine[i]) * (11 - i) for i in range(10))
    d2 = 0 if (total % 11) < 2 else 11 - (total % 11)
    return nine + str(d2)


class _NullStorage(BaseStorageProvider):
    """The production storage providers, with their file system amputated.

    The three upload routes in the matrix (`POST /uploads/photo`,
    `POST /announcements/{id}/media`, `POST /finance/transactions/{id}/invoice`)
    reach a module-level `LocalStorageProvider` that writes under
    `backend/static/uploads`. The harness swaps all three for this stub while
    the matrix runs: the handlers, the services and the status codes are
    untouched, and no cell can leave a file behind or make the baseline
    depend on a directory. `settings` carries no upload-directory knob, so
    redirecting the provider *is* how "point the upload directory somewhere
    disposable" is spelled in this codebase.
    """

    def save_file(self, file_bytes, filename, content_type):  # noqa: ARG002
        return f"/dev/null/{filename}", f"http://null/{filename}"

    def delete_file(self, file_path):  # noqa: ARG002
        return True


@contextmanager
def neutralised_storage() -> Iterator[None]:
    """Point every module-level storage provider at :class:`_NullStorage`."""
    stub = _NullStorage()
    original_media = media_service.storage_provider
    original_announcement = announcement_service._storage_provider  # noqa: SLF001
    original_finance = finance_service._storage_provider  # noqa: SLF001
    media_service.storage_provider = stub
    announcement_service._storage_provider = stub  # noqa: SLF001  # type: ignore[assignment]
    finance_service._storage_provider = stub  # noqa: SLF001  # type: ignore[assignment]
    try:
        yield
    finally:
        media_service.storage_provider = original_media
        announcement_service._storage_provider = original_announcement  # noqa: SLF001
        finance_service._storage_provider = original_finance  # noqa: SLF001


# ---------------------------------------------------------------------------
# The world (§6.2)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MatrixWorld:
    """Every non-role dimension neutralised.

    Only ids are carried: the world is seeded in its own `Session` and every
    cell runs in another, so an ORM instance would be detached the moment a
    cell touched it.
    """

    tokens: dict[str, str]
    users: dict[str, uuid.UUID]
    target_user_id: uuid.UUID
    outsider_user_id: uuid.UUID
    tenant_b_id: uuid.UUID
    lot_id: uuid.UUID
    category_id: uuid.UUID
    role_id: uuid.UUID
    task_id: uuid.UUID
    task_comment_id: uuid.UUID
    resident_id: uuid.UUID
    visitor_id: uuid.UUID
    authorization_id: uuid.UUID
    access_log_id: uuid.UUID
    occurrence_id: uuid.UUID
    folder_id: uuid.UUID
    document_id: uuid.UUID
    announcement_id: uuid.UUID
    announcement_comment_id: uuid.UUID
    announcement_media_id: uuid.UUID
    feedback_id: uuid.UUID
    space_id: uuid.UUID
    reservation_id: uuid.UUID
    package_id: uuid.UUID
    vote_id: uuid.UUID
    vote_option_id: uuid.UUID
    assembly_id: uuid.UUID
    asset_id: uuid.UUID
    movement_id: uuid.UUID
    purchase_request_id: uuid.UUID
    quote_id: uuid.UUID
    media_asset_id: uuid.UUID
    device_id: uuid.UUID
    project_id: uuid.UUID
    milestone_id: uuid.UUID
    project_update_id: uuid.UUID
    finance_category_id: uuid.UUID
    budget_line_id: uuid.UUID
    transaction_id: uuid.UUID
    # APRAS-44 §12.6: an active rule with a three-rung ladder, and one
    # infraction already carrying a NOTIFICACAO whose deadline is open, so
    # the contestation cell measures authorization and not state.
    infraction_rule_id: uuid.UUID
    infraction_id: uuid.UUID
    built_at: datetime = field(default_factory=_now)


def build_world(session: Session) -> MatrixWorld:  # noqa: PLR0915
    """Seed one row of every object the matrix touches, and commit it.

    Called **once** per matrix run, on a plain (non request-scoped) session,
    exactly as `app/seed.py` would: every tenant-scoped model defaults its
    `tenant_id` to `DEFAULT_TENANT_ID`, so the world lands in the default
    tenant without the request-time filter being involved.
    """
    now = _now()

    if session.get(Tenant, DEFAULT_TENANT_ID) is None:
        session.add(Tenant(id=DEFAULT_TENANT_ID, name=DEFAULT_TENANT_NAME))
        session.commit()
    tenant_b = Tenant(name="Matrix Tenant B")
    session.add(tenant_b)
    session.commit()
    session.refresh(tenant_b)

    # A spare, unassigned role: what `{role_id}` binds to. Since IAM F5 every
    # role row is renamable and deletable, so this is no longer needed to dodge
    # a "role-linked rows cannot be edited" refusal -- but the write cells must
    # still not target a row an actor is a member of, or a delete would change
    # the world under the next cell.
    spare_type = Role(name="Matrix Spare Type")
    session.add(spare_type)
    session.commit()
    session.refresh(spare_type)

    # One actor per profile, each a member of exactly the correspondingly
    # named legacy role row carrying `bundle(profile)` -- the same union
    # migration `0033` writes. `conftest.make_user` creates the row on first
    # use, so the bundles come from `tests/data/legacy_role_bundles.json` and
    # never from a second literal.
    #
    # The ADMINISTRATOR profile also carries `is_superuser=True`, which
    # `make_user` defaults for it: IAM F3 already routed every administrator
    # decision through the flag, so the profile would otherwise stop being the
    # actor the baseline recorded.
    #
    # The menu-granting type every actor used to carry is gone with the gate
    # (§4.1). It existed so the matrix measured permissions and not menus; the
    # gate's removal makes that true by construction.
    users: dict[str, User] = {}
    for index, profile in enumerate(PARITY_PROFILES):
        users[profile] = make_user(
            session,
            profile=profile,
            id=uuid.uuid4(),
            email=f"{profile.lower()}@matrix.example.com",
            full_name=f"{profile} Matrix",
            hashed_password="not-a-real-hash",
            cpf=_cpf(index + 1),
        )
    target_user = make_user(
        session,
        id=uuid.uuid4(),
        email="target@matrix.example.com",
        full_name="Matrix Target",
        hashed_password="not-a-real-hash",
        profile="GUEST",
        cpf=_cpf(50),
    )
    outsider_user = make_user(
        session,
        id=uuid.uuid4(),
        email="outsider@matrix.example.com",
        full_name="Matrix Outsider",
        hashed_password="not-a-real-hash",
        profile="GUEST",
        cpf=_cpf(51),
    )
    session.add(target_user)
    session.add(outsider_user)
    session.commit()

    for user in [*users.values(), target_user]:
        session.add(
            UserTenantLink(
                user_id=user.id, tenant_id=DEFAULT_TENANT_ID, is_tenant_admin=False
            )
        )
    session.add(
        UserTenantLink(
            user_id=outsider_user.id, tenant_id=tenant_b.id, is_tenant_admin=False
        )
    )
    session.commit()

    lot = Lot(block="A", lot_number="1")
    session.add(lot)
    session.commit()
    session.refresh(lot)

    # Open-ended dates are what make `_is_link_active` true *now*, and an
    # active `Resident` row is what the per-lot narrowings read.
    for index, (role_value, user) in enumerate(users.items()):
        session.add(UserLotLink(user_id=user.id, lot_id=lot.id, start_date=None, end_date=None))
        session.add(
            Resident(
                lot_id=lot.id,
                user_id=user.id,
                full_name=f"{role_value} Resident",
                cpf=_cpf(100 + index),
                is_active=True,
            )
        )
    session.add(
        UserLotLink(user_id=target_user.id, lot_id=lot.id, start_date=None, end_date=None)
    )
    # `{resident_id}` binds to a resident with **no** linked user, so
    # `POST /residents/{id}/link-user` has something to do.
    spare_resident = Resident(
        lot_id=lot.id, full_name="Matrix Spare Resident", cpf=_cpf(150), is_active=True
    )
    session.add(spare_resident)
    session.add(LotVoterEligibility(lot_id=lot.id, user_id=target_user.id))
    session.commit()
    session.refresh(spare_resident)

    category = Category(name="Matrix Category", color="#808080")
    session.add(category)

    # `visible_to=[]` is visible to every MANAGER; `assigned_to_id=None`
    # means a MANAGER may edit it. Any other task silently drops MANAGER
    # from the tasks cells.
    task = Task(
        title="Matrix task",
        created_by_id=users["ADMINISTRATOR"].id,
        assigned_to_id=None,
    )
    session.add(task)
    session.commit()
    session.refresh(category)
    session.refresh(task)

    task_comment = TaskComment(
        task_id=task.id,
        created_by_id=users["ADMINISTRATOR"].id,
        content="Matrix comment",
    )
    session.add(task_comment)

    visitor = Visitor(full_name="Matrix Visitor")
    session.add(visitor)
    session.commit()
    session.refresh(task_comment)
    session.refresh(visitor)

    authorization = VisitorAuthorization(
        visitor_id=visitor.id,
        lot_id=lot.id,
        authorizer_user_id=users["ADMINISTRATOR"].id,
        status=AuthorizationStatus.ACTIVE,
        valid_from=now - timedelta(days=1),
        valid_until=now + timedelta(days=30),
    )
    session.add(authorization)
    session.commit()
    session.refresh(authorization)

    access_log = AccessLog(
        visitor_id=visitor.id,
        lot_id=lot.id,
        authorization_id=authorization.id,
        entry_time=now - timedelta(hours=1),
    )
    session.add(access_log)

    occurrence = Occurrence(
        protocol_number="MATRIX-0001",
        category=OccurrenceCategory.OTHER,
        title="Matrix occurrence",
        description="Matrix occurrence description",
        reporter_user_id=users["RESIDENT"].id,
        lot_id=lot.id,
        is_anonymous=False,
    )
    session.add(occurrence)

    # The per-folder ACL is a list of role **ids** since IAM F5 (APRAS-49
    # §6); it held the four `UserRole` value strings `0010`'s `server_default`
    # named. Seeding the corresponding profile rows keeps every recorded
    # `documents:*` cell -- including the GUEST and PORTEIRO 403s the baseline
    # attributes to "per-folder ACL" -- exactly what it was.
    folder = DocumentFolder(
        name="Matrix Folder",
        allowed_role_ids_json=json.dumps(
            [
                str(profile_role(session, profile).id)
                for profile in ("ADMINISTRATOR", "DIRECTOR", "MANAGER", "RESIDENT")
            ]
        ),
    )
    session.add(folder)
    session.commit()
    session.refresh(access_log)
    session.refresh(occurrence)
    session.refresh(folder)

    document = AssociationDocument(
        folder_id=folder.id,
        title="Matrix Document",
        file_url="http://null/matrix.pdf",
        file_size_bytes=1,
        uploaded_by_id=users["ADMINISTRATOR"].id,
    )
    session.add(document)

    announcement = Announcement(
        title="Matrix Announcement",
        content="Matrix announcement content",
        author_id=users["ADMINISTRATOR"].id,
    )
    session.add(announcement)
    session.commit()
    session.refresh(document)
    session.refresh(announcement)

    announcement_comment = AnnouncementComment(
        announcement_id=announcement.id,
        user_id=users["ADMINISTRATOR"].id,
        content="Matrix announcement comment",
    )
    announcement_media = AnnouncementMedia(
        announcement_id=announcement.id,
        media_type=AnnouncementMediaType.IMAGE,
        file_path="/dev/null/matrix.jpg",
        url="http://null/matrix.jpg",
        mime_type="image/jpeg",
        file_size_bytes=1,
    )
    session.add(announcement_comment)
    session.add(announcement_media)

    feedback = Feedback(
        reporter_user_id=users["RESIDENT"].id,
        category=FeedbackCategory.SUGGESTION,
        message="Matrix feedback",
    )
    session.add(feedback)

    space = ReservableSpace(name="Matrix Space")
    session.add(space)
    session.commit()
    session.refresh(announcement_comment)
    session.refresh(announcement_media)
    session.refresh(feedback)
    session.refresh(space)

    reservation = SpaceReservation(
        space_id=space.id,
        reserved_by_id=users["RESIDENT"].id,
        start_time=now + timedelta(days=2),
        end_time=now + timedelta(days=2, hours=2),
    )
    session.add(reservation)

    package = Package(lot_id=lot.id, description="Matrix package")
    session.add(package)

    vote = Vote(
        kind=VoteKind.ENQUETE,
        title="Matrix poll",
        vote_type=VoteType.SINGLE_CHOICE,
        status=VoteStatus.OPEN,
        opens_at=now - timedelta(hours=1),
        closes_at=now + timedelta(days=7),
        created_by_id=users["ADMINISTRATOR"].id,
    )
    session.add(vote)

    assembly = Assembly(
        title="Matrix Assembly",
        type=AssemblyType.AGO,
        held_on=(now + timedelta(days=7)).date(),
        created_by_id=users["ADMINISTRATOR"].id,
    )
    session.add(assembly)

    asset = Asset(
        name="Matrix Asset",
        category=AssetCategory.OUTROS,
        location="Matrix location",
        is_consumable=True,
        current_quantity=100,
    )
    session.add(asset)
    session.commit()
    session.refresh(reservation)
    session.refresh(package)
    session.refresh(vote)
    session.refresh(assembly)
    session.refresh(asset)

    vote_option = VoteOption(vote_id=vote.id, label="Matrix option")
    session.add(vote_option)

    movement = InventoryMovement(
        asset_id=asset.id,
        movement_type=MovementType.ENTRADA,
        quantity=1,
        previous_quantity=99,
        new_quantity=100,
        performed_by_id=users["ADMINISTRATOR"].id,
        reason="Matrix movement",
    )
    session.add(movement)

    purchase_request = PurchaseRequest(
        title="Matrix purchase",
        requested_by_id=users["ADMINISTRATOR"].id,
    )
    session.add(purchase_request)

    media_asset = MediaAsset(
        entity_type=EntityType.RESIDENT,
        storage_provider=StorageProvider.LOCAL_DISK,
        file_path="/dev/null/matrix-photo.jpg",
        url="http://null/matrix-photo.jpg",
        file_size_bytes=1,
        mime_type="image/jpeg",
        status=PhotoApprovalStatus.PENDING_APPROVAL,
        uploaded_by_id=users["RESIDENT"].id,
        approved_by_id=None,
    )
    session.add(media_asset)

    device = AccessDevice(
        name="Matrix Device",
        device_key="matrix-device-key",
        created_by_id=users["ADMINISTRATOR"].id,
    )
    session.add(device)

    project = ConstructionProject(title="Matrix Project")
    session.add(project)

    finance_category = FinanceCategory(name="Matrix Finance", type=TransactionType.EXPENSE)
    session.add(finance_category)
    session.commit()
    session.refresh(vote_option)
    session.refresh(movement)
    session.refresh(purchase_request)
    session.refresh(media_asset)
    session.refresh(device)
    session.refresh(project)
    session.refresh(finance_category)

    quote = PurchaseQuote(
        purchase_request_id=purchase_request.id,
        supplier_name="Matrix Supplier",
        unit_price=10.0,
        quantity=1,
        created_by_id=users["ADMINISTRATOR"].id,
    )
    session.add(quote)

    milestone = ProjectMilestone(project_id=project.id, title="Matrix Milestone")
    session.add(milestone)

    project_update = ProjectUpdate(
        project_id=project.id,
        author_id=users["ADMINISTRATOR"].id,
        title="Matrix Update",
        content="Matrix update content",
    )
    session.add(project_update)

    budget_line = BudgetLine(
        category_id=finance_category.id,
        fiscal_year=now.year,
        planned_amount=1000.0,
    )
    session.add(budget_line)

    transaction = FinancialTransaction(
        type=TransactionType.EXPENSE,
        category_id=finance_category.id,
        description="Matrix transaction",
        amount=10.0,
        transaction_date=now.date(),
        created_by_id=users["ADMINISTRATOR"].id,
    )
    session.add(transaction)
    session.commit()
    session.refresh(quote)
    session.refresh(milestone)
    session.refresh(project_update)
    session.refresh(budget_line)
    session.refresh(transaction)

    # --- APRAS-44 -----------------------------------------------------------
    # An **active** rule (§7.7 refuses a deactivated one) with the three-rung
    # ladder of §12.6, and one infraction on `world.lot` whose responsible is a
    # resident of that lot. `build_world` already gives every profile user both
    # a `UserLotLink` to `lot` and an active `Resident` row on it, so §7.6's
    # predicate holds for all six profiles: the 403 never fires, the
    # contestation cell measures authorization, and `GET /infractions/my-lots`
    # returns one item rather than `[]`.
    #
    # No `infraction_settings` row is seeded, so `GET /infraction-settings`
    # exercises the §5 absent-row read.
    infraction_rule = InfractionRule(
        article="art. 12",
        origin=InfractionRuleOrigin.REGIMENTO_INTERNO,
        description="Matrix infraction rule",
        recidivism_window_days=365,
        is_active=True,
    )
    session.add(infraction_rule)
    session.commit()
    session.refresh(infraction_rule)

    session.add(
        InfractionPolicyStep(
            rule_id=infraction_rule.id,
            step_order=1,
            action=InfractionStepAction.AVISO,
        )
    )
    session.add(
        InfractionPolicyStep(
            rule_id=infraction_rule.id,
            step_order=2,
            action=InfractionStepAction.NOTIFICACAO,
            defense_deadline_days=30,
        )
    )
    session.add(
        InfractionPolicyStep(
            rule_id=infraction_rule.id,
            step_order=3,
            action=InfractionStepAction.MULTA,
            fine_mode=InfractionFineMode.FIXED,
            fine_fixed_amount=100.0,
        )
    )

    infraction = Infraction(
        rule_id=infraction_rule.id,
        lot_id=lot.id,
        responsible_resident_id=spare_resident.id,
        registered_by_id=users["ADMINISTRATOR"].id,
        occurred_on=(now - timedelta(days=1)).date(),
        description="Matrix infraction",
    )
    session.add(infraction)
    session.commit()
    session.refresh(infraction)

    session.add(
        InfractionStage(
            infraction_id=infraction.id,
            action=InfractionStepAction.NOTIFICACAO,
            applied_on=now.date(),
            note="Matrix notification",
            actor_id=users["ADMINISTRATOR"].id,
            defense_due_on=(now + timedelta(days=30)).date(),
            policy_step_order=2,
            suggestion_followed=True,
        )
    )
    session.commit()

    return MatrixWorld(
        tokens={
            role_value: create_access_token(str(user.id))
            for role_value, user in users.items()
        },
        users={role_value: user.id for role_value, user in users.items()},
        target_user_id=target_user.id,
        outsider_user_id=outsider_user.id,
        tenant_b_id=tenant_b.id,
        lot_id=lot.id,
        category_id=category.id,
        role_id=spare_type.id,
        task_id=task.id,
        task_comment_id=task_comment.id,
        resident_id=spare_resident.id,
        visitor_id=visitor.id,
        authorization_id=authorization.id,
        access_log_id=access_log.id,
        occurrence_id=occurrence.id,
        folder_id=folder.id,
        document_id=document.id,
        announcement_id=announcement.id,
        announcement_comment_id=announcement_comment.id,
        announcement_media_id=announcement_media.id,
        feedback_id=feedback.id,
        space_id=space.id,
        reservation_id=reservation.id,
        package_id=package.id,
        vote_id=vote.id,
        vote_option_id=vote_option.id,
        assembly_id=assembly.id,
        asset_id=asset.id,
        movement_id=movement.id,
        purchase_request_id=purchase_request.id,
        quote_id=quote.id,
        media_asset_id=media_asset.id,
        device_id=device.id,
        project_id=project.id,
        milestone_id=milestone.id,
        project_update_id=project_update.id,
        finance_category_id=finance_category.id,
        budget_line_id=budget_line.id,
        transaction_id=transaction.id,
        infraction_rule_id=infraction_rule.id,
        infraction_id=infraction.id,
    )


# ---------------------------------------------------------------------------
# Path parameter bindings
# ---------------------------------------------------------------------------

Binder = Callable[[MatrixWorld], str]


def _bind(attribute: str) -> Binder:
    return lambda world: str(getattr(world, attribute))


def _path_params() -> dict[tuple[str, str], Binder]:
    """`(path, name) -> binder`, derived from one binder per parameter name.

    `{id}`, `{user_id}` and `{category_id}` name different objects on
    different routes, so the map is keyed by the path too and the per-path
    exceptions are spelled out rather than guessed.
    """
    by_name: dict[str, str] = {
        "assembly_id": "assembly_id",
        "asset_id": "asset_id",
        "auth_id": "authorization_id",
        "authorization_id": "authorization_id",
        "category_id": "category_id",
        "comment_id": "task_comment_id",
        "device_id": "device_id",
        # APRAS-44. Three `by_name` entries, not six `(path, name)` pairs: the
        # derived map is keyed by path, so `{rule_id}` on two paths,
        # `{infraction_id}` on four and `{occurrence_id}` on one produce seven
        # entries from these three lines.
        #
        # `occurrence_id` needs its own binder and does **not** inherit the
        # existing `("/api/v1/occurrences/", "occurrence_id")` one: that lives
        # in `by_prefix`, which is consulted only when the parameter is
        # literally named `id`. Without this line `_path_params()` raises
        # `KeyError` at import and the whole matrix module fails to collect.
        "infraction_id": "infraction_id",
        "occurrence_id": "occurrence_id",
        "rule_id": "infraction_rule_id",
        "lot_id": "lot_id",
        "media_id": "announcement_media_id",
        "milestone_id": "milestone_id",
        "package_id": "package_id",
        "photo_id": "media_asset_id",
        "quote_id": "quote_id",
        "request_id": "purchase_request_id",
        "reservation_id": "reservation_id",
        "resident_id": "resident_id",
        "space_id": "space_id",
        "task_id": "task_id",
        "update_id": "project_update_id",
        "user_id": "target_user_id",
        "role_id": "role_id",
        "visitor_id": "visitor_id",
        "vote_id": "vote_id",
    }
    #: `{id}` is polymorphic: the object is named by the URL prefix.
    by_prefix: tuple[tuple[str, str], ...] = (
        ("/api/v1/announcements/", "announcement_id"),
        ("/api/v1/documents/folders/", "folder_id"),
        ("/api/v1/documents/", "document_id"),
        ("/api/v1/feedback/", "feedback_id"),
        ("/api/v1/finance/budget-lines/", "budget_line_id"),
        ("/api/v1/finance/categories/", "finance_category_id"),
        ("/api/v1/finance/transactions/", "transaction_id"),
        ("/api/v1/occurrences/", "occurrence_id"),
        ("/api/v1/projects/", "project_id"),
    )
    overrides: dict[tuple[str, str], str] = {
        # The finance dimension, not the task Category.
        (
            "/api/v1/finance/budget-vs-actual/{category_id}/transactions",
            "category_id",
        ): "finance_category_id",
        # The announcement comment, not the task comment.
        ("/api/v1/announcements/comments/{comment_id}", "comment_id"): (
            "announcement_comment_id"
        ),
        # Tenant membership is global-scoped; the acting tenant is the
        # default one, and every actor is a member of it.
        ("/api/v1/tenants/{tenant_id}", "tenant_id"): "_default_tenant",
        ("/api/v1/tenants/{tenant_id}/members", "tenant_id"): "_default_tenant",
        (
            "/api/v1/tenants/{tenant_id}/members/{user_id}",
            "tenant_id",
        ): "_default_tenant",
    }

    bindings: dict[tuple[str, str], Binder] = {}
    for _method, path in ROUTE_PERMISSIONS:
        for name in re.findall(r"\{(\w+)\}", path):
            key = (path, name)
            if key in bindings:
                continue
            attribute = overrides.get(key)
            if attribute is None and name == "id":
                attribute = next(
                    value for prefix, value in by_prefix if path.startswith(prefix)
                )
            if attribute is None:
                attribute = by_name[name]
            if attribute == "_default_tenant":
                bindings[key] = lambda _world: str(DEFAULT_TENANT_ID)
            else:
                bindings[key] = _bind(attribute)
    return bindings


#: `(path, name) -> callable(world) -> str`. Every `{name}` in every matrix
#: path has an entry, and every entry resolves to a `MatrixWorld` id.
PATH_PARAMS: dict[tuple[str, str], Binder] = _path_params()


#: `(METHOD, path) -> callable(world) -> query dict`, for the five routes that
#: declare a **required** query parameter. Without them those cells answer
#: `422` for every role, which is request-shape validation and would mask the
#: authorization answer (§6.4's `PERMITTED_422` rule). Same discipline as
#: `PATH_PARAMS`: every value is either a `MatrixWorld` id or an offset from
#: `datetime.utcnow()`, never a literal date.
QUERY_PARAMS: dict[tuple[str, str], Callable[[MatrixWorld], dict[str, str]]] = {
    ("GET", "/api/v1/finance/budget-lines"): lambda _w: {
        "fiscal_year": str(_now().year)
    },
    ("GET", "/api/v1/finance/budget-vs-actual"): lambda _w: {
        "fiscal_year": str(_now().year)
    },
    ("GET", "/api/v1/finance/budget-vs-actual/{category_id}/transactions"): lambda _w: {
        "fiscal_year": str(_now().year)
    },
    ("GET", "/api/v1/finance/statement"): lambda _w: {
        "start_date": (_now() - timedelta(days=30)).date().isoformat(),
        "end_date": (_now() + timedelta(days=30)).date().isoformat(),
    },
    ("GET", "/api/v1/packages"): lambda w: {"lot_id": str(w.lot_id)},
}


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------


class _NoBody:
    """The route declares no body model. Sending one would be meaningless.

    An *explicit* entry rather than a missing one: `REQUEST_BODIES` must
    cover exactly the 99 POST/PUT/PATCH routes, and "this route takes no
    body" is a decision that has to be visible in the map.
    """

    __slots__ = ()


NO_BODY = _NoBody()


@dataclass(frozen=True)
class Upload:
    """A multipart body: one small in-memory file plus optional form fields."""

    field_name: str
    filename: str
    content_type: str
    form: dict[str, str] = field(default_factory=dict)


#: One pixel's worth of bytes. Never written to disk (see `_NullStorage`).
_FILE_BYTES = b"matrix-upload"

BodySpec = Callable[[MatrixWorld], Any]


def _static(payload: Any) -> BodySpec:
    return lambda _world: payload


def _future(days: int = 0, hours: int = 0) -> str:
    return (_now() + timedelta(days=days, hours=hours)).isoformat()


def _today() -> str:
    return _now().date().isoformat()


#: `(METHOD, path) -> body spec`, for exactly the 99 POST/PUT/PATCH routes
#: of `ROUTE_PERMISSIONS`. The 25 DELETE routes declare no body model and are
#: deliberately absent. A missing entry is never allowed to default to `{}`.
REQUEST_BODIES: dict[tuple[str, str], BodySpec] = {
    # --- tasks -------------------------------------------------------------
    ("POST", "/api/v1/tasks/"): _static({"title": "Matrix created task"}),
    ("PATCH", "/api/v1/tasks/{task_id}"): _static({"title": "Matrix renamed task"}),
    ("POST", "/api/v1/tasks/{task_id}/comments"): _static({"content": "Matrix note"}),
    ("PATCH", "/api/v1/tasks/{task_id}/comments/{comment_id}"): _static(
        {"content": "Matrix edited note"}
    ),
    # --- categories --------------------------------------------------------
    ("POST", "/api/v1/categories/"): _static(
        {"name": "Matrix new category", "color": "#123456"}
    ),
    ("PATCH", "/api/v1/categories/{category_id}"): _static({"name": "Matrix renamed"}),
    # --- users -------------------------------------------------------------
    ("PATCH", "/api/v1/users/{user_id}"): _static({"full_name": "Matrix Renamed"}),
    ("PATCH", "/api/v1/users/{user_id}/contact-info"): _static({"phone": "11999990000"}),
    # --- roles --------------------------------------------------------
    ("POST", "/api/v1/roles/"): _static(
        {"name": "Matrix new type"}
    ),
    ("PATCH", "/api/v1/roles/{role_id}"): _static(
        {"name": "Matrix renamed type"}
    ),
    # --- tenants -----------------------------------------------------------
    ("POST", "/api/v1/tenants"): _static({"name": "Matrix new tenant"}),
    ("PATCH", "/api/v1/tenants/{tenant_id}"): _static({"name": "Matrix renamed tenant"}),
    ("POST", "/api/v1/tenants/{tenant_id}/members"): lambda w: {
        "user_id": str(w.outsider_user_id)
    },
    ("PATCH", "/api/v1/tenants/{tenant_id}/members/{user_id}"): _static(
        {"is_tenant_admin": True}
    ),
    # --- lots --------------------------------------------------------------
    ("POST", "/api/v1/lots/"): _static({"block": "B", "lot_number": "2"}),
    ("PUT", "/api/v1/lots/{lot_id}"): _static({"block": "A"}),
    ("POST", "/api/v1/lots/{lot_id}/users"): lambda w: {
        "user_id": str(w.outsider_user_id)
    },
    ("PATCH", "/api/v1/lots/{lot_id}/delinquency"): _static({"is_delinquent": True}),
    # --- residents ---------------------------------------------------------
    ("POST", "/api/v1/lots/{lot_id}/residents"): _static(
        {"full_name": "Matrix New Resident", "cpf": _cpf(200)}
    ),
    ("PUT", "/api/v1/residents/{resident_id}"): _static(
        {"full_name": "Matrix Renamed Resident"}
    ),
    ("POST", "/api/v1/residents/{resident_id}/link-user"): lambda w: {
        "user_id": str(w.outsider_user_id)
    },
    ("POST", "/api/v1/residents/{resident_id}/unlink-user"): NO_BODY,
    # --- visitors ----------------------------------------------------------
    ("POST", "/api/v1/visitors"): _static({"full_name": "Matrix New Visitor"}),
    ("PUT", "/api/v1/visitors/{visitor_id}"): _static(
        {"full_name": "Matrix Renamed Visitor"}
    ),
    # --- authorizations ----------------------------------------------------
    ("POST", "/api/v1/lots/{lot_id}/authorizations"): lambda w: {
        "visitor_id": str(w.visitor_id)
    },
    ("PUT", "/api/v1/authorizations/{auth_id}/revoke"): _static(
        {"reason": "Matrix revoke"}
    ),
    # --- gate --------------------------------------------------------------
    ("POST", "/api/v1/access-logs/check-in"): lambda w: {
        "visitor_id": str(w.visitor_id),
        "lot_id": str(w.lot_id),
        "authorization_id": str(w.authorization_id),
    },
    ("POST", "/api/v1/access-logs/check-out"): lambda w: {
        "access_log_id": str(w.access_log_id)
    },
    # --- occurrences -------------------------------------------------------
    ("POST", "/api/v1/occurrences"): _static(
        {
            "category": OccurrenceCategory.OTHER.value,
            "title": "Matrix new occurrence",
            "description": "Matrix new occurrence description",
        }
    ),
    ("PUT", "/api/v1/occurrences/{id}/status"): _static({"status": "UNDER_REVIEW"}),
    ("POST", "/api/v1/occurrences/{id}/timeline"): _static({"note": "Matrix note"}),
    # --- documents ---------------------------------------------------------
    ("POST", "/api/v1/documents"): lambda w: {
        "folder_id": str(w.folder_id),
        "title": "Matrix new document",
        "file_url": "http://null/new.pdf",
        "file_size_bytes": 1,
    },
    ("POST", "/api/v1/documents/{id}/download"): NO_BODY,
    ("POST", "/api/v1/documents/{id}/versions"): _static(
        {"file_url": "http://null/v2.pdf", "file_size_bytes": 2}
    ),
    ("POST", "/api/v1/documents/folders"): _static(
        # `allowed_role_ids` is required on create since IAM F5 (§6).
        {"name": "Matrix New Folder", "allowed_role_ids": []}
    ),
    ("PUT", "/api/v1/documents/folders/{id}"): _static({"name": "Matrix Renamed Folder"}),
    # --- assemblies --------------------------------------------------------
    ("POST", "/api/v1/assemblies/"): lambda _w: {
        "title": "Matrix new assembly",
        "type": AssemblyType.AGE.value,
        "held_on": _today(),
    },
    ("PATCH", "/api/v1/assemblies/{assembly_id}"): _static(
        {"title": "Matrix renamed assembly"}
    ),
    ("POST", "/api/v1/assemblies/{assembly_id}/close"): NO_BODY,
    ("POST", "/api/v1/assemblies/{assembly_id}/minutes/save"): NO_BODY,
    # --- votes -------------------------------------------------------------
    ("POST", "/api/v1/votes/"): lambda _w: {
        "kind": VoteKind.ENQUETE.value,
        "title": "Matrix new poll",
        "vote_type": VoteType.SINGLE_CHOICE.value,
        "closes_at": _future(days=7),
        "options": [{"label": "Yes"}, {"label": "No"}],
    },
    ("PATCH", "/api/v1/votes/{vote_id}"): _static({"title": "Matrix renamed poll"}),
    ("POST", "/api/v1/votes/{vote_id}/close"): NO_BODY,
    ("POST", "/api/v1/votes/{vote_id}/ballots"): lambda w: {
        "selected_option_ids": [str(w.vote_option_id)]
    },
    ("POST", "/api/v1/votes/{vote_id}/ballots/retract"): _static({}),
    ("POST", "/api/v1/lots/{lot_id}/voter-eligibility"): lambda w: {
        "user_id": str(w.outsider_user_id)
    },
    # --- finance -----------------------------------------------------------
    ("POST", "/api/v1/finance/categories"): _static(
        {"name": "Matrix new finance category", "type": TransactionType.INCOME.value}
    ),
    ("PUT", "/api/v1/finance/categories/{id}"): _static(
        {"name": "Matrix renamed finance category"}
    ),
    ("POST", "/api/v1/finance/budget-lines"): lambda w: {
        "category_id": str(w.finance_category_id),
        "fiscal_year": _now().year,
        "planned_amount": 500.0,
    },
    ("PUT", "/api/v1/finance/budget-lines/{id}"): _static({"planned_amount": 750.0}),
    ("POST", "/api/v1/finance/transactions"): lambda w: {
        "type": TransactionType.EXPENSE.value,
        "category_id": str(w.finance_category_id),
        "description": "Matrix new transaction",
        "amount": 5.0,
        "transaction_date": _today(),
    },
    ("PUT", "/api/v1/finance/transactions/{id}"): _static(
        {"description": "Matrix renamed transaction"}
    ),
    ("POST", "/api/v1/finance/transactions/{id}/invoice"): _static(
        Upload("file", "invoice.pdf", "application/pdf")
    ),
    # --- projects ----------------------------------------------------------
    ("POST", "/api/v1/projects"): _static({"title": "Matrix new project"}),
    ("PUT", "/api/v1/projects/{id}"): _static({"title": "Matrix renamed project"}),
    ("POST", "/api/v1/projects/{id}/milestones"): _static(
        {"title": "Matrix new milestone"}
    ),
    ("PUT", "/api/v1/projects/{id}/milestones/{milestone_id}"): _static(
        {"title": "Matrix renamed milestone"}
    ),
    ("POST", "/api/v1/projects/{id}/updates"): _static(
        {"title": "Matrix new update", "content": "Matrix new update content"}
    ),
    # --- announcements -----------------------------------------------------
    ("POST", "/api/v1/announcements"): _static(
        {"title": "Matrix new announcement", "content": "Matrix content"}
    ),
    ("PUT", "/api/v1/announcements/{id}"): _static({"title": "Matrix renamed"}),
    ("POST", "/api/v1/announcements/{id}/media"): _static(
        Upload("file", "matrix.jpg", "image/jpeg")
    ),
    ("POST", "/api/v1/announcements/{id}/comments"): _static(
        {"content": "Matrix announcement comment"}
    ),
    ("POST", "/api/v1/announcements/{id}/read"): NO_BODY,
    # --- feedback ----------------------------------------------------------
    ("POST", "/api/v1/feedback"): _static(
        {"category": FeedbackCategory.SUGGESTION.value, "message": "Matrix feedback"}
    ),
    ("PUT", "/api/v1/feedback/{id}/respond"): _static(
        {"board_response": "Matrix board response"}
    ),
    # --- spaces & reservations --------------------------------------------
    ("POST", "/api/v1/reservable-spaces/"): _static({"name": "Matrix New Space"}),
    ("PATCH", "/api/v1/reservable-spaces/{space_id}"): _static(
        {"name": "Matrix Renamed Space"}
    ),
    ("POST", "/api/v1/space-reservations/"): lambda w: {
        "space_id": str(w.space_id),
        "start_time": _future(days=5),
        "end_time": _future(days=5, hours=2),
    },
    ("POST", "/api/v1/space-reservations/{reservation_id}/approve"): _static({}),
    ("POST", "/api/v1/space-reservations/{reservation_id}/reject"): _static(
        {"reason": "Matrix reject"}
    ),
    ("POST", "/api/v1/space-reservations/{reservation_id}/cancel"): NO_BODY,
    # --- packages ----------------------------------------------------------
    ("POST", "/api/v1/packages"): lambda w: {
        "lot_id": str(w.lot_id),
        "description": "Matrix new package",
    },
    ("POST", "/api/v1/packages/{package_id}/pickup"): _static(
        {"picked_up_by_name": "Matrix Receiver"}
    ),
    # --- assets & inventory ------------------------------------------------
    ("POST", "/api/v1/assets"): _static(
        {
            "name": "Matrix new asset",
            "category": AssetCategory.OUTROS.value,
            "location": "Matrix location",
        }
    ),
    ("PUT", "/api/v1/assets/{asset_id}"): _static({"name": "Matrix renamed asset"}),
    ("POST", "/api/v1/assets/{asset_id}/movements"): _static(
        {
            "movement_type": MovementType.ENTRADA.value,
            "quantity": 1,
            "reason": "Matrix movement",
        }
    ),
    # --- purchases ---------------------------------------------------------
    ("POST", "/api/v1/purchase-requests"): _static({"title": "Matrix new request"}),
    ("PUT", "/api/v1/purchase-requests/{request_id}"): _static(
        {"title": "Matrix renamed request"}
    ),
    ("POST", "/api/v1/purchase-requests/{request_id}/quotes"): _static(
        {"supplier_name": "Matrix Supplier B", "unit_price": 20.0, "quantity": 2}
    ),
    ("PUT", "/api/v1/purchase-requests/{request_id}/quotes/{quote_id}"): _static(
        {"supplier_name": "Matrix Supplier C"}
    ),
    ("POST", "/api/v1/purchase-requests/{request_id}/decision"): lambda w: {
        "quote_id": str(w.quote_id),
        "justification": "Matrix decision justification",
    },
    ("POST", "/api/v1/purchase-requests/{request_id}/cancel"): NO_BODY,
    # --- uploads -----------------------------------------------------------
    ("POST", "/api/v1/uploads/photo"): _static(
        Upload(
            "file",
            "matrix.jpg",
            "image/jpeg",
            form={"entity_type": EntityType.RESIDENT.value},
        )
    ),
    ("PUT", "/api/v1/uploads/photos/{photo_id}/approve"): NO_BODY,
    ("PUT", "/api/v1/uploads/photos/{photo_id}/reject"): _static(
        {"rejection_reason": "Matrix rejection reason"}
    ),
    # --- access control ----------------------------------------------------
    ("POST", "/api/v1/access-control/devices"): _static(
        {"name": "Matrix New Device", "location": "Gate"}
    ),
    ("PUT", "/api/v1/access-control/devices/{device_id}/status"): _static(
        {"status": "ONLINE"}
    ),
    ("POST", "/api/v1/access-control/devices/{device_id}/regenerate-key"): NO_BODY,
    (
        "POST",
        "/api/v1/access-control/residents/{resident_id}/facial-template/sync",
    ): NO_BODY,
    # --- billing (APRAS-40 §5.1) -------------------------------------------
    # The complete desired CONTRACTED set. An empty list is shape-valid and
    # semantically the "cancel everything the plan covers" request, so the
    # cell measures authorization and nothing else. Without this entry the
    # ADMINISTRATOR cell would answer 422 rather than the 404 the §4.6
    # unmanaged world owes it, and the semantic oracle forbids a permitted
    # 422.
    ("PUT", "/api/v1/subscription/modules"): _static({"active_modules": []}),
    # --- infractions (APRAS-44 §11) ----------------------------------------
    # Nine entries: every POST/PUT of the module's 18 routes. The one DELETE
    # and the eight GETs contribute none -- 1 + 8 + 9 = 18.
    #
    # Every body that names an object resolves it from the seeded world and
    # must satisfy §7.7, or the create cells would record 422 instead of 201
    # and measure request shape instead of authorization: `rule_id` names the
    # **active** `world.infraction_rule` and `responsible_resident_id` names a
    # resident **of** `world.lot`.
    ("POST", "/api/v1/infraction-rules"): _static(
        {
            "article": "art. 99",
            "origin": InfractionRuleOrigin.ESTATUTO.value,
            "description": "Matrix new infraction rule",
            "recidivism_window_days": 180,
        }
    ),
    ("PUT", "/api/v1/infraction-rules/{rule_id}"): _static(
        {"description": "Matrix renamed infraction rule"}
    ),
    ("PUT", "/api/v1/infraction-rules/{rule_id}/policy"): _static(
        {"steps": [{"step_order": 1, "action": InfractionStepAction.AVISO.value}]}
    ),
    ("PUT", "/api/v1/infraction-settings"): _static({"condo_fee_amount": 100.0}),
    ("POST", "/api/v1/infractions"): lambda w: {
        "rule_id": str(w.infraction_rule_id),
        "lot_id": str(w.lot_id),
        "responsible_resident_id": str(w.resident_id),
        "occurred_on": _today(),
        "description": "Matrix new infraction",
    },
    # `lot_id` is omitted, so the promotion cell exercises §7.4's ordinary
    # case -- `world.occurrence.lot_id` is set.
    ("POST", "/api/v1/infractions/from-occurrence/{occurrence_id}"): lambda w: {
        "rule_id": str(w.infraction_rule_id),
        "responsible_resident_id": str(w.resident_id),
    },
    ("POST", "/api/v1/infractions/{infraction_id}/stages"): _static(
        {"note": "Matrix stage note"}
    ),
    ("POST", "/api/v1/infractions/{infraction_id}/contestation"): _static(
        {"body": "Matrix contestation body"}
    ),
    # `lot_id` omitted: §4.4 makes it optional audit context.
    ("POST", "/api/v1/infractions/cycles/close"): lambda w: {
        "rule_id": str(w.infraction_rule_id),
        "responsible_resident_id": str(w.resident_id),
        "justification": "Matrix cycle close justification",
    },
}


# ---------------------------------------------------------------------------
# Running one cell (§6.3)
# ---------------------------------------------------------------------------


def resolve_path(world: MatrixWorld, path: str) -> str:
    """Substitute every `{name}` in `path` from `PATH_PARAMS`."""
    url = path
    for name in re.findall(r"\{(\w+)\}", path):
        url = url.replace("{" + name + "}", PATH_PARAMS[(path, name)](world))
    return url


def run_cell(client: TestClient, world: MatrixWorld, role: str, method: str, path: str) -> int:
    """Issue one real HTTP request for a cell and return its status code."""
    url = resolve_path(world, path)
    headers = {
        "Authorization": f"Bearer {world.tokens[role]}",
        "X-Tenant-Id": str(DEFAULT_TENANT_ID),
    }
    kwargs: dict[str, Any] = {}
    if (method, path) in QUERY_PARAMS:
        kwargs["params"] = QUERY_PARAMS[(method, path)](world)
    if (method, path) in REQUEST_BODIES:
        spec = REQUEST_BODIES[(method, path)]
        payload = spec if isinstance(spec, _NoBody) else spec(world)
        if isinstance(payload, Upload):
            kwargs["files"] = {
                payload.field_name: (payload.filename, _FILE_BYTES, payload.content_type)
            }
            if payload.form:
                kwargs["data"] = payload.form
        elif not isinstance(payload, _NoBody):
            kwargs["json"] = payload
    response = client.request(method, url, headers=headers, **kwargs)
    return response.status_code


@contextmanager
def cell_client(engine: Engine) -> Iterator[TestClient]:
    """A `TestClient` whose every write is undone when the cell ends.

    The connection-level transaction is the outer scope; the session joins it
    with `join_transaction_mode="create_savepoint"`, so a handler's `commit()`
    releases a savepoint rather than committing the outer transaction, and the
    closing `rollback()` restores the world exactly.
    """
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    session.info[REQUEST_SCOPED_KEY] = True

    def _override() -> Session:
        return session

    app.dependency_overrides[get_session] = _override
    try:
        yield TestClient(app, raise_server_exceptions=False)
    finally:
        app.dependency_overrides.clear()
        session.close()
        transaction.rollback()
        connection.close()


@contextmanager
def matrix_engine(database_path: str) -> Iterator[Engine]:
    """One SQLite **file** engine with the schema created and the world seeded.

    A file, not `:memory:`, so a second connection sees the same data without
    `StaticPool` tricks. Rate limiting is disabled for the same reason every
    other suite disables it: 1080 requests would otherwise trip it.

    The two listeners are SQLAlchemy's documented pysqlite recipe ("Serializable
    isolation / Savepoints / Transactional DDL"): the DBAPI driver otherwise
    swallows `BEGIN`, which silently breaks `SAVEPOINT` and would let a cell's
    committed writes survive the outer `rollback()` -- i.e. would break the one
    isolation mechanism §6.2 permits. It is a property of the *driver*, not of
    the application, and it changes no application behaviour.
    """
    app.state.limiter.enabled = False
    engine = create_engine(
        f"sqlite:///{database_path}", connect_args={"check_same_thread": False}
    )

    @event.listens_for(engine, "connect")
    def _disable_implicit_begin(dbapi_connection, _record) -> None:
        dbapi_connection.isolation_level = None

    @event.listens_for(engine, "begin")
    def _emit_begin(connection) -> None:
        connection.exec_driver_sql("BEGIN")

    SQLModel.metadata.create_all(engine)
    try:
        yield engine
    finally:
        engine.dispose()


def seed_once(engine: Engine) -> MatrixWorld:
    """Build and commit the world exactly once. 1206 cells, one world."""
    with Session(engine) as session:
        return build_world(session)
