"""Mechanical proof that the purchase-quotation module (APRAS-37) is isolated.

The no-integration constraint from the spec is a hard requirement, not a
preference: choosing a quote must create no ``FinancialTransaction``, no
``InventoryMovement``, no ``Asset`` and no link to a ``ConstructionProject``.

This module proves it two ways:

* **Statically**, by parsing each of the five files of the module with
  ``ast.parse()`` and inspecting import nodes and ``op.*`` / ``sa.ForeignKey*``
  call arguments. A raw substring scan is deliberately *not* used: it would be
  both a false positive (the mandatory ``down_revision`` identifier
  ``0026_add_asset_and_inventory``, and the unrelated legitimate module
  ``app.models.media_asset``) and a false negative (``from app.models import
  Asset`` contains no lowercase ``asset``). Because the scan only reads import
  nodes and call arguments, the module docstring and the ``revision`` /
  ``down_revision`` / ``branch_labels`` / ``depends_on`` assignments are outside
  its reach by construction — so the migration is scanned in full, never
  excluded. A separate positive assertion pins the chain link.
* **At runtime**, by driving the whole flow through the API and asserting the
  four foreign tables stay empty.
"""

import ast
import os
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func
from sqlmodel import Session, select

from app.core.security import create_access_token
from app.models.asset import Asset, InventoryMovement
from app.models.enums import UserRole
from app.models.finance import FinancialTransaction
from app.models.project import ConstructionProject
from app.models.user import User

_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MIGRATION = "alembic/versions/0027_add_purchase_quotation.py"

SCANNED = [
    "app/models/purchase.py",
    "app/schemas/purchase.py",
    "app/services/purchase_service.py",
    "app/api/v1/endpoints/purchases.py",
    MIGRATION,
]

FORBIDDEN_MODULES = {
    "app.models.finance",
    "app.models.asset",
    "app.models.project",
    "app.schemas.finance",
    "app.schemas.asset",
    "app.schemas.project",
    "app.services.finance_service",
    "app.services.asset_service",
    "app.services.project_service",
    "app.api.v1.endpoints.finance",
    "app.api.v1.endpoints.assets",
    "app.api.v1.endpoints.inventory_movements",
    "app.api.v1.endpoints.projects",
}

FORBIDDEN_NAMES = {
    "FinanceCategory",
    "BudgetLine",
    "FinancialTransaction",
    "Asset",
    "InventoryMovement",
    "ConstructionProject",
    "ProjectMilestone",
    "ProjectUpdate",
    "FinanceService",
    "AssetService",
    "ProjectService",
}

AGGREGATE_PACKAGES = {"app.models", "app.schemas", "app.services"}

ALLOWED_TABLES = {
    "purchase_request",
    "purchase_quote",
    "purchase_quote_decision",
    "user",
}

# op.* / sa.* calls whose *first* positional argument is the table name.
# `op.execute` is included on purpose: raw SQL is not statically checkable, so
# its literal argument is treated as a "table" and fails the subset check
# below, while a non-literal argument trips the assertion. Either way, raw SQL
# cannot slip past the scan — and this migration needs none.
_FIRST_ARG_TABLE_CALLS = {
    "op.create_table",
    "op.drop_table",
    "op.add_column",
    "op.drop_column",
    "op.alter_column",
    "op.execute",
    "op.rename_table",
}
# op.* calls whose table is the 2nd positional arg or the `table_name=` kwarg.
_INDEX_CALLS = {"op.create_index", "op.drop_index"}


def _source(relative_path: str) -> str:
    with open(os.path.join(_BACKEND_DIR, relative_path), encoding="utf-8") as handle:
        return handle.read()


def _tree(relative_path: str) -> ast.Module:
    return ast.parse(_source(relative_path), filename=relative_path)


def _imported_modules(tree: ast.Module) -> set[str]:
    """Full dotted module paths imported by the file (absolute imports only)."""
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            modules.add(node.module)
    return modules


def _names_from_aggregate_packages(tree: ast.Module) -> set[str]:
    """Names imported through ``app.models`` / ``app.schemas`` / ``app.services``."""
    names: set[str] = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.ImportFrom)
            and node.level == 0
            and node.module in AGGREGATE_PACKAGES
        ):
            names.update(alias.name for alias in node.names)
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
    """``"user.id"`` -> ``"user"``."""
    return qualified.split(".", 1)[0]


def _tables_touched(tree: ast.Module) -> set[str]:
    """Table names appearing as arguments of DDL / foreign-key calls."""
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
# Rule 1 — no forbidden module imports
# --------------------------------------------------------------------- #


@pytest.mark.parametrize("relative_path", SCANNED)
def test_no_forbidden_module_imports(relative_path: str) -> None:
    modules = _imported_modules(_tree(relative_path))
    offenders = modules & FORBIDDEN_MODULES
    assert not offenders, (
        f"{relative_path} imports forbidden module(s): {sorted(offenders)}"
    )


def test_media_asset_is_not_treated_as_forbidden() -> None:
    """`app.models.media_asset` must survive the rule-1 comparison."""
    tree = ast.parse("from app.models.media_asset import MediaAsset")
    assert not _imported_modules(tree) & FORBIDDEN_MODULES


def test_rule_one_actually_catches_a_violation() -> None:
    """The scan is not vacuous: a real forbidden import must be detected."""
    tree = ast.parse("from app.models.asset import Asset")
    assert _imported_modules(tree) & FORBIDDEN_MODULES == {"app.models.asset"}


