"""The structural proof of the enforcement swap (IAM F2, APRAS-46 §8).

Two walks, both mechanical:

* a **route walk** over `app.main.app`, built on the same `_depends_on` /
  `_api_routes` shape `test_tenant_route_scope.py` and `test_tenant_admin.py`
  already use, asserting that the two tenant-admin role guards are gone, that
  every `PermissionRequired` mounted on a route declares exactly
  `ROUTE_PERMISSIONS[(method, path)]`, and that the is_superuser carve-out is
  still exactly the five global tenant writes;
* an **AST walk** over `backend/app/`, asserting that the actor-role reads
  that survive the slice are *exactly* the twenty-two of §5.3 — a new read
  fails, a removed read fails, a moved read fails — and that the arithmetic
  `100 - 85 == 15` closes.

The counting rule is stated once, in §8.2 of the spec, and implemented once,
here:

*Scope.* Every `*.py` under `backend/app/` except `app/models/`,
`app/schemas/` and `app/seed.py` — the whole application minus the
declarative layer and the seeder.

*Actor-role attribute.* An `ast.Attribute` whose `attr == "role"` and whose
`.value` is an `ast.Name` in `{current_user, user, admin_user}`. Nothing else
qualifies: `user_in.role`, `db_user.role`, `resident.user.role`,
`UserType.role` and `folder.allowed_roles_json` are payloads, targets,
columns or data, and are outside the rule **by construction**.

*Rule C.* One count per `ast.Compare` node whose subtree contains at least
one actor-role attribute. One `Compare` is one read however many operands it
has, so `user.role in (A, D)` is 1 and `a == user.role == b` is 1, while
`user.role == A or user.role == D` is 2.

*Rule N.* One count per actor-role attribute node **not** inside any
`Compare`. This counts *nodes*, so one physical line with three `user.role`
accesses contributes 3 — exactly the `document_service` per-folder ACL case.

Rule C and Rule N partition every actor-role read in scope: a node is either
inside a `Compare` or it is not.

*Attribution.* `"<path relative to app/>::<function>"`, the innermost
enclosing `FunctionDef`/`AsyncFunctionDef`. Keying on `module::function`
rather than a line number keeps the allowlists stable under an unrelated edit
above a site while still failing on a real change.
"""

import ast
import pathlib

from fastapi.dependencies.models import Dependant
from fastapi.routing import APIRoute

from app.api import deps
from app.core.permissions import ROUTE_PERMISSIONS, TENANT_ADMIN_PERMISSIONS
from app.main import app

APP_ROOT = pathlib.Path(deps.__file__).resolve().parent.parent
EXCLUDED_PREFIXES = ("models/", "schemas/")
EXCLUDED_FILES = ("seed.py",)
ACTOR_NAMES = frozenset({"current_user", "user", "admin_user"})

#: Measured at this task's merge base, 02c2025abcda4626569921eafb3863dfc540eb9e
#: (the commit that landed APRAS-45), with the walker below. A future slice
#: that changes either number has to change it deliberately.
RULE_C_BASELINE = 100
RULE_N_BASELINE = 7
#: §5.4's per-module subtraction, aggregated.
CONVERTED_COMPARE = 85

#: The seven routes APRAS-43 gated with `get_current_tenant_admin` /
#: `get_current_tenant_admin_or_manager`, which IAM F2 swaps to
#: `require_permission` — the only route-level use of the dependency form.
PERMISSION_GUARDED_ROUTES: frozenset[tuple[str, str]] = frozenset(
    {
        ("DELETE", "/api/v1/tasks/{task_id}"),
        ("DELETE", "/api/v1/lots/{lot_id}"),
        ("PATCH", "/api/v1/users/{user_id}"),
        ("PATCH", "/api/v1/users/{user_id}/contact-info"),
        ("POST", "/api/v1/user-types/"),
        ("PATCH", "/api/v1/user-types/{user_type_id}"),
        ("DELETE", "/api/v1/user-types/{user_type_id}"),
    }
)

