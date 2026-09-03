"""Cross-tenant isolation matrix (APRAS-42 §9.1).

Every test here drives the real application through ``tenant_client``, whose
override gives **each request its own SQLAlchemy Session** — exactly what
``app.db.get_session`` does in production. Tenant-B rows are seeded and
inspected through ``raw_session``, a separate unfiltered/unstamped session, so
they never enter a request session's identity map.

If ``test_harness_gives_each_request_its_own_session`` fails, **every 404 in
this module is meaningless**: a shared session would answer a by-id lookup out
of its identity map without ever issuing the filtered SELECT the assertion is
about.
"""

import ast
import importlib
import io
import os
import pkgutil
import uuid
from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from pydantic import BaseModel
from sqlmodel import Session, SQLModel, select

import app.schemas
from app.api.deps import get_effective_role_ids
from app.core.security import create_access_token, get_password_hash
from app.core.tenant_context import TENANT_SCOPED_MODELS, acting_tenant_scope
from app.models.access_control import AccessDevice, FacialAccessEvent, FacialTemplate
from app.models.announcement import Announcement, AnnouncementComment, AnnouncementMedia
from app.models.asset import Asset, InventoryMovement
from app.models.category import Category
from app.models.document import AssociationDocument, DocumentFolder
from app.models.enums import (
    AnnouncementMediaType,
    AssemblyType,
    AssetCategory,
    EntityType,
    FacialTemplateSyncStatus,
    FeedbackCategory,
    LotAssociationType,
    MovementType,
    OccurrenceCategory,
    PhotoApprovalStatus,
    TransactionType,
    VoteKind,
    VoteType,
)
from app.models.feedback import Feedback
from app.models.finance import BudgetLine, FinanceCategory, FinancialTransaction
from app.models.lot import Lot, UserLotLink
from app.models.media_asset import MediaAsset
from app.models.occurrence import Occurrence
from app.models.package import Package
from app.models.project import ConstructionProject, ProjectMilestone, ProjectUpdate
from app.models.purchase import PurchaseQuote, PurchaseQuoteDecision, PurchaseRequest
from app.models.reservation import ReservableSpace, SpaceReservation
from app.models.resident import Resident
from app.models.role import Role
from app.models.task import Task
from app.models.tenant import DEFAULT_TENANT_ID, Tenant, UserTenantLink
from app.models.user import User
from app.models.visitor import AccessLog, Visitor, VisitorAuthorization
from app.models.voting import Assembly, LotVoterEligibility, Vote
from app.services.tenant_service import LEGACY_ROLE_NAMES
from tests.conftest import make_user
from tests.test_tenant_models import INHERITED_TABLES

TENANT_A = DEFAULT_TENANT_ID


def _now() -> datetime:
    """Naive UTC `now`, matching what every model in this codebase stores."""
    return datetime.now(UTC).replace(tzinfo=None)


def _today() -> date:
    """Today in UTC, as a naive date."""
    return _now().date()


def _auth(user: User, tenant_id=None) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {create_access_token(user.id)}"}
    if tenant_id is not None:
        headers["X-Tenant-Id"] = str(tenant_id)
    return headers


def _ids(payload) -> set[str]:
    """Collect the `id` of every row in a list or paginated response body."""
    rows = payload.get("items", []) if isinstance(payload, dict) else payload
    return {row["id"] for row in rows if isinstance(row, dict) and "id" in row}


def _png_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (8, 8), color="blue").save(buffer, format="PNG")
    return buffer.getvalue()


# ---------------------------------------------------------------------------
# Seeding — one row of every scoped entity, in both tenants
# ---------------------------------------------------------------------------


