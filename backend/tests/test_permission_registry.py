"""Static proof that every route declares a permission (APRAS-45 §5.2).

Mirrors `test_tenant_route_scope.py` deliberately — same file layout, same
`_api_routes()` walk — because that is the pattern this repo already reviews
and trusts. `test_every_route_is_declared_or_unguarded` is the ER-bearing
case: a new router that ships without declared permissions fails here, in CI,
before F2 can build a matrix with a hole in it. The other cases keep it from
rotting.

IAM F1 built the vocabulary and the plumbing only. IAM F2 (`APRAS-46`) is
the enforcement swap, and amends exactly two assertions here: the
reachability rule now admits `SCOPE_PERMISSIONS` (§4.2), and the `UserType`
schemas now carry `permissions` (§9.1).
"""

import re

from fastapi.routing import APIRoute

from app.core.permissions import (
    PERMISSIONS,
    ROUTE_PERMISSIONS,
    SCOPE_PERMISSIONS,
    UNGUARDED_ROUTES,
    module_of,
    permission_for_route,
)
from app.main import app
from app.schemas.user_type import UserTypeCreate, UserTypeRead, UserTypeUpdate

#: §3 — `<module>:<action>`, exactly one colon, snake_case on both sides.
PERMISSION_RE = re.compile(r"^[a-z][a-z0-9_]*:[a-z][a-z0-9_]*$")

#: The tag groups that are entirely unguarded (§4.24).
FULLY_UNGUARDED_TAGS = frozenset({"auth", "health", "<root>"})


def _api_routes() -> list[APIRoute]:
    return [route for route in app.routes if isinstance(route, APIRoute)]


def _route_keys(route: APIRoute) -> list[tuple[str, str]]:
    """Every (METHOD, path) key of a route, ignoring the automatic verbs."""
    return [
        (method, route.path)
        for method in sorted(route.methods - {"HEAD", "OPTIONS"})
    ]


def _all_route_keys() -> set[tuple[str, str]]:
    return {key for route in _api_routes() for key in _route_keys(route)}


def _tag_of(route: APIRoute) -> str:
    return route.tags[0] if route.tags else "<root>"


def test_every_route_is_declared_or_unguarded():
    """Every route maps to a permission XOR sits on the unguarded allowlist.

    This is the case that fails when a new router ships without declared
    permissions.
    """
    undeclared = []
    double_declared = []
    for key in sorted(_all_route_keys()):
        mapped = key in ROUTE_PERMISSIONS
        unguarded = key in UNGUARDED_ROUTES
        if mapped and unguarded:
            double_declared.append(key)
        elif not (mapped or unguarded):
            undeclared.append(key)

    assert not undeclared, (
        "routes with no declared permission and not on the unguarded "
        f"allowlist: {undeclared}"
    )
    assert not double_declared, (
        f"routes both mapped and allowlisted as unguarded: {double_declared}"
    )


def test_no_stale_registry_entries():
    """Every registry key names a route that actually exists."""
    live = _all_route_keys()
    stale_mapped = sorted(set(ROUTE_PERMISSIONS) - live)
    stale_unguarded = sorted(UNGUARDED_ROUTES - live)
    assert not stale_mapped, f"ROUTE_PERMISSIONS names dead routes: {stale_mapped}"
    assert not stale_unguarded, (
        f"UNGUARDED_ROUTES names dead routes: {stale_unguarded}"
    )


def test_every_declared_permission_is_in_the_catalogue():
    unknown = sorted(set(ROUTE_PERMISSIONS.values()) - PERMISSIONS)
    assert not unknown, f"mapped permissions missing from PERMISSIONS: {unknown}"


def test_every_catalogue_permission_is_reachable():
    """No dead vocabulary: route surface plus IAM F2's four scope permissions.

    Amended by APRAS-46 §7.1. F1's intent survives: a scope permission is
    dead unless it appears in the enforcement code, which
    `test_permission_enforcement.py`'s AST allowlist makes visible.
    """
    assert set(ROUTE_PERMISSIONS.values()) | SCOPE_PERMISSIONS == PERMISSIONS


def test_scope_permissions_are_not_route_mapped():
    assert SCOPE_PERMISSIONS & set(ROUTE_PERMISSIONS.values()) == frozenset()


def test_scope_permissions_are_exactly_four():
    assert set(SCOPE_PERMISSIONS) == {
        "residents:read_any_lot",
        "visitors:manage_any_lot",
        "occurrences:manage_all",
        "uploads:auto_approve",
    }


def test_permission_strings_follow_the_convention():
    bad = sorted(p for p in PERMISSIONS if not PERMISSION_RE.match(p))
    assert not bad, f"permissions violating <module>:<action>: {bad}"


def test_unguarded_allowlist_is_ten_routes():
    assert len(UNGUARDED_ROUTES) == 10


def test_route_count_is_fully_accounted_for():
    """The registry accounts for the whole route table, with no overlap.

    The total is recomputed from `app.main.app` rather than hard-coded, so
    the invariant survives a baseline shift; 190/180/10 is what to expect on
    the APRAS-38 tree this task was written against.
    """
    total = len(_all_route_keys())
    assert set(ROUTE_PERMISSIONS) & UNGUARDED_ROUTES == set()
    assert len(ROUTE_PERMISSIONS) + len(UNGUARDED_ROUTES) == total
    assert len(UNGUARDED_ROUTES) == 10
    assert len(ROUTE_PERMISSIONS) == total - 10


def test_every_router_module_has_at_least_one_permission():
    """Each tag group is either mapped or entirely unguarded."""
    by_tag: dict[str, set[tuple[str, str]]] = {}
    for route in _api_routes():
        by_tag.setdefault(_tag_of(route), set()).update(_route_keys(route))

    silent = sorted(
        tag
        for tag, keys in by_tag.items()
        if not any(key in ROUTE_PERMISSIONS for key in keys)
    )
    assert silent == sorted(FULLY_UNGUARDED_TAGS)
    for tag in FULLY_UNGUARDED_TAGS:
        assert by_tag[tag] <= UNGUARDED_ROUTES


def test_permission_for_route_resolves_and_returns_none_for_unguarded():
    assert permission_for_route("GET", "/api/v1/tasks/") == "tasks:read"
    assert permission_for_route("POST", "/api/v1/auth/login") is None
    assert permission_for_route("GET", "/nope") is None


def test_module_of_returns_the_module_segment():
    assert module_of("purchases:decide") == "purchases"
    assert {module_of(p) for p in PERMISSIONS} == {p.split(":")[0] for p in PERMISSIONS}


def test_user_type_schemas_expose_permissions():
    """The declared F1 -> F2 handoff (APRAS-46 §7.1).

    F1's ER-6 pinned these schemas *in F1*; IAM F2 is the slice that makes
    groups editable, so the three schemas gain `permissions`. The assertion
    stays exact, so a future field still fails CI.
    """
    assert set(UserTypeCreate.model_fields) == {
        "name",
        "allowed_menus",
        "permissions",
    }
    assert set(UserTypeUpdate.model_fields) == {
        "name",
        "allowed_menus",
        "permissions",
    }
    assert set(UserTypeRead.model_fields) == {
        "id",
        "name",
        "allowed_menus",
        "role",
        "permissions",
    }
