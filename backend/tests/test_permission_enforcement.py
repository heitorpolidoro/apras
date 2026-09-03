"""The structural proof of the enforcement swap (IAM F2, APRAS-46 §8),
carried forward by the superuser swap (IAM F3, APRAS-47 §5.3).

Two walks, both mechanical:

* a **route walk** over `app.main.app`, built on the same `_depends_on` /
  `_api_routes` shape `test_tenant_route_scope.py` and `test_tenant_admin.py`
  already use, asserting that the four deleted role guards are gone, that
  every `PermissionRequired` mounted on a route declares exactly
  `ROUTE_PERMISSIONS[(method, path)]`, and that the `get_current_superuser`
  carve-out is still exactly the five global tenant writes;
* an **AST walk** over `backend/app/`, asserting that the actor-role reads
  that survive the slice are *exactly* the thirteen of APRAS-47 §5.3 — a new
  read fails, a removed read fails, a moved read fails — and that the
  arithmetic `100 - 92 == 8` closes. A third walk runs the same two rules
  over the three paths the second one excludes, so the exclusion is proved
  empty rather than trusted.

The counting rule is stated once, in §8.2 of the spec, and implemented once,
here:

*Scope.* Every `*.py` under `backend/app/` except `app/models/`,
`app/schemas/` and `app/seed.py` — the whole application minus the
declarative layer and the seeder.

*Actor-role attribute.* An `ast.Attribute` whose `attr == "role"` and whose
`.value` is an `ast.Name` in `{current_user, user, admin_user}`. Nothing else
qualifies: `user_in.role`, `db_user.role`, `resident.user.role`,
`Role.role` and `folder.allowed_roles_json` are payloads, targets,
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
from app.core.permissions import ROUTE_PERMISSIONS
from app.main import app

APP_ROOT = pathlib.Path(deps.__file__).resolve().parent.parent
#: **Empty since IAM F5** (APRAS-49 §11.3). F2 excluded `app/models/`,
#: `app/schemas/` and `app/seed.py` because they held the enum's columns,
#: payload shapes and the seeder. The enum is gone, so the reason for the
#: exclusion is gone, and the walk now covers all of `app/` -- which is what
#: makes "both allowlists are empty" a statement about the whole application.
EXCLUDED_PREFIXES: tuple[str, ...] = ()
EXCLUDED_FILES: tuple[str, ...] = ()
ACTOR_NAMES = frozenset({"current_user", "user", "admin_user"})

#: Measured at this task's merge base, 02c2025abcda4626569921eafb3863dfc540eb9e
#: (the commit that landed APRAS-45), with the walker below. A future slice
#: that changes either number has to change it deliberately.
RULE_C_BASELINE = 100
RULE_N_BASELINE = 7
#: §5.4's per-module subtraction, aggregated: 85 in F2 (APRAS-46), the 7
#: is_superuser-shaped reads F3 converted (APRAS-47), and F5's last 8
#: (APRAS-49 §3.1) -- 85 + 7 + 8 = 100, the whole of `RULE_C_BASELINE`.
CONVERTED_COMPARE = 100
#: All 7 Rule-N reads were converted by IAM F5 (APRAS-49 §3.2, §3.3).
CONVERTED_NON_COMPARE = 7

#: The seven routes APRAS-43 gated with `get_current_tenant_admin` /
#: `get_current_tenant_admin_or_manager`, which IAM F2 swaps to
#: `require_permission` — the only route-level use of the dependency form.
PERMISSION_GUARDED_ROUTES: frozenset[tuple[str, str]] = frozenset(
    {
        ("DELETE", "/api/v1/tasks/{task_id}"),
        ("DELETE", "/api/v1/lots/{lot_id}"),
        ("PATCH", "/api/v1/users/{user_id}"),
        ("PATCH", "/api/v1/users/{user_id}/contact-info"),
        ("POST", "/api/v1/roles/"),
        ("PATCH", "/api/v1/roles/{role_id}"),
        ("DELETE", "/api/v1/roles/{role_id}"),
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
        # IAM F5 (APRAS-49 §8.4): the grant *and the revoke* of the global
        # flag. It is the sixth and only route this slice adds, and the only
        # one outside `/api/v1/tenants` that `get_current_superuser` guards.
        ("PATCH", "/api/v1/users/{user_id}/superuser"),
        # APRAS-39 §6.4: the per-tenant module switch, read and write.
        # Superuser only, on the global tenants router. They **must** declare
        # `Depends(api_deps.get_current_superuser)` rather than an inlined
        # `if not user.is_superuser`: this assertion is an exact set over
        # `_depends_on(route.dependant, deps.get_current_superuser)`, so an
        # inlined check would be invisible to it and to the two other
        # structural walkers in this repository.
        ("GET", "/api/v1/tenants/{tenant_id}/modules"),
        ("PUT", "/api/v1/tenants/{tenant_id}/modules"),
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

#: **Empty.** The ledger closes at zero (IAM F5, APRAS-49 §11.3).
#:
#: F1 measured 100 Rule-C reads and 7 Rule-N reads. F2 converted 85, F3
#: another 7, and F5 the last 8 -- plus all 7 Rule-N reads. The walkers do
#: **not** die with the survivors: they are retargeted at the whole of
#: `app/` and now assert that nothing is left, which is a stronger statement
#: than any allowlist could make.
ROLE_READS_COMPARE: dict[str, tuple[int, str, str]] = {}

#: **Empty**, for the same reason.
ROLE_READS_NON_COMPARE: dict[str, tuple[int, str, str]] = {}

VALID_SLICES = frozenset({"F5"})


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


def _declarative_paths() -> list[pathlib.Path]:
    """The three paths `_in_scope` excludes: the declarative layer + the seeder."""
    paths = [
        path
        for path in sorted(APP_ROOT.rglob("*.py"))
        if path.relative_to(APP_ROOT).as_posix().startswith(EXCLUDED_PREFIXES)
    ]
    paths.append(APP_ROOT / "seed.py")
    return paths


def _walk_role_reads_over(paths) -> tuple[dict[str, int], dict[str, int]]:
    """`walk_role_reads`'s two rules, over an arbitrary set of files."""
    compare: dict[str, int] = {}
    non_compare: dict[str, int] = {}
    for path in paths:
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