def _seed_tenant(raw: Session, tenant_id, actor: User, tag: str) -> dict:  # noqa: PLR0915
    """Seed one row of every tenant-scoped entity (plus the child rows the
    matrix needs) into `tenant_id`, through the unfiltered raw session.

    Deliberately one long, flat function (`PLR0915` waived): it seeds exactly
    one row per tenant-scoped model, so its length is the number of scoped
    models. Splitting it would only move the same statements behind a
    parameter list of a dozen interdependent locals.
    """
    rows: dict[str, object] = {}
    visitor_cpf, resident_cpf = (
        ("11122233396", "44455566619") if tag == "A" else ("77788899941", "12345678062")
    )

    def add(key, obj):
        obj.tenant_id = tenant_id
        raw.add(obj)
        rows[key] = obj
        return obj

    category = add("category", Category(name=f"Cat {tag}", color="#123456"))
    add("role", Role(name=f"Type {tag}",))
    lot = add("lot", Lot(block=f"B{tag}", lot_number=f"{tag}1"))
    reservable = add("reservable_space", ReservableSpace(name=f"Space {tag}"))
    folder = add("document_folder", DocumentFolder(name=f"Folder {tag}"))
    finance_category = add(
        "finance_category",
        FinanceCategory(name=f"Fin {tag}", type=TransactionType.INCOME),
    )
    asset = add(
        "asset",
        Asset(
            name=f"Asset {tag}",
            category=AssetCategory.FERRAMENTAS,
            location=f"Loc {tag}",
            asset_tag=f"TAG-{tag}",
            quantity=5,
        ),
    )
    visitor = add("visitor", Visitor(full_name=f"Visitor {tag}", cpf=visitor_cpf))
    device = add(
        "access_device",
        AccessDevice(
            name=f"Device {tag}",
            device_key=f"device-key-{tag}",
            created_by_id=actor.id,
        ),
    )
    project = add(
        "construction_project", ConstructionProject(title=f"Project {tag}")
    )
    announcement = add(
        "announcement",
        Announcement(title=f"News {tag}", content="body", author_id=actor.id),
    )
    raw.commit()

    add(
        "task", Task(title=f"Task {tag}", created_by_id=actor.id, category_id=category.id)
    )
    resident = add(
        "resident",
        Resident(lot_id=lot.id, full_name=f"Resident {tag}", cpf=resident_cpf),
    )
    add("package", Package(lot_id=lot.id, received_by_id=actor.id))
    add(
        "space_reservation",
        SpaceReservation(
            space_id=reservable.id,
            reserved_by_id=actor.id,
            start_time=_now() + timedelta(days=1),
            end_time=_now() + timedelta(days=1, hours=2),
        ),
    )
    add(
        "association_document",
        AssociationDocument(
            folder_id=folder.id,
            title=f"Doc {tag}",
            file_url=f"http://example.test/{tag}.pdf",
            file_size_bytes=10,
            uploaded_by_id=actor.id,
        ),
    )
    add(
        "budget_line",
        BudgetLine(
            category_id=finance_category.id, fiscal_year=2030, planned_amount=100.0
        ),
    )
    add(
        "financial_transaction",
        FinancialTransaction(
            type=TransactionType.INCOME,
            category_id=finance_category.id,
            description=f"Tx {tag}",
            amount=50.0,
            transaction_date=_today(),
            created_by_id=actor.id,
        ),
    )
    add(
        "inventory_movement",
        InventoryMovement(
            asset_id=asset.id,
            movement_type=MovementType.ENTRADA,
            quantity=1,
            previous_quantity=5,
            new_quantity=6,
            performed_by_id=actor.id,
            reason=f"Move {tag}",
        ),
    )
    authorization = add(
        "visitor_authorization",
        VisitorAuthorization(
            visitor_id=visitor.id, lot_id=lot.id, authorizer_user_id=actor.id
        ),
    )
    add("access_log", AccessLog(visitor_id=visitor.id, lot_id=lot.id))
    add(
        "occurrence",
        Occurrence(
            protocol_number=f"OC-{tag}",
            category=OccurrenceCategory.OTHER,
            title=f"Occ {tag}",
            description="desc",
            reporter_id=actor.id,
        ),
    )
    add("feedback", Feedback(category=FeedbackCategory.SUGGESTION, message=f"Fb {tag}"))
    add(
        "media_asset",
        MediaAsset(
            entity_type=EntityType.RESIDENT,
            entity_id=resident.id,
            file_path=f"media/{tag}.png",
            url=f"http://example.test/{tag}.png",
            file_size_bytes=10,
            mime_type="image/png",
            uploaded_by_id=actor.id,
            status=PhotoApprovalStatus.PENDING_APPROVAL,
        ),
    )
    assembly = add(
        "assembly",
        Assembly(
            title=f"Assembly {tag}",
            type=AssemblyType.AGO,
            held_on=_today(),
            created_by_id=actor.id,
        ),
    )
    add(
        "purchase_request",
        PurchaseRequest(title=f"Purchase {tag}", requested_by_id=actor.id),
    )
    raw.commit()

    vote = add(
        "vote",
        Vote(
            kind=VoteKind.ENQUETE,
            title=f"Vote {tag}",
            vote_type=VoteType.SINGLE_CHOICE,
            closes_at=_now() + timedelta(days=5),
            created_by_id=actor.id,
            assembly_id=None,
        ),
    )
    raw.commit()

    # Child (inherited) rows: no tenant_id of their own, protected through
    # the scoped parents above.
    comment = AnnouncementComment(
        announcement_id=announcement.id, user_id=actor.id, content=f"Comment {tag}"
    )
    media = AnnouncementMedia(
        announcement_id=announcement.id,
        media_type=AnnouncementMediaType.IMAGE,
        url=f"http://example.test/{tag}-media.png",
        file_path=f"media/{tag}-media.png",
        mime_type="image/png",
        file_size_bytes=10,
        order_index=0,
    )
    milestone = ProjectMilestone(
        project_id=project.id, title=f"Milestone {tag}", order_index=0
    )
    project_update = ProjectUpdate(
        project_id=project.id, author_id=actor.id, title=f"Update {tag}", content="c"
    )
    quote = PurchaseQuote(
        purchase_request_id=rows["purchase_request"].id,
        supplier_name=f"Supplier {tag}",
        unit_price=10.0,
        quantity=2,
        created_by_id=actor.id,
    )
    eligibility = LotVoterEligibility(lot_id=lot.id, user_id=actor.id)
    raw.add_all([comment, media, milestone, project_update, quote, eligibility])
    raw.commit()

    decision = PurchaseQuoteDecision(
        purchase_request_id=rows["purchase_request"].id,
        quote_id=quote.id,
        decided_by_id=actor.id,
        justification=f"Because {tag}",
    )
    template = FacialTemplate(
        resident_id=resident.id,
        media_asset_id=rows["media_asset"].id,
        sync_status=FacialTemplateSyncStatus.SYNCED,
        synced_at=_now(),
    )
    event = FacialAccessEvent(
        device_id=device.id,
        resident_id=resident.id,
        matched=True,
        access_granted=True,
        event_time=_now(),
    )
    raw.add_all([decision, template, event])
    raw.add(
        UserLotLink(
            user_id=actor.id,
            lot_id=lot.id,
            association_type=LotAssociationType.PROPRIETARIO,
        )
    )
    raw.commit()

    rows["announcement_comment"] = comment
    rows["announcement_media"] = media
    rows["project_milestone"] = milestone
    rows["project_update"] = project_update
    rows["purchase_quote"] = quote
    rows["purchase_quote_decision"] = decision
    rows["facial_template"] = template
    rows["facial_access_event"] = event
    rows["visitor_authorization"] = authorization
    rows["assembly"] = assembly
    rows["vote"] = vote
    return {key: (str(value.id), value.id) for key, value in rows.items()}


@pytest.fixture(name="seeded")
def seeded_fixture(
    session: Session,
    raw_session: Session,
    tenant_b: Tenant,
    user_in_tenant_a: User,
    user_in_tenant_b: User,
):
    """One row of every scoped entity in tenant A and in tenant B."""
    session.commit()
    a = _seed_tenant(raw_session, TENANT_A, user_in_tenant_a, "A")
    b = _seed_tenant(raw_session, tenant_b.id, user_in_tenant_b, "B")
    raw_session.commit()
    return {"a": a, "b": b}


# ---------------------------------------------------------------------------
# 0. Harness self-test — the rest of this module is void if this fails
# ---------------------------------------------------------------------------


