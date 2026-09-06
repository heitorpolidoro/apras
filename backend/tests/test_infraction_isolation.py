"""ER-5: the infraction module is mechanically isolated from Financeiro.

Modelled on ``tests/test_purchase_isolation.py`` (APRAS-37), whose reasoning
applies verbatim: a raw substring scan would be both a false positive (the
mandatory ``down_revision`` identifier, the unrelated legitimate module
``app.models.media_asset``) and a false negative (``from app.models import
FinancialTransaction`` contains no lowercase ``finance``). So the static half
parses each of the five files with ``ast`` and inspects **import nodes** and
**call arguments** only, and the runtime half drives the whole flow through the
API and counts rows.

Applying a MULTA records a value, a date and the person it was applied
against. It creates **no** ledger row. When APRAS eventually grows per-lot
billing, a separate task connects them; the point of this module is that the
connection has to be a *decision* rather than a drift.
"""

from __future__ import annotations

import ast
import os
from datetime import date
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import func
from sqlmodel import select

from app.models.finance import BudgetLine, FinanceCategory, FinancialTransaction
from tests.infraction_helpers import (
    create_infraction,
    create_rule,
    headers,
    make_lot,
    make_member,
    make_resident,
)

if TYPE_CHECKING:  # pragma: no cover
    from fastapi.testclient import TestClient
    from sqlmodel import Session


_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MIGRATION = "alembic/versions/0036_add_infraction_tables.py"

SCANNED = [
    "app/models/infraction.py",
    "app/schemas/infraction.py",
    "app/services/infraction_service.py",
    "app/api/v1/endpoints/infractions.py",
    MIGRATION,
]

FORBIDDEN_MODULES = {
    "app.models.finance",
    "app.schemas.finance",
    "app.services.finance_service",
    "app.api.v1.endpoints.finance",
}

FORBIDDEN_NAMES = {
    "FinanceCategory",
    "BudgetLine",
    "FinancialTransaction",
    "FinanceService",
}

AGGREGATE_PACKAGES = {"app.models", "app.schemas", "app.services"}

#: Every table the module's own migration may name. `user`, `lot`, `resident`,
#: `occurrence` and `tenant` are the five foreign parents it legitimately
#: points at; none of them is a finance table.
ALLOWED_TABLES = {
    "infraction",
    "infraction_rule",
    "infraction_policy_step",
    "infraction_stage",
    "infraction_contestation",
    "infraction_cycle_close",
    "infraction_settings",
    "user",
    "lot",
    "resident",
    "occurrence",
    "tenant",
}

FINANCE_TABLES = {"financial_transaction", "finance_category", "budget_line"}

#: The finance module's own files. `test_no_finance_source_file_is_in_this_module`
#: asserts the scanned set is disjoint from it.
FINANCE_FILES = {
    "app/models/finance.py",
    "app/schemas/finance.py",
    "app/services/finance_service.py",
    "app/api/v1/endpoints/finance.py",
}

_FIRST_ARG_TABLE_CALLS = {
    "op.create_table",
    "op.drop_table",
    "op.add_column",
    "op.drop_column",
    "op.alter_column",
    "op.execute",
    "op.rename_table",
}
_INDEX_CALLS = {"op.create_index", "op.drop_index"}


def _source(relative_path: str) -> str:
    with open(os.path.join(_BACKEND_DIR, relative_path), encoding="utf-8") as handle:
        return handle.read()


def _tree(relative_path: str) -> ast.Module:
    return ast.parse(_source(relative_path), filename=relative_path)


def _imported_modules(tree: ast.Module) -> set[str]:
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            modules.add(node.module)
    return modules


def _names_from_aggregate_packages(tree: ast.Module) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.ImportFrom)
            and node.level == 0
            and node.module in AGGREGATE_PACKAGES
        ):
            names.update(alias.name for alias in node.names)
    return names


