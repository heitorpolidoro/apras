"""ER-1: the entity is `role` in the API, the UI and the database.

Deliverable **A** of IAM F5 (APRAS-49 §2) is a pure rename, so this module is
deliberately shallow: it pins the *names*, and every behavioural claim about
them lives in the module that already owned it. The three greps of §2.2 are
run by CI and quoted in the PR body; what an executable test can add is the
route table, the registry keys and the catalogue shape.
"""

import re

from fastapi.routing import APIRoute

from app.core.permissions import (
    PERMISSIONS,
    ROUTE_PERMISSIONS,
    TIER_PERMISSIONS,
    module_of,
)
from app.main import app

#: The four routes the rename moved, and nothing else.
ROLE_ROUTES: frozenset[tuple[str, str]] = frozenset(
    {
        ("GET", "/api/v1/roles/"),
        ("POST", "/api/v1/roles/"),
        ("PATCH", "/api/v1/roles/{role_id}"),
        ("DELETE", "/api/v1/roles/{role_id}"),
    }
)


def _route_keys() -> set[tuple[str, str]]:
    return {
        (method, route.path)
        for route in app.routes
        if isinstance(route, APIRoute)
        for method in route.methods - {"HEAD", "OPTIONS"}
    }


def test_the_roles_router_is_mounted_at_api_v1_roles():
    assert _route_keys() >= ROLE_ROUTES


def test_no_route_path_contains_user_types():
    offenders = sorted(
        key for key in _route_keys() if "user-types" in key[1] or "user_type" in key[1]
    )
    assert not offenders, f"routes still spelling the retired name: {offenders}"


def test_route_permissions_uses_the_roles_module():
    """The four keys and the four strings move together."""
    assert {ROUTE_PERMISSIONS[key] for key in ROLE_ROUTES} == {
        "roles:read",
        "roles:create",
        "roles:update",
        "roles:delete",
    }
    assert not [p for p in ROUTE_PERMISSIONS.values() if p.startswith("user_types:")]


def test_the_catalogue_has_159_permissions_in_26_modules():
    """156 -> 159 (§3.0); the module count is unchanged, `user_types` -> `roles`."""
    assert len(PERMISSIONS) == 159
    modules = {module_of(permission) for permission in PERMISSIONS}
    assert len(modules) == 26
    assert "roles" in modules
    assert "user_types" not in modules


def test_the_three_new_tier_permissions_exist_and_are_not_route_mapped():
    """They are in-code object predicates, like `SCOPE_PERMISSIONS` (§3.0)."""
    assert frozenset(
        {"tasks:read_all", "tasks:update_any", "occurrences:read_assigned"}
    ) == TIER_PERMISSIONS
    assert TIER_PERMISSIONS <= PERMISSIONS
    assert TIER_PERMISSIONS & set(ROUTE_PERMISSIONS.values()) == frozenset()


def test_no_catalogue_string_names_the_retired_module():
    assert not [p for p in PERMISSIONS if re.match(r"^user_types?:", p)]