def test_harness_gives_each_request_its_own_session(
    tenant_client: TestClient,
    raw_session: Session,
    tenant_b: Tenant,
    user_in_tenant_a: User,
):
    """Two consecutive requests must run on two distinct `Session` objects.

    Under a shared session, a tenant-B row seeded here would sit in the
    request session's identity map and `session.get()` would return it
    without ever issuing the SELECT the tenant filter constrains — making
    every by-id 404 assertion in this module vacuous.
    """
    foreign = Category(name="B seed", color="#000000", tenant_id=tenant_b.id)
    raw_session.add(foreign)
    raw_session.commit()

    headers = _auth(user_in_tenant_a)
    assert tenant_client.get("/api/v1/categories/", headers=headers).status_code == 200
    assert tenant_client.get("/api/v1/categories/", headers=headers).status_code == 200

    sessions = tenant_client.request_sessions
    assert len(sessions) >= 2
    assert sessions[-1] is not sessions[-2], "two requests shared one Session"
    ids = tenant_client.request_session_ids
    assert ids[-1] != ids[-2], "two requests shared one Session"
    assert foreign in raw_session, "the tenant-B row must live in raw_session only"


# ---------------------------------------------------------------------------
# 1. List matrix
# ---------------------------------------------------------------------------

COLLECTION_ENDPOINTS = [
    ("/api/v1/tasks/", "task"),
    ("/api/v1/categories/", "category"),
    ("/api/v1/roles/", "role"),
    ("/api/v1/lots/", "lot"),
    ("/api/v1/visitors", "visitor"),
    ("/api/v1/access-logs", "access_log"),
    ("/api/v1/occurrences", "occurrence"),
    ("/api/v1/documents", "association_document"),
    ("/api/v1/documents/folders", "document_folder"),
    ("/api/v1/uploads/photos/pending", "media_asset"),
    ("/api/v1/access-control/devices", "access_device"),
    ("/api/v1/access-control/events", "facial_access_event"),
    ("/api/v1/projects", "construction_project"),
    ("/api/v1/announcements", "announcement"),
    ("/api/v1/finance/categories", "finance_category"),
    ("/api/v1/finance/transactions", "financial_transaction"),
    ("/api/v1/finance/budget-lines?fiscal_year=2030", "budget_line"),
    ("/api/v1/feedback", "feedback"),
    ("/api/v1/reservable-spaces/", "reservable_space"),
    ("/api/v1/space-reservations/", "space_reservation"),
    ("/api/v1/packages?lot_id={lot}", "package"),
    ("/api/v1/packages/queue", "package"),
    ("/api/v1/assemblies/", "assembly"),
    ("/api/v1/votes/", "vote"),
    ("/api/v1/assets", "asset"),
    ("/api/v1/inventory-movements", "inventory_movement"),
    ("/api/v1/purchase-requests", "purchase_request"),
]


@pytest.mark.parametrize(("path", "entity"), COLLECTION_ENDPOINTS)
def test_collections_never_return_another_tenants_rows(
    tenant_client: TestClient, seeded, user_in_tenant_a: User, path: str, entity: str
):
    """A tenant-A member sees tenant-A rows and no tenant-B row."""
    url = path.format(lot=seeded["a"]["lot"][0])
    response = tenant_client.get(url, headers=_auth(user_in_tenant_a))
    assert response.status_code == 200, response.text
    returned = _ids(response.json())
    assert seeded["a"][entity][0] in returned, f"{url} hid the caller's own row"
    assert seeded["b"][entity][0] not in returned, f"{url} leaked a tenant-B row"


@pytest.mark.parametrize(("path", "entity"), COLLECTION_ENDPOINTS)
def test_administrator_with_header_sees_the_other_tenant(
    tenant_client: TestClient,
    seeded,
    member_admin: User,
    tenant_b: Tenant,
    path: str,
    entity: str,
):
    """`X-Tenant-Id: <B>` gives an ADMINISTRATOR tenant-B rows, and only those."""
    url = path.format(lot=seeded["b"]["lot"][0])
    response = tenant_client.get(url, headers=_auth(member_admin, tenant_b.id))
    assert response.status_code == 200, response.text
    returned = _ids(response.json())
    assert seeded["b"][entity][0] in returned, f"{url} hid the tenant-B row"
    assert seeded["a"][entity][0] not in returned, f"{url} leaked a tenant-A row"


def test_lot_keyed_collections(
    tenant_client: TestClient,
    seeded,
    raw_session: Session,
    user_in_tenant_a: User,
    user_in_tenant_b: User,
):
    """The residents collection is lot-keyed, so its isolation shape differs."""
    headers = _auth(user_in_tenant_a)
    a_lot = seeded["a"]["lot"][0]
    b_lot = seeded["b"]["lot"][0]

    assert (
        tenant_client.get(f"/api/v1/lots/{b_lot}/residents", headers=headers).status_code
        == 404
    )
    response = tenant_client.get(f"/api/v1/lots/{a_lot}/residents", headers=headers)
    assert response.status_code == 200
    returned = _ids(response.json())
    assert seeded["a"]["resident"][0] in returned
    assert seeded["b"]["resident"][0] not in returned

    assert (
        tenant_client.get(
            f"/api/v1/lots/{b_lot}/authorizations", headers=headers
        ).status_code
        == 404
    )

    # 200-empty, not 404: this route never loads its Lot, and the `.join(Lot)`
    # fix deliberately preserves its current answer for an unknown lot id.
    response = tenant_client.get(
        f"/api/v1/lots/{b_lot}/voter-eligibility", headers=headers
    )
    assert response.status_code == 200
    assert response.json() == []

    # The write sibling of the same route: 404, not a 204 that silently
    # deletes another condominium's row (and not an existence oracle for
    # tenant-B `(lot, user)` pairs either).
    assert (
        tenant_client.delete(
            f"/api/v1/lots/{b_lot}/voter-eligibility/{user_in_tenant_b.id}",
            headers=headers,
        ).status_code
        == 404
    )
    raw_session.expire_all()
    surviving = raw_session.exec(
        select(LotVoterEligibility).where(
            LotVoterEligibility.lot_id == seeded["b"]["lot"][1],
            LotVoterEligibility.user_id == user_in_tenant_b.id,
        )
    ).first()
    assert surviving is not None, "the tenant-B eligibility row was deleted"


