"""The append-only subscription history (APRAS-40 §3.3, §5.4).

The pattern is `PurchaseQuoteDecision` (APRAS-37): a child of a scoped parent,
never updated, never deleted, ordered by its own timestamp. Append-only is
enforced **structurally**, not by convention: there is no `PATCH`, no `DELETE`
and no update route for this table, and the service only ever `session.add()`s
one.
"""

from __future__ import annotations

import ast
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import UUID

import pytest
from fastapi.routing import APIRoute

from app.core.permissions import ROUTE_PERMISSIONS, TOGGLEABLE_MODULES, UNGUARDED_ROUTES
from app.main import app
from app.models.subscription import SubscriptionChange
from app.models.tenant import Tenant
from app.services.subscription_service import SubscriptionService
from tests.subscription_helpers import (
    TENANT_A,
    auth,
    history_of,
    make_plan,
    make_superuser,
    make_tenant_admin,
    subscribe,
    subscription_id,
)
from tests.test_permission_alignment import (
    MEMBERSHIP_GATED,
    REFUSAL_SHAPES,
    SERVICE_ENFORCED,
    UNENFORCED,
)
from tests.test_permission_enforcement import (
    ADMIN_ONLY_ROUTES as ENFORCEMENT_ADMIN_ONLY,
)
from tests.test_tenant_admin import ADMIN_ONLY_ROUTES as TENANT_ADMIN_ADMIN_ONLY

if TYPE_CHECKING:  # pragma: no cover
    from fastapi.testclient import TestClient
    from sqlmodel import Session

BACKEND_ROOT = Path(__file__).resolve().parent.parent
APP_ROOT = BACKEND_ROOT / "app"

HISTORY_URL = "/api/v1/subscription/history"
MODULES_URL = "/api/v1/subscription/modules"


def _sub_url(tenant_id) -> str:
    return f"/api/v1/tenants/{tenant_id}/subscription"


@pytest.fixture(name="superuser")
def superuser_fixture(session: Session):
    return make_superuser(session)


def test_every_write_path_appends_exactly_one_kind(
    session: Session, tenant_client: TestClient, superuser
):
    """The five kinds, one operation each, in the order they happened."""
    narrow = make_plan(session, name="Estreito", included=["documents"])
    wide = make_plan(session, name="Largo", included=["documents", "projects"])
    tenant_admin = make_tenant_admin(session)

    # PLAN_CHANGE -- first adoption, from all-on.
    tenant_client.put(
        _sub_url(TENANT_A), json={"plan_id": str(wide.id)}, headers=auth(superuser)
    )
    # CONTRACTED -- the tenant cancels one the plan covers.
    tenant_client.put(
        MODULES_URL,
        json={"active_modules": ["documents"]},
        headers=auth(tenant_admin, TENANT_A),
    )
    # COURTESY_GRANT -- one module outside the plan, activated.
    tenant_client.put(
        f"{_sub_url(TENANT_A)}/courtesy",
        json={"courtesy_modules": ["assets"], "reason": "trial"},
        headers=auth(superuser),
    )
    # COURTESY_REVOKE -- and taken away again.
    tenant_client.put(
        f"{_sub_url(TENANT_A)}/courtesy",
        json={"courtesy_modules": [], "reason": "fim do trial"},
        headers=auth(superuser),
    )
    # OVERRIDE -- APRAS-39's raw lever, outside the ceiling on purpose.
    tenant_client.put(
        f"/api/v1/tenants/{TENANT_A}/modules",
        json={
            "disabled_modules": sorted(TOGGLEABLE_MODULES - {"documents", "finance"})
        },
        headers=auth(superuser),
    )
    # ...and one more plan change, so PLAN_CHANGE is not only the first row.
    tenant_client.put(
        _sub_url(TENANT_A), json={"plan_id": str(narrow.id)}, headers=auth(superuser)
    )

    kinds = [
        row.kind.value
        for row in history_of(session, subscription_id(session, TENANT_A))
    ]
    assert kinds == [
        "PLAN_CHANGE",
        "CONTRACTED",
        "COURTESY_GRANT",
        "COURTESY_REVOKE",
        "OVERRIDE",
        "PLAN_CHANGE",
    ]
    assert set(kinds) == {
        "PLAN_CHANGE",
        "CONTRACTED",
        "COURTESY_GRANT",
        "COURTESY_REVOKE",
        "OVERRIDE",
    }