#: The is_superuser carve-out, duplicated from `test_tenant_admin.py` on
#: purpose: this module states its own boundary, and the original test keeps
#: passing unmodified.
ADMIN_ONLY_ROUTES: frozenset[tuple[str, str]] = frozenset(
    {
        ("POST", "/api/v1/tenants"),
        ("PATCH", "/api/v1/tenants/{tenant_id}"),
        ("POST", "/api/v1/tenants/{tenant_id}/members"),
        ("DELETE", "/api/v1/tenants/{tenant_id}/members/{user_id}"),
        ("PATCH", "/api/v1/tenants/{tenant_id}/members/{user_id}"),
    }
)

#: The routes `test_tenant_route_scope.py` classifies as global; re-stated
#: here so `test_every_route_is_still_tenant_classified` can run without
#: importing another test module.
GLOBAL_PREFIXES = ("/api/v1/tenants", "/api/v1/auth", "/api/v1/health")
GLOBAL_EXTRA = frozenset({("GET", "/"), ("POST", "/api/v1/access-control/webhook/verification")})


# ---------------------------------------------------------------------------
# §5.3 -- the three allowlists, as two literals
# ---------------------------------------------------------------------------

#: Rule-C survivors: 15 reads in 15 functions.
#:
#: A = is_superuser-marked / global scope (F3 replaces them);
#: B = object / visibility dimension (F5 owns);
#: D = the resolver plumbing that cannot be converted without circularity.
ROLE_READS_COMPARE: dict[str, tuple[int, str, str]] = {
    # --- A: is_superuser-marked / global scope ---------------------------
    "api/deps.py::get_current_active_admin": (
        1,
        "F3",
        (
            "still guards the 5 global /api/v1/tenants writes; no acting "
            "tenant exists there, so no permission is resolvable"
        ),
    ),
    "api/deps.py::get_current_admin_or_manager": (
        1,
        "F3",
        (
            "no route uses it; kept so test_tenant_admin.py's structural case "
            "stays unmodified. F3 removes both together"
        ),
    ),
    "api/deps.py::has_admin_capability": (
        1,
        "F3",
        "feeds the allowed_menus gate and the §3.3 tenant_admin bridge",
    ),
    "api/deps.py::_resolve_from_header": (
        1,
        "F3",
        (
            "'an ADMINISTRATOR may act in any tenant' plus the 404/403 "
            "existence oracle of APRAS-42"
        ),
    ),
    "api/v1/endpoints/users.py::update_user": (
        1,
        "F3",
        (
            "the three escalation rules for non-global-administrators "
            "(APRAS-43 §6.3); the target-role reads are payload reads and are "
            "outside both rules by construction"
        ),
    ),
    "services/tenant_service.py::list_tenants": (
        1,
        "F3",
        "tenant visibility on the global GET /api/v1/tenants list",
    ),
    "services/tenant_service.py::get_visible_tenant": (
        1,
        "F3",
        "the same tenant-visibility rule for GET /api/v1/tenants/{id}",
    ),
    # --- B: object / visibility dimension --------------------------------
    "api/deps.py::assert_manager_can_see_task": (
        1,
        "F5",
        "the MANAGER Task.visible_to tier; its GUEST branch is converted",
    ),
    "api/deps.py::assert_can_edit_task": (
        1,
        "F5",
        "the MANAGER own/unassigned-task rule; its GUEST branch is converted",
    ),
    "api/v1/endpoints/tasks.py::list_tasks": (
        1,
        "F5",
        "the MANAGER Task.visible_to query filter; its GUEST branch is converted",
    ),
    "services/task_service.py::create_task": (
        1,
        "F5",
        "MANAGER visible_to defaulting; the module is not edited by this slice",
    ),
    "services/task_service.py::update_task": (
        1,
        "F5",
        "MANAGER visible_to subset rule; the module is not edited by this slice",
    ),
    "services/occurrence_service.py::_check_user_access": (
        1,
        "F5",
        (
            "the MANAGER visibility tier between 'all' and 'own + public'; "
            "its A/D branch is converted"
        ),
    ),
    "services/occurrence_service.py::get_occurrences": (
        1,
        "F5",
        "the same visibility tier as a query filter; its A/D branch is converted",
    ),
    # --- D: resolver plumbing --------------------------------------------
    "api/deps.py::get_effective_user_type_ids": (
        1,
        "F5",
        (
            "the role-implicit UserType resolution get_effective_permissions "
            "is built on; converting it would be circular. Retired in F5, "
            "when User.role stops existing and group membership becomes "
            "explicit"
        ),
    ),
}

