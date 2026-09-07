"""Every mapped route is in a *declared enforcement form* (APRAS-51).

The defect this module closes: `ROUTE_PERMISSIONS` maps 201 routes to one
catalogue permission each, and on 25 of them that permission was never
consulted anywhere in the request. The map claimed a gate the code did not
have. Nothing noticed, because `test_permission_registry.py` only asserts a
route is *classified*, `test_permission_enforcement.py` only asserts the
dependency-form routes declare the right permission, and the parity matrix
measures six legacy profiles that hold almost all of the permissions
involved.

Two oracles, both mechanical, both here:

* **structural** (§4.2) -- one walk over `route.dependant` placing every
  `ROUTE_PERMISSIONS` entry in exactly one of five declared forms, with
  `UNENFORCED` shipping **empty**;
* **behavioural** (§4.3) -- one real request per swept route from an actor
  holding *the entire catalogue except the route's own permission*, asserting
  the **shape** of the refusal and not merely its non-success.

What the two together prove: every mapped route is in a declared form, and
every swept route refuses, in a declared shape, a caller who holds everything
but its mapped permission. What they do **not** prove: that the refusal is
*caused* by the mapped permission on the 135 in-handler routes. For those the
sweep is a strong necessary condition, and `REFUSAL_SHAPES` is what stops an
unrelated 404 or 400 from passing silently -- which is exactly what an earlier
`not 2xx` assertion did on three routes whose permission was never read.

The world
---------

This module builds **its own** world, from `tests/matrix_world.py`'s
*unmodified* helpers (`matrix_engine`, `seed_once`, `neutralised_storage`,
`cell_client`, `run_cell`, `resolve_path`, `REQUEST_BODIES`, `QUERY_PARAMS`).
It does not import `build_world` or `test_permission_parity_matrix.matrix_run`
and it edits nothing in the harness -- `test_the_harness_is_untouched` pins
`sha256(tests/matrix_world.py)`, so the frozen IAM F2 baseline keeps running
against exactly the world it recorded. A seventh actor seeded *inside*
`build_world` would have been the alternative, and it would have mutated the
harness the golden file names in `_meta.harness`.
"""

from __future__ import annotations

import hashlib
import inspect
import re
import uuid
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from fastapi.routing import APIRoute
from sqlmodel import Session, select

from app.api import deps
from app.core import tenant_context
from app.core.permissions import (
    PERMISSIONS,
    ROUTE_PERMISSIONS,
    SUPERUSER_ONLY_PERMISSIONS,
)
from app.core.security import create_access_token
from app.db import get_session
from app.main import app
from app.models.enums import BallotRejectionReason
from app.models.lot import UserLotLink
from app.models.resident import Resident
from app.models.role import Role
from app.models.tenant import DEFAULT_TENANT_ID, UserTenantLink
from app.models.user import User
from app.models.voting import BallotRejection
from tests.matrix_world import (
    cell_client,
    matrix_engine,
    neutralised_storage,
    run_cell,
    seed_once,
)

if TYPE_CHECKING:  # pragma: no cover
    from fastapi.dependencies.models import Dependant

BACKEND_ROOT = Path(__file__).resolve().parent.parent
HARNESS_PATH = BACKEND_ROOT / "tests" / "matrix_world.py"

#: `shasum -a 256 backend/tests/matrix_world.py` at this task's merge base
#: (f71608f). ER-1 requires it unchanged: this module reuses the harness and
#: must not edit it, or the 1206-cell star test would stop running against the
#: world its golden file recorded.
HARNESS_SHA256 = "fd701faad1d07fcdca156cca28e8db79259113e96acfd132d59db6022380f4c4"


# ---------------------------------------------------------------------------
# §4.2 -- the five declared enforcement forms
# ---------------------------------------------------------------------------

#: **D** -- `PermissionRequired(P)` in `route.dependant`.
EXPECTED_DEPENDENCY_FORM = 53
#: **S** -- `deps.get_current_superuser` and `P in SUPERUSER_ONLY_PERMISSIONS`.
EXPECTED_SUPERUSER_FORM = 5
#: **M** -- `MEMBERSHIP_GATED`, §5.
EXPECTED_MEMBERSHIP_FORM = 3
#: **E** -- `SERVICE_ENFORCED`, §4.4.
EXPECTED_SERVICE_FORM = 5
#: **H** -- derived, never listed: everything else, proven by the sweep.
EXPECTED_IN_HANDLER_FORM = 135

#: The exception allowlist. It ships **empty** and a future task may not grow
#: it without deleting `test_no_mapped_route_is_unenforced`'s assertion: a
#: route that satisfies no form is a route whose mapping is a lie.
UNENFORCED: frozenset[tuple[str, str]] = frozenset()

#: **M** -- the three global tenant reads, gated by *membership* and not by
#: the mapped permission, with the reason each (§5). They may not take the
#: dependency form: the tenants router is mounted `GLOBAL_SCOPED`, and
#: `PermissionRequired` depends on `get_current_tenant`, which would arm the
#: ambient tenant filter on a route whose whole job is to answer across
#: tenants. They may not take the in-handler form either: with no acting
#: tenant `get_effective_role_ids` falls back to `DEFAULT_TENANT_ID`, so a
#: user whose only roles are in tenant B would be refused their own tenant
#: list -- the list `TenantContext.tsx` fetches to render the switcher, i.e.
#: the app would not boot for them.
MEMBERSHIP_GATED: dict[tuple[str, str], str] = {
    ("GET", "/api/v1/tenants"): (
        "TenantService.list_tenants filters by membership and never errors: "
        "the caller gets their own tenants, never anyone else's"
    ),
    ("GET", "/api/v1/tenants/{tenant_id}"): (
        "get_visible_tenant raises TenantNotFoundError (404, never 403) for a "
        "tenant the caller is not a member of"
    ),
    ("GET", "/api/v1/tenants/{tenant_id}/members"): (
        "idem: the members list resolves through get_visible_tenant first"
    ),
}

