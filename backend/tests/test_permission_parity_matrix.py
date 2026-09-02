"""The exhaustive `role x route x verb` parity matrix (IAM F2, APRAS-46 §6).

The star test of the enforcement swap. 1080 cells -- six roles times the 180
permission-mapped routes -- each one real HTTP request against the shared
`tests/matrix_world.py` harness, each asserted equal to the status code
recorded in `tests/data/parity_matrix_baseline.json` **before** a single
production file was touched.

The baseline's provenance is *reproducibility, not chronology* (§6.4): this
task ships as one commit, so "the JSON was committed first" is unprovable
after the squash. Instead the recorder is committed, it refuses to run
against a dirty `app/` tree, and `_meta.regenerate` re-records it in a clean
worktree at `_meta.merge_base_sha` with only the harness copied in. That
command must produce a byte-identical file.

Two further oracles keep the recorded numbers honest, so "same status code"
cannot be satisfied by incidental noise: every *denied* cell must have
recorded a 403 (six documented GUEST exceptions), and no *permitted* cell may
have recorded a 403, a 422 or anything >= 500 outside the pinned, bounded and
individually justified lists below.

This module deliberately contains no skip of any kind
(`test_the_matrix_module_never_skips`): a missing baseline must be a red run,
never a green one.
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

import pytest
from fastapi.routing import APIRoute

from app.core.permissions import (
    LEGACY_ROLE_PERMISSIONS,
    ROUTE_PERMISSIONS,
    UNGUARDED_ROUTES,
)
from app.main import app
from app.models.enums import UserRole
from tests import matrix_world
from tests.matrix_world import (
    CELLS,
    PATH_PARAMS,
    QUERY_PARAMS,
    REQUEST_BODIES,
    cell_client,
    matrix_engine,
    neutralised_storage,
    run_cell,
    seed_once,
)
from tests.tools import record_parity_baseline

BACKEND_ROOT = Path(__file__).resolve().parent.parent
BASELINE_PATH = BACKEND_ROOT / "tests" / "data" / "parity_matrix_baseline.json"
HARNESS_PATH = BACKEND_ROOT / "tests" / "matrix_world.py"

EXPECTED_CELL_COUNT = 1080
WRITE_METHODS = frozenset({"POST", "PUT", "PATCH"})
EXPECTED_REQUEST_BODY_COUNT = 89
META_KEYS = frozenset(
    {"merge_base_sha", "generator", "harness", "cell_count", "regenerate"}
)


# ---------------------------------------------------------------------------
# The denial-shape overrides (§6.4) -- exactly six, all GUEST
# ---------------------------------------------------------------------------

#: A *denied* cell normally answers 403. These six answer something else, and
#: the reason is derivable rather than asserted by fiat: `tasks:read`,
#: `tasks:update` and `tasks:comment` are each `{A, D, M, R, P}` in
#: `LEGACY_ROLE_PERMISSIONS`, so GUEST is the only denied role on the six task
#: routes that reach `assert_manager_can_see_task` (which raises
#: `TaskNotFoundError`) or the `list_tasks` empty-list early return.
DENIAL_SHAPE_OVERRIDES: dict[tuple[str, str, str], tuple[int, str]] = {
    ("GUEST", "GET", "/api/v1/tasks/"): (
        200,
        "documented empty-list refusal, endpoints/tasks.py list_tasks",
    ),
    ("GUEST", "PATCH", "/api/v1/tasks/{task_id}"): (
        404,
        "assert_manager_can_see_task raises TaskNotFoundError for GUEST",
    ),
    ("GUEST", "GET", "/api/v1/tasks/{task_id}/history"): (404, "idem"),
    ("GUEST", "GET", "/api/v1/tasks/{task_id}/comments"): (404, "idem"),
    ("GUEST", "POST", "/api/v1/tasks/{task_id}/comments"): (404, "idem"),
    ("GUEST", "PATCH", "/api/v1/tasks/{task_id}/comments/{comment_id}"): (404, "idem"),
}


# ---------------------------------------------------------------------------
# The object-dimension refusals (§5.2) a six-role matrix cannot avoid
# ---------------------------------------------------------------------------

#: The §5.2 dimensions a `NON_ROLE_403` reason is allowed to name. A reason
#: that names none of them is not an explanation, it is an excuse.
NON_ROLE_403_DIMENSIONS = (
    "ownership",
    "visibility",
    "per-lot linkage",
    "per-folder ACL",
    "payload narrowing",
    "role-linked row",
)

#: Cells whose permission **is** held and which still answered 403, because
#: the object dimension refused them. Pinned by construction (recorded, then
#: frozen) and bounded three ways below, so it cannot become a way to silence
#: the oracle.
NON_ROLE_403: dict[tuple[str, str, str], str] = {
    # --- authorship of the task comment (created by the ADMINISTRATOR) ---
    ("DIRECTOR", "PATCH", "/api/v1/tasks/{task_id}/comments/{comment_id}"): (
        "ownership: 'Only the comment author can edit it'"
    ),
    ("MANAGER", "PATCH", "/api/v1/tasks/{task_id}/comments/{comment_id}"): (
        "ownership: 'Only the comment author can edit it'"
    ),
    ("PORTEIRO", "PATCH", "/api/v1/tasks/{task_id}/comments/{comment_id}"): (
        "ownership: 'Only the comment author can edit it'"
    ),
    ("RESIDENT", "PATCH", "/api/v1/tasks/{task_id}/comments/{comment_id}"): (
        "ownership: 'Only the comment author can edit it'"
    ),
    # --- authorship of the announcement comment --------------------------
    ("GUEST", "DELETE", "/api/v1/announcements/comments/{comment_id}"): (
        "ownership: only the comment author (or a publisher) may delete it"
    ),
    ("MANAGER", "DELETE", "/api/v1/announcements/comments/{comment_id}"): (
        "ownership: only the comment author (or a publisher) may delete it"
    ),
    ("RESIDENT", "DELETE", "/api/v1/announcements/comments/{comment_id}"): (
        "ownership: only the comment author (or a publisher) may delete it"
    ),
    # --- authorship of the pending photo (uploaded by the RESIDENT) ------
    ("GUEST", "DELETE", "/api/v1/uploads/photos/{photo_id}"): (
        "ownership: only the uploader may delete their own photo"
    ),
    ("MANAGER", "DELETE", "/api/v1/uploads/photos/{photo_id}"): (
        "ownership: only the uploader may delete their own photo"
    ),
    ("PORTEIRO", "DELETE", "/api/v1/uploads/photos/{photo_id}"): (
        "ownership: only the uploader may delete their own photo"
    ),
    # --- authorship of the feedback (reported by the RESIDENT) -----------
    ("GUEST", "GET", "/api/v1/feedback/{id}"): (
        "ownership: only the reporter sees their own feedback"
    ),
    ("MANAGER", "GET", "/api/v1/feedback/{id}"): (
        "ownership: only the reporter sees their own feedback"
    ),
    ("PORTEIRO", "GET", "/api/v1/feedback/{id}"): (
        "ownership: only the reporter sees their own feedback"
    ),
    # --- the occurrence visibility tiers ---------------------------------
    ("GUEST", "GET", "/api/v1/occurrences/{id}"): (
        "visibility: the occurrence's reporter/assignee tier, not a role gate"
    ),
    ("MANAGER", "GET", "/api/v1/occurrences/{id}"): (
        "visibility: the occurrence's reporter/assignee tier, not a role gate"
    ),
    ("GUEST", "POST", "/api/v1/occurrences/{id}/timeline"): (
        "visibility: the occurrence's reporter/assignee tier, not a role gate"
    ),
    ("MANAGER", "POST", "/api/v1/occurrences/{id}/timeline"): (
        "visibility: the occurrence's reporter/assignee tier, not a role gate"
    ),
    ("GUEST", "PUT", "/api/v1/occurrences/{id}/status"): (
        "visibility: only the assigned staff may move an occurrence's status"
    ),
    ("MANAGER", "PUT", "/api/v1/occurrences/{id}/status"): (
        "visibility: only the assigned staff may move an occurrence's status"
    ),
    ("RESIDENT", "PUT", "/api/v1/occurrences/{id}/status"): (
        "visibility: only the assigned staff may move an occurrence's status"
    ),
    # --- the per-folder document ACL -------------------------------------
    ("GUEST", "POST", "/api/v1/documents/{id}/download"): (
        "per-folder ACL: DocumentFolder.allowed_roles_json, an object dimension"
    ),
    # --- authorship of the transaction (created by the ADMINISTRATOR) ----
    ("MANAGER", "PUT", "/api/v1/finance/transactions/{id}"): (
        "ownership: a MANAGER may only touch transactions they created"
    ),
    ("MANAGER", "POST", "/api/v1/finance/transactions/{id}/invoice"): (
        "ownership: a MANAGER may only touch transactions they created"
    ),
    ("MANAGER", "DELETE", "/api/v1/finance/transactions/{id}/invoice"): (
        "ownership: a MANAGER may only touch transactions they created"
    ),
    # --- authorship of the purchase request / quote ----------------------
    ("MANAGER", "PUT", "/api/v1/purchase-requests/{request_id}"): (
        "ownership: a MANAGER may only change requests they created"
    ),
    ("MANAGER", "DELETE", "/api/v1/purchase-requests/{request_id}"): (
        "ownership: a MANAGER may only change requests they created"
    ),
    ("MANAGER", "PUT", "/api/v1/purchase-requests/{request_id}/quotes/{quote_id}"): (
        "ownership: a MANAGER may only change quotes they registered"
    ),
    ("MANAGER", "DELETE", "/api/v1/purchase-requests/{request_id}/quotes/{quote_id}"): (
        "ownership: a MANAGER may only change quotes they registered"
    ),
    # --- ownership of the reservation (made by the RESIDENT) -------------
    ("MANAGER", "POST", "/api/v1/space-reservations/{reservation_id}/cancel"): (
        "ownership: 'You can only cancel your own reservations'"
    ),
    ("PORTEIRO", "POST", "/api/v1/space-reservations/{reservation_id}/cancel"): (
        "ownership: 'You can only cancel your own reservations'"
    ),
}

#: Cells whose permission **is** held and which nevertheless answered 422 --
#: i.e. requests the world cannot complete at all. The expected length is
#: **0**: the first remedy for a permitted 422 is always to fix
#: `REQUEST_BODIES` / `QUERY_PARAMS` and re-record, never to list the cell.
PERMITTED_422: dict[tuple[str, str, str], str] = {}

MAX_NON_ROLE_403 = 40
MAX_PERMITTED_422 = 15


# ---------------------------------------------------------------------------
# Fixtures -- one world, 1080 cells
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def matrix_run(tmp_path_factory):
    """One SQLite file, one engine, one world. The world is never rebuilt."""
    database_path = tmp_path_factory.mktemp("matrix") / "matrix.sqlite3"
    with matrix_engine(str(database_path)) as engine, neutralised_storage():
        yield engine, seed_once(engine)


def load_baseline() -> dict:
    """The committed golden file. Missing means **fail**, never skip."""
    assert BASELINE_PATH.exists(), (
        f"the parity baseline {BASELINE_PATH} is missing; it is recorded by "
        "`uv run python -m tests.tools.record_parity_baseline` and a deleted "
        "baseline must be a red run, not a green one"
    )
    return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))


def baseline_status(baseline: dict, role: str, method: str, path: str) -> int:
    return baseline["cells"][role][method][path]


def holds(role: str, method: str, path: str) -> bool:
    return ROUTE_PERMISSIONS[(method, path)] in LEGACY_ROLE_PERMISSIONS[UserRole(role)]


#: Divergences accumulated by the parametrised cells, reported in one sorted
#: diff by the aggregate test at the bottom of the module.
_DIVERGENCES: list[tuple[str, str, str, int, int]] = []


# ---------------------------------------------------------------------------
# The grid itself (§6.1)
# ---------------------------------------------------------------------------


def test_matrix_covers_every_permission_mapped_route():
    assert {(method, path) for _role, method, path in CELLS} == set(ROUTE_PERMISSIONS)
    assert len(CELLS) == len(UserRole) * len(ROUTE_PERMISSIONS)
    assert len(CELLS) == EXPECTED_CELL_COUNT


def test_the_twelve_unguarded_routes_are_the_only_ones_excluded():
    """No cell may be dropped for any reason other than being unguarded."""
    assert len(UNGUARDED_ROUTES) == 12
    assert not (set(ROUTE_PERMISSIONS) & UNGUARDED_ROUTES)


def test_every_path_parameter_has_a_binding():
    missing = sorted(
        (path, name)
        for _method, path in ROUTE_PERMISSIONS
        for name in re.findall(r"\{(\w+)\}", path)
        if (path, name) not in PATH_PARAMS
    )
    assert not missing, f"unbound path parameters: {missing}"


def test_every_write_route_has_a_request_body():
    missing = sorted(
        key for key in ROUTE_PERMISSIONS if key[0] in WRITE_METHODS and key not in REQUEST_BODIES
    )
    assert not missing, f"write routes with no declared body: {missing}"


def test_request_bodies_covers_exactly_the_write_routes():
    """No missing entry, no stale one; the 24 DELETE routes take no body."""
    assert set(REQUEST_BODIES) == {
        key for key in ROUTE_PERMISSIONS if key[0] in WRITE_METHODS
    }
    assert len(REQUEST_BODIES) == EXPECTED_REQUEST_BODY_COUNT
    assert not [key for key in REQUEST_BODIES if key[0] == "DELETE"]


def test_every_required_query_parameter_has_a_binding():
    """A required query parameter the matrix does not send answers 422."""
    missing = []
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        for method in route.methods:
            key = (method, route.path)
            if key not in ROUTE_PERMISSIONS:
                continue
            required = [
                param.name
                for param in route.dependant.query_params
                if param.field_info.is_required()
            ]
            if required and key not in QUERY_PARAMS:
                missing.append((key, required))
    assert not missing, f"routes with unbound required query parameters: {missing}"


def test_no_absolute_datetime_in_the_harness():
    """A wall-clock-dependent cell would rot the golden file (§6.2)."""
    source = HARNESS_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    offenders = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
            if name in {"datetime", "date"} and any(
                isinstance(arg, ast.Constant) and isinstance(arg.value, int)
                for arg in node.args
            ):
                offenders.append(f"line {node.lineno}: literal {name}(...)")
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and re.search(r"\d{4}-\d{2}-\d{2}", node.value)
        ):
            offenders.append(f"line {node.lineno}: ISO date literal")
    assert not offenders, f"absolute datetimes in the harness: {offenders}"


def test_the_matrix_module_never_skips():
    """A missing baseline must fail. `pytest.skip` must not exist here."""
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    offenders = [
        f"line {node.lineno}: pytest.{node.attr}"
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute)
        and node.attr in {"skip", "skipif", "xfail"}
        and isinstance(node.value, ast.Name)
        and node.value.id == "pytest"
    ]
    offenders += [
        f"line {node.lineno}: pytest.mark.{node.attr}"
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute)
        and node.attr in {"skip", "skipif", "xfail"}
        and isinstance(node.value, ast.Attribute)
        and node.value.attr == "mark"
    ]
    assert not offenders, f"the matrix module must never skip: {offenders}"


# ---------------------------------------------------------------------------
# Provenance of the golden file (§6.4)
# ---------------------------------------------------------------------------


def test_baseline_file_exists():
    baseline = load_baseline()
    assert baseline["_meta"]["cell_count"] == EXPECTED_CELL_COUNT


def test_baseline_declares_its_provenance():
    meta = load_baseline()["_meta"]
    assert set(meta) == META_KEYS, "no timestamp, hostname or absolute path"
    assert re.fullmatch(r"[0-9a-f]{40}", meta["merge_base_sha"])
    assert (BACKEND_ROOT / meta["generator"]).exists()
    assert (BACKEND_ROOT / meta["harness"]).exists()
    assert meta["cell_count"] == len(CELLS) == EXPECTED_CELL_COUNT
    assert meta["merge_base_sha"] in meta["regenerate"]
    assert "git worktree add" in meta["regenerate"]


def test_baseline_carries_no_absolute_path_and_no_timestamp():
    raw = BASELINE_PATH.read_text(encoding="utf-8")
    assert str(BACKEND_ROOT) not in raw
    assert not re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}", raw)


def test_baseline_records_only_integer_status_codes():
    for by_method in load_baseline()["cells"].values():
        for by_path in by_method.values():
            for status in by_path.values():
                assert isinstance(status, int)


def test_baseline_covers_exactly_the_matrix():
    baseline = load_baseline()
    recorded = {
        (role, method, path)
        for role, by_method in baseline["cells"].items()
        for method, by_path in by_method.items()
        for path in by_path
    }
    assert recorded == set(CELLS)


def test_recorder_refuses_a_dirty_production_tree():
    """Both branches of the recorder's own ordering guard (§6.4)."""
    with pytest.raises(SystemExit) as excinfo:
        record_parity_baseline.assert_clean_production_tree(
            run_git=lambda *_args: " M app/api/deps.py\n"
        )
    assert excinfo.value.code == 2
    assert record_parity_baseline.assert_clean_production_tree(
        run_git=lambda *_args: ""
    ) is None


