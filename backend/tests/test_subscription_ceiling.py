"""§4 -- how APRAS-40 composes with APRAS-39. The single most important module.

The rule, once:

    `tenant.disabled_modules` remains the only input to permission resolution.
    APRAS-40 changes no line of `deps.get_effective_permissions`,
    `deps.disabled_modules` or `permissions.filter_by_modules`. What APRAS-40
    adds is a constraint on *who may write that column and to what value*.

So 40 does **not** subsume 39's toggle. 39's superuser `PUT
/api/v1/tenants/{id}/modules` survives verbatim as the operator's **raw
lever**, deliberately *not* constrained by the ceiling; 40 gives tenant-side
actors a **second, ceiling-constrained lever on the same column**, and gives
the superuser a **third, entitlement-expanding lever** (courtesy). Three
writers, one column, one reader.
"""

from __future__ import annotations

import ast
import hashlib
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import event

from app.core.permissions import CORE_MODULES, TOGGLEABLE_MODULES
from app.models.enums import SubscriptionChangeKind, SubscriptionStatus
from app.models.subscription import TenantSubscription
from app.models.tenant import Tenant, UserTenantLink
from app.schemas.tenant import TenantModulesUpdate
from app.services.subscription_service import Entitlement, SubscriptionService
from app.services.tenant_service import TenantService
from tests.subscription_helpers import (
    TENANT_A,
    auth,
    disabled_of,
    history_of,
    make_plan,
    make_role_holder,
    make_superuser,
    make_tenant_admin,
    module_row,
    subscribe,
)

if TYPE_CHECKING:  # pragma: no cover
    from fastapi.testclient import TestClient
    from sqlmodel import Session

BACKEND_ROOT = Path(__file__).resolve().parent.parent
APP_ROOT = BACKEND_ROOT / "app"
SERVICE_PATH = APP_ROOT / "services" / "subscription_service.py"

MODULES_URL = "/api/v1/subscription/modules"
SUBSCRIPTION = "/api/v1/subscription"


def _raw_url(tenant_id) -> str:
    return f"/api/v1/tenants/{tenant_id}/modules"


def _sub_url(tenant_id) -> str:
    return f"/api/v1/tenants/{tenant_id}/subscription"


def over(session: Session, tenant_id, entitled: set[str]) -> set[str]:
    """§4.5's `over(t)`: active toggleable modules outside the entitlement."""
    active = TOGGLEABLE_MODULES - set(disabled_of(session, tenant_id))
    return active - entitled


@pytest.fixture(name="superuser")
def superuser_fixture(session: Session):
    return make_superuser(session)


# ---------------------------------------------------------------------------
# §4.5 -- the three-part invariant
# ---------------------------------------------------------------------------


