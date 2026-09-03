"""The exhaustive `role x route x verb` parity matrix (IAM F2, APRAS-46 §6).

The star test of the enforcement swap. 1080 cells -- six roles times the 180
permission-mapped routes IAM F2 measured -- each one real HTTP request against
the shared `tests/matrix_world.py` harness, each asserted equal to the status
code recorded in `tests/data/parity_matrix_baseline.json` **before** a single
production file was touched.

APRAS-40 adds three permission-guarded routes, so the live matrix is now
`6 x 183 == 1098` cells. The F2 file is **not** re-recorded for them: it stays
byte-identical (`test_the_f2_baseline_is_untouched_by_apras_40`), and the 18
new cells live in the additive `tests/data/parity_matrix_baseline_40.json`,
whose `_meta.merge_base_sha` names the branch point the `+3` route delta is
measured from rather than a sha its statuses could be reproduced at -- the
three routes do not exist there. Every semantic oracle below reads
`load_union()`, the two files keyed the way `CELLS` is keyed; the provenance
and hygiene cases stay one per file.

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
import hashlib
import json
import re
from pathlib import Path

import pytest
from fastapi.routing import APIRoute
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.api import deps
from app.core import tenant_context
from app.core.permissions import (
    ADMIN_GAP_PERMISSIONS,
    PERMISSIONS,
    ROUTE_PERMISSIONS,
    UNGUARDED_ROUTES,
    filter_by_modules,
)
from app.main import app
from app.models.tenant import Tenant
from app.models.user import User
from tests import matrix_world
from tests.conftest import bundle
from tests.matrix_world import (
    CELLS,
    PARITY_PROFILES,
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
BASELINE_40_PATH = (
    BACKEND_ROOT / "tests" / "data" / "parity_matrix_baseline_40.json"
)
HARNESS_PATH = BACKEND_ROOT / "tests" / "matrix_world.py"

F2_CELL_COUNT = 1080
APRAS_40_CELL_COUNT = 18
EXPECTED_CELL_COUNT = F2_CELL_COUNT + APRAS_40_CELL_COUNT

F2_MERGE_BASE_SHA = "02c2025abcda4626569921eafb3863dfc540eb9e"
#: Measured at the APRAS-39 merge base (68cfd1d) with
#: `shasum -a 256 backend/tests/data/parity_matrix_baseline.json`, and pinned
#: so "byte-identical" is a machine statement rather than an intention.
F2_BASELINE_SHA256 = (
    "3691cea1cddfa13ddcba4cf9b5c1c3e8b7bbac7c295bae4bbd4e3e8c45c016cd"
)

#: The three routes APRAS-40 adds to `ROUTE_PERMISSIONS`, and the exact set the
#: additive baseline records.
APRAS_40_ROUTES = frozenset(
    {
        ("GET", "/api/v1/subscription"),
        ("GET", "/api/v1/subscription/history"),
        ("PUT", "/api/v1/subscription/modules"),
    }
)

#: The profiles `matrix_world.build_world` builds with `is_superuser=True` --
#: the ADMINISTRATOR profile only. Not asserted by fiat:
#: `test_the_superuser_profiles_are_the_ones_the_world_seeds` reads the flag
#: back off the seeded users.
SUPERUSER_PROFILES: frozenset[str] = frozenset({"ADMINISTRATOR"})

#: The permissions the recorded ADMINISTRATOR bundle does not carry, and the
#: one place the superuser branch must NOT fire: production refuses
#: `GET /packages/my-lots` to an administrator in the *service*
#: (`PackageService.get_my_lots`, a routing message), not at the permission
#: gate, so that cell answers 403 with the flag set or unset. Read from the
#: constant, never a literal, so an addition to that tier changes nothing here.
MATRIX_ADMIN_GAP: frozenset[str] = ADMIN_GAP_PERMISSIONS

#: The only edit IAM F5 (APRAS-49 §11.1) makes to the golden file's *keys*,
#: and it makes it **here** rather than by re-recording: `/api/v1/user-types`
#: became `/api/v1/roles`, a pure rename with no authorization content, so
#: `tests/data/parity_matrix_baseline.json` stays byte-identical
#: (`git diff --stat` on that path is empty after F5) and keeps its
#: `_meta.merge_base_sha = 02c2025…`. Four `(method, path)` entries live under
#: these two path strings — `GET`/`POST` on the collection, `PATCH`/`DELETE`
#: on the item — so `4 x 6 profiles = 24` cells are re-keyed and **no value
#: moves**.
F5_PATH_RENAMES: dict[str, str] = {
    "/api/v1/user-types/": "/api/v1/roles/",
    "/api/v1/user-types/{user_type_id}": "/api/v1/roles/{role_id}",
}

WRITE_METHODS = frozenset({"POST", "PUT", "PATCH"})
EXPECTED_REQUEST_BODY_COUNT = 90
META_KEYS = frozenset(
    {"merge_base_sha", "generator", "harness", "cell_count", "regenerate"}
)


# ---------------------------------------------------------------------------
# The denial-shape overrides (§6.4) -- exactly six, all GUEST
# ---------------------------------------------------------------------------

#: A *denied* cell normally answers 403. These six answer something else, and
#: the reason is derivable rather than asserted by fiat: `tasks:read`,
#: `tasks:update` and `tasks:comment` are each `{A, D, M, R, P}` in the
#: recorded bundles, so GUEST is the only denied profile on the six task
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


def load_file(path: Path) -> dict:
    """One recorded baseline document. Missing means **fail**, never skip.

    The former body of ``load_baseline``, parameterised by path; the missing-file
    assertion and its message move here verbatim. The renames are **not**
    applied here: this returns the document as it is on disk, so the hygiene
    and provenance cases see exactly the recorded bytes.
    """
    assert path.exists(), (
        f"the parity baseline {path} is missing; it is recorded by "
        "`uv run python -m tests.tools.record_parity_baseline` and a deleted "
        "baseline must be a red run, not a green one"
    )
    return json.loads(path.read_text(encoding="utf-8"))


def load_baseline() -> dict:
    """The IAM F2 golden file, and only ever that (APRAS-40 §9.2.1)."""
    return load_file(BASELINE_PATH)


def load_apras_40_baseline() -> dict:
    """The additive file of APRAS-40 §9.2.2, and only ever that."""
    return load_file(BASELINE_40_PATH)


def cells_of(baseline: dict) -> set[tuple[str, str, str]]:
    """Every `(role, method, path)` a document records, keyed the way `CELLS`
    is keyed -- i.e. with `F5_PATH_RENAMES` already applied."""
    return {
        (role, method, F5_PATH_RENAMES.get(path, path))
        for role, by_method in baseline["cells"].items()
        for method, by_path in by_method.items()
        for path in by_path
    }


def load_union() -> dict[tuple[str, str, str], int]:
    """Both baselines as one `CELLS`-keyed cell map.

    Overlap is an error, not a merge: the two files partition
    `ROUTE_PERMISSIONS` and a cell appearing in both would mean one of them
    had been re-recorded. `F5_PATH_RENAMES` is applied to **both** -- it is
    the identity on every path it does not name, and one keying rule is
    cheaper to keep true than two.
    """
    merged: dict[tuple[str, str, str], int] = {}
    for path in (BASELINE_PATH, BASELINE_40_PATH):
        for role, by_method in load_file(path)["cells"].items():
            for method, by_path in by_method.items():
                for route, status in by_path.items():
                    key = (role, method, F5_PATH_RENAMES.get(route, route))
                    assert key not in merged, f"the two baselines overlap at {key}"
                    merged[key] = status
    return merged


def baseline_status(
    union: dict[tuple[str, str, str], int], role: str, method: str, path: str
) -> int:
    """Same arity as before; only the first argument's type changed."""
    return union[(role, method, path)]