def test_the_recorder_has_no_allow_dirty_escape():
    """The dirty-tree refusal has no opt-out flag (§6.4)."""
    source = (BACKEND_ROOT / record_parity_baseline.GENERATOR).read_text(
        encoding="utf-8"
    )
    declared = {
        argument.value
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Call)
        and getattr(node.func, "attr", None) == "add_argument"
        for argument in node.args
        if isinstance(argument, ast.Constant)
    }
    assert declared == {"--out", "--overwrite"}


# ---------------------------------------------------------------------------
# The semantic oracles (§6.4)
# ---------------------------------------------------------------------------


def test_every_denied_cell_is_denied_in_the_baseline():
    baseline = load_baseline()
    offenders = sorted(
        (role, method, path, baseline_status(baseline, role, method, path))
        for role, method, path in CELLS
        if not holds(role, method, path)
        and baseline_status(baseline, role, method, path) != 403
        and (role, method, path) not in DENIAL_SHAPE_OVERRIDES
    )
    assert not offenders, f"denied cells that did not answer 403: {offenders}"


def test_denial_shape_overrides_is_exactly_six():
    assert len(DENIAL_SHAPE_OVERRIDES) == 6
    assert {role for role, _m, _p in DENIAL_SHAPE_OVERRIDES} == {"GUEST"}


