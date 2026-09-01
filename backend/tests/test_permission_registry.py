"""Static proof that every route declares a permission (APRAS-45 §5.2).

Mirrors `test_tenant_route_scope.py` deliberately — same file layout, same
`_api_routes()` walk — because that is the pattern this repo already reviews
and trusts. `test_every_route_is_declared_or_unguarded` is the ER-bearing
case: a new router that ships without declared permissions fails here, in CI,
before F2 can build a matrix with a hole in it. The other cases keep it from
rotting.

Nothing here enforces anything at runtime. IAM F1 builds the vocabulary and
the plumbing only; enforcement is F4.
"""

import re

from fastapi.routing import APIRoute

from app.core.permissions import (
    PERMISSIONS,
    ROUTE_PERMISSIONS,
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
    """No dead vocabulary: the catalogue is exactly the route surface."""
    assert set(ROUTE_PERMISSIONS.values()) == PERMISSIONS


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


def test_user_type_schemas_are_unchanged():
    """The model gains `permissions`; the wire format does not (§9.3)."""
    assert set(UserTypeCreate.model_fields) == {"name", "allowed_menus"}
    assert set(UserTypeRead.model_fields) == {"id", "name", "allowed_menus", "role"}
    assert set(UserTypeUpdate.model_fields) == {"name", "allowed_menus"}