def bundle_of(profile: str) -> frozenset[str]:
    """The recorded legacy bundle of one profile.

    `LEGACY_ROLE_PERMISSIONS` pre-F5; since IAM F5 (APRAS-49 §11.1)
    `legacy_role_bundles.json` union `NEW_TIER`, through `conftest.bundle` --
    the same source `matrix_world` gives the six actors and migration `0033`
    writes onto the real rows. One source, three readers.
    """
    return bundle(profile)


def holds_by_bundle(profile: str, method: str, path: str) -> bool:
    """The IAM F2 predicate, verbatim. Kept so the branch below is provably
    inert (`test_the_superuser_branch_changes_no_f2_verdict`)."""
    return ROUTE_PERMISSIONS[(method, path)] in bundle_of(profile)


def holds(profile: str, method: str, path: str) -> bool:
    """Does this profile pass the *authorization* gate of this route?

    APRAS-40 §9.2.4.1: a superuser profile passes it for every catalogue
    permission, by APRAS-47's short-circuit -- except the recorded admin gap,
    whose route refuses an administrator for a non-permission reason and whose
    recorded 403 is therefore right either way.

    APRAS-40 is the first task where this can matter at all: `billing:read`
    and `billing:manage` are the first **permission-guarded** catalogue
    strings minted after the legacy bundles were recorded, so they are the
    first the ADMINISTRATOR profile reaches by the flag rather than by its
    bundle. The predicate is what moves here, never the recorded artefact:
    the file records what production answered, the predicate records what
    production *should* answer, and a superuser flag that did not exist when
    the file was recorded is a change to the second.
    """
    if (
        profile in SUPERUSER_PROFILES
        and ROUTE_PERMISSIONS[(method, path)] not in MATRIX_ADMIN_GAP
    ):
        return True
    return holds_by_bundle(profile, method, path)


