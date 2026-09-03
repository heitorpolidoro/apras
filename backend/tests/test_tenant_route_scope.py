"""Static proof that every route is classified (APRAS-42 §5.2).

The isolation mechanism is only as good as its coverage of the route table.
This module walks ``app.routes`` and asserts that every ``APIRoute`` either
depends (transitively) on ``deps.get_current_tenant`` or is one of the
deliberately allowlisted global routes below. A route added without either
fails here, in CI, before it can ever leak at runtime.

``GLOBAL_ROUTES`` is literally "the routes that do not depend on
``get_current_tenant``". Three of them are not *unscoped* in the data sense —
``POST /api/v1/auth/signup`` acts in the default tenant, ``POST
/api/v1/tenants`` seeds the new tenant's role types under
``acting_tenant_scope``, and the device webhook resolves its tenant from the
``X-Device-Key`` it authenticates — they simply resolve their tenant
somewhere other than the header dependency.
"""

from fastapi.dependencies.models import Dependant
from fastapi.routing import APIRoute

from app.api import deps
from app.main import app

#: (method, path) pairs that deliberately do not depend on get_current_tenant.
GLOBAL_ROUTES: frozenset[tuple[str, str]] = frozenset(
    {
        # No session at all.
        ("GET", "/"),
        ("GET", "/api/v1/health"),
        # `user` is a global identity; these routes read/write it only.
        ("POST", "/api/v1/auth/login"),
        ("GET", "/api/v1/auth/me"),
        ("GET", "/api/v1/auth/dev-users"),
        ("POST", "/api/v1/auth/dev-login"),
        ("POST", "/api/v1/auth/forgot-password"),
        ("POST", "/api/v1/auth/reset-password"),
        # Public signup: acts in the default tenant, never in a header-chosen
        # one (`deps.use_default_tenant_scope`).
        ("POST", "/api/v1/auth/signup"),
        # `tenant` / `user_tenant_link` are unscoped tables and these routes
        # *are* the tenant surface.
        ("GET", "/api/v1/tenants"),
        ("POST", "/api/v1/tenants"),
        ("GET", "/api/v1/tenants/{tenant_id}"),
        ("PATCH", "/api/v1/tenants/{tenant_id}"),
        ("GET", "/api/v1/tenants/{tenant_id}/members"),
        ("POST", "/api/v1/tenants/{tenant_id}/members"),
        ("DELETE", "/api/v1/tenants/{tenant_id}/members/{user_id}"),
        # APRAS-43: grants/revokes the tenant_admin capability. Global on
        # purpose — on a route with no acting tenant the capability is not
        # even readable, so a tenant_admin cannot grant it to themselves.
        ("PATCH", "/api/v1/tenants/{tenant_id}/members/{user_id}"),
        # APRAS-39: the per-tenant module switch, read and write. Global for
        # the same reason as the line above -- the module switch is a
        # property of the tenant, written from outside it: a tenant_admin
        # must not be able to reach it by acting in their own tenant.
        ("GET", "/api/v1/tenants/{tenant_id}/modules"),
        ("PUT", "/api/v1/tenants/{tenant_id}/modules"),
        # Authenticated by X-Device-Key, not a JWT: resolves its tenant from
        # the device it authenticates.
        ("POST", "/api/v1/access-control/webhook/verification"),
    }
)


def _depends_on(dependant: Dependant, target) -> bool:
    """Whether `target` appears anywhere in the dependency tree."""
    if dependant.call is target:
        return True
    return any(_depends_on(sub, target) for sub in dependant.dependencies)


def _route_keys(route: APIRoute) -> list[tuple[str, str]]:
    return [(method, route.path) for method in sorted(route.methods)]


def _api_routes() -> list[APIRoute]:
    return [route for route in app.routes if isinstance(route, APIRoute)]


def test_every_route_is_either_tenant_scoped_or_allowlisted():
    """Exactly the allowlisted routes skip `get_current_tenant`."""
    unclassified = []
    wrongly_scoped = []
    for route in _api_routes():
        scoped = _depends_on(route.dependant, deps.get_current_tenant)
        for key in _route_keys(route):
            if key in GLOBAL_ROUTES:
                if scoped:
                    wrongly_scoped.append(key)
            elif not scoped:
                unclassified.append(key)

    assert not unclassified, (
        "these routes neither depend on get_current_tenant nor are "
        f"allowlisted as global: {sorted(unclassified)}"
    )
    assert not wrongly_scoped, (
        f"these allowlisted routes are tenant-scoped after all: {sorted(wrongly_scoped)}"
    )


def test_allowlist_has_no_stale_entries():
    """Every allowlist entry names a route that actually exists."""
    existing = {key for route in _api_routes() for key in _route_keys(route)}
    assert existing >= GLOBAL_ROUTES, sorted(GLOBAL_ROUTES - existing)


def test_allowlist_is_twenty_routes():
    """The global surface is small and reviewed; growing it is a decision.

    18 at the APRAS-49 merge base; APRAS-39 adds the two module-switch
    routes, which inherit `GLOBAL_SCOPED` from the tenants router mount.
    """
    assert len(GLOBAL_ROUTES) == 20


def test_route_count_is_fully_accounted_for():
    """scoped + global == every APIRoute in the application."""
    keys = [key for route in _api_routes() for key in _route_keys(route)]
    scoped = [
        key
        for route in _api_routes()
        if _depends_on(route.dependant, deps.get_current_tenant)
        for key in _route_keys(route)
    ]
    assert len(scoped) + len(GLOBAL_ROUTES) == len(keys)


def test_global_auth_routes_resolve_a_scope_explicitly():
    """Global routes still mark their scope resolved, so the fail-closed
    guard cannot fire on them by accident."""
    resolvers = (
        deps.use_global_tenant_scope,
        deps.use_default_tenant_scope,
        deps.get_current_tenant,
    )
    for route in _api_routes():
        keys = _route_keys(route)
        if not any(key in GLOBAL_ROUTES for key in keys):
            continue
        if keys in ([("GET", "/")], [("GET", "/api/v1/health")]):
            continue  # no session, nothing to resolve
        assert any(
            _depends_on(route.dependant, resolver) for resolver in resolvers
        ), f"{keys} resolves no tenant scope"