def _referenced_names(tree: ast.Module) -> set[str]:
    """Every `Name` and attribute tail the file mentions.

    Wider than the import scan on purpose: it catches
    `app.models.finance.FinancialTransaction` written as an attribute chain,
    which no import node would show.
    """
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
    return names


def _positional(node: ast.Call, index: int):
    return node.args[index] if len(node.args) > index else None


def _keyword(node: ast.Call, name: str):
    for kw in node.keywords:
        if kw.arg == name:
            return kw.value
    return None


def _constant_str(node) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _table_of(qualified: str) -> str:
    return qualified.split(".", 1)[0]


def _tables_touched(tree: ast.Module) -> set[str]:
    tables: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        rendered = ast.unparse(node.func)

        if rendered in _FIRST_ARG_TABLE_CALLS:
            name = _constant_str(_positional(node, 0))
            assert name is not None, f"{rendered} must take a literal table name."
            tables.add(name)

        elif rendered in _INDEX_CALLS:
            target = _positional(node, 1) or _keyword(node, "table_name")
            name = _constant_str(target)
            assert name is not None, f"{rendered} must name a literal table."
            tables.add(name)

        elif rendered == "sa.ForeignKeyConstraint":
            refs = _positional(node, 1)
            assert isinstance(refs, (ast.List, ast.Tuple)), (
                "sa.ForeignKeyConstraint must take a literal list of references."
            )
            for element in refs.elts:
                ref = _constant_str(element)
                assert ref is not None, "Foreign key references must be literals."
                tables.add(_table_of(ref))

        elif rendered == "sa.ForeignKey":
            ref = _constant_str(_positional(node, 0))
            assert ref is not None, "sa.ForeignKey must take a literal reference."
            tables.add(_table_of(ref))

        elif rendered == "op.create_foreign_key":
            for position, keyword in ((1, "source_table"), (2, "referent_table")):
                target = _positional(node, position) or _keyword(node, keyword)
                name = _constant_str(target)
                assert name is not None, (
                    "op.create_foreign_key must name literal tables."
                )
                tables.add(name)

    return tables


# --------------------------------------------------------------------- #
# Rule 1 -- no forbidden module imports
# --------------------------------------------------------------------- #


@pytest.mark.parametrize("relative_path", SCANNED)
def test_no_forbidden_module_imports(relative_path: str) -> None:
    modules = _imported_modules(_tree(relative_path))
    offenders = modules & FORBIDDEN_MODULES
    assert not offenders, (
        f"{relative_path} imports forbidden module(s): {sorted(offenders)}"
    )


def test_rule_one_actually_catches_a_violation() -> None:
    """The scan is not vacuous."""
    tree = ast.parse("from app.models.finance import FinancialTransaction")
    assert _imported_modules(tree) & FORBIDDEN_MODULES == {"app.models.finance"}


# --------------------------------------------------------------------- #
# Rule 2 -- no forbidden names, by any spelling
# --------------------------------------------------------------------- #


@pytest.mark.parametrize("relative_path", SCANNED)
def test_no_forbidden_names(relative_path: str) -> None:
    tree = _tree(relative_path)
    offenders = (
        _names_from_aggregate_packages(tree) | _referenced_names(tree)
    ) & FORBIDDEN_NAMES
    assert not offenders, (
        f"{relative_path} names forbidden symbol(s): {sorted(offenders)}"
    )


def test_rule_two_actually_catches_a_violation() -> None:
    """`from app.models import BudgetLine` has no lowercase 'finance'."""
    tree = ast.parse("from app.models import BudgetLine, FinanceCategory")
    assert _names_from_aggregate_packages(tree) & FORBIDDEN_NAMES == {
        "BudgetLine",
        "FinanceCategory",
    }
    attribute = ast.parse("x = finance_module.FinancialTransaction")
    assert _referenced_names(attribute) & FORBIDDEN_NAMES == {
        "FinancialTransaction"
    }