#: **E** -- routes whose mapped permission is enforced in a *service*, not in
#: the route signature, because the service does something a route-level guard
#: would skip. Exactly five, each with a pinned behavioural test below. This
#: is **not** a cheaper `UNENFORCED`: every entry costs its author a per-route
#: test that asserts the service's own refusal, message and side effect.
SERVICE_ENFORCED: dict[tuple[str, str], str] = {
    ("POST", "/api/v1/votes/{vote_id}/ballots"): (
        "voting_service._assert_can_cast step 2 reads votes:cast and writes a "
        "BallotRejection(ROLE_FORBIDDEN) row before raising "
        "ForbiddenError('Este perfil não vota'): a route-level guard would "
        "delete the audit row and the Portuguese message"
    ),
    ("POST", "/api/v1/votes/{vote_id}/ballots/retract"): (
        "idem, with votes:retract -- the argument is an IfExp, which is why "
        "an AST probe cannot see it"
    ),
    ("GET", "/api/v1/packages"): (
        "PackageService._assert_lot_access requires packages:read, after a "
        "documented short-circuit for a packages:queue_read holder: the "
        "gatehouse hands packages to every lot and a route-level guard would "
        "403 it"
    ),
    ("GET", "/api/v1/packages/{package_id}"): ("idem, packages:read"),
    ("POST", "/api/v1/packages/{package_id}/pickup"): ("idem, packages:pickup"),
}

#: The 25 routes APRAS-51 converts to the dependency form. Listed rather than
#: derived because each one is a reviewable decision, and because
#: `test_permission_enforcement.PERMISSION_GUARDED_ROUTES` has to name the
#: same 25 -- one literal, two readers.
APRAS_51_ROUTES: frozenset[tuple[str, str]] = frozenset(
    {
        ("GET", "/api/v1/tasks/"),
        ("POST", "/api/v1/tasks/{task_id}/comments"),
        ("PATCH", "/api/v1/tasks/{task_id}/comments/{comment_id}"),
        ("GET", "/api/v1/categories/"),
        ("GET", "/api/v1/roles/"),
        ("GET", "/api/v1/users/"),
        ("GET", "/api/v1/visitors"),
        ("GET", "/api/v1/visitors/{visitor_id}"),
        ("POST", "/api/v1/visitors"),
        ("PUT", "/api/v1/visitors/{visitor_id}"),
        ("GET", "/api/v1/access-logs"),
        ("GET", "/api/v1/authorizations/{authorization_id}"),
        ("GET", "/api/v1/authorizations/{authorization_id}/qr-code"),
        ("GET", "/api/v1/lots/{lot_id}/residents"),
        ("GET", "/api/v1/residents/{resident_id}"),
        ("GET", "/api/v1/feedback"),
        ("GET", "/api/v1/feedback/{id}"),
        ("POST", "/api/v1/feedback"),
        ("GET", "/api/v1/reservable-spaces/"),
        ("POST", "/api/v1/space-reservations/{reservation_id}/cancel"),
        ("POST", "/api/v1/space-reservations/{reservation_id}/reject"),
        ("GET", "/api/v1/uploads/photos/{photo_id}"),
        ("DELETE", "/api/v1/uploads/photos/{photo_id}"),
        ("POST", "/api/v1/uploads/photo"),
        ("GET", "/api/v1/votes/{vote_id}/tally"),
    }
)


# ---------------------------------------------------------------------------
# §4.3 -- the refusal shapes of the complement sweep
# ---------------------------------------------------------------------------

#: Swept routes whose refusal of a non-holder is *not* a bare 403, with the
#: reason. Every other swept route must answer exactly 403. An entry here is a
#: reviewed decision; without this map the sweep's assertion would be
#: `not 2xx`, which three routes satisfied at the merge base while never
#: consulting their mapped permission at all.
REFUSAL_SHAPES: dict[tuple[str, str], tuple[int, str]] = {
    ("GET", "/api/v1/tasks/{task_id}/comments"): (
        404,
        (
            "deps.assert_manager_can_see_task refuses a non-holder of tasks:read "
            "with TaskNotFoundError: the existence of the task is not information "
            "a non-holder is entitled to"
        ),
    ),
    ("GET", "/api/v1/tasks/{task_id}/history"): (
        404,
        (
            "deps.assert_manager_can_see_task refuses a non-holder of tasks:read "
            "with TaskNotFoundError, on the same route-existence argument: this "
            "route is mapped to tasks:read too"
        ),
    ),
}

#: The routes the sweep issues: every mapped route except the three
#: membership-gated ones and the five service-enforced ones. The eight are not
#: sweep *exceptions*: each carries its own, stronger, per-route test below,
#: and for the three `packages` routes the sweep's actor is provably the wrong
#: instrument -- it holds `packages:queue_read` by construction and passes the
#: documented gatehouse short-circuit.
SWEPT_ROUTES: list[tuple[str, str]] = sorted(
    set(ROUTE_PERMISSIONS) - set(MEMBERSHIP_GATED) - set(SERVICE_ENFORCED)
)