# ---------------------------------------------------------------------------
# 2. By-id matrix
# ---------------------------------------------------------------------------

BY_ID_CASES = [
    ("GET", "/api/v1/lots/{id}", "lot", None),
    ("PUT", "/api/v1/lots/{id}", "lot", {"block": "X", "lot_number": "9"}),
    ("DELETE", "/api/v1/lots/{id}", "lot", None),
    ("PATCH", "/api/v1/tasks/{id}", "task", {"title": "hijack"}),
    ("DELETE", "/api/v1/tasks/{id}", "task", None),
    ("GET", "/api/v1/tasks/{id}/comments", "task", None),
    ("PATCH", "/api/v1/categories/{id}", "category", {"name": "hijack"}),
    ("DELETE", "/api/v1/categories/{id}", "category", None),
    ("PATCH", "/api/v1/roles/{id}", "role", {"name": "hijack"}),
    ("DELETE", "/api/v1/roles/{id}", "role", None),
    ("GET", "/api/v1/residents/{id}", "resident", None),
    ("DELETE", "/api/v1/residents/{id}", "resident", None),
    ("GET", "/api/v1/visitors/{id}", "visitor", None),
    ("GET", "/api/v1/authorizations/{id}", "visitor_authorization", None),
    ("GET", "/api/v1/authorizations/{id}/qr-code", "visitor_authorization", None),
    ("GET", "/api/v1/occurrences/{id}", "occurrence", None),
    ("DELETE", "/api/v1/documents/{id}", "association_document", None),
    ("DELETE", "/api/v1/documents/folders/{id}", "document_folder", None),
    ("GET", "/api/v1/projects/{id}", "construction_project", None),
    ("DELETE", "/api/v1/projects/{id}", "construction_project", None),
    ("GET", "/api/v1/announcements/{id}", "announcement", None),
    ("DELETE", "/api/v1/announcements/{id}", "announcement", None),
    ("GET", "/api/v1/announcements/{id}/comments", "announcement", None),
    ("GET", "/api/v1/finance/transactions/{id}", "financial_transaction", None),
    ("DELETE", "/api/v1/finance/transactions/{id}", "financial_transaction", None),
    ("DELETE", "/api/v1/finance/budget-lines/{id}", "budget_line", None),
    ("GET", "/api/v1/feedback/{id}", "feedback", None),
    ("PATCH", "/api/v1/reservable-spaces/{id}", "reservable_space", {"name": "x"}),
    ("DELETE", "/api/v1/reservable-spaces/{id}", "reservable_space", None),
    ("GET", "/api/v1/space-reservations/{id}", "space_reservation", None),
    ("GET", "/api/v1/packages/{id}", "package", None),
    ("GET", "/api/v1/assemblies/{id}", "assembly", None),
    ("GET", "/api/v1/votes/{id}", "vote", None),
    ("GET", "/api/v1/votes/{id}/tally", "vote", None),
    ("GET", "/api/v1/assets/{id}", "asset", None),
    ("DELETE", "/api/v1/assets/{id}", "asset", None),
    ("GET", "/api/v1/purchase-requests/{id}", "purchase_request", None),
    ("DELETE", "/api/v1/purchase-requests/{id}", "purchase_request", None),
    ("GET", "/api/v1/uploads/photos/{id}", "media_asset", None),
    ("DELETE", "/api/v1/uploads/photos/{id}", "media_asset", None),
]


@pytest.mark.parametrize(("method", "template", "entity", "body"), BY_ID_CASES)
def test_by_id_access_to_another_tenant_is_404(
    tenant_client: TestClient,
    seeded,
    user_in_tenant_a: User,
    method: str,
    template: str,
    entity: str,
    body,
):
    """Every by-id verb on a tenant-B resource answers 404 to a tenant-A caller."""
    path = template.format(id=seeded["b"][entity][0])
    response = tenant_client.request(
        method, path, headers=_auth(user_in_tenant_a), json=body
    )
    assert response.status_code == 404, f"{method} {path} -> {response.status_code}"


@pytest.mark.parametrize(("method", "template", "entity", "body"), BY_ID_CASES)
def test_by_id_access_within_the_tenant_is_not_404(
    tenant_client: TestClient,
    seeded,
    user_in_tenant_a: User,
    method: str,
    template: str,
    entity: str,
    body,
):
    """The same verb on the caller's *own* tenant is reachable — proving the
    404 above comes from the tenant boundary, not from a broken route."""
    path = template.format(id=seeded["a"][entity][0])
    response = tenant_client.request(
        method, path, headers=_auth(user_in_tenant_a), json=body
    )
    assert response.status_code != 404, f"{method} {path} -> {response.status_code}"


# ---------------------------------------------------------------------------
# 3. Create stamping
# ---------------------------------------------------------------------------


def test_create_is_stamped_with_the_actors_tenant(
    tenant_client: TestClient,
    raw_session: Session,
    tenant_b: Tenant,
    user_in_tenant_b: User,
):
    """A create by a tenant-B actor persists `tenant_id == B`."""
    response = tenant_client.post(
        "/api/v1/categories/",
        headers=_auth(user_in_tenant_b),
        json={"name": "Created in B", "color": "#abcdef"},
    )
    assert response.status_code == 201, response.text

    raw_session.expire_all()
    row = raw_session.get(Category, uuid.UUID(response.json()["id"]))
    assert row.tenant_id == tenant_b.id


def test_forged_tenant_id_in_the_body_is_ignored(
    tenant_client: TestClient,
    raw_session: Session,
    tenant_b: Tenant,
    user_in_tenant_b: User,
):
    """`tenant_id` in a request body is never trusted."""
    response = tenant_client.post(
        "/api/v1/categories/",
        headers=_auth(user_in_tenant_b),
        json={"name": "Forged", "color": "#abcdef", "tenant_id": str(TENANT_A)},
    )
    assert response.status_code == 201, response.text

    raw_session.expire_all()
    row = raw_session.get(Category, uuid.UUID(response.json()["id"]))
    assert row.tenant_id == tenant_b.id