# --------------------------------------------------------------------- #
# Rule 3 -- the migration touches only the module's own tables
# --------------------------------------------------------------------- #


def test_migration_touches_only_allowed_tables() -> None:
    tables = _tables_touched(_tree(MIGRATION))
    assert tables, "The scan found no tables at all -- it is not doing its job."
    assert not tables & FINANCE_TABLES, (
        f"the migration targets a finance table: {sorted(tables & FINANCE_TABLES)}"
    )
    assert tables <= ALLOWED_TABLES, (
        f"Migration touches foreign table(s): {sorted(tables - ALLOWED_TABLES)}"
    )
    assert {
        "infraction",
        "infraction_rule",
        "infraction_policy_step",
        "infraction_stage",
        "infraction_contestation",
        "infraction_cycle_close",
        "infraction_settings",
    } <= tables


def test_rule_three_actually_catches_a_violation() -> None:
    tree = ast.parse(
        'sa.ForeignKeyConstraint(["fine_id"], ["financial_transaction.id"], '
        'ondelete="RESTRICT")'
    )
    assert _tables_touched(tree) & FINANCE_TABLES == {"financial_transaction"}


def test_migration_chain_link_is_explicit() -> None:
    module = {}
    for node in _tree(MIGRATION).body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Name) and isinstance(
                    node.value, ast.Constant
                ):
                    module[target.id] = node.value.value

    assert module["revision"] == "0036_add_infraction_tables"
    assert module["down_revision"] == "0035_add_subscription_tables"
    # `alembic_version.version_num` is VARCHAR(32).
    assert len(module["revision"]) <= 32


def test_no_finance_source_file_is_in_this_module() -> None:
    """The five scanned paths are disjoint from the finance file set."""
    assert not set(SCANNED) & FINANCE_FILES
    for relative_path in SCANNED:
        assert os.path.isfile(os.path.join(_BACKEND_DIR, relative_path)), relative_path
    assert MIGRATION in SCANNED


# --------------------------------------------------------------------- #
# Runtime half -- the whole flow writes nothing into Financeiro
# --------------------------------------------------------------------- #


def test_the_full_flow_writes_no_finance_row(
    client: TestClient, session: Session
) -> None:
    """settings → rule → policy → infraction → advance to MULTA, and count."""
    staff = make_member(session, profile="ADMINISTRATOR", seed=1)
    lot = make_lot(session)
    resident = make_resident(session, lot, seed=10)

    def _counts() -> tuple[int, int, int]:
        return tuple(
            session.exec(select(func.count()).select_from(model)).one()
            for model in (FinancialTransaction, FinanceCategory, BudgetLine)
        )

    # Virgin world.
    assert _counts() == (0, 0, 0)
    before = _counts()

    assert (
        client.put(
            "/api/v1/infraction-settings",
            json={"condo_fee_amount": 400.0},
            headers=headers(staff),
        ).status_code
        == 200
    )
    rule_id = create_rule(
        client,
        staff,
        steps=[
            {
                "step_order": 1,
                "action": "MULTA",
                "fine_mode": "MULTIPLE",
                "fine_fee_multiplier": 2.0,
            }
        ],
    )
    infraction = create_infraction(
        client,
        staff,
        rule_id=rule_id,
        lot=lot,
        resident=resident,
        occurred_on=date.today(),
    )
    applied = client.post(
        f"/api/v1/infractions/{infraction['id']}/stages",
        json={"note": "Multa aplicada."},
        headers=headers(staff),
    )
    assert applied.status_code == 201, applied.text

    # ER-5: a MULTA records a value, a date and the person it was applied
    # against -- and nothing else anywhere.
    entry = applied.json()["timeline"][0]
    assert entry["fine_amount"] == 800.0
    assert applied.json()["responsible"]["id"] == str(resident.id)
    assert _counts() == before == (0, 0, 0)