def test_every_denial_shape_override_is_needed():
    baseline = load_baseline()
    stale = sorted(
        (role, method, path)
        for (role, method, path), (status, _reason) in DENIAL_SHAPE_OVERRIDES.items()
        if holds(role, method, path)
        or baseline_status(baseline, role, method, path) != status
    )
    assert not stale, f"stale or speculative denial-shape overrides: {stale}"


def test_every_denial_shape_override_has_a_reason():
    for cell, (_status, reason) in DENIAL_SHAPE_OVERRIDES.items():
        assert reason.strip(), f"{cell}: empty reason"


def test_no_cell_is_5xx_in_the_baseline():
    """No allowlist, no exception: a 5xx is never an authorization answer."""
    baseline = load_baseline()
    offenders = sorted(
        (role, method, path, baseline_status(baseline, role, method, path))
        for role, method, path in CELLS
        if baseline_status(baseline, role, method, path) >= 500
    )
    assert not offenders, f"the world broke these routes: {offenders}"


def test_no_permitted_cell_is_403_in_the_baseline():
    baseline = load_baseline()
    excused = {
        (role, method, path)
        for role, method, path in CELLS
        if holds(role, method, path)
        and baseline_status(baseline, role, method, path) == 403
    }
    assert excused == set(NON_ROLE_403)