def test_no_create_or_update_schema_declares_tenant_id():
    """Belt and braces on ER-3: the schema surface never accepts a tenant_id."""
    offenders = []
    for module_info in pkgutil.iter_modules(app.schemas.__path__):
        module = importlib.import_module(f"app.schemas.{module_info.name}")
        for name, obj in vars(module).items():
            if (
                isinstance(obj, type)
                and issubclass(obj, BaseModel)
                and name.endswith(("Create", "Update"))
                and "tenant_id" in obj.model_fields
            ):
                offenders.append(f"{module_info.name}.{name}")
    assert not offenders, offenders


def test_cross_tenant_fk_on_create_does_not_resolve(
    tenant_client: TestClient, seeded, user_in_tenant_a: User
):
    """A tenant-B `category_id` supplied on a task create never resolves: the
    response cannot expose the other tenant's category."""
    response = tenant_client.post(
        "/api/v1/tasks/",
        headers=_auth(user_in_tenant_a),
        json={"title": "Cross FK", "category_id": seeded["b"]["category"][0]},
    )
    if response.status_code < 400:
        assert response.json()["category_name"] is None


# ---------------------------------------------------------------------------
# 4. Child tables and aggregates
# ---------------------------------------------------------------------------


def test_child_table_writes_across_tenants_are_404(
    tenant_client: TestClient, seeded, user_in_tenant_a: User
):
    """Inherited tables are protected through their scoped parent."""
    headers = _auth(user_in_tenant_a)
    b = seeded["b"]

    assert (
        tenant_client.delete(
            f"/api/v1/announcements/comments/{b['announcement_comment'][0]}",
            headers=headers,
        ).status_code
        == 404
    )
    assert (
        tenant_client.delete(
            f"/api/v1/announcements/{b['announcement'][0]}/media/{b['announcement_media'][0]}",
            headers=headers,
        ).status_code
        == 404
    )
    assert (
        tenant_client.put(
            f"/api/v1/projects/{b['construction_project'][0]}/milestones/{b['project_milestone'][0]}",
            headers=headers,
            json={"title": "hijack"},
        ).status_code
        == 404
    )
    assert (
        tenant_client.delete(
            f"/api/v1/projects/{b['construction_project'][0]}/updates/{b['project_update'][0]}",
            headers=headers,
        ).status_code
        == 404
    )
    assert (
        tenant_client.get(
            f"/api/v1/votes/{b['vote'][0]}/tally", headers=headers
        ).status_code
        == 404
    )


def test_child_table_writes_within_the_tenant_still_work(
    tenant_client: TestClient, seeded, user_in_tenant_a: User
):
    """The same routes are reachable inside the caller's own tenant."""
    headers = _auth(user_in_tenant_a)
    a = seeded["a"]

    assert (
        tenant_client.put(
            f"/api/v1/projects/{a['construction_project'][0]}/milestones/{a['project_milestone'][0]}",
            headers=headers,
            json={"title": "renamed"},
        ).status_code
        == 200
    )
    assert (
        tenant_client.delete(
            f"/api/v1/announcements/comments/{a['announcement_comment'][0]}",
            headers=headers,
        ).status_code
        == 204
    )


def test_purchase_summary_excludes_the_other_tenant(
    tenant_client: TestClient, seeded, user_in_tenant_a: User, member_admin: User,
    tenant_b: Tenant,
):
    """The summary aggregates only the acting tenant's requests and quotes."""
    response = tenant_client.get(
        "/api/v1/purchase-requests/summary", headers=_auth(user_in_tenant_a)
    )
    assert response.status_code == 200
    assert response.json()["open_count"] == 1


def test_assets_summary_excludes_the_other_tenant(
    tenant_client: TestClient, seeded, user_in_tenant_a: User
):
    """Asset aggregates count only the acting tenant's assets."""
    response = tenant_client.get(
        "/api/v1/assets/summary", headers=_auth(user_in_tenant_a)
    )
    assert response.status_code == 200
    assert response.json()["total_assets"] == 1


def test_access_control_events_exclude_the_other_tenant(
    tenant_client: TestClient, seeded, user_in_tenant_a: User
):
    """`FacialAccessEvent` is inherited; the device join is what scopes it."""
    response = tenant_client.get(
        "/api/v1/access-control/events", headers=_auth(user_in_tenant_a)
    )
    assert response.status_code == 200
    body = response.json()
    assert seeded["b"]["facial_access_event"][0] not in _ids(body)
    assert body["total"] == 1


# ---------------------------------------------------------------------------
# 5. Gatekeeper / FacialTemplate
# ---------------------------------------------------------------------------


def test_facial_template_of_a_foreign_resident_is_404(
    tenant_client: TestClient, seeded, raw_session: Session, user_in_tenant_a: User
):
    """This route returns 200 with the tenant-B template body on master."""
    response = tenant_client.get(
        f"/api/v1/access-control/residents/{seeded['b']['resident'][0]}/facial-template",
        headers=_auth(user_in_tenant_a),
    )
    assert response.status_code == 404

    raw_session.expire_all()
    still_there = raw_session.get(FacialTemplate, seeded["b"]["facial_template"][1])
    assert still_there is not None, "the 404 must come from the boundary, not a delete"


def test_facial_template_of_an_unsynced_own_resident_is_200_null(
    tenant_client: TestClient,
    raw_session: Session,
    session: Session,
    user_in_tenant_a: User,
):
    """An existing resident of the acting tenant with no template: 200 null."""
    lot = Lot(block="Z", lot_number="1")
    raw_session.add(lot)
    raw_session.commit()
    resident = Resident(lot_id=lot.id, full_name="No Template", cpf="22233344405")
    raw_session.add(resident)
    raw_session.commit()

    response = tenant_client.get(
        f"/api/v1/access-control/residents/{resident.id}/facial-template",
        headers=_auth(user_in_tenant_a),
    )
    assert response.status_code == 200
    assert response.json() is None