# --------------------------------------------------------------------- #
# Rule 2 — no forbidden names re-exported through the aggregate packages
# --------------------------------------------------------------------- #


@pytest.mark.parametrize("relative_path", SCANNED)
def test_no_forbidden_names_via_aggregate_packages(relative_path: str) -> None:
    names = _names_from_aggregate_packages(_tree(relative_path))
    offenders = names & FORBIDDEN_NAMES
    assert not offenders, (
        f"{relative_path} imports forbidden name(s) through an aggregate "
        f"package: {sorted(offenders)}"
    )


def test_rule_two_actually_catches_a_violation() -> None:
    """`from app.models import Asset` has no lowercase 'asset' — rule 2 sees it."""
    tree = ast.parse("from app.models import Asset, InventoryMovement")
    assert _names_from_aggregate_packages(tree) & FORBIDDEN_NAMES == {
        "Asset",
        "InventoryMovement",
    }


# --------------------------------------------------------------------- #
# Rule 3 — the migration touches only the module's own tables
# --------------------------------------------------------------------- #


def test_migration_touches_only_allowed_tables() -> None:
    tables = _tables_touched(_tree(MIGRATION))
    assert tables, "The scan found no tables at all — it is not doing its job."
    assert tables <= ALLOWED_TABLES, (
        f"Migration touches foreign table(s): {sorted(tables - ALLOWED_TABLES)}"
    )
    assert {"purchase_request", "purchase_quote", "purchase_quote_decision"} <= tables


def test_rule_three_actually_catches_a_violation() -> None:
    """A cross-module FK declared the way this repo declares them is caught."""
    tree = ast.parse(
        'sa.ForeignKeyConstraint(["performed_by_id"], ["asset.id"], '
        'ondelete="RESTRICT")'
    )
    assert _tables_touched(tree) - ALLOWED_TABLES == {"asset"}


def test_rule_three_catches_op_add_column_and_create_foreign_key() -> None:
    tree = ast.parse(
        'op.add_column("financial_transaction", sa.Column("x", sa.Uuid()))\n'
        'op.create_foreign_key("fk", "asset", "purchase_quote", ["a"], ["b"])\n'
        'op.create_index("ix", "inventory_movement", ["a"])\n'
        'op.drop_index("ix", table_name="construction_project")\n'
        'sa.ForeignKey("asset.id")\n'
    )
    assert _tables_touched(tree) - ALLOWED_TABLES == {
        "financial_transaction",
        "asset",
        "inventory_movement",
        "construction_project",
    }


def test_rule_three_rejects_raw_sql_execute() -> None:
    """Raw SQL is not statically checkable, so it can never pass the scan."""
    literal_sql = ast.parse('op.execute("UPDATE asset SET x = 1")')
    assert _tables_touched(literal_sql) - ALLOWED_TABLES

    with pytest.raises(AssertionError):
        _tables_touched(ast.parse("op.execute(some_statement)"))


def test_migration_chain_link_is_explicit() -> None:
    """The exempted `down_revision` assignment is asserted positively."""
    module = {}
    tree = _tree(MIGRATION)
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Name) and isinstance(
                    node.value, ast.Constant
                ):
                    module[target.id] = node.value.value

    assert module["revision"] == "0027_add_purchase_quotation"
    assert module["down_revision"] == "0026_add_asset_and_inventory"


def test_every_scanned_file_exists_and_the_migration_is_included() -> None:
    for relative_path in SCANNED:
        assert os.path.isfile(os.path.join(_BACKEND_DIR, relative_path)), relative_path
    assert MIGRATION in SCANNED


# --------------------------------------------------------------------- #
# Runtime half — the flow writes nothing outside its own tables
# --------------------------------------------------------------------- #


def _headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


@pytest.fixture
def board_user(session: Session) -> User:
    user = User(
        id=uuid.uuid4(),
        email="board_iso@test.com",
        full_name="Board Member",
        hashed_password="hash",
        role=UserRole.DIRECTOR,
        cpf="99999999999",
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def test_full_flow_writes_nothing_into_finance_inventory_assets_or_projects(
    client: TestClient, session: Session, board_user: User
) -> None:
    request_id = client.post(
        "/api/v1/purchase-requests",
        json={
            "title": "Compra de bombas",
            "description": "Duas bombas submersas",
            "general_notes": "Verba do fundo de obras (apenas anotação)",
        },
        headers=_headers(board_user),
    ).json()["id"]

    first = client.post(
        f"/api/v1/purchase-requests/{request_id}/quotes",
        json={
            "supplier_name": "Hidráulica Central",
            "unit_price": 1500.0,
            "quantity": 2,
            "extra_fields": [{"label": "Prazo", "value": "20 dias"}],
        },
        headers=_headers(board_user),
    )
    assert first.status_code == 201
    second = client.post(
        f"/api/v1/purchase-requests/{request_id}/quotes",
        json={"supplier_name": "Bombas & Cia", "unit_price": 1200.0, "quantity": 2},
        headers=_headers(board_user),
    )
    assert second.status_code == 201

    decision = client.post(
        f"/api/v1/purchase-requests/{request_id}/decision",
        json={
            "quote_id": second.json()["id"],
            "justification": "Menor preço e mesmo prazo de entrega.",
        },
        headers=_headers(board_user),
    )
    assert decision.status_code == 201

    for model in (FinancialTransaction, InventoryMovement, Asset, ConstructionProject):
        count = session.exec(select(func.count()).select_from(model)).one()
        assert count == 0, f"{model.__name__} must stay empty after a purchase flow."