def test_every_non_role_403_is_needed():
    baseline = load_baseline()
    stale = sorted(
        cell
        for cell in NON_ROLE_403
        if not holds(*cell) or baseline_status(baseline, *cell) != 403
    )
    assert not stale, f"NON_ROLE_403 entries that are not permitted-and-403: {stale}"


def test_every_non_role_403_has_a_reason():
    for cell, reason in NON_ROLE_403.items():
        assert reason.strip(), f"{cell}: empty reason"
        assert reason.startswith(NON_ROLE_403_DIMENSIONS), (
            f"{cell}: reason must name a §5.2 dimension, got {reason!r}"
        )


def test_non_role_403_is_bounded():
    assert len(NON_ROLE_403) <= MAX_NON_ROLE_403


def test_no_permitted_cell_is_422_in_the_baseline():
    baseline = load_baseline()
    excused = {
        (role, method, path)
        for role, method, path in CELLS
        if holds(role, method, path)
        and baseline_status(baseline, role, method, path) == 422
    }
    assert excused == set(PERMITTED_422)


def test_every_permitted_422_is_needed():
    baseline = load_baseline()
    stale = sorted(
        cell
        for cell in PERMITTED_422
        if not holds(*cell) or baseline_status(baseline, *cell) != 422
    )
    assert not stale, f"PERMITTED_422 entries that are not permitted-and-422: {stale}"