def test_history_is_ordered_newest_first_and_names_the_actor(
    session: Session, tenant_client: TestClient, superuser
):
    plan = make_plan(session, included=["documents", "projects"])
    subscribe(session, tenant_id=TENANT_A, plan=plan)
    tenant_admin = make_tenant_admin(session)

    tenant_client.put(
        f"{_sub_url(TENANT_A)}/courtesy",
        json={"courtesy_modules": ["assets"], "reason": "cortesia"},
        headers=auth(superuser),
    )
    tenant_client.put(
        MODULES_URL,
        json={"active_modules": ["documents"]},
        headers=auth(tenant_admin, TENANT_A),
    )

    response = tenant_client.get(HISTORY_URL, headers=auth(tenant_admin, TENANT_A))

    assert response.status_code == 200
    rows = response.json()
    assert [row["kind"] for row in rows] == ["CONTRACTED", "COURTESY_GRANT"]
    assert rows[0]["changed_by_id"] == str(tenant_admin.id)
    assert rows[0]["changed_by_name"] == tenant_admin.full_name
    assert rows[1]["changed_by_name"] == superuser.full_name
    assert rows[1]["reason"] == "cortesia"
    assert rows[0]["changed_at"] >= rows[1]["changed_at"]


def test_plan_change_records_both_plan_ids(
    session: Session, tenant_client: TestClient, superuser
):
    first = make_plan(session, name="Primeiro", included=["documents"])
    second = make_plan(session, name="Segundo", included=["projects"])
    subscribe(session, tenant_id=TENANT_A, plan=first)
    tenant_admin = make_tenant_admin(session)

    tenant_client.put(
        _sub_url(TENANT_A), json={"plan_id": str(second.id)}, headers=auth(superuser)
    )

    rows = tenant_client.get(
        HISTORY_URL, headers=auth(tenant_admin, TENANT_A)
    ).json()

    assert rows[0]["kind"] == "PLAN_CHANGE"
    assert rows[0]["from_plan_name"] == "Primeiro"
    assert rows[0]["to_plan_name"] == "Segundo"


def test_a_tenant_only_sees_its_own_history(
    session: Session, tenant_client: TestClient, superuser, tenant_b
):
    """The acting-tenant filter: A's history has zero rows from B."""
    plan_a = make_plan(session, name="Plano A", included=["documents"])
    plan_b = make_plan(session, name="Plano B", included=["projects"])
    subscribe(session, tenant_id=TENANT_A, plan=plan_a)
    subscribe(session, tenant_id=tenant_b.id, plan=plan_b)

    tenant_client.put(
        f"{_sub_url(tenant_b.id)}/courtesy",
        json={"courtesy_modules": ["assets"], "reason": "só do B"},
        headers=auth(superuser),
    )
    tenant_client.put(
        f"{_sub_url(TENANT_A)}/courtesy",
        json={"courtesy_modules": ["finance"], "reason": "só do A"},
        headers=auth(superuser),
    )

    admin_a = make_tenant_admin(session)
    rows = tenant_client.get(HISTORY_URL, headers=auth(admin_a, TENANT_A)).json()

    assert [row["reason"] for row in rows] == ["só do A"]
    assert all(row["modules_added"] == ["finance"] for row in rows)


