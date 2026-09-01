"""What survives of F1's derived-parity module (APRAS-45 §6, APRAS-46 §7.2).

**The derivation is retired, and that is the deliverable of IAM F2, not an
accident.** F1 derived every row of `LEGACY_ROLE_PERMISSIONS` from a *live*
production object: `RoleSet(asset_service._STAFF_ROLES)`,
`RoleSetComplement(voting_service.NON_VOTING_ROLES)`,
`Guard(deps.get_current_tenant_admin)` and so on. `APRAS-46` deletes those
objects — `_LOT_READ_ROLES`, `_FINANCE_*_ROLES`, `BOARD_ROLES`,
`NON_VOTING_ROLES`, `_GATEKEEPER_ROLES`, `get_current_tenant_admin`,
`get_current_tenant_admin_or_manager` and the rest stop existing, because
every one of them was a role-dimension authorization check and the whole
point of the slice is that none is left. `PARITY_SOURCES` therefore cannot be
evaluated at all, and keeping the constants alive as dead literals purely to
feed a test would make it assert "the map equals a tuple nobody consults",
which is true and meaningless.

So the module keeps only its **production-independent** assertions, and the
proof the derivation carried moves to the recorded matrix of
`tests/test_permission_parity_matrix.py`: 1080 real HTTP cells recorded
against unswapped production at merge base
**02c2025abcda4626569921eafb3863dfc540eb9e** — the same sha as
`_meta.merge_base_sha` in `tests/data/parity_matrix_baseline.json` — and
re-asserted after the swap with zero divergence. That commit is where the
derived parity test was last green, and one sha anchors the whole chain:
`post-swap == baseline == pre-swap production`, and `baseline denials ==
LEGACY_ROLE_PERMISSIONS`.

Collected cases go **162 -> 6**: 157 retired (the 152-case
`test_legacy_map_matches_the_live_guards` parametrisation plus the five
source-shape tests that evaluate `PARITY_SOURCES`), 1 added
(`test_every_scope_permission_has_a_legacy_entry`).
"""

import inspect

from app.core import permissions as permissions_module
from app.core.permissions import (
    ADMIN_GAP_PERMISSIONS,
    LEGACY_MAP_REMOVAL_SLICE,
    LEGACY_ROLE_PERMISSIONS,
    PERMISSIONS,
    SCOPE_PERMISSIONS,
)
from app.models.enums import UserRole

A = UserRole.ADMINISTRATOR

#: §6.2 — the 17 permissions that resolve to all six roles, pinned by exact
#: match so a route that quietly widens fails CI with a named diff. The four
#: `SCOPE_PERMISSIONS` are `{A, D, M}` or `{A, D}`, so the seventeen are
#: unchanged by IAM F2.
ALL_SIX_ROLE_PERMISSIONS: frozenset[str] = frozenset(
    {
        "categories:read",
        "users:read",
        "user_types:read",
        "tenants:read",
        "tenants:members_read",
        "visitors:read",
        "visitors:create",
        "visitors:update",
        "feedback:read",
        "feedback:create",
        "spaces:read",
        "uploads:photo_create",
        "uploads:photo_read",
        "gate:logs_read",
        "uploads:delete",
        "residents:read",
        "authorizations:gate_lookup",
    }
)


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
    """A new admin gap, or a closed one, fails CI until the constant moves.

    `ADMIN_GAP_PERMISSIONS` moved from this module into
    `app/core/permissions.py` with IAM F2 (§11, expectation E1), so
    `user_type_service.assert_can_grant` can read it without importing a test
    module. The assertion is unchanged.
    """
    admin = LEGACY_ROLE_PERMISSIONS[A]
    live_gaps = {
        permission
        for permission in PERMISSIONS
        if permission not in admin
        and any(permission in LEGACY_ROLE_PERMISSIONS[role] for role in UserRole)
    }
    assert live_gaps == ADMIN_GAP_PERMISSIONS


def test_all_six_role_permissions_are_the_documented_seventeen():
    live = {
        permission
        for permission in PERMISSIONS
        if all(permission in LEGACY_ROLE_PERMISSIONS[role] for role in UserRole)
    }
    assert len(ALL_SIX_ROLE_PERMISSIONS) == 17
    assert live == ALL_SIX_ROLE_PERMISSIONS


def test_every_scope_permission_has_a_legacy_entry():
    """IAM F2's four scope permissions are in the map, not floating (§4.2)."""
    for permission in SCOPE_PERMISSIONS:
        holders = {
            role for role in UserRole if permission in LEGACY_ROLE_PERMISSIONS[role]
        }
        assert holders, f"{permission} is held by nobody"
        assert holders <= {UserRole.ADMINISTRATOR, UserRole.DIRECTOR, UserRole.MANAGER}


def test_legacy_map_is_marked_transitional():
    assert LEGACY_MAP_REMOVAL_SLICE == "IAM F5"

    source = inspect.getsource(permissions_module)
    assignment = source.index(
        "LEGACY_ROLE_PERMISSIONS: dict[UserRole, frozenset[str]] ="
    )
    banner = source.rindex("TRANSITIONAL", 0, assignment)
    assert banner < assignment