#: Rule-N survivors: 7 reads in 5 functions, all F5.
ROLE_READS_NON_COMPARE: dict[str, tuple[int, str, str]] = {
    "services/document_service.py::get_accessible_folder_ids": (
        3,
        "F5",
        (
            "one physical line -- role_str = user.role.value if hasattr(...) "
            "-- carries three actor-role nodes, and Rule N counts nodes. "
            "role_str is matched against the folder's stored "
            "allowed_roles_json: a data-driven per-folder ACL, the object "
            "dimension of §5.2"
        ),
    ),
    "api/deps.py::get_effective_permissions": (
        1,
        "F5",
        (
            "LEGACY_ROLE_PERMISSIONS.get(user.role, ...) -- F1's own "
            "resolver. Not an authorization decision; it is the transitional "
            "map that produces permissions. F5 deletes it with the legacy map"
        ),
    ),
    "api/v1/endpoints/lots.py::link_user_to_lot": (
        1,
        "F5",
        (
            "serialisation only: UserSummaryRead(..., role=user.role). "
            "No branch, no decision"
        ),
    ),
    "services/lot_service.py::get_lot_detail": (
        1,
        "F5",
        "the same serialisation into UserSummaryRead",
    ),
    "services/tenant_service.py::_to_member_read": (
        1,
        "F5",
        "the same serialisation into TenantMemberRead",
    ),
}

VALID_SLICES = frozenset({"F3", "F5"})


# ---------------------------------------------------------------------------
# The walkers
# ---------------------------------------------------------------------------


def _in_scope() -> list[pathlib.Path]:
    paths = []
    for path in sorted(APP_ROOT.rglob("*.py")):
        relative = path.relative_to(APP_ROOT).as_posix()
        if relative.startswith(EXCLUDED_PREFIXES) or relative in EXCLUDED_FILES:
            continue
        paths.append(path)
    return paths


def _is_actor_role(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Attribute)
        and node.attr == "role"
        and isinstance(node.value, ast.Name)
        and node.value.id in ACTOR_NAMES
    )


def _function_index(tree: ast.AST) -> dict[int, str]:
    """`id(node) -> innermost enclosing function name`, `<module>` at top level."""
    index: dict[int, str] = {}

    def visit(node: ast.AST, current: str) -> None:
        for child in ast.iter_child_nodes(node):
            name = current
            if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef):
                name = child.name
            index[id(child)] = name
            visit(child, name)

    index[id(tree)] = "<module>"
    visit(tree, "<module>")
    return index


def walk_role_reads() -> tuple[dict[str, int], dict[str, int]]:
    """The Rule-C and Rule-N mappings, `module::function -> count`."""
    compare: dict[str, int] = {}
    non_compare: dict[str, int] = {}
    for path in _in_scope():
        relative = path.relative_to(APP_ROOT).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8"))
        where = _function_index(tree)
        inside_compare: set[int] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare):
                hits = [n for n in ast.walk(node) if _is_actor_role(n)]
                if hits:
                    key = f"{relative}::{where.get(id(node), '<module>')}"
                    compare[key] = compare.get(key, 0) + 1
                inside_compare.update(id(n) for n in hits)
        for node in ast.walk(tree):
            if _is_actor_role(node) and id(node) not in inside_compare:
                key = f"{relative}::{where.get(id(node), '<module>')}"
                non_compare[key] = non_compare.get(key, 0) + 1
    return compare, non_compare