#: Divergences accumulated by the parametrised cells, reported in one sorted
#: diff by the aggregate test at the bottom of the module.
_DIVERGENCES: list[tuple[str, str, str, int, int]] = []


# ---------------------------------------------------------------------------
# The grid itself (§6.1)
# ---------------------------------------------------------------------------


def test_matrix_covers_every_permission_mapped_route():
    assert {(method, path) for _role, method, path in CELLS} == set(ROUTE_PERMISSIONS)
    assert len(CELLS) == len(PARITY_PROFILES) * len(ROUTE_PERMISSIONS)
    assert len(CELLS) == EXPECTED_CELL_COUNT


def test_the_twenty_two_unguarded_routes_are_the_only_ones_excluded():
    """No cell may be dropped for any reason other than being unguarded.

    13 at the IAM F5 merge base; APRAS-39 added the two superuser-only
    module-switch routes; APRAS-40 adds seven more (four `/api/v1/plans` and
    three `/api/v1/tenants/{tenant_id}/subscription*`). None of the nine maps
    to a catalogue permission, so none adds a cell -- the 18 new cells come
    from APRAS-40's three *permission-guarded* routes and nothing else.
    """
    assert len(UNGUARDED_ROUTES) == 22
    assert not (set(ROUTE_PERMISSIONS) & UNGUARDED_ROUTES)


def test_the_matrix_world_runs_with_every_module_active():
    """The 1098-cell world has all 27 modules on, in every tenant it builds.

    `matrix_world` seeds its tenants through the ordinary model
    constructors, so `disabled_modules` is `[]` everywhere and every cell
    keeps its pre-APRAS-39 answer. Asserted rather than assumed: a future
    task that turns a module off in a fixture fails *here*, with a clear
    message, instead of producing a mysterious baseline diff.
    """
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        matrix_world.build_world(session)
        tenants = session.exec(select(Tenant)).all()
        assert tenants
        for tenant in tenants:
            assert tenant.disabled_modules == [], (
                f"matrix world tenant {tenant.name!r} has modules disabled: "
                f"{tenant.disabled_modules}"
            )

        for tenant in tenants:
            tenant_context.set_acting_tenant(session, tenant.id)
            assert filter_by_modules(PERMISSIONS, deps.disabled_modules(session)) == (
                PERMISSIONS
            )
    SQLModel.metadata.drop_all(engine)


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
    assert baseline["_meta"]["cell_count"] == F2_CELL_COUNT