#: The detail `deps.PermissionRequired` raises, byte-identical to the one
#: `get_current_superuser` raises. Asserted rather than quoted loosely: it is
#: what tells a "the guard refused" apart from a "the object refused".
PERMISSION_DENIED_DETAIL = "The user doesn't have enough privileges"

#: §4.5's positive direction is "the caller reached the handler", and on eight
#: of the 25 the handler then refuses for a reason that is **not** the mapped
#: permission: a *second* permission, an object dimension, or the harness's
#: own payload. Those answers are pinned exactly, with the dimension named, so
#: "passed the guard" never degrades into "did not 403".
#:
#: Read for a caller whose role carries **exactly** the mapped permission and
#: nothing else -- which is why a second permission can be missing here and
#: cannot be missing for a flag holder.
HOLDER_SECOND_GATE: dict[tuple[str, str], tuple[int, str]] = {
    ("POST", "/api/v1/tasks/{task_id}/comments"): (
        404,
        (
            "second permission: deps.assert_manager_can_see_task needs tasks:read, "
            "and this caller holds only tasks:comment"
        ),
    ),
    ("PATCH", "/api/v1/tasks/{task_id}/comments/{comment_id}"): (
        404,
        (
            "second permission: deps.assert_manager_can_see_task needs tasks:read "
            "before the comment is even looked up, and this caller holds only "
            "tasks:comment"
        ),
    ),
    ("GET", "/api/v1/feedback/{id}"): (
        403,
        (
            "ownership: FeedbackService.get_feedback serves the reporter, or a "
            "holder of feedback:respond; the world's item is the RESIDENT's"
        ),
    ),
    ("DELETE", "/api/v1/uploads/photos/{photo_id}"): (
        403,
        (
            "ownership: media_service.delete_photo serves the uploader, or a "
            "holder of uploads:approve; the world's photo is the RESIDENT's"
        ),
    ),
    ("GET", "/api/v1/votes/{vote_id}/tally"): (
        403,
        (
            "second permission: voting_service._assert_can_view_tally serves a "
            "holder of votes:create, or a votes:cast holder with an eligible lot"
        ),
    ),
    ("POST", "/api/v1/space-reservations/{reservation_id}/reject"): (
        403,
        (
            "second permission: reservation_service.decide_reservation reads "
            "reservations:approve for both approve and reject"
        ),
    ),
    ("POST", "/api/v1/space-reservations/{reservation_id}/cancel"): (
        403,
        (
            "ownership: 'You can only cancel your own reservations'; the world's "
            "reservation is the RESIDENT's"
        ),
    ),
    ("POST", "/api/v1/uploads/photo"): (
        400,
        (
            "harness payload: matrix_world._FILE_BYTES is not a decodable image, "
            "so media_service.upload_photo raises InvalidPhotoFormatError at step "
            "2/3 -- inside the handler, i.e. after the guard has already passed"
        ),
    ),
}

#: The same, for a caller carrying the **whole catalogue** by flag
#: (`is_superuser`, or `is_tenant_admin` of the acting tenant). Only two
#: survive, and neither can be granted away: one is pure ownership, the other
#: is the harness's undecodable upload.
FLAG_HOLDER_SECOND_GATE: dict[tuple[str, str], tuple[int, str]] = {
    ("PATCH", "/api/v1/tasks/{task_id}/comments/{comment_id}"): (
        403,
        (
            "ownership: 'Only the comment author can edit it' -- no permission "
            "grants it, and the world's comment is the ADMINISTRATOR profile's"
        ),
    ),
    ("POST", "/api/v1/uploads/photo"): (
        400,
        (
            "harness payload: matrix_world._FILE_BYTES is not a decodable image "
            "either way, so media_service.upload_photo raises "
            "InvalidPhotoFormatError inside the handler for a flag holder too"
        ),
    ),
}


# ---------------------------------------------------------------------------
# The structural walk (§4.2)
# ---------------------------------------------------------------------------


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
    found: list[deps.PermissionRequired] = []
    if isinstance(dependant.call, deps.PermissionRequired):
        found.append(dependant.call)
    for sub in dependant.dependencies:
        found.extend(_permission_guards(sub))
    return found


def dependency_form() -> dict[tuple[str, str], str]:
    """`(method, path) -> declared permission` for every **D**-form route."""
    guarded: dict[tuple[str, str], str] = {}
    for route in _api_routes():
        for guard in _permission_guards(route.dependant):
            for key in _route_keys(route):
                if key in ROUTE_PERMISSIONS:
                    guarded[key] = guard.permission
    return guarded


def superuser_form() -> set[tuple[str, str]]:
    """The **S**-form routes: `get_current_superuser` + a superuser-only P."""
    return {
        key
        for route in _api_routes()
        if _depends_on(route.dependant, deps.get_current_superuser)
        for key in _route_keys(route)
        if key in ROUTE_PERMISSIONS
        and ROUTE_PERMISSIONS[key] in SUPERUSER_ONLY_PERMISSIONS
    }


def in_handler_form() -> set[tuple[str, str]]:
    """**H** is *derived*, deliberately, and never hand-listed.

    A hand list of 135 keys would give a future author somewhere to type a new
    unenforced route and call it declared. A derived bucket sends every new
    route straight into the sweep, which cannot be satisfied by typing.
    """
    return (
        set(ROUTE_PERMISSIONS)
        - set(dependency_form())
        - superuser_form()
        - set(MEMBERSHIP_GATED)
        - set(SERVICE_ENFORCED)
    )


