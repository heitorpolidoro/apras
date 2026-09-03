"""The per-tenant subscription, from the operator's side (APRAS-40 §5.3, §4.4).

Three routes on the **existing global** `tenants` router, beside APRAS-39's
`/modules` pair and for its reasons: the subject is a tenant named in the path,
written from outside it, by an actor whose authority is global.
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.permissions import CORE_MODULES, TOGGLEABLE_MODULES
from app.models.enums import SubscriptionChangeKind
from app.models.subscription import TenantSubscription
from app.schemas.subscription import SubscriptionAdminUpdate
from app.services.subscription_service import SubscriptionService
from tests.subscription_helpers import (
    TENANT_A,
    auth,
    disabled_of,
    history_of,
    make_plan,
    make_superuser,
    make_tenant_admin,
    module_row,
    subscribe,
    subscription_id,
)


def _url(tenant_id) -> str:
    return f"/api/v1/tenants/{tenant_id}/subscription"


def _courtesy_url(tenant_id) -> str:
    return f"/api/v1/tenants/{tenant_id}/subscription/courtesy"


@pytest.fixture(name="superuser")
def superuser_fixture(session: Session):
    return make_superuser(session)


# ---------------------------------------------------------------------------
# §4.4 (b) -- assigning and changing the plan
# ---------------------------------------------------------------------------


def test_assigning_a_plan_creates_the_subscription_and_applies_the_ceiling(
    session: Session, tenant_client: TestClient, superuser
):
    """First adoption is the same rule: an all-on tenant keeps exactly the
    plan's modules, in one visible, history-recorded event."""
    plan = make_plan(session, included=["finance", "documents"])
    assert disabled_of(session, TENANT_A) == []

    response = tenant_client.put(
        _url(TENANT_A), json={"plan_id": str(plan.id)}, headers=auth(superuser)
    )

    assert response.status_code == 200
    assert response.json()["plan"]["id"] == str(plan.id)
    assert response.json()["status"] == "ACTIVE"
    assert disabled_of(session, TENANT_A) == sorted(
        TOGGLEABLE_MODULES - {"finance", "documents"}
    )

    modules = tenant_client.get(
        f"/api/v1/tenants/{TENANT_A}/modules", headers=auth(superuser)
    ).json()["modules"]
    inactive = {row["module"] for row in modules if not row["is_active"]}
    assert inactive == TOGGLEABLE_MODULES - {"finance", "documents"}

    rows = history_of(session, subscription_id(session, TENANT_A))
    assert [row.kind for row in rows] == [SubscriptionChangeKind.PLAN_CHANGE]
    assert rows[0].to_plan_id == plan.id
    assert rows[0].from_plan_id is None
    assert rows[0].changed_by_id == superuser.id


def test_a_plan_change_that_widens_does_not_auto_activate(
    session: Session, tenant_client: TestClient, superuser
):
    """Contracting a newly covered module is the tenant's explicit act (ER-2),
    and that is what makes the contracting screen meaningful."""
    narrow = make_plan(session, included=["documents"])
    wide = make_plan(session, included=["documents", "finance"])
    subscribe(session, tenant_id=TENANT_A, plan=narrow)

    response = tenant_client.put(
        _url(TENANT_A), json={"plan_id": str(wide.id)}, headers=auth(superuser)
    )

    assert response.status_code == 200
    row = module_row(response.json(), "finance")
    assert row["in_plan"] is True
    assert row["is_active"] is False
    assert row["can_contract"] is True
    assert row["source"] is None
    assert "finance" in disabled_of(session, TENANT_A)


