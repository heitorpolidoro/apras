"""Shared fixtures for the APRAS-40 subscription suite.

**Not a test module.** Pytest does not collect it (no `test_` prefix): the six
subscription modules seed the same three things -- a superuser, a plan and a
subscription -- and a sixfold copy of that is how the six drift apart.
"""

from __future__ import annotations

import itertools
import uuid
from typing import TYPE_CHECKING

from sqlmodel import Session, select

from app.core.permissions import TOGGLEABLE_MODULES
from app.core.security import create_access_token
from app.models.plan import Plan
from app.models.role import Role
from app.models.subscription import SubscriptionChange, TenantSubscription
from app.models.tenant import DEFAULT_TENANT_ID, Tenant, UserTenantLink
from tests.conftest import make_user

if TYPE_CHECKING:  # pragma: no cover
    from fastapi.testclient import TestClient

    from app.models.user import User


TENANT_A = DEFAULT_TENANT_ID

_cpf_counter = itertools.count(1)


def next_cpf() -> str:
    return str(next(_cpf_counter)).zfill(11)


def new_user(session: Session, profile: str, **kwargs) -> User:
    user = make_user(
        session,
        id=uuid.uuid4(),
        email=f"{uuid.uuid4().hex[:12]}@billing.example.com",
        full_name=f"{profile} billing user",
        hashed_password="hash",
        profile=profile,
        cpf=next_cpf(),
        **kwargs,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def auth(user: User, tenant_id=None) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {create_access_token(user.id)}"}
    if tenant_id is not None:
        headers["X-Tenant-Id"] = str(tenant_id)
    return headers


def make_superuser(session: Session, tenant_id=TENANT_A) -> User:
    user = new_user(session, "ADMINISTRATOR", is_superuser=True)
    session.add(UserTenantLink(user_id=user.id, tenant_id=tenant_id))
    session.commit()
    return user


def make_tenant_admin(session: Session, tenant_id=TENANT_A) -> User:
    """A non-superuser who holds the whole catalogue in `tenant_id` only."""
    user = new_user(session, "RESIDENT", is_superuser=False)
    session.add(
        UserTenantLink(user_id=user.id, tenant_id=tenant_id, is_tenant_admin=True)
    )
    session.commit()
    return user


def make_role_holder(
    session: Session, permissions: list[str], tenant_id=TENANT_A
) -> tuple[User, Role]:
    """A plain member whose one extra role carries exactly `permissions`.

    This is the "Diretor" of §2.3: nothing seeds `billing:*` into any bundle,
    so a director reaches the area exactly when the condominium's role row
    carries the two strings.
    """
    role = Role(name=f"Papel {uuid.uuid4().hex[:8]}", tenant_id=tenant_id, permissions=[])
    session.add(role)
    session.commit()
    session.refresh(role)

    user = new_user(session, "GUEST", is_superuser=False, roles=[role])
    session.add(UserTenantLink(user_id=user.id, tenant_id=tenant_id))
    session.commit()

    role.permissions = list(permissions)
    session.add(role)
    session.commit()
    session.refresh(role)
    return user, role


def make_plan(
    session: Session,
    *,
    name: str | None = None,
    included: list[str] | None = None,
    prices: dict[str, float] | None = None,
    base_price: float = 100.0,
    is_active: bool = True,
) -> Plan:
    plan = Plan(
        name=name or f"Plano {uuid.uuid4().hex[:8]}",
        included_modules=sorted(included or []),
        module_prices=dict(prices or {}),
        base_price=base_price,
        is_active=is_active,
    )
    session.add(plan)
    session.commit()
    session.refresh(plan)
    return plan


def subscribe(
    session: Session,
    *,
    tenant_id,
    plan: Plan,
    courtesy: list[str] | None = None,
    status=None,
    active: list[str] | None = None,
) -> TenantSubscription:
    """Put `tenant_id` on `plan` directly, bypassing the API.

    `disabled_modules` is set to whatever leaves `active` on. The default --
    everything the plan and the courtesy set cover -- is exactly the state a
    real `PUT /tenants/{id}/subscription` leaves an all-on tenant in (§4.4 b
    is shrink-only, so nothing the plan covers is switched off). Pass
    `active=[]` for a tenant that has contracted nothing yet.

    No history row is written, which is what lets the history cases count
    from zero.
    """
    subscription = TenantSubscription(
        tenant_id=tenant_id,
        plan_id=plan.id,
        courtesy_modules=sorted(courtesy or []),
    )
    if status is not None:
        subscription.status = status
    session.add(subscription)

    if active is None:
        on = (set(plan.included_modules) | set(courtesy or [])) & TOGGLEABLE_MODULES
    else:
        on = set(active) & TOGGLEABLE_MODULES
    tenant = session.get(Tenant, tenant_id)
    tenant.disabled_modules = sorted(TOGGLEABLE_MODULES - on)
    session.add(tenant)
    session.commit()
    session.refresh(subscription)
    return subscription


def history_of(session: Session, subscription_id) -> list[SubscriptionChange]:
    session.expire_all()
    return list(
        session.exec(
            select(SubscriptionChange)
            .where(SubscriptionChange.subscription_id == subscription_id)
            .order_by(SubscriptionChange.changed_at)
        ).all()
    )


def disabled_of(session: Session, tenant_id) -> list[str]:
    session.expire_all()
    return list(session.get(Tenant, tenant_id).disabled_modules)


def get_subscription(client: TestClient, user: User, tenant_id=TENANT_A):
    return client.get("/api/v1/subscription", headers=auth(user, tenant_id))


def module_row(body: dict, module: str) -> dict:
    return next(row for row in body["modules"] if row["module"] == module)


def subscription_id(session: Session, tenant_id):
    """The id of `tenant_id`'s subscription row, read outside any request."""
    session.expire_all()
    return session.exec(
        select(TenantSubscription).where(TenantSubscription.tenant_id == tenant_id)
    ).first().id