def success_status(method: str, path: str) -> int:
    """The status code the route declares for a successful call."""
    for route in _api_routes():
        if route.path == path and method in route.methods:
            return route.status_code or 200
    raise AssertionError(f"no route for {method} {path}")


# ---------------------------------------------------------------------------
# ER-1 -- the forms partition `ROUTE_PERMISSIONS`
# ---------------------------------------------------------------------------


def test_the_five_forms_partition_route_permissions():
    """53 + 5 + 3 + 5 + 135 == 201, as an equality against the registry."""
    dependency = set(dependency_form())
    superuser = superuser_form()
    membership = set(MEMBERSHIP_GATED)
    service = set(SERVICE_ENFORCED)
    in_handler = in_handler_form()

    assert len(dependency) == EXPECTED_DEPENDENCY_FORM
    assert len(superuser) == EXPECTED_SUPERUSER_FORM
    assert len(membership) == EXPECTED_MEMBERSHIP_FORM
    assert len(service) == EXPECTED_SERVICE_FORM
    assert len(in_handler) == EXPECTED_IN_HANDLER_FORM

    assert (
        (
            EXPECTED_DEPENDENCY_FORM
            + EXPECTED_SUPERUSER_FORM
            + EXPECTED_MEMBERSHIP_FORM
            + EXPECTED_SERVICE_FORM
            + EXPECTED_IN_HANDLER_FORM
        )
        == 201
        == len(ROUTE_PERMISSIONS)
    )

    assert dependency | superuser | membership | service | in_handler == set(
        ROUTE_PERMISSIONS
    )


def test_the_five_forms_are_pairwise_disjoint():
    """ "Exactly one form" is a claim, so it is the thing that is tested."""
    forms = {
        "D": set(dependency_form()),
        "S": superuser_form(),
        "M": set(MEMBERSHIP_GATED),
        "E": set(SERVICE_ENFORCED),
        "H": in_handler_form(),
    }
    overlaps = sorted(
        (left, right, sorted(forms[left] & forms[right]))
        for index, left in enumerate(sorted(forms))
        for right in sorted(forms)[index + 1 :]
        if forms[left] & forms[right]
    )
    assert not overlaps, f"routes in two enforcement forms: {overlaps}"


def test_no_mapped_route_is_unenforced():
    """The allowlist ships empty, and is asserted empty by name."""
    assert not UNENFORCED
    assert UNENFORCED == frozenset()  # noqa: SIM300 - the literal is the point


def test_every_route_level_permission_matches_the_registry():
    """A `PermissionRequired` must declare its own route's permission."""
    mismatched = sorted(
        (key, declared, ROUTE_PERMISSIONS[key])
        for key, declared in dependency_form().items()
        if declared != ROUTE_PERMISSIONS[key]
    )
    assert not mismatched, f"(route, declared, registry): {mismatched}"


def test_the_dependency_form_gained_exactly_the_twenty_five():
    """The 25 of §3 are D-form, and D grew from 28 to 53 by exactly them."""
    dependency = set(dependency_form())
    assert dependency >= APRAS_51_ROUTES
    assert len(APRAS_51_ROUTES) == 25
    assert len(dependency) - len(APRAS_51_ROUTES) == 28


def test_membership_gated_is_exactly_three_with_a_reason_each():
    assert len(MEMBERSHIP_GATED) == 3
    for key, reason in MEMBERSHIP_GATED.items():
        assert key in ROUTE_PERMISSIONS, key
        assert reason.strip(), key
    assert not (set(MEMBERSHIP_GATED) & set(dependency_form()))
    assert not (set(MEMBERSHIP_GATED) & superuser_form())


def test_service_enforced_is_exactly_five_with_a_reason_each():
    assert len(SERVICE_ENFORCED) == 5
    for key, reason in SERVICE_ENFORCED.items():
        assert key in ROUTE_PERMISSIONS, key
        assert reason.strip(), key
    assert not (set(SERVICE_ENFORCED) & set(dependency_form()))
    assert not (set(SERVICE_ENFORCED) & superuser_form())
    assert not (set(SERVICE_ENFORCED) & set(MEMBERSHIP_GATED))


def test_the_superuser_form_routes_carry_a_superuser_only_permission():
    for key in superuser_form():
        assert ROUTE_PERMISSIONS[key] in SUPERUSER_ONLY_PERMISSIONS


def test_the_harness_is_untouched():
    """ER-1: this module builds its own world, it does not edit the harness."""
    raw = HARNESS_PATH.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == HARNESS_SHA256


#: Every spelling a docstring could use to claim a fixed number of routes.
_COUNT_WORD = (
    r"(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|"
    r"thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|"
    r"twenty[-\w]*|thirty[-\w]*|forty[-\w]*|fifty[-\w]*)"
)

#: "is used on **exactly** the seven routes", in any spelling and with any
#: emphasis. IAM F2 wrote that sentence when the count was true; APRAS-40,
#: APRAS-44 and APRAS-51 made it false three times over without anybody
#: noticing, because nothing read it.
_FIXED_COUNT_CLAIM = re.compile(
    rf"\b(?:used|mounted|carried|declared|applied)\s+on\s+[\*\s]*"
    rf"(?:exactly[\*\s]*)?(?:the[\*\s]*)?{_COUNT_WORD}\s+routes",
    re.IGNORECASE,
)