def test_a_plan_change_that_narrows_deactivates(
    session: Session, tenant_client: TestClient, superuser
):
    wide = make_plan(session, included=["documents", "finance"])
    narrow = make_plan(session, included=["documents"])
    subscription = subscribe(session, tenant_id=TENANT_A, plan=wide)

    response = tenant_client.put(
        _url(TENANT_A), json={"plan_id": str(narrow.id)}, headers=auth(superuser)
    )

    assert response.status_code == 200
    assert module_row(response.json(), "finance")["is_active"] is False
    assert "finance" in disabled_of(session, TENANT_A)

    rows = history_of(session, subscription.id)
    assert [row.kind for row in rows] == [SubscriptionChangeKind.PLAN_CHANGE]
    assert rows[0].modules_removed == ["finance"]
    assert rows[0].from_plan_id == wide.id
    assert rows[0].to_plan_id == narrow.id


def test_assigning_an_inactive_plan_is_400(
    session: Session, tenant_client: TestClient, superuser
):
    """...but re-assigning the plan a tenant already carries is allowed, so
    deactivating a plan never strands its subscribers."""
    retired = make_plan(session, name="Plano Retirado", included=["documents"])
    subscribe(session, tenant_id=TENANT_A, plan=retired)
    tenant_client.patch(
        f"/api/v1/plans/{retired.id}",
        json={"is_active": False},
        headers=auth(superuser),
    )

    again = tenant_client.put(
        _url(TENANT_A), json={"plan_id": str(retired.id)}, headers=auth(superuser)
    )
    assert again.status_code == 200

    fresh = make_plan(session, name="Outro Retirado", is_active=False)
    refused = tenant_client.put(
        _url(TENANT_A), json={"plan_id": str(fresh.id)}, headers=auth(superuser)
    )
    assert refused.status_code == 400
    assert refused.json()["detail"] == "Plan 'Outro Retirado' is not active"


# ---------------------------------------------------------------------------
# §4.4 (c) -- courtesy
# ---------------------------------------------------------------------------


def test_a_no_op_plan_assignment_writes_no_history_row(
    session: Session, tenant_client: TestClient, superuser
):
    """The three levers are idempotent in the same way (round-1 review S-4).

    Re-sending the plan, status and notes a tenant already carries, with
    nothing left to deactivate, is a 200 that appends nothing -- so a UI that
    re-saves cannot manufacture history. First adoption is deliberately *not*
    a no-op: it is a real commercial event and §4.4 (b) requires it to be
    visible.
    """
    plan = make_plan(session, included=["documents"])

    first = tenant_client.put(
        _url(TENANT_A),
        json={"plan_id": str(plan.id), "notes": "contrato inicial"},
        headers=auth(superuser),
    )
    assert first.status_code == 200
    subscription = subscription_id(session, TENANT_A)
    assert len(history_of(session, subscription)) == 1

    again = tenant_client.put(
        _url(TENANT_A),
        json={"plan_id": str(plan.id), "notes": "contrato inicial"},
        headers=auth(superuser),
    )

    assert again.status_code == 200
    assert again.json() == first.json()
    assert len(history_of(session, subscription)) == 1

    # ...but a real change still records, so the silence is about no-ops only.
    changed = tenant_client.put(
        _url(TENANT_A),
        json={"plan_id": str(plan.id), "notes": "renegociado"},
        headers=auth(superuser),
    )
    assert changed.status_code == 200
    assert len(history_of(session, subscription)) == 2


def test_a_repeat_assignment_repairs_an_override_and_records_it(
    session: Session, tenant_client: TestClient, superuser
):
    """Re-assigning the *same* plan is how an operator repairs a drifted row.

    That is not a no-op even though nothing commercial changed: APRAS-39's raw
    lever may have activated something outside the entitlement, and §4.5's I2
    says the plan-change path leaves `over(t)` empty. The repair is a real
    event, so it is recorded.
    """
    plan = make_plan(session, included=["documents"])
    subscribe(session, tenant_id=TENANT_A, plan=plan)
    subscription = subscription_id(session, TENANT_A)

    tenant_client.put(
        f"/api/v1/tenants/{TENANT_A}/modules",
        json={
            "disabled_modules": sorted(
                TOGGLEABLE_MODULES - {"documents", "finance"}
            )
        },
        headers=auth(superuser),
    )
    assert "finance" not in disabled_of(session, TENANT_A)
    before = len(history_of(session, subscription))

    response = tenant_client.put(
        _url(TENANT_A), json={"plan_id": str(plan.id)}, headers=auth(superuser)
    )

    assert response.status_code == 200
    assert "finance" in disabled_of(session, TENANT_A)
    rows = history_of(session, subscription)[before:]
    assert [row.kind for row in rows] == [SubscriptionChangeKind.PLAN_CHANGE]
    assert rows[0].modules_removed == ["finance"]


