"""Shared world-building for the four APRAS-44 test modules.

**Not a test module.** It exists so the escalation, process, RBAC and
isolation suites all build the same world the same way: one lot, one
resident-with-a-user, one staff actor, one rule and its ladder. A second
implementation of "a tenant with an infraction in it" would let two suites
disagree about what they are testing.

CPFs are *derived* from a seed rather than listed, exactly as
``tests/matrix_world._cpf`` derives them: ``ResidentCreate`` validates the
check digits and ``User.cpf`` is globally unique, so a hand-written pool runs
out and a derivation never does.
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from typing import TYPE_CHECKING

from app.core.security import create_access_token
from app.models.lot import Lot, UserLotLink
from app.models.resident import Resident
from app.models.role import Role
from app.models.tenant import DEFAULT_TENANT_ID, UserTenantLink
from tests.conftest import make_user

if TYPE_CHECKING:  # pragma: no cover
    from sqlmodel import Session

    from app.models.user import User


def cpf(seed: int) -> str:
    """A check-digit-valid CPF derived from `seed`."""
    base = f"{seed:09d}"
    total = sum(int(base[index]) * (10 - index) for index in range(9))
    first = 0 if (total % 11) < 2 else 11 - (total % 11)
    nine = base + str(first)
    total = sum(int(nine[index]) * (11 - index) for index in range(10))
    second = 0 if (total % 11) < 2 else 11 - (total % 11)
    return nine + str(second)


def headers(user: User, tenant_id: uuid.UUID = DEFAULT_TENANT_ID) -> dict[str, str]:
    """Bearer token plus the acting tenant, the shape every scoped route wants."""
    return {
        "Authorization": f"Bearer {create_access_token(user.id)}",
        "X-Tenant-Id": str(tenant_id),
    }


def make_member(
    session: Session,
    *,
    profile: str,
    seed: int,
    tenant_id: uuid.UUID = DEFAULT_TENANT_ID,
    permissions: list[str] | None = None,
    is_superuser: bool | None = None,
    is_tenant_admin: bool = False,
) -> User:
    """A user who is a member of `tenant_id`, optionally with an extra role.

    ``permissions`` builds one *ad-hoc* role carrying exactly those strings,
    which is how the RBAC suite expresses "a role with exactly
    ``{my_lots_read, contest}``" without touching the recorded legacy bundles.
    """
    extra: list[Role] = []
    if permissions is not None:
        role = Role(name=f"Bundle {seed}", permissions=sorted(permissions))
        session.add(role)
        session.commit()
        session.refresh(role)
        extra = [role]

    kwargs: dict = {}
    if is_superuser is not None:
        kwargs["is_superuser"] = is_superuser
    user = make_user(
        session,
        profile=profile,
        tenant_id=tenant_id,
        id=uuid.uuid4(),
        email=f"infr{seed}@test.com",
        full_name=f"Infração Ator {seed}",
        hashed_password="hash",
        cpf=cpf(seed),
        roles=extra,
        **kwargs,
    )
    session.add(
        UserTenantLink(
            user_id=user.id, tenant_id=tenant_id, is_tenant_admin=is_tenant_admin
        )
    )
    session.commit()
    session.refresh(user)
    return user


def make_lot(session: Session, *, block: str = "A", number: str = "1") -> Lot:
    lot = Lot(block=block, lot_number=number)
    session.add(lot)
    session.commit()
    session.refresh(lot)
    return lot


def make_resident(
    session: Session,
    lot: Lot,
    *,
    seed: int,
    user: User | None = None,
    is_active: bool = True,
) -> Resident:
    """A resident of `lot`, optionally linked to `user` in both ways.

    Both linkage branches are created together because that is what "the
    unit" means to :meth:`InfractionService.linked_lot_ids` and what the
    matrix world seeds.
    """
    resident = Resident(
        lot_id=lot.id,
        user_id=user.id if user is not None else None,
        full_name=f"Morador {seed}",
        cpf=cpf(seed),
        is_active=is_active,
    )
    session.add(resident)
    if user is not None:
        session.add(
            UserLotLink(
                user_id=user.id, lot_id=lot.id, start_date=None, end_date=None
            )
        )
    session.commit()
    session.refresh(resident)
    return resident


#: The three-rung ladder every suite that needs "a real policy" uses:
#: ``AVISO`` → ``NOTIFICACAO(30 days)`` → ``MULTA(FIXED 250)``.
LADDER_THREE = [
    {"step_order": 1, "action": "AVISO"},
    {"step_order": 2, "action": "NOTIFICACAO", "defense_deadline_days": 30},
    {
        "step_order": 3,
        "action": "MULTA",
        "fine_mode": "FIXED",
        "fine_fixed_amount": 250.0,
    },
]


def create_rule(
    client,
    actor: User,
    *,
    article: str = "art. 12, §2º",
    origin: str = "REGIMENTO_INTERNO",
    window_days: int = 365,
    steps: list[dict] | None = None,
    tenant_id: uuid.UUID = DEFAULT_TENANT_ID,
) -> str:
    """Create a rule through the API and optionally write its ladder."""
    response = client.post(
        "/api/v1/infraction-rules",
        json={
            "article": article,
            "origin": origin,
            "description": f"Regra {article}",
            "recidivism_window_days": window_days,
        },
        headers=headers(actor, tenant_id),
    )
    assert response.status_code == 201, response.text
    rule_id = response.json()["id"]
    if steps:
        written = client.put(
            f"/api/v1/infraction-rules/{rule_id}/policy",
            json={"steps": steps},
            headers=headers(actor, tenant_id),
        )
        assert written.status_code == 200, written.text
    return rule_id


def create_infraction(
    client,
    actor: User,
    *,
    rule_id: str,
    lot: Lot,
    resident: Resident,
    occurred_on: date | None = None,
    description: str = "Som alto às 23h.",
    tenant_id: uuid.UUID = DEFAULT_TENANT_ID,
) -> dict:
    """Register one infraction through the API and return the response body."""
    response = client.post(
        "/api/v1/infractions",
        json={
            "rule_id": rule_id,
            "lot_id": str(lot.id),
            "responsible_resident_id": str(resident.id),
            "occurred_on": (occurred_on or date.today() - timedelta(days=1)).isoformat(),
            "description": description,
        },
        headers=headers(actor, tenant_id),
    )
    assert response.status_code == 201, response.text
    return response.json()