def _api_routes() -> list[APIRoute]:
    return [route for route in app.routes if isinstance(route, APIRoute)]


def _route_keys(route: APIRoute) -> list[tuple[str, str]]:
    return [
        (method, route.path) for method in sorted(route.methods - {"HEAD", "OPTIONS"})
    ]


def _depends_on(dependant: Dependant, target) -> bool:
    if dependant.call is target:
        return True
    return any(_depends_on(sub, target) for sub in dependant.dependencies)


def _permission_guards(dependant: Dependant) -> list[deps.PermissionRequired]:
    found = []
    if isinstance(dependant.call, deps.PermissionRequired):
        found.append(dependant.call)
    for sub in dependant.dependencies:
        found.extend(_permission_guards(sub))
    return found


# ---------------------------------------------------------------------------
# §8.1 -- the route walk
# ---------------------------------------------------------------------------


def test_no_route_depends_on_a_tenant_admin_role_guard():
    """Both guards are deleted; re-adding either is a failure, not a warning."""
    assert not hasattr(deps, "get_current_tenant_admin")
    assert not hasattr(deps, "get_current_tenant_admin_or_manager")


def test_get_current_active_admin_is_still_exactly_the_five_tenant_writes():
    found = {
        key
        for route in _api_routes()
        if _depends_on(route.dependant, deps.get_current_active_admin)
        for key in _route_keys(route)
    }
    assert found == ADMIN_ONLY_ROUTES


def test_every_route_level_permission_matches_the_registry():
    """A `PermissionRequired` must declare its own route's permission."""
    guarded: dict[tuple[str, str], str] = {}
    for route in _api_routes():
        for guard in _permission_guards(route.dependant):
            for key in _route_keys(route):
                guarded[key] = guard.permission

    assert set(guarded) == PERMISSION_GUARDED_ROUTES
    mismatched = sorted(
        (key, permission, ROUTE_PERMISSIONS[key])
        for key, permission in guarded.items()
        if permission != ROUTE_PERMISSIONS[key]
    )
    assert not mismatched, f"(route, declared, registry): {mismatched}"


def test_require_permission_returns_the_class_the_route_walk_reads():
    guard = deps.require_permission("lots:delete")
    assert isinstance(guard, deps.PermissionRequired)
    assert guard.permission == "lots:delete"


def test_every_route_is_still_tenant_classified():
    """The APRAS-42 invariant survives the dependency changes."""
    unclassified = []
    for route in _api_routes():
        keys = _route_keys(route)
        if _depends_on(route.dependant, deps.get_current_tenant):
            continue
        if _depends_on(route.dependant, deps.use_global_tenant_scope):
            continue
        if _depends_on(route.dependant, deps.use_default_tenant_scope):
            continue
        if all(
            key in GLOBAL_EXTRA or key[1].startswith(GLOBAL_PREFIXES) for key in keys
        ):
            continue
        unclassified.extend(keys)
    assert not unclassified, sorted(unclassified)


def test_tenant_admin_permissions_are_exactly_the_apras43_routes():
    """The bridge constant cannot drift from the routes it reproduces (§3.3)."""
    apras43_admin_routes = [
        ("DELETE", "/api/v1/tasks/{task_id}"),
        ("DELETE", "/api/v1/lots/{lot_id}"),
        ("PATCH", "/api/v1/users/{user_id}"),
        ("PATCH", "/api/v1/users/{user_id}/contact-info"),
        ("POST", "/api/v1/user-types/"),
        ("PATCH", "/api/v1/user-types/{user_type_id}"),
        ("DELETE", "/api/v1/user-types/{user_type_id}"),
    ]
    assert {
        ROUTE_PERMISSIONS[key] for key in apras43_admin_routes
    } == TENANT_ADMIN_PERMISSIONS
    assert set(apras43_admin_routes) == PERMISSION_GUARDED_ROUTES