def test_baseline_declares_its_provenance():
    meta = load_baseline()["_meta"]
    assert set(meta) == META_KEYS, "no timestamp, hostname or absolute path"
    assert re.fullmatch(r"[0-9a-f]{40}", meta["merge_base_sha"])
    assert (BACKEND_ROOT / meta["generator"]).exists()
    assert (BACKEND_ROOT / meta["harness"]).exists()
    assert meta["cell_count"] == F2_CELL_COUNT
    assert len(CELLS) == EXPECTED_CELL_COUNT
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


# ---------------------------------------------------------------------------
# APRAS-40 §9.2 -- the F2 freeze and the additive file
# ---------------------------------------------------------------------------


def test_the_f2_baseline_is_untouched_by_apras_40():
    """Byte-identity, pinned mechanically rather than by good intentions.

    The previous round's instinct was to re-record this file for the three new
    routes. That is wrong four ways -- most sharply, `record()` stamps
    `merge_base_sha` from `git rev-parse HEAD`, so any re-record moves the sha
    off `02c2025…` and turns the star test of IAM F2 into a tautology,
    silently. The file is frozen; the new cells get their own document.
    """
    raw = BASELINE_PATH.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == F2_BASELINE_SHA256
    meta = json.loads(raw)["_meta"]
    assert meta["merge_base_sha"] == F2_MERGE_BASE_SHA
    assert meta["cell_count"] == F2_CELL_COUNT == 1080
    assert "git worktree add" in meta["regenerate"]


def test_the_f2_sha_anchors_still_agree_with_the_frozen_file():
    """The prose anchors that quote the sha stay valid and stay quoted.

    IAM F5 deleted `tests/test_legacy_role_permissions.py`, which used to be
    one of the two anchors; the surviving one is
    `tests/test_permission_enforcement.py`'s `RULE_C_BASELINE` comment, and
    this module's own `F5_PATH_RENAMES` note is the other. Neither sentence is
    edited by APRAS-40.
    """
    for name in ("test_permission_enforcement.py", "test_permission_parity_matrix.py"):
        text = (BACKEND_ROOT / "tests" / name).read_text(encoding="utf-8")
        assert F2_MERGE_BASE_SHA[:7] in text, name


def test_the_apras_40_baseline_declares_its_provenance():
    """Same five `_meta` keys, and the one documented difference asserted.

    `merge_base_sha` does **not** mean here what it means in the F2 file: the
    three routes do not exist at that sha, so no worktree there can reproduce
    these statuses. It names the branch point the `+3` route delta is measured
    from -- the provenance of the accounting -- and `regenerate` is
    correspondingly a plain scoped recorder invocation with no
    `git worktree add`. The file's independent check is the semantic oracle
    below, which derives the expected answers from the permission map rather
    than from the file, which is what keeps it from being a tautology.
    """
    meta = load_apras_40_baseline()["_meta"]
    assert set(meta) == META_KEYS, "no timestamp, hostname or absolute path"
    assert re.fullmatch(r"[0-9a-f]{40}", meta["merge_base_sha"])
    assert meta["cell_count"] == APRAS_40_CELL_COUNT == 18
    assert meta["merge_base_sha"] in meta["regenerate"]
    assert "--routes" in meta["regenerate"]
    assert "git worktree add" not in meta["regenerate"]
    assert (BACKEND_ROOT / meta["generator"]).exists()
    assert (BACKEND_ROOT / meta["harness"]).exists()


def test_the_apras_40_baseline_carries_no_absolute_path_and_no_timestamp():
    """The F2 hygiene case's body over the additive file.

    Duplicated rather than parametrised over both: the F2 case is pinned green
    and unedited by the freeze, and duplicating a three-line body is cheaper
    than moving a case the freeze depends on.
    """
    raw = BASELINE_40_PATH.read_text(encoding="utf-8")
    assert str(BACKEND_ROOT) not in raw
    assert not re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}", raw)


