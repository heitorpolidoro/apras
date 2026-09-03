"""Model-layer proof of the multi-tenant partition (APRAS-41).

The tenant boundary is a *schema* decision, and the single thing that makes
it reviewable is that the partition of ``SQLModel.metadata.tables`` into
"directly scoped", "scope inherited from a parent" and "global" is
**exhaustive and disjoint**. This module asserts that arithmetic, so a table
added by a future task cannot silently escape classification.

The list of directly-scoped tables is read out of the Alembic migration
itself (via ``ast``, following the precedent set by
``tests/test_purchase_isolation.py``) rather than re-declared here: the
migration is the artefact that has to be right, and parsing it instead of
importing it avoids the ``backend/alembic/`` package shadowing the real
third-party ``alembic`` library.

Migration ``0028``'s ``_TENANT_SCOPED_TABLES`` literal is **frozen history**:
it records which tables that migration itself scoped, and amending it would
turn a record of what happened into a running total. A directly-scoped table
created *after* ``0028`` therefore has no entry there and registers in
:data:`POST_0028_SCOPED_TABLES` below instead. APRAS-40's
``tenant_subscription`` is the first. Both
``test_partition_of_metadata_is_exhaustive`` and
``test_scoped_tables_have_a_not_null_tenant_id_fk`` union the constant in --
the second one matters just as much as the first, or a post-``0028`` scoped
table would be the only one in the codebase whose ``tenant_id`` column shape
is never checked by anything.
"""

import ast
import os
import uuid

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, SQLModel

from app.models.category import Category
from app.models.lot import Lot
from app.models.plan import Plan  # noqa: F401  -- registers `plan` in metadata
from app.models.role import Role
from app.models.subscription import (  # noqa: F401  -- registers both tables
    SubscriptionChange,
    TenantSubscription,
)
from app.models.tenant import (
    DEFAULT_TENANT_ID,
    DEFAULT_TENANT_NAME,
    Tenant,
    UserTenantLink,
)

_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIGRATION = os.path.join(
    _BACKEND_DIR, "alembic", "versions", "0028_add_tenant_and_membership.py"
)

# The 20 tables that carry no `tenant_id` and derive their tenant through a
# NOT NULL foreign key to a directly-scoped parent (spec §2.2).
INHERITED_TABLES = {
    "taskcomment": "task",
    "taskhistory": "task",
    "task_visible_to_link": "task",
    "user_role_link": "role",
    "user_lot_link": "lot",
    "announcement_media": "announcement",
    "announcement_comment": "announcement",
    "announcement_read_receipt": "announcement",
    "occurrence_timeline": "occurrence",
    "document_download_log": "association_document",
    "project_milestone": "construction_project",
    "project_update": "construction_project",
    "purchase_quote": "purchase_request",
    "purchase_quote_decision": "purchase_request",
    "vote_option": "vote",
    "ballot": "vote",
    "ballot_rejection": "vote",
    "lot_voter_eligibility": "lot",
    "facial_template": "resident",
    "facial_access_event": "access_device",
    # APRAS-40: append-only, and it reaches its tenant through the NOT NULL FK
    # to `tenant_subscription`. A second `tenant_id` copy would be a forgeable
    # source of truth that can disagree with the parent.
    "subscription_change": "tenant_subscription",
}

# Directly-scoped tables created after migration 0028, whose `tenant_id` is
# therefore absent from that migration's frozen `_TENANT_SCOPED_TABLES`
# literal. 0028 records history and must not be edited; new scoped tables
# register here. APRAS-40 is the first.
POST_0028_SCOPED_TABLES = {"tenant_subscription"}

# `user` is a global identity (§1.2); `tenant` and `user_tenant_link` are the
# tenancy tables themselves; `plan` is the install-wide commercial catalogue
# (APRAS-40 §3.1) -- global on purpose, so that "which plan is this
# condominium on" is a comparable answer across the install.
UNSCOPED_TABLES = {"user", "tenant", "user_tenant_link", "plan"}


def _migration_constant(name: str) -> tuple[str, ...]:
    """Read a module-level literal constant out of the 0028 migration.

    Parsed with ``ast`` rather than imported: ``backend/alembic/`` is itself
    an importable package on the test ``pythonpath``, so importing a
    migration module would resolve ``from alembic import op`` against the
    project directory instead of the real library.
    """
    with open(MIGRATION, encoding="utf-8") as handle:
        tree = ast.parse(handle.read(), filename=MIGRATION)
    for node in tree.body:
        targets = []
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        for target in targets:
            if isinstance(target, ast.Name) and target.id == name:
                return tuple(ast.literal_eval(node.value))
    raise AssertionError(f"{name} not found in {MIGRATION}")


#: Tables migration `0028` named under a spelling a later migration changed.
#: `0028` is a historical artefact and must keep saying `user_type`; migration
#: `0032` (IAM F5, APRAS-49 §2.3) renamed that table to `role`. Mapping here
#: is what keeps these cases about *which* tables are scoped rather than about
#: what they were called in 2026-08.
_RENAMED_SINCE_0028: dict[str, str] = {"user_type": "role"}


@pytest.fixture(name="scoped_tables")
def scoped_tables_fixture() -> tuple[str, ...]:
    """`_TENANT_SCOPED_TABLES` from migration 0028, under current spellings."""
    return tuple(
        _RENAMED_SINCE_0028.get(name, name)
        for name in _migration_constant("_TENANT_SCOPED_TABLES")
    )


def test_default_tenant_id_is_the_well_known_uuid():
    """The default tenant id is a fixed, well-known literal, not generated."""
    assert uuid.UUID("00000000-0000-0000-0000-000000000001") == DEFAULT_TENANT_ID
    assert DEFAULT_TENANT_NAME == "Condomínio Padrão"