def test_every_permitted_422_has_a_reason():
    for cell, reason in PERMITTED_422.items():
        assert reason.strip(), f"{cell}: empty reason"


def test_permitted_422_is_bounded():
    assert len(PERMITTED_422) <= MAX_PERMITTED_422


# ---------------------------------------------------------------------------
# ER-3 -- the 1080 cells
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("role", "method", "path"),
    CELLS,
    ids=[f"{role}-{method}-{path}" for role, method, path in CELLS],
)
def test_cell_matches_the_recorded_baseline(matrix_run, role, method, path):
    """One real HTTP request; its status must equal the pre-swap recording."""
    engine, world = matrix_run
    expected = baseline_status(load_baseline(), role, method, path)
    with cell_client(engine) as client:
        actual = run_cell(client, world, role, method, path)
    if actual != expected:
        _DIVERGENCES.append((role, method, path, expected, actual))
    assert actual == expected, (
        f"divergence: role={role} {method} {path} expected={expected} actual={actual}"
    )


def test_the_matrix_has_zero_divergence():
    """The sorted `(role, method, path, expected, actual)` diff, in one place."""
    assert not sorted(_DIVERGENCES), (
        "the enforcement swap changed behaviour on these cells: "
        f"{sorted(_DIVERGENCES)}"
    )


def test_the_harness_is_shared_by_the_recorder_and_this_module():
    """A baseline produced by a second implementation would prove nothing."""
    assert record_parity_baseline.CELLS is matrix_world.CELLS
    assert record_parity_baseline.run_cell is matrix_world.run_cell
    assert record_parity_baseline.seed_once is matrix_world.seed_once
