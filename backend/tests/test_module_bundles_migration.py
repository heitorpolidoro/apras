"""The 0008 backfill (APRAS-128): a split becomes whole, upward, idempotently.

Runs on SQLite against the revision's own `backfill(bind)`; the revision is
loaded by path with a stub `alembic` because the repo's `alembic/` directory
shadows the library under `pythonpath = .`. The real-Postgres replay lives in
`test_migrations_postgres.py`.
"""

import importlib.util
import pathlib
import sys
from types import SimpleNamespace

import pytest
import sqlalchemy as sa

from app.core.permissions import MODULE_BUNDLES

_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "alembic"
    / "versions"
    / "0008_module_bundles_backfill.py"
)


@pytest.fixture(name="migration")
def migration_fixture(monkeypatch):
    monkeypatch.setitem(
        sys.modules,
        "alembic",
        SimpleNamespace(op=SimpleNamespace(get_bind=lambda: None)),
    )
    spec = importlib.util.spec_from_file_location("rev_0008", _PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(name="conn")
def conn_fixture():
    engine = sa.create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(
            sa.text("CREATE TABLE tenant (id INTEGER, disabled_modules JSON)")
        )
        connection.execute(
            sa.text("CREATE TABLE plan (id INTEGER, included_modules JSON)")
        )
        connection.execute(
            sa.text(
                "CREATE TABLE tenant_subscription (id INTEGER, courtesy_modules JSON)"
            )
        )
        yield connection
    engine.dispose()


def _table(name, column):
    return sa.table(name, sa.column("id"), sa.column(column, sa.JSON()))


def _put(conn, table, column, value):
    conn.execute(sa.insert(_table(table, column)).values(id=1, **{column: value}))


def _get(conn, table, column):
    return conn.execute(sa.select(_table(table, column).c[column])).scalar_one()


def test_the_frozen_bundles_equal_the_live_declaration(migration):
    assert set(migration.BUNDLES) == set(MODULE_BUNDLES.values())


def test_a_split_tenant_gets_the_missing_members_switched_on(migration, conn):
    _put(conn, "tenant", "disabled_modules", ["categories", "finance"])

    migration.backfill(conn)

    assert _get(conn, "tenant", "disabled_modules") == ["finance"]


def test_a_split_plan_and_courtesy_gain_the_missing_members(migration, conn):
    _put(conn, "plan", "included_modules", ["tasks", "gate", "finance"])
    _put(conn, "tenant_subscription", "courtesy_modules", ["assets"])

    migration.backfill(conn)

    assert set(_get(conn, "plan", "included_modules")) == {
        "finance",
        "tasks",
        "categories",
        "visitors",
        "authorizations",
        "gate",
    }
    assert set(_get(conn, "tenant_subscription", "courtesy_modules")) == {
        "assets",
        "inventory",
    }


def test_whole_bundles_are_untouched_and_the_backfill_is_idempotent(migration, conn):
    whole_off = ["tasks", "categories", "gate", "visitors", "authorizations"]
    _put(conn, "tenant", "disabled_modules", whole_off)
    _put(conn, "plan", "included_modules", ["assets", "inventory"])
    _put(conn, "tenant_subscription", "courtesy_modules", [])

    migration.backfill(conn)
    migration.backfill(conn)

    assert _get(conn, "tenant", "disabled_modules") == whole_off
    assert _get(conn, "plan", "included_modules") == ["assets", "inventory"]
    assert _get(conn, "tenant_subscription", "courtesy_modules") == []


def test_upgrade_runs_the_backfill_and_downgrade_is_a_no_op(migration, monkeypatch):
    calls = []
    monkeypatch.setattr(migration, "backfill", calls.append)
    monkeypatch.setattr(migration.op, "get_bind", lambda: "bind")

    migration.upgrade()
    migration.downgrade()

    assert calls == ["bind"]