def test_the_permission_required_docstring_claims_no_fixed_route_count():
    """CR1: the guard class may not state a count that its own users rot.

    `PermissionRequired`'s docstring said it was used on "**exactly** the
    seven routes" while sitting on 53. That is the defect class this whole
    task exists to close -- a normative statement about enforcement that the
    code contradicts -- and it sat in the docstring of the guard class itself,
    where the next author reads it first.

    Three assertions. (a) The retired sentence may not come back, in any
    spelling. (b) The docstring may not name the *current* count either, since
    a number written here is a number nobody updates: the count lives in
    `test_permission_enforcement.PERMISSION_GUARDED_ROUTES`, which is asserted
    against a walk of the live app. (c) It must point at the machine-checked
    enumeration instead, so a reader who wants the list knows where it is.
    """
    doc = inspect.getdoc(deps.PermissionRequired) or ""

    assert "exactly** the seven routes" not in doc
    claims = _FIXED_COUNT_CLAIM.findall(doc)
    assert not claims, f"PermissionRequired claims a fixed route count: {claims}"

    current = str(len(dependency_form()))
    assert current not in doc, (
        f"the docstring hard-codes today's D-form count ({current}); it is "
        "asserted in test_permission_enforcement.py, where a walk keeps it true"
    )

    for anchor in (
        "ROUTE_PERMISSIONS",
        "PERMISSION_GUARDED_ROUTES",
        "tests/test_permission_enforcement.py",
        "tests/test_permission_alignment.py",
        # The rule that *does* still bind, and the form it keeps routes out of.
        "SERVICE_ENFORCED",
    ):
        assert anchor in doc, f"PermissionRequired's docstring does not name {anchor}"


def test_the_swept_routes_are_two_hundred_and_one_minus_eight():
    assert len(SWEPT_ROUTES) == 193
    assert set(SWEPT_ROUTES) == (
        set(ROUTE_PERMISSIONS) - set(MEMBERSHIP_GATED) - set(SERVICE_ENFORCED)
    )


def test_every_refusal_shape_is_a_swept_route():
    """A stale entry is a failure, not dead prose."""
    stale = sorted(set(REFUSAL_SHAPES) - set(SWEPT_ROUTES))
    assert not stale, f"REFUSAL_SHAPES entries that are not swept: {stale}"
    assert len(REFUSAL_SHAPES) == 2
    for key, (status, reason) in REFUSAL_SHAPES.items():
        assert status != 403, f"{key}: a 403 needs no override"
        assert not 200 <= status < 300, f"{key}: a 2xx is never a refusal"
        assert reason.strip(), key


#: The dimensions a second-gate reason may name. A reason naming none of them
#: is not an explanation, it is an excuse -- the same rule
#: `test_permission_parity_matrix.NON_ROLE_403_DIMENSIONS` states.
SECOND_GATE_DIMENSIONS = ("second permission", "ownership", "harness payload")


def test_every_second_gate_entry_is_one_of_the_twenty_five_with_a_reason():
    for name, table in (
        ("HOLDER_SECOND_GATE", HOLDER_SECOND_GATE),
        ("FLAG_HOLDER_SECOND_GATE", FLAG_HOLDER_SECOND_GATE),
    ):
        stale = sorted(set(table) - APRAS_51_ROUTES)
        assert not stale, f"{name} entries outside the 25: {stale}"
        for key, (status, reason) in table.items():
            assert status >= 400, f"{name} {key}: {status} is not a refusal"
            assert reason.startswith(SECOND_GATE_DIMENSIONS), (
                f"{name} {key}: reason must name a dimension, got {reason!r}"
            )
    # A flag holds the whole catalogue, so a *second permission* can never be
    # what refuses it: only ownership and the harness's payload survive.
    assert set(FLAG_HOLDER_SECOND_GATE) <= set(HOLDER_SECOND_GATE)
    assert len(FLAG_HOLDER_SECOND_GATE) == 2


# ---------------------------------------------------------------------------
# The world (§4.3) -- built here, from the unmodified harness helpers
# ---------------------------------------------------------------------------

#: `world.tokens` keys this module adds. `run_cell` reads `world.tokens[role]`,
#: so an actor is usable by the harness the moment its token is registered.
PROBE = "APRAS51_PROBE"
SUPERUSER = "APRAS51_SUPERUSER"
TENANT_ADMIN = "APRAS51_TENANT_ADMIN"
OUTSIDER = "APRAS51_OUTSIDER"
GATEHOUSE = "APRAS51_GATEHOUSE"

_CPF_SEEDS = {
    PROBE: 900_000_001,
    SUPERUSER: 900_000_002,
    TENANT_ADMIN: 900_000_003,
    OUTSIDER: 900_000_004,
    GATEHOUSE: 900_000_005,
}


def _cpf(seed: int) -> str:
    """A check-digit-valid CPF, derived rather than a literal."""
    base = f"{seed:09d}"
    total = sum(int(base[i]) * (10 - i) for i in range(9))
    d1 = 0 if (total % 11) < 2 else 11 - (total % 11)
    nine = base + str(d1)
    total = sum(int(nine[i]) * (11 - i) for i in range(10))
    d2 = 0 if (total % 11) < 2 else 11 - (total % 11)
    return nine + str(d2)


class Actors:
    """The five extra actors, by id, plus the role rows the cells rewrite."""

    def __init__(self) -> None:
        self.user_ids: dict[str, uuid.UUID] = {}
        self.role_ids: dict[str, uuid.UUID] = {}