def test_the_apras_40_baseline_records_only_integer_status_codes():
    for by_method in load_apras_40_baseline()["cells"].values():
        for by_path in by_method.values():
            for status in by_path.values():
                assert isinstance(status, int)


def test_the_two_baselines_partition_route_permissions_exactly():
    """Disjoint, and together exactly `ROUTE_PERMISSIONS`.

    `f2 | new == set(ROUTE_PERMISSIONS)` is exact rather than a subset because
    APRAS-49's three tier permissions are deliberately **not** route-mapped,
    so the map stays at its base size plus APRAS-40's `+3` and nothing else
    creeps in.
    """
    f2 = {(method, path) for _role, method, path in cells_of(load_baseline())}
    new = {(method, path) for _role, method, path in cells_of(load_apras_40_baseline())}

    assert new == APRAS_40_ROUTES
    assert not (f2 & new), "the two baselines must not overlap"
    assert f2 | new == set(ROUTE_PERMISSIONS)
    assert f2 == set(ROUTE_PERMISSIONS) - APRAS_40_ROUTES

    union = load_union()
    assert set(union) == set(CELLS)
    assert len(union) == EXPECTED_CELL_COUNT == len(CELLS)


def test_the_recorder_refuses_to_write_the_frozen_f2_baseline():
    """Both branches of APRAS-40 §9.2.3's `FROZEN` guard.

    It fires before anything is built, `--overwrite` or not, so a typo cannot
    clobber the frozen file even in a clean tree.
    """
    with pytest.raises(SystemExit) as excinfo:
        record_parity_baseline.refuse_the_frozen_baseline(BASELINE_PATH)
    assert excinfo.value.code == 2
    assert (
        record_parity_baseline.refuse_the_frozen_baseline(BASELINE_40_PATH) is None
    )
    assert record_parity_baseline.FROZEN == "tests/data/parity_matrix_baseline.json"


def test_the_recorder_scopes_by_route_and_validates_the_merge_base():
    """`--routes` filters `CELLS`; an unknown route or sha is `SystemExit(2)`.

    `select_cells` filters the *same* list this module reads, rather than
    building a second one, which is what keeps
    `test_the_harness_is_shared_by_the_recorder_and_this_module` meaningful.
    """
    assert record_parity_baseline.select_cells(None) == list(CELLS)
    assert record_parity_baseline.select_cells([]) == list(CELLS)

    scoped = record_parity_baseline.select_cells(
        [f"{method} {path}" for method, path in sorted(APRAS_40_ROUTES)]
    )
    assert len(scoped) == APRAS_40_CELL_COUNT
    assert {(method, path) for _role, method, path in scoped} == APRAS_40_ROUTES

    with pytest.raises(SystemExit) as excinfo:
        record_parity_baseline.select_cells(["GET /api/v1/nope"])
    assert excinfo.value.code == 2

    assert (
        record_parity_baseline.resolve_merge_base(
            F2_MERGE_BASE_SHA, run_git=lambda *_args: ""
        )
        == F2_MERGE_BASE_SHA
    )
    assert (
        record_parity_baseline.resolve_merge_base(
            None, run_git=lambda *_args: f"{F2_MERGE_BASE_SHA}\n"
        )
        == F2_MERGE_BASE_SHA
    )
    with pytest.raises(SystemExit) as excinfo:
        record_parity_baseline.resolve_merge_base("not-a-sha")
    assert excinfo.value.code == 2


# ---------------------------------------------------------------------------
# APRAS-40 §9.2.4.1 -- the oracle's superuser branch, proven inert
# ---------------------------------------------------------------------------


def test_the_superuser_branch_changes_no_f2_verdict():
    """Additive on the 18 new cells, inert on the 1080 recorded ones."""
    moved = sorted(
        cell
        for cell in CELLS
        if (cell[1], cell[2]) not in APRAS_40_ROUTES
        and holds(*cell) != holds_by_bundle(*cell)
    )
    assert not moved, f"the superuser branch moved an F2 verdict: {moved}"


