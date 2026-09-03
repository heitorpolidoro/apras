"""ER-4: `app/seed.py` on the new model, and the three demo profiles.

`seed.py` used to construct four users with `role=UserRole.X` and lean on the
role-implicit membership for their permissions. After IAM F5 a user's power is
**only** its role memberships, so the seed has to create them — which is the
whole reason this module exists: the seeder is the one place in `app/` that
could quietly keep working while granting nobody anything.

The demo bundles are a literal in `seed.py` and are **the dev demo's opinion,
not a product default**. F1's "nothing is seeded with permissions" decision
binds `ensure_legacy_roles` and every migration; it does not bind a script
whose job is to produce a usable demo. This module asserts that distinction
rather than assuming it.

`seed_db()` itself is not run here: it `TRUNCATE`s a live Postgres and is
exercised by the §9.3 runbook. What is run is everything the demo's
correctness rests on — the literal, the profiles it names, and the fact that
each profile's bundle really resolves.
"""

import uuid

import pytest
from sqlmodel import Session, select

from app.api import deps
from app.core.permissions import PERMISSIONS
from app.models.role import Role
from app.models.tenant import DEFAULT_TENANT_ID, UserTenantLink
from app.models.user import User
from app.seed import DEMO_BUNDLES
from app.services.tenant_service import LEGACY_ROLE_NAMES, TenantService

#: The three profiles of ER-4, and what each is a member of.
DEMO_PROFILES: dict[str, tuple[str, ...]] = {
    "admin@apras.com": ("Administrador (papel)",),
    "diretor1@apras.com": ("Diretor (papel)", "Diretor Comercial"),
    "gerente1@apras.com": ("Gerente (papel)", "Gerente Operacional"),
}


def test_the_demo_bundles_name_only_catalogue_permissions():
    """A typo in the literal would seed a role that grants nothing."""
    for name, permissions in DEMO_BUNDLES.items():
        unknown = sorted(set(permissions) - PERMISSIONS)
        assert not unknown, f"{name} names non-catalogue strings: {unknown}"


def test_the_demo_bundles_target_three_historically_named_roles():
    assert set(DEMO_BUNDLES) == {
        "Administrador (papel)",
        "Diretor (papel)",
        "Gerente (papel)",
    }
    assert set(DEMO_BUNDLES) <= set(LEGACY_ROLE_NAMES)


def test_the_demo_manager_bundle_keeps_the_legacy_tier(session: Session):
    """The one thing the demo must not accidentally flatten (§3.0).

    `MANAGER` deliberately holds neither `tasks:read_all` nor
    `tasks:update_any`, and it *does* hold `occurrences:read_assigned`. Those
    two facts are the legacy tiers, and a demo that granted the manager
    everything would stop showing them.
    """
    manager = DEMO_BUNDLES["Gerente (papel)"]
    assert "tasks:read_all" not in manager
    assert "tasks:update_any" not in manager
    assert "occurrences:read_assigned" in manager

    for board in ("Administrador (papel)", "Diretor (papel)"):
        assert "tasks:read_all" in DEMO_BUNDLES[board]
        assert "tasks:update_any" in DEMO_BUNDLES[board]


def test_the_demo_bundles_are_the_demos_opinion_not_a_product_default():
    """They are strictly smaller than the recorded legacy bundles.

    Stated as an assertion so the literal cannot silently grow into a second
    copy of `legacy_role_bundles.json` — which is exactly what F1's no-seeds
    decision forbids anywhere outside this script.
    """
    from tests.conftest import bundle  # noqa: PLC0415

    for name, profile in (
        ("Administrador (papel)", "ADMINISTRATOR"),
        ("Diretor (papel)", "DIRECTOR"),
        ("Gerente (papel)", "MANAGER"),
    ):
        assert set(DEMO_BUNDLES[name]) < bundle(profile)


def test_ensure_legacy_roles_seeds_no_permission(session: Session):
    """The production path, unlike the seed script, grants nobody anything."""
    TenantService.ensure_legacy_roles(session, DEFAULT_TENANT_ID)

    rows = session.exec(select(Role)).all()
    assert {row.name for row in rows} == set(LEGACY_ROLE_NAMES)
    assert all(row.permissions == [] for row in rows)


@pytest.mark.parametrize("email", sorted(DEMO_PROFILES))
def test_the_three_demo_profiles_have_the_recorded_bundles(
    session: Session, email: str
):
    """The demo, rebuilt in miniature: the seed's shape, not its `TRUNCATE`.

    Each profile is created exactly as `seed_db()` creates it — the six
    historically-named rows first, the demo bundles written onto three of
    them, then users linked to their roles — and the assertion is that the
    resulting effective set is the union of those bundles and nothing else.
    """
    TenantService.ensure_legacy_roles(session, DEFAULT_TENANT_ID)
    by_name = {row.name: row for row in session.exec(select(Role)).all()}
    for name, permissions in DEMO_BUNDLES.items():
        by_name[name].permissions = sorted(permissions)
        session.add(by_name[name])
    for extra in ("Diretor Comercial", "Gerente Operacional"):
        row = Role(name=extra)
        session.add(row)
        by_name[extra] = row
    session.commit()

    memberships = DEMO_PROFILES[email]
    user = User(
        id=uuid.uuid4(),
        email=email,
        full_name=email,
        hashed_password="hash",
        cpf=str(uuid.uuid4().int)[:11],
        is_superuser=email == "admin@apras.com",
        roles=[by_name[name] for name in memberships],
    )
    session.add(user)
    session.commit()
    session.add(UserTenantLink(user_id=user.id, tenant_id=DEFAULT_TENANT_ID))
    session.commit()
    session.refresh(user)

    assert {role.name for role in user.roles} == set(memberships)

    expected: set[str] = set()
    for name in memberships:
        expected |= set(DEMO_BUNDLES.get(name, []))

    if user.is_superuser:
        # The admin profile short-circuits to the whole catalogue (F3 §4).
        assert deps.get_effective_permissions(user, session) == PERMISSIONS
    else:
        assert deps.get_effective_permissions(user, session) == expected
        assert expected, f"{email} would hold nothing"


def test_the_seed_module_names_no_retired_enum():
    """`app/seed.py` was one of the three paths F2's walker excluded (§11.3)."""
    import pathlib  # noqa: PLC0415

    import app.seed as seed_module  # noqa: PLC0415

    source = pathlib.Path(seed_module.__file__).read_text(encoding="utf-8")
    assert "UserRole" not in source
    assert "allowed_menus" not in source
    # And it truncates the link table, or the demo users would keep their
    # memberships across a re-seed (§9.1).
    assert "user_role_link" in source