def test_webhook_with_a_foreign_resident_is_indistinguishable_from_no_match(
    tenant_client: TestClient, seeded, raw_session: Session
):
    """A tenant-A device posting a tenant-B resident id must not confirm it."""
    response = tenant_client.post(
        "/api/v1/access-control/webhook/verification",
        headers={"X-Device-Key": "device-key-A"},
        json={"resident_id": seeded["b"]["resident"][0], "confidence_score": 0.99},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["matched"] is False
    assert body["access_granted"] is False
    assert body["resident_id"] is None

    raw_session.expire_all()
    event = raw_session.get(FacialAccessEvent, uuid.UUID(body["id"]))
    # `facial_access_event` inherits its tenant from `access_device`
    # (APRAS-41 keeps it free of a `tenant_id` of its own), so "stamped with
    # the device's tenant" is asserted through the device it hangs off.
    assert raw_session.get(AccessDevice, event.device_id).tenant_id == TENANT_A
    assert event.resident_id is None
    assert raw_session.get(FacialTemplate, seeded["b"]["facial_template"][1]) is not None


def test_webhook_with_its_own_tenants_resident_still_matches(
    tenant_client: TestClient, seeded, raw_session: Session
):
    """The happy path is unchanged and the event carries the device's tenant."""
    response = tenant_client.post(
        "/api/v1/access-control/webhook/verification",
        headers={"X-Device-Key": "device-key-A"},
        json={"resident_id": seeded["a"]["resident"][0], "confidence_score": 0.99},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["matched"] is True

    raw_session.expire_all()
    event = raw_session.get(FacialAccessEvent, uuid.UUID(body["id"]))
    assert raw_session.get(AccessDevice, event.device_id).tenant_id == TENANT_A


# ---------------------------------------------------------------------------
# 6. PORTEIRO
# ---------------------------------------------------------------------------


def test_porteiro_stays_inside_its_tenant(
    tenant_client: TestClient, seeded, session: Session
):
    """A gatekeeper's condo-wide flows are confined by the ambient filter."""
    porteiro = make_user(
        session,
        id=uuid.uuid4(),
        email="porteiro-a@test.com",
        full_name="Porteiro A",
        hashed_password=get_password_hash("password"),
        profile="PORTEIRO",
        cpf="70768527086",
    )
    session.add(porteiro)
    session.commit()
    session.add(UserTenantLink(user_id=porteiro.id, tenant_id=TENANT_A))
    session.commit()

    headers = _auth(porteiro)
    response = tenant_client.get("/api/v1/packages/queue", headers=headers)
    assert response.status_code == 200
    assert seeded["b"]["package"][0] not in _ids(response.json())

    response = tenant_client.post(
        "/api/v1/packages",
        headers=headers,
        json={"lot_id": seeded["b"]["lot"][0], "description": "cross"},
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# 7. Header semantics (§3)
# ---------------------------------------------------------------------------


def test_malformed_header_is_400(tenant_client: TestClient, user_in_tenant_a: User):
    response = tenant_client.get(
        "/api/v1/categories/",
        headers={**_auth(user_in_tenant_a), "X-Tenant-Id": "not-a-uuid"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid X-Tenant-Id header"


def test_empty_header_is_400(tenant_client: TestClient, user_in_tenant_a: User):
    response = tenant_client.get(
        "/api/v1/categories/", headers={**_auth(user_in_tenant_a), "X-Tenant-Id": ""}
    )
    assert response.status_code == 400


def test_unknown_tenant_is_404_for_an_administrator(
    tenant_client: TestClient, user_in_tenant_a: User
):
    response = tenant_client.get(
        "/api/v1/categories/", headers=_auth(user_in_tenant_a, uuid.uuid4())
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Tenant not found"


def test_unknown_tenant_is_403_for_everyone_else(
    tenant_client: TestClient, session: Session
):
    """A non-administrator is never told whether a tenant exists."""
    user = make_user(
        session,
        id=uuid.uuid4(),
        email="director-a@test.com",
        full_name="Director A",
        hashed_password=get_password_hash("password"),
        profile="DIRECTOR",
        cpf="45317828791",
    )
    session.add(user)
    session.commit()

    response = tenant_client.get("/api/v1/categories/", headers=_auth(user, uuid.uuid4()))
    assert response.status_code == 403
    assert response.json()["detail"] == "Not a member of the requested tenant"


def test_non_member_of_an_existing_tenant_is_403(
    tenant_client: TestClient, session: Session, tenant_b: Tenant
):
    user = make_user(
        session,
        id=uuid.uuid4(),
        email="director-b@test.com",
        full_name="Director B",
        hashed_password=get_password_hash("password"),
        profile="DIRECTOR",
        cpf="19100000034",
    )
    session.add(user)
    session.commit()
    session.add(UserTenantLink(user_id=user.id, tenant_id=TENANT_A))
    session.commit()

    response = tenant_client.get("/api/v1/categories/", headers=_auth(user, tenant_b.id))
    assert response.status_code == 403
    assert response.json()["detail"] == "Not a member of the requested tenant"


def test_inactive_tenant_is_403_even_for_an_administrator(
    tenant_client: TestClient,
    session: Session,
    tenant_b: Tenant,
    user_in_tenant_a: User,
):
    tenant_b.is_active = False
    session.add(tenant_b)
    session.commit()

    response = tenant_client.get(
        "/api/v1/categories/", headers=_auth(user_in_tenant_a, tenant_b.id)
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Tenant is inactive"


def test_single_membership_resolves_without_a_header(
    tenant_client: TestClient, seeded, user_in_tenant_b: User
):
    """One membership → that tenant, with no header at all."""
    response = tenant_client.get("/api/v1/categories/", headers=_auth(user_in_tenant_b))
    assert response.status_code == 200
    returned = _ids(response.json())
    assert seeded["b"]["category"][0] in returned
    assert seeded["a"]["category"][0] not in returned


def test_zero_memberships_fall_back_to_the_default_tenant(
    tenant_client: TestClient, seeded, session: Session
):
    """Zero memberships → the default tenant, which is what every existing
    test fixture relies on."""
    user = make_user(
        session,
        id=uuid.uuid4(),
        email="no-membership@test.com",
        full_name="No Membership",
        hashed_password=get_password_hash("password"),
        profile="ADMINISTRATOR",
        cpf="63311527079",
    )
    session.add(user)
    session.commit()

    response = tenant_client.get("/api/v1/categories/", headers=_auth(user))
    assert response.status_code == 200
    returned = _ids(response.json())
    assert seeded["a"]["category"][0] in returned
    assert seeded["b"]["category"][0] not in returned


def test_multiple_memberships_without_a_header_is_400(
    tenant_client: TestClient, member_admin: User
):
    response = tenant_client.get("/api/v1/categories/", headers=_auth(member_admin))
    assert response.status_code == 400
    assert "multiple tenants" in response.json()["detail"]


def test_member_with_a_header_gets_that_tenant(
    tenant_client: TestClient, seeded, member_admin: User, tenant_b: Tenant
):
    response = tenant_client.get(
        "/api/v1/categories/", headers=_auth(member_admin, tenant_b.id)
    )
    assert response.status_code == 200
    assert seeded["b"]["category"][0] in _ids(response.json())


# ---------------------------------------------------------------------------
# 8. The reviewed child-query allowlist (§6.3)
# ---------------------------------------------------------------------------

#: `file:function` sites that read an inherited (tenant_id-less) table.
#: Each carries a one-line justification for why it is safe. A new,
#: unreviewed child-table query fails this test.
REVIEWED_CHILD_QUERIES: dict[str, str] = {
    "app/api/v1/endpoints/tasks.py:update_comment": "parent Task loaded through the filtered session two lines above",
    "app/services/task_service.py:get_comments": "parent Task loaded and 404'd by the endpoint first",
    "app/services/task_service.py:get_history": "parent Task loaded and 404'd by the endpoint first",
    "app/services/announcement_service.py:_format_announcement_read": "operates on an Announcement already fetched through the filter",
    "app/services/announcement_service.py:delete_media": "parent Announcement loaded and 404'd first (APRAS-42 §6.1)",
    "app/services/announcement_service.py:list_comments": "parent Announcement loaded and 404'd first",
    "app/services/announcement_service.py:delete_comment": "joined to Announcement, which the filter scopes (APRAS-42 §6.1)",
    "app/services/announcement_service.py:mark_read": "parent Announcement loaded and 404'd first",
    "app/services/announcement_service.py:list_read_receipts": "parent Announcement loaded and 404'd first",
    "app/services/announcement_service.py:get_announcement": "parent Announcement loaded and 404'd first",
    "app/services/lot_service.py:get_lot_detail": "parent Lot loaded and 404'd first",
    "app/services/lot_service.py:link_user": "parent Lot loaded and 404'd first",
    "app/services/lot_service.py:unlink_user": "parent Lot loaded and 404'd first",
    "app/services/project_service.py:get_project_detail": "parent ConstructionProject loaded and 404'd first",
    "app/services/project_service.py:update_milestone": "parent ConstructionProject loaded and 404'd first (APRAS-42 §6.1)",
    "app/services/project_service.py:delete_milestone": "parent ConstructionProject loaded and 404'd first (APRAS-42 §6.1)",
    "app/services/project_service.py:delete_project_update": "parent ConstructionProject loaded and 404'd first (APRAS-42 §6.1)",
    "app/services/purchase_service.py:_get_quote_or_404": "parent PurchaseRequest loaded and 404'd first",
    "app/services/purchase_service.py:list_requests": "keyed on ids of already-filtered PurchaseRequest rows",
    "app/services/purchase_service.py:get_summary": "keyed on ids of already-filtered PurchaseRequest rows (APRAS-42 §6.2)",
    "app/services/access_control_service.py:sync_facial_template": "parent Resident loaded and 404'd first",
    "app/services/access_control_service.py:get_facial_template": "parent Resident loaded and 404'd first (APRAS-42 §6.2)",
    "app/services/access_control_service.py:process_verification_webhook": "gated on the Resident loaded under the device's tenant (APRAS-42 §6.4)",
    "app/services/access_control_service.py:list_events": "joined to AccessDevice, which the filter scopes (APRAS-42 §6.2)",
    "app/services/voting_service.py:_active_lot_ids": "joined to Lot (APRAS-42 §6.2)",
    "app/services/voting_service.py:get_lot_eligible_user_ids": "keyed on an already-filtered Lot",
    "app/services/voting_service.py:get_user_eligible_lot_ids": "joined to Lot (APRAS-42 §6.2)",
    "app/services/voting_service.py:_co_resident_user_ids": "joined to Lot (APRAS-42 §6.2)",
    "app/services/voting_service.py:list_lot_voter_eligibility": "joined to Lot (APRAS-42 §6.2)",
    "app/services/voting_service.py:set_lot_voter_eligibility": "parent Lot loaded and 404'd first",
    "app/services/voting_service.py:remove_lot_voter_eligibility": "joined to Lot (APRAS-42 §6.2)",
    "app/services/voting_service.py:_latest_ballot_for_key": "keyed on an already-filtered Vote",
    "app/services/voting_service.py:get_latest_ballots": "keyed on an already-filtered Vote",
    "app/services/voting_service.py:has_ballots": "keyed on an already-filtered Vote",
    "app/services/voting_service.py:get_delinquency_barred_lots": "keyed on the vote ids of an already-filtered Assembly",
    "app/services/resident_service.py:_check_lot_access": "joined to Lot (APRAS-42 §6.2)",
    "app/services/visitor_service.py:_check_lot_access": "joined to Lot (APRAS-42 §6.2)",
}


def _model_name_by_table() -> dict[str, str]:
    """``__tablename__`` -> model class name, over every mapped SQLModel."""
    return {
        mapper.local_table.name: mapper.class_.__name__
        for mapper in SQLModel._sa_registry.mappers  # noqa: SLF001
    }


#: The inherited (child) model names, **derived** from APRAS-41's authoritative
#: 20-table partition (``tests/test_tenant_models.INHERITED_TABLES``) rather
#: than hand-written, as spec §6.3 requires. A hand-written copy drifts: it
#: dropped ``TaskVisibleToLink`` once, which would have let an unreviewed
#: ``select(TaskVisibleToLink)`` slip past the regression below.
INHERITED_MODELS: tuple[str, ...] = tuple(
    sorted(_model_name_by_table()[table] for table in INHERITED_TABLES)
)

_APP_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app"
)


def _child_query_sites() -> dict[str, set[str]]:
    """`file:function` -> inherited models it reads, across services + endpoints."""
    sites: dict[str, set[str]] = {}
    roots = [
        os.path.join(_APP_DIR, "services"),
        os.path.join(_APP_DIR, "api", "v1", "endpoints"),
    ]
    for root in roots:
        for filename in sorted(os.listdir(root)):
            if not filename.endswith(".py"):
                continue
            full = os.path.join(root, filename)
            rel = os.path.relpath(full, os.path.dirname(_APP_DIR)).replace(os.sep, "/")
            with open(full, encoding="utf-8") as handle:
                tree = ast.parse(handle.read(), filename=full)
            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                for call in ast.walk(node):
                    if not isinstance(call, ast.Call):
                        continue
                    func = call.func
                    name = getattr(func, "id", None) or getattr(func, "attr", None)
                    if name not in ("select", "get"):
                        continue
                    if not call.args:
                        continue
                    first = call.args[0]
                    model = getattr(first, "id", None)
                    if model in INHERITED_MODELS:
                        sites.setdefault(f"{rel}:{node.name}", set()).add(model)
    return sites


def test_inherited_models_cover_apras41_partition():
    """`INHERITED_MODELS` is exactly APRAS-41's 20-table inherited partition.

    Spec §6.3 requires the names to come from that partition rather than from
    a fresh hand-written list. A hand-written copy is precisely how
    ``TaskVisibleToLink`` went missing: the regression below would then
    silently pass an unreviewed ``select(TaskVisibleToLink)``.
    """
    by_table = _model_name_by_table()
    assert len(INHERITED_TABLES) == 20
    assert {by_table[table] for table in INHERITED_TABLES} == set(INHERITED_MODELS)


def test_inherited_table_queries_are_reviewed():
    """Every query over an inherited table is on the reviewed allowlist.

    This is the regression that keeps §6's audit honest: a new child-table
    query added without a tenant-safety argument fails here.
    """
    found = set(_child_query_sites())
    allowlisted = set(REVIEWED_CHILD_QUERIES)
    assert not (found - allowlisted), (
        "unreviewed inherited-table query sites: " f"{sorted(found - allowlisted)}"
    )
    assert not (allowlisted - found), (
        "stale allowlist entries: " f"{sorted(allowlisted - found)}"
    )


def test_registry_covers_every_scoped_table():
    """Sanity: the isolation matrix seeds every model the filter protects."""
    assert len(TENANT_SCOPED_MODELS) == 27


# ---------------------------------------------------------------------------
# 9. Per-tenant role-linked Role seeding (§7)
# ---------------------------------------------------------------------------


def test_creating_a_tenant_seeds_its_role_linked_roles(
    tenant_client: TestClient, raw_session: Session, user_in_tenant_a: User
):
    """Every new tenant gets the six historically-named rows.

    They carry `permissions = []` and grant nobody anything (IAM F5, §9.2);
    they exist so an operator opening a fresh tenant finds the same six names
    every other tenant has.
    """
    response = tenant_client.post(
        "/api/v1/tenants",
        headers=_auth(user_in_tenant_a),
        json={"name": "Condomínio Seeded"},
    )
    assert response.status_code == 201, response.text
    new_id = uuid.UUID(response.json()["id"])

    raw_session.expire_all()
    seeded_types = raw_session.exec(
        select(Role).where(Role.tenant_id == new_id)
    ).all()
    assert {ut.name for ut in seeded_types} == set(LEGACY_ROLE_NAMES)
    assert all(ut.permissions == [] for ut in seeded_types)


def test_creating_a_tenant_does_not_touch_the_acting_tenants_types(
    tenant_client: TestClient, raw_session: Session, user_in_tenant_a: User
):
    """`acting_tenant_scope` stamps the *new* tenant, not the acting one."""
    before = len(
        raw_session.exec(select(Role).where(Role.tenant_id == TENANT_A)).all()
    )
    response = tenant_client.post(
        "/api/v1/tenants",
        headers=_auth(user_in_tenant_a),
        json={"name": "Condomínio Untouched"},
    )
    assert response.status_code == 201

    raw_session.expire_all()
    after = len(
        raw_session.exec(select(Role).where(Role.tenant_id == TENANT_A)).all()
    )
    assert after == before


def test_effective_roles_resolve_the_acting_tenants_role_type(
    session: Session, raw_session: Session, tenant_b: Tenant
):
    """`get_effective_role_ids` reads the acting tenant from the session
    and falls back to the default tenant when there is none (§7.1)."""
    b_type = Role(name="Diretor (papel) B", tenant_id=tenant_b.id)
    session.add(b_type)
    session.commit()
    session.refresh(b_type)

    user = make_user(
        session,
        id=uuid.uuid4(),
        email="effective@test.com",
        full_name="Effective",
        hashed_password=get_password_hash("password"),
        profile="DIRECTOR",
        cpf="55566677720",
    )
    a_type = user.roles[0]
    user.roles = [a_type, b_type]
    session.add(user)
    session.commit()

    with Session(session.get_bind()) as probe:
        probe_user = probe.get(User, user.id)
        assert get_effective_role_ids(probe_user, probe) == {a_type.id}
        with acting_tenant_scope(probe, tenant_b.id):
            assert get_effective_role_ids(probe_user, probe) == {b_type.id}


def test_zero_memberships_with_an_unusable_default_tenant_is_400(
    tenant_client: TestClient, session: Session
):
    """The zero-membership fallback needs a usable default tenant; when that
    row is deactivated there is no tenant to act in, and the header stops
    being optional (§3.2)."""
    default_tenant = session.get(Tenant, TENANT_A)
    default_tenant.is_active = False
    session.add(default_tenant)
    session.commit()

    user = make_user(
        session,
        id=uuid.uuid4(),
        email="orphan@test.com",
        full_name="Orphan",
        hashed_password=get_password_hash("password"),
        profile="ADMINISTRATOR",
        cpf="12345678062",
    )
    session.add(user)
    session.commit()

    response = tenant_client.get("/api/v1/categories/", headers=_auth(user))
    assert response.status_code == 400
    assert response.json()["detail"] == "X-Tenant-Id header is required"