def test_the_admin_gap_is_the_only_bundle_gap_the_superuser_branch_excludes():
    """Why the case above can be true, and the day a human should look again.

    It goes red when a new mapped route lands that ADMINISTRATOR's recorded
    bundle misses -- which is exactly when the branch's inertness stops being
    provable by inspection.
    """
    unheld = sorted(
        (method, path)
        for method, path in ROUTE_PERMISSIONS
        if (method, path) not in APRAS_40_ROUTES
        and not holds_by_bundle("ADMINISTRATOR", method, path)
    )
    assert unheld == [("GET", "/api/v1/packages/my-lots")]
    # Intersected, deliberately. `ADMIN_GAP_PERMISSIONS` is defined over
    # *permissions* ADMINISTRATOR does not hold, mapped or not, and IAM F5
    # adds in-code object predicates that never enter `ROUTE_PERMISSIONS`.
    # Only the *routed* part of the gap can ever appear in `unheld`, so a bare
    # `== MATRIX_ADMIN_GAP` would go red for an unrouted addition, for a reason
    # having nothing to do with the superuser branch.
    assert {ROUTE_PERMISSIONS[cell] for cell in unheld} == (
        MATRIX_ADMIN_GAP & set(ROUTE_PERMISSIONS.values())
    )


def test_the_superuser_profiles_are_the_ones_the_world_seeds(matrix_run):
    """`SUPERUSER_PROFILES` is read back off the world, never declared at it.

    An unflagged world does **not** make the branch unreachable -- it keys off
    this constant, not off the seeded flag -- so it would fail here *and* in
    `test_no_permitted_cell_is_403_in_the_baseline` at once. That is loud, and
    it is the intended shape: stop and report, never repair by adding
    `NON_ROLE_403` entries.
    """
    engine, world = matrix_run
    with Session(engine) as session:
        seeded = {
            profile
            for profile, user_id in world.users.items()
            if session.get(User, user_id).is_superuser
        }
    assert seeded == SUPERUSER_PROFILES


def test_baseline_covers_exactly_the_matrix():
    """The two recorded documents together key exactly the live matrix.

    A shrink, not a weakening: `load_union()` already normalises the keys the
    comprehension this replaces used to normalise by hand.
    """
    assert set(load_union()) == set(CELLS)


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
    """The dirty-tree refusal has no opt-out flag (§6.4).

    APRAS-40 adds `--routes` and `--merge-base` (§9.2.3) so a *new* route can
    be recorded into its own file. Neither weakens the refusal: there is still
    no `--allow-dirty`, `assert_clean_production_tree` is untouched, and the
    scoped run is still impossible while `app/` is dirty.
    """
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
    assert declared == {"--out", "--overwrite", "--routes", "--merge-base"}


# ---------------------------------------------------------------------------
# The semantic oracles (§6.4)
# ---------------------------------------------------------------------------


def test_every_denied_cell_is_denied_in_the_baseline():
    baseline = load_union()
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
    baseline = load_union()
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
    baseline = load_union()
    offenders = sorted(
        (role, method, path, baseline_status(baseline, role, method, path))
        for role, method, path in CELLS
        if baseline_status(baseline, role, method, path) >= 500
    )
    assert not offenders, f"the world broke these routes: {offenders}"


def test_no_permitted_cell_is_403_in_the_baseline():
    baseline = load_union()
    excused = {
        (role, method, path)
        for role, method, path in CELLS
        if holds(role, method, path)
        and baseline_status(baseline, role, method, path) == 403
    }
    assert excused == set(NON_ROLE_403)


def test_every_non_role_403_is_needed():
    baseline = load_union()
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
    baseline = load_union()
    excused = {
        (role, method, path)
        for role, method, path in CELLS
        if holds(role, method, path)
        and baseline_status(baseline, role, method, path) == 422
    }
    assert excused == set(PERMITTED_422)


def test_every_permitted_422_is_needed():
    baseline = load_union()
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
    expected = baseline_status(load_union(), role, method, path)
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