def test_the_invariant_holds_after_every_apras_40_write(
    session: Session, tenant_client: TestClient, superuser
):
    """I1 no write escalates; I2 the plan path repairs; I3 the tenant-side
    path is neutral on what it does not govern.

    Stated in three parts because §4.4 (a) *preserves* an out-of-entitlement
    activation rather than repairing it -- a single `⊆ entitlement` statement
    would be false.
    """
    plan = make_plan(session, included=["documents"])
    subscribe(session, tenant_id=TENANT_A, plan=plan)
    tenant_admin = make_tenant_admin(session)

    # The raw lever puts `finance` outside the entitlement, deliberately.
    tenant_client.put(
        _raw_url(TENANT_A),
        json={
            "disabled_modules": sorted(
                TOGGLEABLE_MODULES - {"documents", "finance"}
            )
        },
        headers=auth(superuser),
    )
    entitled = {"documents"}
    assert over(session, TENANT_A, entitled) == {"finance"}

    # -- I3: the tenant-side path leaves `over(t)` unchanged ----------------
    before = over(session, TENANT_A, entitled)
    response = tenant_client.put(
        MODULES_URL,
        json={"active_modules": ["documents"]},
        headers=auth(tenant_admin, TENANT_A),
    )
    assert response.status_code == 200
    after = over(session, TENANT_A, entitled)
    assert after == before, "I3: the tenant-side write is not neutral"
    assert after <= before, "I1: the tenant-side write escalated"

    # -- I1/I2: the plan-change path repairs --------------------------------
    other = make_plan(session, included=["documents"])
    before = over(session, TENANT_A, entitled)
    tenant_client.put(
        _sub_url(TENANT_A), json={"plan_id": str(other.id)}, headers=auth(superuser)
    )
    after = over(session, TENANT_A, entitled)
    assert after == set(), "I2: the plan change did not repair over(t)"
    assert after <= before, "I1: the plan change escalated"

    # -- I1: the courtesy path expands the entitlement, never `over` --------
    before = over(session, TENANT_A, entitled)
    tenant_client.put(
        f"{_sub_url(TENANT_A)}/courtesy",
        json={"courtesy_modules": ["assets"]},
        headers=auth(superuser),
    )
    widened = entitled | {"assets"}
    assert over(session, TENANT_A, widened) <= before, "I1: courtesy escalated"
    assert over(session, TENANT_A, widened) == set()


def test_a_module_outside_the_plan_cannot_be_activated_by_a_tenant_admin(
    session: Session, tenant_client: TestClient
):
    plan = make_plan(session, included=["documents"])
    subscribe(session, tenant_id=TENANT_A, plan=plan)
    tenant_admin = make_tenant_admin(session)

    response = tenant_client.put(
        MODULES_URL,
        json={"active_modules": ["documents", "finance"]},
        headers=auth(tenant_admin, TENANT_A),
    )

    assert response.status_code == 400
    assert "finance" in disabled_of(session, TENANT_A)
    refused = tenant_client.get(
        "/api/v1/finance/categories", headers=auth(tenant_admin, TENANT_A)
    )
    assert refused.status_code == 403


def test_a_module_outside_the_plan_cannot_be_activated_by_a_billing_manage_holder(
    session: Session, tenant_client: TestClient
):
    """The "DIRECTOR" case: a plain role granted the two strings, nothing more."""
    plan = make_plan(session, included=["documents"])
    subscribe(session, tenant_id=TENANT_A, plan=plan)
    director, _role = make_role_holder(
        session, ["billing:read", "billing:manage"]
    )

    response = tenant_client.put(
        MODULES_URL,
        json={"active_modules": ["finance"]},
        headers=auth(director, TENANT_A),
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Modules not covered by the subscription: finance"
    )
    assert "finance" in disabled_of(session, TENANT_A)


def test_a_tenant_side_write_preserves_courtesy_and_override_activations(
    session: Session, tenant_client: TestClient, superuser
):
    """§4.4 (a) step 5. A `PUT` whose body omits a courtesy module and an
    override module leaves **both** active, and appends a `CONTRACTED` row
    naming neither: omission deactivates only plan-covered modules."""
    plan = make_plan(session, included=["documents", "projects"])
    subscription = subscribe(
        session, tenant_id=TENANT_A, plan=plan, courtesy=["assets"]
    )
    tenant_admin = make_tenant_admin(session)

    # An APRAS-39 raw override activates `finance`, outside the entitlement.
    tenant_client.put(
        _raw_url(TENANT_A),
        json={
            "disabled_modules": sorted(
                TOGGLEABLE_MODULES
                - {"documents", "projects", "assets", "finance"}
            )
        },
        headers=auth(superuser),
    )
    before_rows = len(history_of(session, subscription.id))

    response = tenant_client.put(
        MODULES_URL,
        json={"active_modules": ["documents"]},
        headers=auth(tenant_admin, TENANT_A),
    )

    assert response.status_code == 200
    body = response.json()
    assert module_row(body, "assets")["is_active"] is True
    assert module_row(body, "assets")["source"] == "COURTESY"
    assert module_row(body, "finance")["is_active"] is True
    assert module_row(body, "finance")["source"] == "OVERRIDE"
    # ...and the plan-covered one the body omitted *is* switched off.
    assert module_row(body, "projects")["is_active"] is False

    rows = history_of(session, subscription.id)[before_rows:]
    assert [row.kind for row in rows] == [SubscriptionChangeKind.CONTRACTED]
    assert rows[0].modules_removed == ["projects"]
    assert rows[0].modules_added == []