def test_the_plan_write_and_its_history_row_are_one_transaction(
    session: Session, tenant_client: TestClient, superuser, monkeypatch
):
    """`set_plan` is one transaction (round-2 review N-2).

    The subscription row is `flush`ed -- so `entitlement`'s join can see it --
    and the plan write, the ceiling shrink and the `PLAN_CHANGE` row all land
    on a single `commit()`. A failure on the history write must leave the plan
    unchanged, not half-applied; the same shape S-5 closed on the raw lever.
    """
    narrow = make_plan(session, name="Estreito N2", included=["documents"])
    wide = make_plan(session, name="Largo N2", included=["documents", "finance"])
    subscribe(session, tenant_id=TENANT_A, plan=wide)
    subscription = subscription_id(session, TENANT_A)
    disabled_before = disabled_of(session, TENANT_A)
    assert "finance" not in disabled_before

    def _explode(**_kwargs):
        raise RuntimeError("the history write failed")

    monkeypatch.setattr(SubscriptionService, "record", staticmethod(_explode))

    with pytest.raises(RuntimeError):
        SubscriptionService.set_plan(
            session=session,
            tenant_id=TENANT_A,
            payload=SubscriptionAdminUpdate(plan_id=narrow.id),
            actor=superuser,
        )
    session.rollback()
    session.expire_all()

    # Neither half survived: the plan is still the wide one and `finance` is
    # still active.
    assert session.get(TenantSubscription, subscription).plan_id == wide.id
    assert disabled_of(session, TENANT_A) == disabled_before
    assert history_of(session, subscription) == []


def test_the_plan_change_row_does_not_borrow_the_subscription_notes(
    session: Session, tenant_client: TestClient, superuser
):
    """`notes` is subscription metadata, `reason` is per-change metadata.

    Round-1 review S-3: setting `reason=payload.notes` would re-stamp the same
    sentence on every future plan change, which makes the history read as
    though someone gave that reason each time.
    """
    plan = make_plan(session, included=["documents"])

    tenant_client.put(
        _url(TENANT_A),
        json={"plan_id": str(plan.id), "notes": "acordo comercial de 2026"},
        headers=auth(superuser),
    )

    rows = history_of(session, subscription_id(session, TENANT_A))
    assert [row.kind for row in rows] == [SubscriptionChangeKind.PLAN_CHANGE]
    assert rows[0].reason is None
    # ...while the note itself is kept, on the subscription, where it belongs.
    body = tenant_client.get(_url(TENANT_A), headers=auth(superuser)).json()
    assert body["notes"] == "acordo comercial de 2026"


def test_courtesy_grant_activates_a_module_outside_the_plan(
    session: Session, tenant_client: TestClient, superuser
):
    """"O ADMINISTRATOR global continua podendo ativar um módulo à revelia do
    plano" is **one call**."""
    plan = make_plan(session, included=["documents"], base_price=100.0)
    subscription = subscribe(session, tenant_id=TENANT_A, plan=plan)
    assert "finance" in disabled_of(session, TENANT_A)

    response = tenant_client.put(
        _courtesy_url(TENANT_A),
        json={"courtesy_modules": ["finance"], "reason": "negociação"},
        headers=auth(superuser),
    )

    assert response.status_code == 200
    row = module_row(response.json(), "finance")
    assert row["is_active"] is True
    assert row["courtesy"] is True
    assert row["in_plan"] is False
    assert row["source"] == "COURTESY"
    assert "finance" not in disabled_of(session, TENANT_A)
    # Courtesy is free: the inert estimate does not move.
    assert response.json()["estimated_monthly_total"] == 100.0

    modules = tenant_client.get(
        f"/api/v1/tenants/{TENANT_A}/modules", headers=auth(superuser)
    ).json()["modules"]
    assert next(r for r in modules if r["module"] == "finance")["is_active"] is True

    rows = history_of(session, subscription.id)
    assert [row.kind for row in rows] == [SubscriptionChangeKind.COURTESY_GRANT]
    assert rows[0].modules_added == ["finance"]
    assert rows[0].reason == "negociação"
    assert rows[0].changed_by_id == superuser.id