def walk_role_reads() -> tuple[dict[str, int], dict[str, int]]:
    """The Rule-C and Rule-N mappings, `module::function -> count`."""
    return _walk_role_reads_over(_in_scope())


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
    """Four guards are deleted; re-adding any of them is a failure.

    The first two went in IAM F2 (APRAS-46); the last two in IAM F3
    (APRAS-47 §5.1), where `get_current_active_admin` was converted and
    renamed to `get_current_superuser` and `get_current_admin_or_manager`,
    whose last caller F2 removed, was dropped outright.
    """
    assert not hasattr(deps, "get_current_tenant_admin")
    assert not hasattr(deps, "get_current_tenant_admin_or_manager")
    assert not hasattr(deps, "get_current_active_admin")
    assert not hasattr(deps, "get_current_admin_or_manager")


def test_get_current_superuser_is_exactly_the_seven_tenant_routes_plus_the_grant():
    found = {
        key
        for route in _api_routes()
        if _depends_on(route.dependant, deps.get_current_superuser)
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


def test_the_permission_guarded_routes_are_exactly_the_apras43_seven():
    """The seven routes APRAS-43 gated are the only route-level permissions."""
    apras43_admin_routes = [
        ("DELETE", "/api/v1/tasks/{task_id}"),
        ("DELETE", "/api/v1/lots/{lot_id}"),
        ("PATCH", "/api/v1/users/{user_id}"),
        ("PATCH", "/api/v1/users/{user_id}/contact-info"),
        ("POST", "/api/v1/roles/"),
        ("PATCH", "/api/v1/roles/{role_id}"),
        ("DELETE", "/api/v1/roles/{role_id}"),
    ]
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


def test_no_actor_role_read_survives():
    """`100 - 100 == 0` and `7 - 7 == 0`: the arithmetic ending of the chain.

    The ledger is cumulative and stays anchored to F1's tree:
    `RULE_C_BASELINE` and `RULE_N_BASELINE` are historical statements about
    the commit that landed APRAS-45 and are **still true**, so only the
    `CONVERTED_*` terms move. Both allowlists are empty, and the walk that
    produces them now covers all of `app/`, `app/models/`, `app/schemas/` and
    `app/seed.py` included (§11.3).
    """
    compare, non_compare = walk_role_reads()

    assert RULE_C_BASELINE == 100
    assert RULE_N_BASELINE == 7
    assert CONVERTED_COMPARE == 100
    assert CONVERTED_NON_COMPARE == 7
    assert RULE_C_BASELINE - CONVERTED_COMPARE == 0
    assert RULE_N_BASELINE - CONVERTED_NON_COMPARE == 0
    assert ROLE_READS_COMPARE == {}
    assert ROLE_READS_NON_COMPARE == {}
    assert compare == {}, f"surviving actor-role comparisons: {sorted(compare)}"
    assert non_compare == {}, f"surviving actor-role reads: {sorted(non_compare)}"


def test_the_walk_scope_is_the_whole_application():
    """IAM F5 (§11.3) removed F2's three exclusions: nothing is skipped."""
    scanned = {path.relative_to(APP_ROOT).as_posix() for path in _in_scope()}
    everything = {
        path.relative_to(APP_ROOT).as_posix() for path in APP_ROOT.rglob("*.py")
    }
    assert scanned == everything
    assert "api/deps.py" in scanned
    assert "core/permissions.py" in scanned
    assert "models/user.py" in scanned
    assert "schemas/user.py" in scanned
    assert "seed.py" in scanned


def test_no_read_is_deferred_to_a_later_slice():
    """There is no later slice: F5 is the last one, and it converted all 15."""
    by_slice: dict[str, int] = {}
    for allowlist in (ROLE_READS_COMPARE, ROLE_READS_NON_COMPARE):
        for count, slice_name, _reason in allowlist.values():
            by_slice[slice_name] = by_slice.get(slice_name, 0) + count
    assert by_slice == {}


# ---------------------------------------------------------------------------
# APRAS-47 §5.3(e) -- the declarative layer, which the walk above excludes
# ---------------------------------------------------------------------------


def test_the_declarative_layer_has_no_actor_role_read():
    """Kept as a separate statement even though the scope now includes it.

    F2 excluded `app/models/`, `app/schemas/` and `app/seed.py` and ran the
    same two rules over them to prove the exclusion hid nothing. IAM F5 folds
    them into the main scope (§11.3); this case survives so the declarative
    layer keeps its own named assertion rather than being merely covered by a
    wider one.
    """
    compare, non_compare = _walk_role_reads_over(_declarative_paths())

    assert compare == {}
    assert non_compare == {}


def test_no_model_names_a_retired_role_literal():
    """The successor of F3's transitional-default pin (§3.3 #4).

    F3 shipped one declared exception in `app/models/`: `User.__init__`
    defaulted `is_superuser` from `data.get("role") == UserRole.ADMINISTRATOR`
    -- a `Call`, not an actor attribute, so neither rule above could see it,
    and it needed its own pin. IAM F5 deleted the default with the enum, so
    the pin inverts: **no** model may name a retired role value at all.
    """
    # Only the two values *nothing else* in the domain uses. `RESIDENT`,
    # `MANAGER`, `DIRECTOR` and `GUEST` are legitimately spelled by other
    # enums (`EntityType.RESIDENT`, for one), so including them would make
    # this case a false-positive generator rather than a pin.
    retired = {"ADMINISTRATOR", "PORTEIRO"}
    found: dict[str, int] = {}
    for path in sorted((APP_ROOT / "models").rglob("*.py")):
        relative = path.relative_to(APP_ROOT / "models").as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8"))
        where = _function_index(tree)
        for node in ast.walk(tree):
            named = (
                isinstance(node, ast.Attribute) and node.attr in retired
            ) or (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and node.value in retired
            )
            if named:
                key = f"{relative}::{where.get(id(node), '<module>')}"
                found[key] = found.get(key, 0) + 1

    assert found == {}, f"models still naming a retired role value: {found}"