def test_the_history_is_never_updated_or_deleted():
    """No route mutates a `subscription_change` row, and no service function
    assigns to an attribute of one or passes one to `session.delete`."""
    live = {
        (method, route.path)
        for route in app.routes
        if isinstance(route, APIRoute)
        for method in route.methods
    }
    assert not [
        key for key in live if "subscription-change" in key[1] or ("history" in key[1]
        and key[0] in {"PATCH", "PUT", "DELETE"})
    ]

    offenders: list[str] = []
    for path in sorted(APP_ROOT.rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        if "SubscriptionChange" not in source:
            continue
        tree = ast.parse(source)
        relative = path.relative_to(BACKEND_ROOT)
        for node in ast.walk(tree):
            # `session.delete(SubscriptionChange(...))` / `session.delete(row)`
            # where `row` was bound from the model -- the constructor form is
            # what a scan can see, and it is the one that would be written.
            if (
                isinstance(node, ast.Call)
                and getattr(node.func, "attr", None) == "delete"
                and any(
                    isinstance(inner, ast.Name)
                    and inner.id == "SubscriptionChange"
                    for argument in node.args
                    for inner in ast.walk(argument)
                )
            ):
                offenders.append(f"{relative}:{node.lineno}: session.delete")
            # Any `<something>.kind = ...` style write onto a history row is
            # caught by forbidding assignment to the model's own field names
            # anywhere outside its declaration module.
            if isinstance(node, ast.Assign) and relative != Path(
                "app/models/subscription.py"
            ):
                offenders.extend(
                    f"{relative}:{node.lineno}: assignment to .{target.attr}"
                    for target in node.targets
                    if isinstance(target, ast.Attribute)
                    and target.attr
                    in {"modules_added", "modules_removed", "changed_at", "kind"}
                )

    assert not offenders, f"the history is append-only: {offenders}"


def test_the_only_writer_of_the_history_is_record():
    """One constructor call site, in `SubscriptionService.record`."""
    source = (APP_ROOT / "services" / "subscription_service.py").read_text(
        encoding="utf-8"
    )
    tree = ast.parse(source)
    constructors = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "SubscriptionChange"
    ]
    assert len(constructors) == 1

    enclosing = [
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
        and any(
            isinstance(inner, ast.Call)
            and isinstance(inner.func, ast.Name)
            and inner.func.id == "SubscriptionChange"
            for inner in ast.walk(node)
        )
    ]
    assert enclosing == ["record"]

    everywhere = sorted(
        {
            str(path.relative_to(BACKEND_ROOT))
            for path in sorted(APP_ROOT.rglob("*.py"))
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "SubscriptionChange"
        }
    )
    assert everywhere == ["app/services/subscription_service.py"]


# ---------------------------------------------------------------------------
# APRAS-52 — the operator-side history read, and the service it shares
# ---------------------------------------------------------------------------

OPERATOR_HISTORY_ROUTE = (
    "GET",
    "/api/v1/tenants/{tenant_id}/subscription/history",
)


def test_the_operator_history_route_is_not_permission_mapped():
    """It is unmapped and superuser-guarded, like its three siblings.

    Stated as a checked fact rather than a silence: the route is outside
    `test_permission_alignment.py`'s walk (which iterates `ROUTE_PERMISSIONS`),
    so nothing there would go red if someone "helpfully" registered it in one
    of the mapped-route subsets. Each of `MEMBERSHIP_GATED`,
    `SERVICE_ENFORCED` and `REFUSAL_SHAPES` is asserted elsewhere to be a
    subset of the mapped routes, so any such addition is a red test -- this
    case is what names the requirement.
    """
    assert OPERATOR_HISTORY_ROUTE in UNGUARDED_ROUTES
    assert OPERATOR_HISTORY_ROUTE not in ROUTE_PERMISSIONS
    assert OPERATOR_HISTORY_ROUTE not in UNENFORCED
    assert OPERATOR_HISTORY_ROUTE not in MEMBERSHIP_GATED
    assert OPERATOR_HISTORY_ROUTE not in SERVICE_ENFORCED
    assert OPERATOR_HISTORY_ROUTE not in REFUSAL_SHAPES
    assert OPERATOR_HISTORY_ROUTE in ENFORCEMENT_ADMIN_ONLY
    assert OPERATOR_HISTORY_ROUTE in TENANT_ADMIN_ADMIN_ONLY