def test_courtesy_revoke_deactivates_unless_the_plan_covers_it(
    session: Session, tenant_client: TestClient, superuser
):
    plan = make_plan(session, included=["documents"])
    subscription = subscribe(
        session, tenant_id=TENANT_A, plan=plan, courtesy=["finance", "documents"]
    )

    response = tenant_client.put(
        _courtesy_url(TENANT_A),
        json={"courtesy_modules": [], "reason": "fim do teste"},
        headers=auth(superuser),
    )

    assert response.status_code == 200
    # Outside the plan: deactivated.
    assert module_row(response.json(), "finance")["is_active"] is False
    # Also covered by the plan: the revoke changes nothing but the label.
    covered = module_row(response.json(), "documents")
    assert covered["is_active"] is True
    assert covered["courtesy"] is False
    assert covered["source"] == "PLAN"

    rows = history_of(session, subscription.id)
    assert [row.kind for row in rows] == [SubscriptionChangeKind.COURTESY_REVOKE]
    assert rows[0].modules_removed == ["documents", "finance"]


def test_a_grant_and_a_revoke_in_one_call_append_one_row_each(
    session: Session, tenant_client: TestClient, superuser
):
    plan = make_plan(session, included=["documents"])
    subscription = subscribe(
        session, tenant_id=TENANT_A, plan=plan, courtesy=["finance"]
    )

    response = tenant_client.put(
        _courtesy_url(TENANT_A),
        json={"courtesy_modules": ["assets"], "reason": "troca"},
        headers=auth(superuser),
    )

    assert response.status_code == 200
    kinds = [row.kind for row in history_of(session, subscription.id)]
    assert sorted(kinds) == sorted(
        [
            SubscriptionChangeKind.COURTESY_GRANT,
            SubscriptionChangeKind.COURTESY_REVOKE,
        ]
    )


def test_a_no_op_courtesy_call_appends_nothing(
    session: Session, tenant_client: TestClient, superuser
):
    plan = make_plan(session, included=["documents"])
    subscription = subscribe(
        session, tenant_id=TENANT_A, plan=plan, courtesy=["finance"]
    )

    response = tenant_client.put(
        _courtesy_url(TENANT_A),
        json={"courtesy_modules": ["finance"]},
        headers=auth(superuser),
    )

    assert response.status_code == 200
    assert history_of(session, subscription.id) == []


def test_courtesy_rejects_unknown_and_core_modules(
    session: Session, tenant_client: TestClient, superuser
):
    """Granting as courtesy something that is never off is meaningless, and
    APRAS-39's `CoreModuleCannotBeDisabledError` is the wrong class here
    because nothing is being disabled."""
    plan = make_plan(session, included=["documents"])
    subscribe(session, tenant_id=TENANT_A, plan=plan)

    unknown = tenant_client.put(
        _courtesy_url(TENANT_A),
        json={"courtesy_modules": ["not_a_module"]},
        headers=auth(superuser),
    )
    assert unknown.status_code == 400
    assert unknown.json()["detail"] == "Unknown module: 'not_a_module'"

    core = tenant_client.put(
        _courtesy_url(TENANT_A),
        json={"courtesy_modules": ["billing"]},
        headers=auth(superuser),
    )
    assert core.status_code == 400
    assert core.json()["detail"] == "Core modules are always active: billing"
    assert "billing" in CORE_MODULES


