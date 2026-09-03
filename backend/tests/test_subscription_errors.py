"""The status code of every APRAS-40 domain error, pinned at the dispatcher.

`domain_exception_handler` is one long `if/elif` chain over `isinstance`
tuples, so a class's status is a property of **which tuple it is in and which
branch runs first** — not of anything the class itself declares. That makes two
mistakes invisible to `ruff` and to every API test:

* an entry duplicated into a later tuple is **unreachable dead code**, and
  becomes live (with the wrong status) the day the branches are reordered;
* an entry in the wrong tuple is only caught if some API test happens to
  exercise that exact path.

Round 1 of code review found exactly the first of those: `PlanNotFoundError`
and `PlanAlreadyExistsError` had been copy-pasted into the 400 tuple as well as
their real 404/409 ones. This module is the guard that would have caught it —
it calls the handler **directly**, once per class, so every one of APRAS-40's
seven errors states its status in one table that a branch reorder cannot
silently move.

The 400s are the *default*: they carry no tuple of their own and fall through
to `status_code`'s initialisation. Asserting them here is what makes "this
class is deliberately not listed anywhere" a checked claim rather than an
absence.
"""

import ast
import asyncio
import pathlib
import uuid

import pytest
from fastapi import status

from app.core.exception_handlers import domain_exception_handler
from app.core.exceptions import (
    CoreModuleNotContractableError,
    InactivePlanError,
    InvalidModulePriceError,
    InvalidPlanPriceError,
    ModuleNotEntitledError,
    PlanAlreadyExistsError,
    PlanNotFoundError,
    SubscriptionNotFoundError,
)

_PLAN_ID = uuid.uuid4()

#: `(exception instance, expected status)` for every class APRAS-40 §6.1 adds.
#: Built as instances rather than classes so the detail string is exercised on
#: the same pass — a constructor that raised would fail here too.
APRAS_40_ERRORS = [
    (PlanNotFoundError(_PLAN_ID), status.HTTP_404_NOT_FOUND),
    (SubscriptionNotFoundError(), status.HTTP_404_NOT_FOUND),
    (PlanAlreadyExistsError("Plano Básico"), status.HTTP_409_CONFLICT),
    (ModuleNotEntitledError(["finance"]), status.HTTP_400_BAD_REQUEST),
    (InactivePlanError("Plano Retirado"), status.HTTP_400_BAD_REQUEST),
    (CoreModuleNotContractableError(["billing"]), status.HTTP_400_BAD_REQUEST),
    (InvalidModulePriceError(["finance"]), status.HTTP_400_BAD_REQUEST),
    (InvalidPlanPriceError("The base price cannot be negative"),
     status.HTTP_400_BAD_REQUEST),
]


@pytest.mark.parametrize(
    ("error", "expected"),
    APRAS_40_ERRORS,
    ids=[type(error).__name__ for error, _expected in APRAS_40_ERRORS],
)
def test_every_apras_40_error_maps_to_its_declared_status(error, expected):
    """One case per class, straight through the real dispatcher."""
    response = asyncio.run(domain_exception_handler(None, error))

    assert response.status_code == expected


def test_the_detail_strings_are_the_ones_the_ers_pin():
    """The detail is part of the contract: three ERs quote it verbatim."""
    assert PlanNotFoundError(_PLAN_ID).message == f"Plan not found: {_PLAN_ID}"
    assert SubscriptionNotFoundError().message == "This tenant has no subscription"
    assert PlanAlreadyExistsError("Plano Básico").message == (
        "A plan named 'Plano Básico' already exists"
    )
    # Sorted, and named -- ER-3 quotes this string.
    assert ModuleNotEntitledError(["purchases", "finance"]).message == (
        "Modules not covered by the subscription: finance, purchases"
    )
    assert CoreModuleNotContractableError(["billing"]).message == (
        "Core modules are always active: billing"
    )
    assert InactivePlanError("Plano Retirado").message == (
        "Plan 'Plano Retirado' is not active"
    )
    assert InvalidModulePriceError(["finance"]).message == (
        "Priced modules must be included in the plan: finance"
    )


def test_no_apras_40_error_is_listed_twice_in_the_dispatcher():
    """The structural half of the same guard: no class appears in two tuples.

    `test_every_apras_40_error_maps_to_its_declared_status` catches a *wrong*
    status; this catches an entry that is merely **unreachable** today and
    would become wrong the day the branches are reordered. That is the exact
    shape of the round-1 finding, so it gets a test of its own rather than
    relying on the behavioural case to notice it later.

    The scan is over the AST of the handler, never over source text: the module
    docstrings and the import block name these classes too and must not count.
    """
    source = pathlib.Path(
        domain_exception_handler.__code__.co_filename
    ).read_text(encoding="utf-8")
    handler = next(
        node
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.AsyncFunctionDef)
        and node.name == "domain_exception_handler"
    )
    mentioned: list[str] = [
        element.id
        for node in ast.walk(handler)
        if isinstance(node, ast.Tuple)
        for element in node.elts
        if isinstance(element, ast.Name)
    ]

    duplicated = sorted({name for name in mentioned if mentioned.count(name) > 1})
    assert not duplicated, (
        "these classes are listed in more than one isinstance tuple, so all but "
        f"the first are unreachable: {duplicated}"
    )
    # ...and every APRAS-40 class the chain routes is actually in it exactly
    # once, so a deletion is caught as loudly as a duplication.
    routed = {"PlanNotFoundError", "SubscriptionNotFoundError", "PlanAlreadyExistsError"}
    assert routed <= set(mentioned)
    for name in routed:
        assert mentioned.count(name) == 1, name