def _seed_actors(engine, world) -> Actors:
    """Seed this module's own actors into the harness's world.

    A plain `Session`, exactly as `build_world` uses: it is not request
    scoped, so the fail-closed tenant guard does not fire and every scoped row
    defaults to `DEFAULT_TENANT_ID`.

    Each actor's only role is a **new** row of the default tenant -- never one
    of the six legacy profile rows, which six other actors read.
    """
    seeds: tuple[tuple[str, list[str]], ...] = (
        (PROBE, []),
        (SUPERUSER, []),
        (TENANT_ADMIN, []),
        (OUTSIDER, sorted(PERMISSIONS)),
        (GATEHOUSE, ["packages:queue_read"]),
    )
    actors = Actors()
    with Session(engine) as session:
        for key, permissions in seeds:
            role = Role(
                name=f"APRAS-51 {key} Role",
                tenant_id=DEFAULT_TENANT_ID,
                permissions=list(permissions),
            )
            session.add(role)
            session.commit()
            session.refresh(role)
            user = User(
                id=uuid.uuid4(),
                email=f"{key.lower()}@alignment.example.com",
                full_name=f"{key} Alignment",
                hashed_password="not-a-real-hash",
                cpf=_cpf(_CPF_SEEDS[key]),
                is_superuser=key == SUPERUSER,
                roles=[role],
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            actors.user_ids[key] = user.id
            actors.role_ids[key] = role.id

            # The outsider is a member of tenant B **only**: it still carries a
            # default-tenant role with the whole catalogue, which is what makes
            # §5's test about *membership* rather than about an empty bundle.
            tenant_id = world.tenant_b_id if key == OUTSIDER else DEFAULT_TENANT_ID
            session.add(
                UserTenantLink(
                    user_id=user.id,
                    tenant_id=tenant_id,
                    is_tenant_admin=key == TENANT_ADMIN,
                )
            )
            if key != OUTSIDER:
                # Linked to the world's lot, with an active Resident row, so
                # the per-lot narrowings are satisfied and the only dimension
                # left to refuse a cell is the permission under measurement.
                session.add(
                    UserLotLink(
                        user_id=user.id,
                        lot_id=world.lot_id,
                        start_date=None,
                        end_date=None,
                    )
                )
                session.add(
                    Resident(
                        lot_id=world.lot_id,
                        user_id=user.id,
                        full_name=f"{key} Resident",
                        cpf=_cpf(_CPF_SEEDS[key] + 100),
                        is_active=True,
                    )
                )
            session.commit()
            world.tokens[key] = create_access_token(str(user.id))
    # Not a restatement of the loop: five *distinct* role rows and five
    # distinct users are what the per-cell rewrite relies on. A copy-paste
    # that reused one role id would make `set_permissions` move two actors at
    # once and quietly weaken every case below.
    assert len(set(actors.role_ids.values())) == len(seeds)
    assert len(set(actors.user_ids.values())) == len(seeds)
    return actors


@pytest.fixture(scope="module")
def alignment_run(tmp_path_factory):
    """One SQLite file, one engine, one world, five extra actors."""
    database_path = tmp_path_factory.mktemp("alignment") / "alignment.sqlite3"
    with matrix_engine(str(database_path)) as engine, neutralised_storage():
        world = seed_once(engine)
        yield engine, world, _seed_actors(engine, world)


def _cell_session() -> Session:
    """The `Session` the open `cell_client` gives every request.

    `cell_client` installs the override itself and yields only the
    `TestClient`, so this is how a cell reaches the same handle -- calling the
    override is exactly what FastAPI does.
    """
    return app.dependency_overrides[get_session]()


def set_permissions(role_id: uuid.UUID, permissions: list[str]) -> None:
    """Rewrite one role's bundle inside the open cell's transaction.

    `acting_tenant_scope` is required and not decorative: the cell session is
    request scoped and unresolved until a request arms it, so a bare
    `session.get(Role, ...)` raises `TenantScopeNotResolvedError` from the
    fail-closed filter.
    """
    session = _cell_session()
    with tenant_context.acting_tenant_scope(session, DEFAULT_TENANT_ID):
        role = session.get(Role, role_id)
        role.permissions = permissions
        session.add(role)
        session.commit()


class _CapturingClient:
    """A `TestClient` proxy that keeps the response `run_cell` throws away.

    `matrix_world.run_cell` builds a cell's request exactly the way the frozen
    harness does -- path parameters through `resolve_path`, `QUERY_PARAMS`,
    `REQUEST_BODIES` and its multipart `Upload` branch -- and then returns only
    an integer. Several cases in this module need the *body* too, to assert
    that a refusal does **not** carry `PermissionRequired`'s detail.

    Round 0 solved that by copying `run_cell`'s twenty lines. That copy is
    gone: it duplicated a function this module may not edit (the harness is
    sha-pinned by ER-1), so the two could drift apart silently and the
    named-route cases would stop issuing the same requests the sweep issues.
    Handing `run_cell` a proxy whose `request` records what came back reuses
    the harness verbatim and owns nothing. It also removes this module's only
    reason to import the private `_FILE_BYTES` and `_NoBody`.
    """

    def __init__(self, client) -> None:
        self._client = client
        self.last = None

    def request(self, *args, **kwargs):
        self.last = self._client.request(*args, **kwargs)
        return self.last


def request_as(client, world, actor: str, method: str, path: str):
    """One real request for `(method, path)` as `actor`, and its response.

    `run_cell`'s own request, unmodified -- see `_CapturingClient`.
    """
    proxy = _CapturingClient(client)
    run_cell(proxy, world, actor, method, path)
    return proxy.last


def _detail(response) -> str:
    """The `detail` string of an error body, or `""` for anything else."""
    try:
        body = response.json()
    except ValueError:  # pragma: no cover - a non-JSON body is never a 403
        return ""
    return str(body.get("detail", "")) if isinstance(body, dict) else ""


# ---------------------------------------------------------------------------
# ER-1, ER-2 -- the shaped complement sweep (§4.3)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("method", "path"),
    SWEPT_ROUTES,
    ids=[f"{method}-{path}" for method, path in SWEPT_ROUTES],
)
def test_a_non_holder_of_the_mapped_permission_is_refused(alignment_run, method, path):
    """The whole catalogue **except** this route's permission must not pass.

    One-sided on purpose: "a holder is not refused" is what the 1206-cell
    parity matrix already measures for the six legacy profiles, including the
    31 object-dimension refusals a two-sided sweep would have to re-litigate.
    """
    engine, world, actors = alignment_run
    permission = ROUTE_PERMISSIONS[(method, path)]
    expected, _reason = REFUSAL_SHAPES.get((method, path), (403, ""))
    with cell_client(engine) as client:
        set_permissions(actors.role_ids[PROBE], sorted(PERMISSIONS - {permission}))
        status = run_cell(client, world, PROBE, method, path)
    assert not 200 <= status < 300, (
        f"{method} {path} answered {status} to a caller holding everything "
        f"except {permission}"
    )
    assert status == expected, (
        f"{method} {path}: expected {expected} for a non-holder of "
        f"{permission}, got {status}"
    )