# ---------------------------------------------------------------------------
# Guards and isolation
# ---------------------------------------------------------------------------


def test_a_tenant_admin_gets_403_on_all_three_routes_including_own_tenant(
    session: Session, tenant_client: TestClient, superuser
):
    """This router is global and resolves no acting tenant, so the capability
    is not even readable here."""
    plan = make_plan(session, included=["documents"])
    subscribe(session, tenant_id=TENANT_A, plan=plan)
    tenant_admin = make_tenant_admin(session)
    headers = auth(tenant_admin, TENANT_A)

    assert tenant_client.get(_url(TENANT_A), headers=headers).status_code == 403
    assert tenant_client.put(
        _url(TENANT_A), json={"plan_id": str(plan.id)}, headers=headers
    ).status_code == 403
    refused = tenant_client.put(
        _courtesy_url(TENANT_A), json={"courtesy_modules": []}, headers=headers
    )
    assert refused.status_code == 403
    assert refused.json()["detail"] == "The user doesn't have enough privileges"


def test_unauthenticated_is_401(tenant_client: TestClient):
    assert tenant_client.get(_url(TENANT_A)).status_code == 401
    assert tenant_client.put(
        _url(TENANT_A), json={"plan_id": str(uuid.uuid4())}
    ).status_code == 401


def test_unknown_tenant_is_404_and_a_missing_subscription_is_404_on_courtesy(
    session: Session, tenant_client: TestClient, superuser
):
    missing = uuid.uuid4()
    plan = make_plan(session, included=["documents"])

    assert tenant_client.get(
        _url(missing), headers=auth(superuser)
    ).status_code == 404
    assert tenant_client.put(
        _url(missing), json={"plan_id": str(plan.id)}, headers=auth(superuser)
    ).status_code == 404

    unknown_plan = tenant_client.put(
        _url(TENANT_A),
        json={"plan_id": str(uuid.uuid4())},
        headers=auth(superuser),
    )
    assert unknown_plan.status_code == 404

    no_subscription = tenant_client.put(
        _courtesy_url(TENANT_A),
        json={"courtesy_modules": ["finance"]},
        headers=auth(superuser),
    )
    assert no_subscription.status_code == 404
    assert no_subscription.json()["detail"] == "This tenant has no subscription"


def test_the_subscription_of_one_tenant_is_written_and_the_other_is_untouched(
    session: Session, tenant_client: TestClient, superuser, tenant_b
):
    plan_a = make_plan(session, name="Plano A", included=["documents"])
    plan_b = make_plan(session, name="Plano B", included=["finance"])
    subscription_b = subscribe(session, tenant_id=tenant_b.id, plan=plan_b)
    disabled_b_before = disabled_of(session, tenant_b.id)

    response = tenant_client.put(
        _url(TENANT_A), json={"plan_id": str(plan_a.id)}, headers=auth(superuser)
    )

    assert response.status_code == 200
    assert disabled_of(session, tenant_b.id) == disabled_b_before
    session.expire_all()
    assert session.get(type(subscription_b), subscription_b.id).plan_id == plan_b.id
    assert history_of(session, subscription_b.id) == []


def test_the_superuser_read_matches_the_tenant_side_read(
    session: Session, tenant_client: TestClient, superuser
):
    """One `build_read`, two paths to it -- so the two surfaces cannot drift."""
    plan = make_plan(session, included=["documents"], prices={"documents": 7.0})
    subscribe(session, tenant_id=TENANT_A, plan=plan)

    operator_view = tenant_client.get(_url(TENANT_A), headers=auth(superuser))
    tenant_view = tenant_client.get(
        "/api/v1/subscription", headers=auth(superuser, TENANT_A)
    )

    assert operator_view.status_code == tenant_view.status_code == 200
    assert operator_view.json() == tenant_view.json()