# ---------------------------------------------------------------------------
# §4.2 -- the raw lever stays unconstrained, and is historied
# ---------------------------------------------------------------------------


def test_the_superuser_raw_switch_is_not_constrained_by_the_ceiling(
    session: Session, tenant_client: TestClient, superuser
):
    """It is the operator's repair tool: a tenant whose subscription data is
    wrong must still be fixable."""
    plan = make_plan(session, included=["documents"])
    subscribe(session, tenant_id=TENANT_A, plan=plan)

    response = tenant_client.put(
        _raw_url(TENANT_A),
        json={
            "disabled_modules": sorted(
                TOGGLEABLE_MODULES - {"documents", "finance"}
            )
        },
        headers=auth(superuser),
    )

    assert response.status_code == 200
    assert "finance" not in disabled_of(session, TENANT_A)
    body = tenant_client.get(_sub_url(TENANT_A), headers=auth(superuser)).json()
    assert module_row(body, "finance")["source"] == "OVERRIDE"


def test_the_raw_switch_records_an_override_history_row(
    session: Session, tenant_client: TestClient, superuser
):
    """The column is NEGATIVE, so a module that LEFT `disabled_modules` was
    activated: `modules_added` is `before - after`."""
    plan = make_plan(session, included=["documents"])
    subscription = subscribe(session, tenant_id=TENANT_A, plan=plan)

    tenant_client.put(
        _raw_url(TENANT_A),
        json={
            "disabled_modules": sorted(
                TOGGLEABLE_MODULES - {"documents", "finance"}
            )
        },
        headers=auth(superuser),
    )

    rows = history_of(session, subscription.id)
    assert [row.kind for row in rows] == [SubscriptionChangeKind.OVERRIDE]
    assert rows[0].modules_added == ["finance"]
    assert rows[0].modules_removed == []
    assert rows[0].changed_by_id == superuser.id


def test_the_raw_switch_and_its_override_row_are_one_transaction(
    session: Session, tenant_client: TestClient, superuser, monkeypatch
):
    """A failure writing the history rolls the module change back too.

    Round-1 review S-5. Two commits could leave `disabled_modules` changed and
    the history silent -- exactly the state an append-only audit exists to
    make impossible. The history row is `session.add`ed before the single
    `commit()`, so the pair is atomic.
    """
    plan = make_plan(session, included=["documents"])
    subscription = subscribe(session, tenant_id=TENANT_A, plan=plan)
    before = disabled_of(session, TENANT_A)
    assert "finance" in before

    def _explode(**_kwargs):
        raise RuntimeError("the history write failed")

    monkeypatch.setattr(SubscriptionService, "record", staticmethod(_explode))

    with pytest.raises(RuntimeError):
        TenantService.set_modules(
            session,
            TENANT_A,
            TenantModulesUpdate(
                disabled_modules=sorted(
                    TOGGLEABLE_MODULES - {"documents", "finance"}
                )
            ),
            actor=superuser,
        )
    session.rollback()

    # The module write did **not** survive the failed history write.
    assert disabled_of(session, TENANT_A) == before
    assert history_of(session, subscription.id) == []


def test_the_raw_switch_on_an_unmanaged_tenant_records_nothing(
    session: Session, tenant_client: TestClient, superuser
):
    """`get_subscription` returns `None` rather than raising, precisely so
    this call site stays a guard and APRAS-39's status codes cannot move."""
    response = tenant_client.put(
        _raw_url(TENANT_A),
        json={"disabled_modules": ["finance"]},
        headers=auth(superuser),
    )

    assert response.status_code == 200
    assert disabled_of(session, TENANT_A) == ["finance"]