def test_the_tenant_side_history_is_unpaginated_by_default(
    session: Session, tenant_client: TestClient, superuser
):
    """`limit=None` means no `LIMIT`, so APRAS-40's route is untouched."""
    plan = make_plan(session, included=["documents", "projects"])
    subscribe(session, tenant_id=TENANT_A, plan=plan)
    tenant_admin = make_tenant_admin(session)
    for index in range(3):
        tenant_client.put(
            f"{_sub_url(TENANT_A)}/courtesy",
            json={
                "courtesy_modules": ["assets"] if index % 2 == 0 else [],
                "reason": f"volta {index}",
            },
            headers=auth(superuser),
        )

    rows = tenant_client.get(HISTORY_URL, headers=auth(tenant_admin, TENANT_A)).json()

    session.expire_all()
    tenant = session.get(Tenant, TENANT_A)
    service_rows = SubscriptionService.list_history(session=session, tenant=tenant)

    assert len(rows) == 3
    assert len(service_rows) == len(rows)
    assert [str(row.id) for row in service_rows] == [row["id"] for row in rows]


def test_the_history_order_is_deterministic_for_rows_sharing_a_timestamp(
    session: Session, tenant_client: TestClient, superuser
):
    """Two rows with an identical `changed_at` order by `id` **descending**.

    `changed_at.desc()` alone is not a total order, so the `id.desc()`
    tiebreak of APRAS-52 §3.1 is what keeps `skip`/`limit` from returning the
    same row twice (or skipping one) across two pages.

    The two ids are explicit, and the **low** one is inserted **first**, so
    descending-id order is the exact reverse of insertion order. That is what
    makes the case load-bearing: with the tiebreak removed the engine falls
    back on insertion order and the `["segunda", "primeira"]` assertion below
    goes red, rather than passing either way.
    """
    plan = make_plan(session, included=["documents"])
    subscription = subscribe(session, tenant_id=TENANT_A, plan=plan)
    # Naive on purpose: `subscription_change.changed_at` is written from
    # `datetime.utcnow()` and stored without a timezone, so a tz-aware literal
    # would not compare with what the service reads back.
    shared = datetime(2026, 3, 1, 12, 0, 0)  # noqa: DTZ001
    low_id = UUID("00000000-0000-4000-8000-0000000000a1")
    high_id = UUID("ffffffff-ffff-4fff-bfff-ffffffffffa2")
    for row_id, reason in ((low_id, "primeira"), (high_id, "segunda")):
        session.add(
            SubscriptionChange(
                id=row_id,
                subscription_id=subscription.id,
                kind="COURTESY_GRANT",
                modules_added=["assets"],
                modules_removed=[],
                reason=reason,
                changed_by_id=superuser.id,
                changed_at=shared,
            )
        )
    session.commit()
    session.expire_all()
    tenant = session.get(Tenant, TENANT_A)

    first_read = SubscriptionService.list_history(session=session, tenant=tenant)
    second_read = SubscriptionService.list_history(session=session, tenant=tenant)
    assert len({row.changed_at for row in first_read}) == 1
    # The exact order, not merely a stable one: highest id first, which is the
    # reverse of the order the two rows were inserted in.
    assert [row.id for row in first_read] == [high_id, low_id]
    assert [row.reason for row in first_read] == ["segunda", "primeira"]
    assert [row.id for row in second_read] == [high_id, low_id]

    page_one = SubscriptionService.list_history(session=session, tenant=tenant, limit=1)
    page_two = SubscriptionService.list_history(
        session=session, tenant=tenant, skip=1, limit=1
    )
    assert [row.id for row in page_one] == [high_id]
    assert [row.id for row in page_two] == [low_id]
    assert {row.id for row in page_one} & {row.id for row in page_two} == set()
    assert [row.id for row in page_one + page_two] == [row.id for row in first_read]