# ---------------------------------------------------------------------------
# §8.2 -- the AST walk
# ---------------------------------------------------------------------------


def test_no_authorization_check_reads_user_role():
    """The Rule-C walk equals `ROLE_READS_COMPARE` exactly."""
    compare, _non_compare = walk_role_reads()
    expected = {key: count for key, (count, _s, _r) in ROLE_READS_COMPARE.items()}
    added = sorted(set(compare) - set(expected))
    removed = sorted(set(expected) - set(compare))
    changed = sorted(
        (key, expected[key], compare[key])
        for key in set(expected) & set(compare)
        if expected[key] != compare[key]
    )
    assert not added, f"unlisted actor-role comparisons: {added}"
    assert not removed, f"allowlisted comparisons that no longer exist: {removed}"
    assert not changed, f"(site, expected, walked): {changed}"


def test_non_comparison_role_reads_are_allowlisted():
    """The Rule-N walk equals `ROLE_READS_NON_COMPARE` exactly."""
    _compare, non_compare = walk_role_reads()
    expected = {key: count for key, (count, _s, _r) in ROLE_READS_NON_COMPARE.items()}
    assert non_compare == expected


def test_every_allowlisted_role_read_has_a_reason():
    for allowlist in (ROLE_READS_COMPARE, ROLE_READS_NON_COMPARE):
        for site, (count, slice_name, reason) in allowlist.items():
            assert count >= 1, site
            assert slice_name in VALID_SLICES, f"{site}: bad slice {slice_name!r}"
            assert reason.strip(), f"{site}: empty reason"


def test_role_read_arithmetic_closes():
    """`100 - 85 == 15` and `7 - 0 == 7`, checkable rather than claimed."""
    compare, non_compare = walk_role_reads()
    surviving_compare = sum(count for count, _s, _r in ROLE_READS_COMPARE.values())
    surviving_non_compare = sum(
        count for count, _s, _r in ROLE_READS_NON_COMPARE.values()
    )

    assert RULE_C_BASELINE == 100
    assert RULE_N_BASELINE == 7
    assert CONVERTED_COMPARE == 85
    assert surviving_compare == 15
    assert surviving_non_compare == 7
    assert surviving_compare == RULE_C_BASELINE - CONVERTED_COMPARE
    assert surviving_non_compare == RULE_N_BASELINE
    assert sum(compare.values()) == surviving_compare
    assert sum(non_compare.values()) == surviving_non_compare
    assert len(ROLE_READS_COMPARE) == 15
    assert len(ROLE_READS_NON_COMPARE) == 5


def test_the_walk_scope_is_the_application_minus_the_declarative_layer():
    """The exclusions are the three of §8.2 and nothing else."""
    scanned = {path.relative_to(APP_ROOT).as_posix() for path in _in_scope()}
    everything = {path.relative_to(APP_ROOT).as_posix() for path in APP_ROOT.rglob("*.py")}
    excluded = everything - scanned
    assert all(
        name.startswith(EXCLUDED_PREFIXES) or name in EXCLUDED_FILES
        for name in excluded
    ), sorted(excluded)
    assert "api/deps.py" in scanned
    assert "core/permissions.py" in scanned
    assert "main.py" in scanned


def test_the_surviving_reads_are_assigned_to_a_later_slice():
    """Seven is_superuser-shaped (F3); the other fifteen are F5's."""
    by_slice: dict[str, int] = {}
    for allowlist in (ROLE_READS_COMPARE, ROLE_READS_NON_COMPARE):
        for count, slice_name, _reason in allowlist.values():
            by_slice[slice_name] = by_slice.get(slice_name, 0) + count
    assert by_slice == {"F3": 7, "F5": 15}