def test_billing_is_core_and_cannot_be_disabled(
    session: Session, tenant_client: TestClient, superuser
):
    """The lock-out `CORE_MODULES` exists to prevent, closed with no new code.

    `deps.disabled_modules` subtracts `CORE_MODULES` from the stored row, so
    even a hand-edited row containing `"billing"` cannot strip `billing:*`.
    """
    assert "billing" in CORE_MODULES

    refused = tenant_client.put(
        _raw_url(TENANT_A),
        json={"disabled_modules": ["billing"]},
        headers=auth(superuser),
    )
    assert refused.status_code == 400
    assert refused.json()["detail"] == "Core modules cannot be disabled: billing"

    hand_edited = session.get(Tenant, TENANT_A)
    hand_edited.disabled_modules = ["billing"]
    session.add(hand_edited)
    session.commit()

    tenant_admin = make_tenant_admin(session)
    permissions = tenant_client.get(
        "/api/v1/permissions/me", headers=auth(tenant_admin, TENANT_A)
    ).json()["permissions"]
    assert {"billing:read", "billing:manage"} <= set(permissions)
    assert (
        tenant_client.get(
            SUBSCRIPTION, headers=auth(tenant_admin, TENANT_A)
        ).status_code
        == 200
    )


# ---------------------------------------------------------------------------
# §4.3 -- status gates nothing
# ---------------------------------------------------------------------------


def test_status_does_not_change_the_entitlement(
    session: Session, tenant_client: TestClient
):
    """§4.3. Enforcing suspension is a consequence of a failed charge, and
    there is no charging (§1.2), so `status` is recorded and displayed and
    gates **nothing**: the same tenant's `active` set, module rows and
    `/permissions/me` are byte-identical under all three values.

    One case, three statuses in one world -- a parametrised case could only
    compare a value against a literal, and what has to be proved is that the
    three answers are identical to *each other*.
    """
    plan = make_plan(session, included=["documents"])
    subscription = subscribe(session, tenant_id=TENANT_A, plan=plan)
    tenant_admin = make_tenant_admin(session)

    probes = {}
    for status in (
        SubscriptionStatus.ACTIVE,
        SubscriptionStatus.SUSPENDED,
        SubscriptionStatus.CANCELED,
    ):
        session.expire_all()
        row = session.get(TenantSubscription, subscription.id)
        row.status = status
        session.add(row)
        session.commit()

        body = tenant_client.get(
            SUBSCRIPTION, headers=auth(tenant_admin, TENANT_A)
        ).json()
        permissions = tenant_client.get(
            "/api/v1/permissions/me", headers=auth(tenant_admin, TENANT_A)
        ).json()

        assert body["status"] == status.value
        probes[status.value] = (
            disabled_of(session, TENANT_A),
            permissions,
            body["modules"],
            body["estimated_monthly_total"],
        )

    reference = probes[SubscriptionStatus.ACTIVE.value]
    for value in probes.values():
        assert value == reference, "status changed the entitlement or the strip"


# ---------------------------------------------------------------------------
# §6.3 -- one loader, and `build_read` is a pure function of its result
# ---------------------------------------------------------------------------


def _function_node(name: str) -> ast.FunctionDef:
    tree = ast.parse(SERVICE_PATH.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"{name} not found in {SERVICE_PATH}")