def test_tenant_defaults(session: Session):
    """A Tenant gets a generated id, is active and carries both timestamps."""
    tenant = Tenant(name="Condomínio Novo")
    session.add(tenant)
    session.commit()
    session.refresh(tenant)

    assert tenant.id is not None
    assert tenant.is_active is True
    assert tenant.created_at is not None
    assert tenant.updated_at is not None


def test_scoped_models_default_to_the_default_tenant(session: Session):
    """Constructing a scoped model without `tenant_id` lands in the default
    tenant — this is what keeps every pre-existing test and every existing
    endpoint working unchanged."""
    category = Category(name="Manutenção")
    role = Role(name="Some Type",)
    lot = Lot(block="A", lot_number="12")
    session.add_all([category, role, lot])
    session.commit()

    assert category.tenant_id == DEFAULT_TENANT_ID
    assert role.tenant_id == DEFAULT_TENANT_ID
    assert lot.tenant_id == DEFAULT_TENANT_ID


def test_user_tenant_link_rejects_duplicate_pair(session: Session, admin_user):
    """`uq_user_tenant_link_user_tenant` rejects the same (user, tenant)
    pair twice."""
    session.add(UserTenantLink(user_id=admin_user.id, tenant_id=DEFAULT_TENANT_ID))
    session.commit()

    session.add(UserTenantLink(user_id=admin_user.id, tenant_id=DEFAULT_TENANT_ID))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_user_tenant_link_allows_multiple_tenants_per_user(
    session: Session, admin_user
):
    """Multi-membership is first class: one user, two tenants."""
    other = Tenant(name="Condomínio B")
    session.add(other)
    session.commit()

    session.add(UserTenantLink(user_id=admin_user.id, tenant_id=DEFAULT_TENANT_ID))
    session.add(UserTenantLink(user_id=admin_user.id, tenant_id=other.id))
    session.commit()

    assert other.id != DEFAULT_TENANT_ID


def test_user_tenant_link_table_name():
    """The join table follows the codebase's snake_case join-table naming."""
    assert UserTenantLink.__tablename__ == "user_tenant_link"
    assert Tenant.__tablename__ == "tenant"


def test_scoped_tables_list_has_27_real_tables(scoped_tables):
    """`_TENANT_SCOPED_TABLES` names 27 distinct, real tables."""
    assert len(scoped_tables) == 27
    assert len(set(scoped_tables)) == 27
    for table in scoped_tables:
        assert table in SQLModel.metadata.tables, f"{table} is not a real table"


def test_scoped_tables_have_a_not_null_tenant_id_fk(scoped_tables):
    """Every directly-scoped table carries a NOT NULL `tenant_id` FK to
    `tenant.id` with a server_default and an `ix_<table>_tenant_id` index.

    `POST_0028_SCOPED_TABLES` is unioned in, or `tenant_subscription` would be
    the first directly-scoped table in the codebase whose column shape nothing
    checks. `tenant_id_field()` supplies all four properties, so the case
    passes as written once it sees the table -- but it has to see it.
    """
    for name in set(scoped_tables) | POST_0028_SCOPED_TABLES:
        table = SQLModel.metadata.tables[name]
        column = table.columns.get("tenant_id")
        assert column is not None, f"{name} has no tenant_id column"
        assert column.nullable is False, f"{name}.tenant_id is nullable"
        assert column.server_default is not None, f"{name}.tenant_id lacks a default"
        targets = {fk.target_fullname for fk in column.foreign_keys}
        assert targets == {"tenant.id"}, f"{name}.tenant_id points at {targets}"
        assert all(fk.ondelete == "RESTRICT" for fk in column.foreign_keys)
        index_names = {index.name for index in table.indexes}
        assert f"ix_{name}_tenant_id" in index_names, f"{name} lacks a tenant index"


def test_inherited_tables_have_no_tenant_id_but_a_not_null_parent_fk():
    """The 20 inherited tables must NOT be denormalised with a `tenant_id`;
    each proves its scope through a NOT NULL FK to its listed parent."""
    for name, parent in INHERITED_TABLES.items():
        table = SQLModel.metadata.tables[name]
        assert "tenant_id" not in table.columns, f"{name} was denormalised"
        parent_columns = [
            column
            for column in table.columns
            if any(fk.column.table.name == parent for fk in column.foreign_keys)
        ]
        assert parent_columns, f"{name} has no FK to {parent}"
        assert any(
            column.nullable is False for column in parent_columns
        ), f"{name}'s FK to {parent} is nullable"


def test_partition_of_metadata_is_exhaustive(scoped_tables):
    """direct + inherited + unscoped == every table: 28 + 21 + 4 == 53."""
    direct = set(scoped_tables) | POST_0028_SCOPED_TABLES
    partition = direct | set(INHERITED_TABLES) | UNSCOPED_TABLES
    assert partition == set(SQLModel.metadata.tables)
    assert not direct & set(INHERITED_TABLES)
    assert not direct & UNSCOPED_TABLES
    assert len(direct) == 28
    assert len(INHERITED_TABLES) == 21
    assert len(UNSCOPED_TABLES) == 4
    assert len(direct) + len(INHERITED_TABLES) + len(UNSCOPED_TABLES) == 53


def test_user_stays_global():
    """A user is one identity across tenants: no `tenant_id`, and `email`
    and `cpf` stay globally unique."""
    user_table = SQLModel.metadata.tables["user"]
    assert "tenant_id" not in user_table.columns
    unique_indexed = {
        index.name for index in user_table.indexes if index.unique
    }
    assert {"ix_user_email", "ix_user_cpf"} <= unique_indexed