# ---------------------------------------------------------------------------
# ER-2 -- the 25 revealed routes, four callers each (§4.5)
# ---------------------------------------------------------------------------

_TWENTY_FIVE = sorted(APRAS_51_ROUTES)


@pytest.mark.parametrize(
    ("method", "path"),
    _TWENTY_FIVE,
    ids=[f"{method}-{path}" for method, path in _TWENTY_FIVE],
)
def test_a_member_with_no_permission_is_refused_by_the_guard(
    alignment_run, method, path
):
    """403, and with `PermissionRequired`'s own detail: the *guard* refused."""
    engine, world, actors = alignment_run
    with cell_client(engine) as client:
        set_permissions(actors.role_ids[PROBE], [])
        response = request_as(client, world, PROBE, method, path)
    assert response.status_code == 403, f"{method} {path}: {response.status_code}"
    assert _detail(response) == PERMISSION_DENIED_DETAIL


@pytest.mark.parametrize(
    ("method", "path"),
    _TWENTY_FIVE,
    ids=[f"{method}-{path}" for method, path in _TWENTY_FIVE],
)
def test_a_holder_of_exactly_the_mapped_permission_passes_the_guard(
    alignment_run, method, path
):
    """A role carrying exactly one string reaches the handler."""
    engine, world, actors = alignment_run
    permission = ROUTE_PERMISSIONS[(method, path)]
    with cell_client(engine) as client:
        set_permissions(actors.role_ids[PROBE], [permission])
        response = request_as(client, world, PROBE, method, path)
    _assert_passed_the_guard(response, method, path, HOLDER_SECOND_GATE)


@pytest.mark.parametrize(
    ("actor", "method", "path"),
    [
        (actor, method, path)
        for actor in (SUPERUSER, TENANT_ADMIN)
        for method, path in _TWENTY_FIVE
    ],
    ids=[
        f"{actor}-{method}-{path}"
        for actor in (SUPERUSER, TENANT_ADMIN)
        for method, path in _TWENTY_FIVE
    ],
)
def test_a_flag_holder_passes_the_guard(alignment_run, actor, method, path):
    """Free by construction, and asserted anyway.

    `_resolve_permissions` short-circuits both `is_superuser` and an acting
    `is_tenant_admin` to the whole catalogue, so this passes without a single
    special case -- which is the property APRAS-47 bought and this task must
    not spend. Both actors' roles carry `permissions = []`.
    """
    engine, world, _actors = alignment_run
    with cell_client(engine) as client:
        response = request_as(client, world, actor, method, path)
    _assert_passed_the_guard(response, method, path, FLAG_HOLDER_SECOND_GATE)


def _assert_passed_the_guard(
    response,
    method: str,
    path: str,
    second_gate: dict[tuple[str, str], tuple[int, str]],
) -> None:
    """The caller reached the handler: never the guard's own 403.

    Two assertions, in this order. The first is the contract -- the refusal,
    if any, does **not** carry `PermissionRequired`'s detail, so the mapped
    permission is not what stopped the caller. The second pins the exact
    answer: the route's declared success code, or the status its `second_gate`
    entry declares.
    """
    assert not (
        response.status_code == 403 and _detail(response) == PERMISSION_DENIED_DETAIL
    ), f"{method} {path}: the permission guard refused a holder"
    expected, _reason = second_gate.get(
        (method, path), (success_status(method, path), "")
    )
    assert response.status_code == expected, (
        f"{method} {path}: expected {expected}, got {response.status_code} "
        f"({_detail(response)})"
    )


# ---------------------------------------------------------------------------
# ER-2 -- the five service-enforced routes (§4.4)
# ---------------------------------------------------------------------------