def _homes_of(name: str) -> set[str]:
    """Every `app/**` file where `name` is an attribute access or a field
    declaration. Over the **AST**, never over source text: the field comments
    contain the literal string and must not count."""
    homes: set[str] = set()
    for path in sorted(APP_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            hit = (
                (isinstance(node, ast.Attribute) and node.attr == name)
                or (
                    isinstance(node, ast.AnnAssign)
                    and isinstance(node.target, ast.Name)
                    and node.target.id == name
                )
                or (isinstance(node, ast.arg) and node.arg == name)
            )
            if hit:
                homes.add(str(path.relative_to(BACKEND_ROOT)))
    return homes


def test_included_modules_has_at_most_four_homes():
    """An **upper bound**, and the name says so.

    A second, divergent ceiling cannot be introduced silently, while a
    legitimate refactor that drops one of the four does not turn this red for
    no reason. `build_read` is not one of the homes and does not need to be:
    it reads `ent.included`.
    """
    allowed = {
        "app/models/plan.py",
        "app/schemas/plan.py",
        "app/services/plan_service.py",
        "app/services/subscription_service.py",
    }
    homes = _homes_of("included_modules")
    assert homes <= allowed, f"a second home for the ceiling: {sorted(homes - allowed)}"

    tree = ast.parse(SERVICE_PATH.read_text(encoding="utf-8"))
    entitlement = _function_node("entitlement")
    inside = {
        node.lineno
        for node in ast.walk(entitlement)
        if isinstance(node, ast.Attribute) and node.attr == "included_modules"
    }
    everywhere = {
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute) and node.attr == "included_modules"
    }
    assert everywhere == inside, (
        "in subscription_service.py `included_modules` must appear only inside "
        f"`entitlement`; stray lines: {sorted(everywhere - inside)}"
    )
    assert "build_read" not in {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
        and any(
            isinstance(inner, ast.Attribute) and inner.attr == "included_modules"
            for inner in ast.walk(node)
        )
    }


def test_build_read_derives_everything_from_the_entitlement_result():
    """The body touches the session **not at all**, and calls `entitlement`
    exactly once. ER-6's "from that result alone", made literal."""
    node = _function_node("build_read")

    session_reads = [
        f"line {inner.lineno}: session.{inner.attr}"
        for inner in ast.walk(node)
        if isinstance(inner, ast.Attribute)
        and isinstance(inner.value, ast.Name)
        and inner.value.id == "session"
    ]
    assert not session_reads, f"build_read touched the session: {session_reads}"

    names = {
        inner.id for inner in ast.walk(node) if isinstance(inner, ast.Name)
    }
    assert not (names & {"Plan", "TenantSubscription", "SubscriptionChange"})
    assert "select" not in names

    forbidden = [
        f"line {inner.lineno}: .{inner.attr}"
        for inner in ast.walk(node)
        if isinstance(inner, ast.Attribute)
        and inner.attr in {"included_modules", "courtesy_modules"}
    ]
    assert not forbidden, f"build_read read a JSON column directly: {forbidden}"

    calls = [
        inner
        for inner in ast.walk(node)
        if isinstance(inner, ast.Call)
        and getattr(inner.func, "attr", None) == "entitlement"
    ]
    assert len(calls) == 1, f"build_read calls entitlement {len(calls)} times"


def test_entitlement_is_the_only_loader_and_costs_one_query(
    session: Session, tenant_client: TestClient
):
    """One statement joining `TenantSubscription` and `Plan`, no lazy
    relationship, and `ent.plan is None` iff `ent.subscription is None`."""
    plan = make_plan(session, included=["documents"])
    subscribe(session, tenant_id=TENANT_A, plan=plan)
    tenant_admin = make_tenant_admin(session)

    assert not hasattr(TenantSubscription, "plan")
    with pytest.raises(AssertionError):
        Entitlement(
            subscription=None, plan=plan, included=frozenset(), courtesy=frozenset()
        )

    ent = SubscriptionService.entitlement(session, session.get(Tenant, TENANT_A))
    assert (ent.plan is None) == (ent.subscription is None)
    assert ent.managed is True
    assert ent.all == frozenset({"documents"})

    statements: list[str] = []

    def _record(_conn, _cursor, statement, *_args):
        statements.append(statement)

    engine = session.get_bind()
    event.listen(engine, "before_cursor_execute", _record)
    try:
        response = tenant_client.get(
            SUBSCRIPTION, headers=auth(tenant_admin, TENANT_A)
        )
    finally:
        event.remove(engine, "before_cursor_execute", _record)

    assert response.status_code == 200
    joined = [
        statement
        for statement in statements
        if "tenant_subscription" in statement and "plan" in statement
    ]
    assert len(joined) == 1, f"expected one subscription/plan query, got {joined}"
    assert "JOIN" in joined[0].upper()


