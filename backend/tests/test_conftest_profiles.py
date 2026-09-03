"""§12.2 category 2: the one proof the 36 converted modules inherit.

`conftest.make_user` is the single substitution for the ~130
`User(..., role=UserRole.X, ...)` constructions the enum's death invalidated.
Pinning the helper here is what lets those 36 modules be a mechanical
`role=UserRole.X` -> `profile="X"` edit instead of 36 bespoke rewrites: if the
helper ever stopped granting exactly the recorded bundle, this module fails
rather than 36 assertions quietly measuring something else.
"""

import uuid

import pytest
from sqlmodel import Session, select

from app.api import deps
from app.core.permissions import PERMISSIONS
from app.models.role import Role
from app.models.tenant import DEFAULT_TENANT_ID
from app.services.role_service import role_names_in
from app.services.tenant_service import LEGACY_ROLE_NAMES
from tests.conftest import (
    LEGACY_BUNDLES,
    NEW_TIER,
    PROFILE_ROLE_NAMES,
    bundle,
    make_user,
    profile_role,
)
from tests.matrix_world import PARITY_PROFILES


def _user(session: Session, profile: str, **kwargs):
    return make_user(
        session,
        profile=profile,
        id=uuid.uuid4(),
        email=f"{uuid.uuid4().hex[:10]}@profiles.example.com",
        full_name=f"{profile} profile case",
        hashed_password="hash",
        cpf=str(uuid.uuid4().int)[:11],
        **kwargs,
    )


@pytest.mark.parametrize("profile", PARITY_PROFILES)
def test_every_profile_grants_exactly_the_recorded_bundle(
    session: Session, profile: str
):
    """`bundle(profile)` is `legacy_role_bundles.json` union `NEW_TIER`.

    The same union migration `0033` writes onto the six historically-named
    rows, from the same recorded artefact — one source, three readers
    (`0033`'s literal, `matrix_world`, this helper).
    """
    user = _user(session, profile, is_superuser=False)

    assert deps.get_effective_permissions(user, session) == bundle(profile)
    assert bundle(profile) == frozenset(LEGACY_BUNDLES[profile]) | NEW_TIER[profile]
    assert bundle(profile) <= PERMISSIONS


def test_the_six_profiles_are_the_six_historically_named_rows():
    assert set(PROFILE_ROLE_NAMES) == set(PARITY_PROFILES)
    assert set(PROFILE_ROLE_NAMES.values()) == set(LEGACY_ROLE_NAMES)


def test_the_recorded_bundles_have_the_documented_sizes():
    """The numbers §11.2 and ER-3 quote, so a silent re-record fails here."""
    assert {k: len(v) for k, v in LEGACY_BUNDLES.items()} == {
        "ADMINISTRATOR": 155,
        "DIRECTOR": 144,
        "GUEST": 30,
        "MANAGER": 83,
        "PORTEIRO": 31,
        "RESIDENT": 50,
    }
    # ADMINISTRATOR: 155 + {tasks:read_all, tasks:update_any} = 157, and
    # deliberately *not* the whole 159-string catalogue -- that is the
    # superuser short-circuit, which is a different statement (§11.2).
    assert len(bundle("ADMINISTRATOR")) == 157
    assert bundle("ADMINISTRATOR") != PERMISSIONS


def test_the_new_tier_is_the_two_legacy_tiers_as_data():
    """`MANAGER` gets neither task permission; nobody else gets the occurrence one."""
    for profile in ("ADMINISTRATOR", "DIRECTOR", "RESIDENT", "PORTEIRO"):
        assert {"tasks:read_all", "tasks:update_any"} <= bundle(profile)
        assert "occurrences:read_assigned" not in bundle(profile)
    assert "occurrences:read_assigned" in bundle("MANAGER")
    assert not {"tasks:read_all", "tasks:update_any"} & bundle("MANAGER")
    assert not NEW_TIER["GUEST"]


def test_profile_role_is_idempotent_per_tenant(session: Session):
    first = profile_role(session, "DIRECTOR")
    second = profile_role(session, "DIRECTOR")

    assert first.id == second.id
    rows = session.exec(
        select(Role).where(Role.name == PROFILE_ROLE_NAMES["DIRECTOR"])
    ).all()
    assert len(rows) == 1


def test_make_user_unions_extra_roles_rather_than_replacing_the_profile(
    session: Session,
):
    extra = Role(name="Conselho", permissions=["finance:read"])
    session.add(extra)
    session.commit()

    user = _user(session, "MANAGER", roles=[extra], is_superuser=False)

    assert {role.name for role in user.roles} == {"Gerente (papel)", "Conselho"}
    assert deps.get_effective_permissions(user, session) == bundle("MANAGER") | {
        "finance:read"
    }


def test_make_user_defaults_the_flag_only_for_the_administrator_profile(
    session: Session,
):
    """Mirrors the `User.__init__` default F3 shipped and F5 deleted.

    A fixture that meant "the global administrator" still means it; an
    explicit `is_superuser=` always wins.
    """
    assert _user(session, "ADMINISTRATOR").is_superuser is True
    assert _user(session, "DIRECTOR").is_superuser is False
    assert _user(session, "ADMINISTRATOR", is_superuser=False).is_superuser is False
    assert _user(session, "GUEST", is_superuser=True).is_superuser is True


def test_the_two_landing_carrying_profiles_carry_their_landing(session: Session):
    assert profile_role(session, "PORTEIRO").landing_path == "/gate"
    assert profile_role(session, "GUEST").landing_path == "/welcome"
    assert profile_role(session, "DIRECTOR").landing_path is None


def test_role_names_in_answers_nothing_without_a_tenant(session: Session):
    """`role_names_in(user, None)` is `[]`, never every role the user has.

    The serialisers reach this helper from objects that carry no `tenant_id`
    of their own, so "no acting tenant" has to fail closed exactly as
    `is_acting_tenant_admin` does — an unresolved session must not leak a
    membership from a tenant nobody asked about.
    """
    user = _user(session, "DIRECTOR")

    assert role_names_in(user, None) == []
    assert role_names_in(user, DEFAULT_TENANT_ID) == ["Diretor (papel)"]