_BALLOT_ROUTES = [
    ("POST", "/api/v1/votes/{vote_id}/ballots", "votes:cast"),
    ("POST", "/api/v1/votes/{vote_id}/ballots/retract", "votes:retract"),
]


@pytest.mark.parametrize(
    ("method", "path", "permission"),
    _BALLOT_ROUTES,
    ids=[path for _m, path, _p in _BALLOT_ROUTES],
)
def test_ballot_routes_refuse_a_non_holder_in_the_service(
    alignment_run, method, path, permission
):
    """403, the Portuguese message, **and** the audit row a guard would skip.

    This is what makes `SERVICE_ENFORCED` a form and not an excuse: the 403 is
    the answer the sweep would have demanded, and the `BallotRejection` row is
    what the sweep cannot see.
    """
    engine, world, actors = alignment_run
    with cell_client(engine) as client:
        set_permissions(actors.role_ids[PROBE], sorted(PERMISSIONS - {permission}))
        response = request_as(client, world, PROBE, method, path)
        session = _cell_session()
        with tenant_context.acting_tenant_scope(session, DEFAULT_TENANT_ID):
            rejections = session.exec(
                select(BallotRejection).where(
                    BallotRejection.vote_id == world.vote_id,
                    BallotRejection.user_id == actors.user_ids[PROBE],
                )
            ).all()
            reasons = [row.reason for row in rejections]

    assert response.status_code == 403
    assert _detail(response) == "Este perfil não vota"
    assert reasons == [BallotRejectionReason.ROLE_FORBIDDEN], reasons


_PACKAGE_ROUTES = [
    ("GET", "/api/v1/packages", "packages:read"),
    ("GET", "/api/v1/packages/{package_id}", "packages:read"),
    ("POST", "/api/v1/packages/{package_id}/pickup", "packages:pickup"),
]


@pytest.mark.parametrize(
    ("method", "path", "permission"),
    _PACKAGE_ROUTES,
    ids=[f"{method}-{path}" for method, path, _p in _PACKAGE_ROUTES],
)
def test_packages_routes_enforce_the_mapped_permission_in_the_service(
    alignment_run, method, path, permission
):
    """Three callers, and the middle one is the reason the form exists.

    A `packages:queue_read` holder without the mapped permission **passes**:
    the gatehouse hands packages to every lot and holds no lot link. A
    route-level `Depends` would 403 it, and no parity cell would move --
    no legacy bundle holds `queue_read` without the mapped permission -- so
    the matrix is structurally blind to that regression.
    """
    engine, world, actors = alignment_run
    success = success_status(method, path)

    with cell_client(engine) as client:
        set_permissions(actors.role_ids[PROBE], [])
        neither = request_as(client, world, PROBE, method, path)
    assert neither.status_code == 403, (
        f"{method} {path}: a caller holding neither {permission} nor "
        f"packages:queue_read got {neither.status_code}"
    )

    with cell_client(engine) as client:
        queue_only = request_as(client, world, GATEHOUSE, method, path)
    assert queue_only.status_code == success, (
        f"{method} {path}: the documented packages:queue_read short-circuit "
        f"answered {queue_only.status_code} ({_detail(queue_only)})"
    )

    with cell_client(engine) as client:
        set_permissions(actors.role_ids[PROBE], [permission])
        holder = request_as(client, world, PROBE, method, path)
    assert holder.status_code == success, (
        f"{method} {path}: a lot-linked holder of {permission} answered "
        f"{holder.status_code} ({_detail(holder)})"
    )


# ---------------------------------------------------------------------------
# §5 -- the membership form, proven positively
# ---------------------------------------------------------------------------


def test_membership_gated_routes_gate_on_membership_and_not_on_the_permission(
    alignment_run,
):
    """Two callers, and the exact answers the handlers give.

    The outsider carries a default-tenant role holding the **whole
    catalogue**, so a refusal cannot be blamed on an empty bundle: with no
    acting tenant `get_effective_role_ids` falls back to `DEFAULT_TENANT_ID`
    and resolves all 174 strings. It is still refused, because membership is
    the gate. The member holds **nothing** and is served, for the same reason.
    """
    engine, world, actors = alignment_run
    default_id = str(DEFAULT_TENANT_ID)

    with cell_client(engine) as client:
        set_permissions(actors.role_ids[PROBE], [])
        headers = {"Authorization": f"Bearer {world.tokens[OUTSIDER]}"}
        listing = client.get("/api/v1/tenants", headers=headers)
        detail = client.get(f"/api/v1/tenants/{default_id}", headers=headers)
        members = client.get(f"/api/v1/tenants/{default_id}/members", headers=headers)

        member_headers = {"Authorization": f"Bearer {world.tokens[PROBE]}"}
        member_listing = client.get("/api/v1/tenants", headers=member_headers)
        member_detail = client.get(
            f"/api/v1/tenants/{default_id}", headers=member_headers
        )
        member_members = client.get(
            f"/api/v1/tenants/{default_id}/members", headers=member_headers
        )

    # The outsider: 200 on the list, with the default tenant absent from it.
    assert listing.status_code == 200
    assert default_id not in {item["id"] for item in listing.json()}
    assert detail.status_code == 404, "never 403 -- APRAS-47 §5.1"
    assert members.status_code == 404

    # The member holding no permission at all: served on all three.
    assert member_listing.status_code == 200
    assert default_id in {item["id"] for item in member_listing.json()}
    assert member_detail.status_code == 200
    assert member_members.status_code == 200