# ---------------------------------------------------------------------------
# ER-6 -- the resolver is untouched
# ---------------------------------------------------------------------------


#: sha256 of the exact source segment of each resolver function, measured at
#: the APRAS-39 merge base `68cfd1d1ca49e8bcec05708de6ff02fa22eba875` -- i.e.
#: **before** this task existed. A hash rather than a `git diff` on purpose: a
#: diff against `HEAD` is empty by construction the moment this task is
#: committed, and a diff against a literal sha stops being runnable the moment
#: the branch is rebased or the repository is cloned shallow. The hash is the
#: same statement, is reproducible from the working tree alone, and fails
#: loudly and specifically when someone edits one of the three.
RESOLVER_SOURCE_SHA256 = {
    "app/api/deps.py": {
        "disabled_modules": (
            "2670a0f5e6fed9f81224c3fb4c826cfc3f8599bccf63c745fabf79fdbdf60521"
        ),
        "get_effective_permissions": (
            "26c5a3eb9e034f819d7dfb76aafc554f749a6c696508dc3a8fe5001169b3ef4f"
        ),
    },
    "app/core/permissions.py": {
        "filter_by_modules": (
            "aa089ff1d0a7d3c15531daa98d2470f73cd5a4ffd652a29af47ab6a6a2acb2a8"
        ),
    },
}


def test_the_resolver_is_untouched():
    """No line of the three resolver functions moved, and `entitlement` is
    referenced only inside `subscription_service.py`.

    `tenant.disabled_modules` remains the only input to permission
    resolution; what APRAS-40 adds is a constraint on who may write it.
    """
    for relative, expected in RESOLVER_SOURCE_SHA256.items():
        source = (BACKEND_ROOT / relative).read_text(encoding="utf-8")
        tree = ast.parse(source)
        measured = {
            node.name: hashlib.sha256(
                ast.get_source_segment(source, node).encode("utf-8")
            ).hexdigest()
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name in expected
        }
        assert measured == expected, (
            f"{relative}: a resolver function changed. APRAS-40 adds no line "
            "to the resolver (§4.1)."
        )

    callers = {
        str(path.relative_to(BACKEND_ROOT))
        for path in sorted(APP_ROOT.rglob("*.py"))
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
        if isinstance(node, ast.Call)
        and getattr(node.func, "attr", None) == "entitlement"
    }
    assert callers == {"app/services/subscription_service.py"}


def test_entitlement_isolation_between_tenants(
    session: Session, tenant_client: TestClient, tenant_b
):
    """One user, two tenants, two plans: 403 with A's header, 200 with B's,
    and nothing else differing."""
    without = make_plan(session, name="Sem finance", included=["documents"])
    with_finance = make_plan(session, name="Com finance", included=["finance"])
    subscribe(session, tenant_id=TENANT_A, plan=without)
    subscribe(session, tenant_id=tenant_b.id, plan=with_finance)

    user = make_tenant_admin(session)
    session.add(
        UserTenantLink(user_id=user.id, tenant_id=tenant_b.id, is_tenant_admin=True)
    )
    session.commit()

    in_a = tenant_client.get(
        "/api/v1/finance/categories", headers=auth(user, TENANT_A)
    )
    in_b = tenant_client.get(
        "/api/v1/finance/categories", headers=auth(user, tenant_b.id)
    )

    assert in_a.status_code == 403
    assert in_b.status_code == 200
