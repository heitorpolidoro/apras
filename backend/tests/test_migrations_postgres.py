"""Postgres-only regression test for the ``userrole`` enum (APRAS-27).

SQLite (used by the rest of the test suite via ``conftest.py``) stores enum
columns as a plain ``VARCHAR`` with no native constraint, so it cannot catch
``psycopg2.errors.InvalidTextRepresentation``-style failures that only occur
against a real PostgreSQL ``userrole`` enum type. These tests exercise the
Alembic migration chain against a real Postgres instance to prove that
``RESIDENT`` (added by migration ``0014_add_resident_userrole``) and
``PORTEIRO`` (added by migration ``0020_add_porteiro_userrole``, APRAS-12)
are actually insertable.

They are skipped automatically unless ``TEST_POSTGRES_URL`` points at a
reachable Postgres database, e.g. via a throwaway Docker container:

    docker run -d --rm -p 55432:5432 \\
        -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=apras_test \\
        postgres:16-alpine

    TEST_POSTGRES_URL=postgresql://postgres:postgres@localhost:55432/apras_test \\
        SECRET_KEY=test uv run pytest tests/test_migrations_postgres.py -v
"""

import os
import subprocess
import sys
import uuid

import pytest
from sqlalchemy import create_engine, text

TEST_POSTGRES_URL = os.environ.get("TEST_POSTGRES_URL")
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

pytestmark = pytest.mark.skipif(
    not TEST_POSTGRES_URL,
    reason=(
        "TEST_POSTGRES_URL not set; skipping Postgres-only userrole enum "
        "regression test (requires a real Postgres instance, e.g. via Docker). "
        "SQLite cannot verify native enum constraints."
    ),
)


def _run_alembic(*args: str) -> None:
    """Run the alembic CLI in a subprocess.

    Invoked as the ``alembic`` console-script entry point (rather than
    ``python -m alembic`` or importing ``alembic.command`` in-process)
    because this project's own ``backend/alembic/`` migrations directory is
    itself an importable package (per ``pytest.ini``'s ``pythonpath = .``),
    which shadows the real third-party ``alembic`` library whenever the
    current working directory ends up on ``sys.path[0]`` (as happens both
    for in-process imports and for ``python -m alembic``).
    """
    result = _alembic(*args)
    assert result.returncode == 0, (
        f"alembic {' '.join(args)} failed:\nstdout={result.stdout}\nstderr={result.stderr}"
    )


def _alembic(*args: str) -> subprocess.CompletedProcess:
    """The module's **only** subprocess call site.

    `_run_alembic` asserts success; the two guard cases of APRAS-49 §7.0 need
    the *failure*, so they read the `CompletedProcess` this returns instead
    of going around it.
    """
    alembic_bin = os.path.join(os.path.dirname(sys.executable), "alembic")
    env = {
        **os.environ,
        "POSTGRES_URL": TEST_POSTGRES_URL,
        "SECRET_KEY": "test-migration-secret",
    }
    return subprocess.run(
        [alembic_bin, *args],
        cwd=_BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.fixture(scope="module")
def migrated_pg_engine():
    """Reset the target database and run all Alembic migrations to head."""
    engine = create_engine(TEST_POSTGRES_URL)
    try:
        with engine.begin() as conn:
            conn.execute(text("DROP SCHEMA public CASCADE"))
            conn.execute(text("CREATE SCHEMA public"))
    except Exception as exc:  # pragma: no cover - environment-dependent
        pytest.skip(f"Could not reach TEST_POSTGRES_URL ({exc})")

    _run_alembic("upgrade", "head")

    yield engine
    engine.dispose()


def _userrole_labels(engine) -> set[str]:
    with engine.connect() as conn:
        return set(
            conn.execute(
                text(
                    "SELECT enumlabel FROM pg_enum e "
                    "JOIN pg_type t ON e.enumtypid = t.oid "
                    "WHERE t.typname = 'userrole'"
                )
            )
            .scalars()
            .all()
        )


def test_the_userrole_type_is_absent_at_head(isolated_pg_engine):
    """ER-2: migration `0033` drops the Postgres type, not only the column.

    APRAS-27's lesson runs in both directions: a Python enum *deletion* is
    not proof the type left the database. These four cases used to assert
    that `RESIDENT` and `PORTEIRO` were insertable; they now assert the type
    is gone at head and comes back on `downgrade -1`, which is the same kind
    of statement about the same object.
    """
    assert _userrole_labels(isolated_pg_engine) == set()
    with isolated_pg_engine.connect() as conn:
        assert (
            conn.execute(
                text("SELECT to_regtype('userrole')")
            ).scalar()
            is None
        )


def test_the_userrole_type_comes_back_with_all_six_labels_on_downgrade(
    isolated_pg_engine,
):
    """`downgrade -1` recreates the type with the six labels `0003`/`0014`/`0020` built."""
    _run_alembic("downgrade", "-1")

    assert _userrole_labels(isolated_pg_engine) == {
        "ADMINISTRATOR",
        "DIRECTOR",
        "MANAGER",
        "GUEST",
        "RESIDENT",
        "PORTEIRO",
    }

    _run_alembic("upgrade", "head")
    assert _userrole_labels(isolated_pg_engine) == set()


def test_the_user_role_column_is_absent_at_head_and_insertable_after_downgrade(
    isolated_pg_engine,
):
    """The column half of the same statement, both directions.

    Inserting `role='PORTEIRO'` was the APRAS-12 regression test; after the
    downgrade it must work again, because a rollback that leaves the column
    uninsertable is not a rollback.
    """
    with isolated_pg_engine.connect() as conn:
        columns = set(
            conn.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name = 'user'"
                )
            )
            .scalars()
            .all()
        )
    assert "role" not in columns

    _run_alembic("downgrade", "-1")

    for value, cpf in (("PORTEIRO", "12345678909"), ("RESIDENT", "52998224725")):
        user_id = uuid.uuid4()
        with isolated_pg_engine.begin() as conn:
            conn.execute(
                text(
                    'INSERT INTO "user" '
                    "(id, email, hashed_password, full_name, role, is_active, cpf) "
                    "VALUES (:id, :email, 'x', :name, :role, true, :cpf)"
                ),
                {
                    "id": user_id,
                    "email": f"{value.lower()}-{user_id}@test.com",
                    "name": f"{value} Regression Test",
                    "role": value,
                    "cpf": cpf,
                },
            )
        with isolated_pg_engine.connect() as conn:
            stored = conn.execute(
                text('SELECT role FROM "user" WHERE id = :id'), {"id": user_id}
            ).scalar_one()
        assert stored == value


# ---------------------------------------------------------------------------
# 0018_add_role_to_user_type (APRAS-9) – seeded role-linked Role rows
# ---------------------------------------------------------------------------


#: The revision at which `user_type.role` exists. These four cases are
#: statements about migration `0018` — a historical artefact — so they are
#: run *there* rather than at head. Migration `0033` dropped the column and
#: `0032` renamed the table; asserting `0018`'s behaviour against head would
#: be asserting `0033`'s.
AT_0018 = "0018_add_role_to_user_type"


@pytest.fixture
def pg_engine_at_0018(migrated_pg_engine):
    _reset_to(migrated_pg_engine, AT_0018)
    yield migrated_pg_engine
    _reset_to(migrated_pg_engine, "head")


def test_legacy_roles_exist_in_every_tenant(isolated_pg_engine):
    """The head-level successor of `test_user_type_role_seeds_five_rows`.

    `0018` seeded five rows in the default tenant; `0020` added PORTEIRO and
    `0033` created whatever any tenant was still missing (§7.1). What matters
    at head is the invariant that replaced "five seeded rows": **every**
    tenant has all six historically-named rows, and none of them is special.
    """
    with isolated_pg_engine.connect() as conn:
        tenants = conn.execute(text("SELECT id FROM tenant")).scalars().all()
        rows = conn.execute(text("SELECT tenant_id, name FROM role")).all()

    by_tenant: dict[str, set[str]] = {}
    for row in rows:
        by_tenant.setdefault(str(row.tenant_id), set()).add(row.name)

    expected = {
        "Administrador (papel)",
        "Diretor (papel)",
        "Gerente (papel)",
        "Convidado (papel)",
        "Morador (papel)",
        "Porteiro (papel)",
    }
    assert tenants
    for tenant_id in tenants:
        assert expected <= by_tenant.get(str(tenant_id), set()), tenant_id


def test_0018_seeds_five_rows(pg_engine_at_0018):
    """Exactly one `user_type` row per `UserRole` value, at `0018` itself."""
    with pg_engine_at_0018.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT role, name, allowed_menus FROM user_type "
                "WHERE role IS NOT NULL"
            )
        ).all()

    assert len(rows) == 5
    assert {row.role for row in rows} == {
        "ADMINISTRATOR",
        "DIRECTOR",
        "MANAGER",
        "GUEST",
        "RESIDENT",
    }
    for row in rows:
        assert row.allowed_menus == []
        assert "(papel)" in row.name


def test_0018_unique_constraint_rejects_a_duplicate_role(pg_engine_at_0018):
    with pytest.raises(Exception, match="duplicate key|unique constraint"):
        with pg_engine_at_0018.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO user_type (id, name, allowed_menus, role) "
                    "VALUES (:id, 'Duplicate Director', '[]', 'DIRECTOR')"
                ),
                {"id": uuid.uuid4()},
            )


def test_0018_unique_constraint_allows_multiple_null_roles(pg_engine_at_0018):
    """A UNIQUE constraint never treats two NULLs as duplicates of each other."""
    id_a, id_b = uuid.uuid4(), uuid.uuid4()
    with pg_engine_at_0018.begin() as conn:
        for row_id, name in ((id_a, "Admin Type A"), (id_b, "Admin Type B")):
            conn.execute(
                text(
                    "INSERT INTO user_type (id, name, allowed_menus, role) "
                    "VALUES (:id, :name, '[]', NULL)"
                ),
                {"id": row_id, "name": f"{name} {row_id}"},
            )

    with pg_engine_at_0018.connect() as conn:
        count = conn.execute(
            text("SELECT count(*) FROM user_type WHERE id = :a OR id = :b"),
            {"a": id_a, "b": id_b},
        ).scalar_one()
    assert count == 2


def test_0018_downgrade_removes_the_seeded_rows_only(pg_engine_at_0018):
    """Downgrading past `0018` removes the five seeded rows and the column.

    Targets the explicit revision id rather than a relative "-N": later
    migrations keep getting chained on top of `0018`, so a relative offset
    silently drifts out of sync with head every time that happens.
    """
    survivor_id = uuid.uuid4()
    survivor_name = f"Survivor {survivor_id}"
    with pg_engine_at_0018.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO user_type (id, name, allowed_menus, role) "
                "VALUES (:id, :name, '[]', NULL)"
            ),
            {"id": survivor_id, "name": survivor_name},
        )

    _run_alembic("downgrade", "0017_add_user_type_allowed_menus")

    with pg_engine_at_0018.connect() as conn:
        columns = (
            conn.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name = 'user_type'"
                )
            )
            .scalars()
            .all()
        )
        remaining_names = (
            conn.execute(text("SELECT name FROM user_type")).scalars().all()
        )

    assert "role" not in columns
    assert survivor_name in remaining_names
    assert not any("(papel)" in name for name in remaining_names)


def test_downgrading_past_0020_is_a_safe_noop(migrated_pg_engine):
    """Postgres has no `DROP VALUE` for enums, so `0020`'s downgrade is a no-op.

    The precedent is `0003_add_guest_to_userrole_enum` /
    `0014_add_resident_userrole`. Retargeted from a relative "-1" to `0020`'s
    own `down_revision` by IAM F5: head is `0033` now, and "-1" from head
    downgrades a migration that has nothing to do with the enum labels.
    """
    _reset_to(migrated_pg_engine, "0020_add_porteiro_userrole")
    _run_alembic("downgrade", "0019_drop_block_lot_from_user")

    assert {"RESIDENT", "PORTEIRO"} <= _userrole_labels(migrated_pg_engine)

    _run_alembic("upgrade", "head")


# ---------------------------------------------------------------------------
# 0024_task_visible_to_m2m (APRAS-11) – Task.visible_to becomes many-to-many
# ---------------------------------------------------------------------------


def test_task_visible_to_id_backfilled_into_join_table(migrated_pg_engine):
    """A task's existing single `visible_to_id` becomes a one-row
    `task_visible_to_link` entry after upgrading past 0021, and the
    `visible_to_id` column itself is dropped."""
    _run_alembic("downgrade", "0023_add_reservation_tables")

    role_id = uuid.uuid4()
    user_id = uuid.uuid4()
    task_id = uuid.uuid4()
    with migrated_pg_engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO user_type (id, name, allowed_menus) "
                "VALUES (:id, :name, '[]')"
            ),
            {"id": role_id, "name": f"Migration Type {role_id}"},
        )
        conn.execute(
            text(
                'INSERT INTO "user" '
                "(id, email, hashed_password, full_name, role, is_active, cpf) "
                "VALUES (:id, :email, 'x', 'Migration Test', 'ADMINISTRATOR', "
                "true, :cpf)"
            ),
            {
                "id": user_id,
                "email": f"migration-{user_id}@test.com",
                # Derived from the row's own uuid (rather than a fixed
                # literal) so it can never collide with a cpf used by an
                # earlier test in this module, regardless of test order.
                "cpf": str(user_id.int % 10**11).zfill(11),
            },
        )
        conn.execute(
            text(
                "INSERT INTO task "
                "(id, title, status, priority, is_deleted, created_by_id, "
                "visible_to_id, created_at, updated_at) "
                "VALUES (:id, 'Migration Task', 'PENDING', 'MEDIUM', false, "
                ":created_by_id, :visible_to_id, now(), now())"
            ),
            {"id": task_id, "created_by_id": user_id, "visible_to_id": role_id},
        )

    _run_alembic("upgrade", "head")

    with migrated_pg_engine.connect() as conn:
        links = conn.execute(
            text(
                "SELECT task_id, role_id FROM task_visible_to_link "
                "WHERE task_id = :task_id"
            ),
            {"task_id": task_id},
        ).all()
        columns = (
            conn.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name = 'task'"
                )
            )
            .scalars()
            .all()
        )

    assert len(links) == 1
    assert links[0].role_id == role_id
    assert "visible_to_id" not in columns


def test_task_visible_to_downgrade_backfills_one_arbitrary_target(migrated_pg_engine):
    """Downgrading after a task has multiple `task_visible_to_link` targets
    re-adds `visible_to_id` populated with one arbitrary target — lossy by
    design (documented on the migration's downgrade), acceptable since this
    is a downgrade path, not a normal operation."""
    task_id = uuid.uuid4()
    creator_id = uuid.uuid4()
    type_a, type_b = uuid.uuid4(), uuid.uuid4()

    with migrated_pg_engine.begin() as conn:
        conn.execute(
            text(
                'INSERT INTO "user" '
                "(id, email, hashed_password, full_name, is_active, cpf) "
                "VALUES (:id, :email, 'x', 'Downgrade Test', true, :cpf)"
            ),
            {
                "id": creator_id,
                "email": f"downgrade-{creator_id}@test.com",
                "cpf": str(creator_id.int % 10**11).zfill(11),
            },
        )
        conn.execute(
            text(
                "INSERT INTO task "
                "(id, title, status, priority, is_deleted, created_by_id, "
                "created_at, updated_at) "
                "VALUES (:id, 'Downgrade Task', 'PENDING', 'MEDIUM', false, "
                ":created_by_id, now(), now())"
            ),
            {"id": task_id, "created_by_id": creator_id},
        )
        for type_id, name in ((type_a, "Type A"), (type_b, "Type B")):
            conn.execute(
                text("INSERT INTO role (id, name) VALUES (:id, :name)"),
                {"id": type_id, "name": f"{name} {type_id}"},
            )
        conn.execute(
            text(
                "INSERT INTO task_visible_to_link (task_id, role_id) "
                "VALUES (:task_id, :type_a), (:task_id, :type_b)"
            ),
            {"task_id": task_id, "type_a": type_a, "type_b": type_b},
        )

    _run_alembic("downgrade", "0023_add_reservation_tables")

    with migrated_pg_engine.connect() as conn:
        visible_to_id = conn.execute(
            text("SELECT visible_to_id FROM task WHERE id = :id"), {"id": task_id}
        ).scalar_one()

    assert visible_to_id in (type_a, type_b)

    # Restore head so other tests in this module are unaffected by ordering.
    _run_alembic("upgrade", "head")


# ---------------------------------------------------------------------------
# 0028_add_tenant_and_membership (APRAS-41) – tenancy schema and backfill
# ---------------------------------------------------------------------------
#
# Isolation, and why it is mandatory here rather than a nicety:
# ``migrated_pg_engine`` is module-scoped and its consumers commit, so every
# case in this module otherwise shares one database and inherits whatever an
# earlier case left behind. Three of the six cases below are impossible on
# that fixture:
#
# * ``test_tenant_table_has_exactly_one_default_row`` asserts
#   ``count(*) FROM tenant == 1`` — order-dependent the moment any sibling
#   commits a second tenant.
# * ``test_existing_rows_are_backfilled`` must seed rows *at revision 0027*
#   and then upgrade, but the shared database is already at ``head``.
# * ``test_scoped_uniques_are_per_tenant`` commits two ``category`` rows with
#   the same name; ``test_downgrade_removes_tenant_schema`` then has to
#   restore the **global** unique index ``ix_category_name`` over exactly
#   those duplicates, which real Postgres refuses with
#   ``could not create unique index "ix_category_name"``.
#
# The two fixtures below reset the ``public`` schema on setup *and* teardown,
# so no execution order is assumed in either direction, and teardown always
# leaves the database at ``head`` — exactly the state ``migrated_pg_engine``'s
# own setup produces, so the pre-existing cases are unaffected. Do not
# optimise the resets away: a full ``base -> head`` run costs ~2 s, and this
# whole module is skipped unless ``TEST_POSTGRES_URL`` is set.

DEFAULT_TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")

# The 27 directly tenant-scoped tables (spec §2.1).
TENANT_SCOPED_TABLES = (
    "task",
    "category",
    "role",
    "lot",
    "resident",
    "visitor",
    "visitor_authorization",
    "access_log",
    "announcement",
    "document_folder",
    "association_document",
    "occurrence",
    "package",
    "reservable_space",
    "space_reservation",
    "construction_project",
    "purchase_request",
    "asset",
    "inventory_movement",
    "access_device",
    "finance_category",
    "budget_line",
    "financial_transaction",
    "assembly",
    "vote",
    "feedback",
    "media_asset",
)

# The 20 tables that inherit their tenant through a NOT NULL parent FK and
# must therefore *not* carry a tenant_id (spec §2.2). Asserting the absence
# is what stops a later drive-by from denormalising `ballot`.
TENANT_INHERITED_TABLES = (
    "taskcomment",
    "taskhistory",
    "task_visible_to_link",
    "user_role_link",
    "user_lot_link",
    "announcement_media",
    "announcement_comment",
    "announcement_read_receipt",
    "occurrence_timeline",
    "document_download_log",
    "project_milestone",
    "project_update",
    "purchase_quote",
    "purchase_quote_decision",
    "vote_option",
    "ballot",
    "ballot_rejection",
    "lot_voter_eligibility",
    "facial_template",
    "facial_access_event",
)


def _current_revision(engine) -> str:
    """Read the applied revision straight out of ``alembic_version``.

    Queried rather than scraped from ``alembic current``'s stdout, which
    mixes INFO logging with the revision and changes format between alembic
    versions.
    """
    with engine.connect() as conn:
        return conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()


def _reset_to(engine, target: str) -> None:
    """Hard-reset ``public`` and re-run the migration chain up to ``target``."""
    engine.dispose()  # drop pooled connections before the DDL
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    _run_alembic("upgrade", target)


@pytest.fixture
def isolated_pg_engine(migrated_pg_engine):
    """A database at ``head`` containing nothing but what the migrations seed.

    Resets on setup *and* on teardown, so a case using it neither inherits
    another case's committed rows nor leaks its own — in either direction,
    and regardless of execution order.
    """
    _reset_to(migrated_pg_engine, "head")
    yield migrated_pg_engine
    _reset_to(migrated_pg_engine, "head")


@pytest.fixture
def pg_engine_at_0027(migrated_pg_engine):
    """Same reset, stopped one revision *before* 0028 so the test can seed
    pre-migration rows and drive ``upgrade head`` itself."""
    _reset_to(migrated_pg_engine, "0027_add_purchase_quotation")
    yield migrated_pg_engine
    _reset_to(migrated_pg_engine, "head")


def test_tenant_table_has_exactly_one_default_row(isolated_pg_engine):
    """The migration seeds exactly one tenant, whose id is the well-known
    default — never a generated one, since the model default, the column
    server_default and the backfill all have to agree on it without a
    lookup."""
    with isolated_pg_engine.connect() as conn:
        rows = conn.execute(text("SELECT id, name, is_active FROM tenant")).all()

    assert len(rows) == 1
    assert rows[0].id == DEFAULT_TENANT_ID
    assert rows[0].name == "Condomínio Padrão"
    assert rows[0].is_active is True


def test_every_scoped_table_has_not_null_tenant_id(isolated_pg_engine):
    """All 27 directly-scoped tables carry a NOT NULL tenant_id defaulting to
    the default tenant, with an ix_<table>_tenant_id index and a RESTRICT FK."""
    with isolated_pg_engine.connect() as conn:
        columns = {
            (row.table_name, row.column_name): row
            for row in conn.execute(
                text(
                    "SELECT table_name, column_name, is_nullable, column_default "
                    "FROM information_schema.columns "
                    "WHERE table_schema = 'public' AND column_name = 'tenant_id'"
                )
            ).all()
        }
        indexes = set(
            conn.execute(
                text(
                    "SELECT indexname FROM pg_indexes WHERE schemaname = 'public'"
                )
            )
            .scalars()
            .all()
        )
        restrict_fks = set(
            conn.execute(
                text(
                    "SELECT conname FROM pg_constraint "
                    "WHERE contype = 'f' AND confdeltype = 'r'"
                )
            )
            .scalars()
            .all()
        )

    for table in TENANT_SCOPED_TABLES:
        column = columns.get((table, "tenant_id"))
        assert column is not None, f"{table} has no tenant_id column"
        assert column.is_nullable == "NO", f"{table}.tenant_id is nullable"
        assert str(DEFAULT_TENANT_ID) in (column.column_default or ""), (
            f"{table}.tenant_id default is {column.column_default!r}"
        )
        assert f"ix_{table}_tenant_id" in indexes, f"{table} lacks its tenant index"
        assert f"fk_{table}_tenant_id" in restrict_fks, (
            f"{table}'s tenant FK is missing or is not ON DELETE RESTRICT"
        )


def test_inherited_tables_have_no_tenant_id(isolated_pg_engine):
    """The 20 inherited tables must stay free of a denormalised tenant_id."""
    with isolated_pg_engine.connect() as conn:
        scoped = set(
            conn.execute(
                text(
                    "SELECT table_name FROM information_schema.columns "
                    "WHERE table_schema = 'public' AND column_name = 'tenant_id'"
                )
            )
            .scalars()
            .all()
        )

    for table in TENANT_INHERITED_TABLES:
        assert table not in scoped, f"{table} was denormalised with a tenant_id"

    # `user` is a global identity; `user_tenant_link` is the membership table.
    assert "user" not in scoped
    assert scoped == set(TENANT_SCOPED_TABLES) | {"user_tenant_link"}


def test_existing_rows_are_backfilled(pg_engine_at_0027):
    """Rows that exist *before* 0028 runs are migrated into the default
    tenant, and every pre-existing user gets exactly one membership row."""
    user_id = uuid.uuid4()
    category_id = uuid.uuid4()
    task_id = uuid.uuid4()

    with pg_engine_at_0027.begin() as conn:
        conn.execute(
            text(
                'INSERT INTO "user" '
                "(id, email, hashed_password, full_name, role, is_active, cpf) "
                "VALUES (:id, :email, 'x', 'Backfill Test', 'ADMINISTRATOR', "
                "true, :cpf)"
            ),
            {
                "id": user_id,
                "email": f"backfill-{user_id}@test.com",
                "cpf": str(user_id.int % 10**11).zfill(11),
            },
        )
        conn.execute(
            text(
                "INSERT INTO category (id, name, color, is_active) "
                "VALUES (:id, :name, '#808080', true)"
            ),
            {"id": category_id, "name": f"Backfill {category_id}"},
        )
        conn.execute(
            text(
                "INSERT INTO task "
                "(id, title, status, priority, is_deleted, created_by_id, "
                "created_at, updated_at) "
                "VALUES (:id, 'Backfill Task', 'PENDING', 'MEDIUM', false, "
                ":created_by_id, now(), now())"
            ),
            {"id": task_id, "created_by_id": user_id},
        )

    _run_alembic("upgrade", "head")

    with pg_engine_at_0027.connect() as conn:
        assert conn.execute(
            text("SELECT tenant_id FROM category WHERE id = :id"), {"id": category_id}
        ).scalar_one() == DEFAULT_TENANT_ID
        assert conn.execute(
            text("SELECT tenant_id FROM task WHERE id = :id"), {"id": task_id}
        ).scalar_one() == DEFAULT_TENANT_ID
        links = conn.execute(
            text("SELECT tenant_id FROM user_tenant_link WHERE user_id = :id"),
            {"id": user_id},
        ).scalars().all()

    assert links == [DEFAULT_TENANT_ID]


def test_scoped_uniques_are_per_tenant(isolated_pg_engine):
    """The relaxed uniques are per-tenant: the same category name in two
    tenants is fine, the same name twice in one tenant is not."""
    other_tenant = uuid.uuid4()
    with isolated_pg_engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO tenant (id, name, is_active, created_at, updated_at) "
                "VALUES (:id, 'Condomínio Beta', true, now(), now())"
            ),
            {"id": other_tenant},
        )
        conn.execute(
            text(
                "INSERT INTO category (id, tenant_id, name, color, is_active) "
                "VALUES (:id, :tenant_id, 'Manutenção', '#808080', true)"
            ),
            {"id": uuid.uuid4(), "tenant_id": DEFAULT_TENANT_ID},
        )
        conn.execute(
            text(
                "INSERT INTO category (id, tenant_id, name, color, is_active) "
                "VALUES (:id, :tenant_id, 'Manutenção', '#808080', true)"
            ),
            {"id": uuid.uuid4(), "tenant_id": other_tenant},
        )

    with isolated_pg_engine.connect() as conn:
        assert (
            conn.execute(
                text("SELECT count(*) FROM category WHERE name = 'Manutenção'")
            ).scalar_one()
            == 2
        )

    with pytest.raises(Exception, match="duplicate key|unique constraint"):
        with isolated_pg_engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO category (id, tenant_id, name, color, is_active) "
                    "VALUES (:id, :tenant_id, 'Manutenção', '#808080', true)"
                ),
                {"id": uuid.uuid4(), "tenant_id": DEFAULT_TENANT_ID},
            )


def test_downgrade_removes_tenant_schema(isolated_pg_engine):
    """Downgrading past 0028 undoes it exactly: both tables gone, no
    surviving tenant_id, and the 8 original global uniques back."""
    # Target 0028's own down_revision explicitly rather than a relative
    # "-1": APRAS-43 chained 0029 on top, so "-1" now undoes that instead —
    # exactly the drift this module's older cases already document.
    _run_alembic("downgrade", "0027_add_purchase_quotation")

    assert _current_revision(isolated_pg_engine) == "0027_add_purchase_quotation"

    with isolated_pg_engine.connect() as conn:
        tables = set(
            conn.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'public'"
                )
            )
            .scalars()
            .all()
        )
        scoped = set(
            conn.execute(
                text(
                    "SELECT table_name FROM information_schema.columns "
                    "WHERE table_schema = 'public' AND column_name = 'tenant_id'"
                )
            )
            .scalars()
            .all()
        )
        unique_indexes = set(
            conn.execute(
                text(
                    "SELECT indexname FROM pg_indexes WHERE schemaname = 'public' "
                    "AND indexdef LIKE '%UNIQUE%'"
                )
            )
            .scalars()
            .all()
        )
        unique_constraints = set(
            conn.execute(
                text(
                    "SELECT c.conname FROM pg_constraint c "
                    "JOIN pg_class cl ON cl.oid = c.conrelid "
                    "JOIN pg_namespace n ON n.oid = cl.relnamespace "
                    "WHERE c.contype = 'u' AND n.nspname = 'public'"
                )
            )
            .scalars()
            .all()
        )

    assert "tenant" not in tables
    assert "user_tenant_link" not in tables
    assert scoped == set()

    # The 8 relaxed uniques are global again.
    assert {"ix_category_name", "ix_user_type_name", "ix_user_type_role"} <= (
        unique_indexes
    )
    assert {
        "uq_lot_block_lot_number",
        "occurrence_protocol_number_key",
        "reservable_space_name_key",
        "uq_asset_asset_tag",
        "uq_finance_category_name_type",
    } <= unique_constraints
    # ...and their tenant-composite replacements are gone.
    assert not {
        "ix_category_tenant_name",
        "ix_user_type_tenant_name",
        "ix_user_type_tenant_role",
        "ix_occurrence_tenant_protocol",
        "ix_reservable_space_tenant_name",
        "ix_asset_tenant_asset_tag",
    } & unique_indexes

    # Re-applying must succeed, so the downgrade left a schema 0028 can
    # migrate again (the fixture's teardown reset assumes nothing about it).
    _run_alembic("upgrade", "head")
    assert _current_revision(isolated_pg_engine) == "0033_drop_user_role_and_menus"


# ---------------------------------------------------------------------------
# 0029_add_is_tenant_admin (APRAS-43) - the tenant_admin capability column
# ---------------------------------------------------------------------------


def test_is_tenant_admin_column_shape_and_backfill(pg_engine_at_0027):
    """`is_tenant_admin` is boolean NOT NULL DEFAULT false at head, every
    membership 0028 backfilled reads false, and downgrading to 0028 removes
    the column again."""
    user_id = uuid.uuid4()
    with pg_engine_at_0027.begin() as conn:
        conn.execute(
            text(
                'INSERT INTO "user" '
                "(id, email, hashed_password, full_name, role, is_active, cpf) "
                "VALUES (:id, :email, 'x', 'Capability Test', 'ADMINISTRATOR', "
                "true, :cpf)"
            ),
            {
                "id": user_id,
                "email": f"capability-{user_id}@test.com",
                "cpf": str(user_id.int % 10**11).zfill(11),
            },
        )

    _run_alembic("upgrade", "head")
    assert _current_revision(pg_engine_at_0027) == "0033_drop_user_role_and_menus"

    with pg_engine_at_0027.connect() as conn:
        column = conn.execute(
            text(
                "SELECT data_type, is_nullable, column_default "
                "FROM information_schema.columns "
                "WHERE table_name = 'user_tenant_link' "
                "AND column_name = 'is_tenant_admin'"
            )
        ).one()
        flags = (
            conn.execute(
                text(
                    "SELECT is_tenant_admin FROM user_tenant_link "
                    "WHERE user_id = :id"
                ),
                {"id": user_id},
            )
            .scalars()
            .all()
        )

    assert column.data_type == "boolean"
    assert column.is_nullable == "NO"
    assert column.column_default == "false"
    # 0028 gave every pre-existing user exactly one membership; 0029 makes it
    # a plain one, which is the only safe default.
    assert flags == [False]

    _run_alembic("downgrade", "0028_add_tenant_and_membership")

    with pg_engine_at_0027.connect() as conn:
        columns = (
            conn.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name = 'user_tenant_link'"
                )
            )
            .scalars()
            .all()
        )
    assert "is_tenant_admin" not in columns

    _run_alembic("upgrade", "head")


# ---------------------------------------------------------------------------
# 0030_add_user_type_permissions (APRAS-45) - the role permission bundle
# ---------------------------------------------------------------------------


def test_permissions_column_shape_and_backfill(pg_engine_at_0027):
    """`permissions` is json NOT NULL DEFAULT '[]' at head, a `role` row
    seeded before the migration back-fills to `[]`, and downgrading to 0029
    removes the column again."""
    role_id = uuid.uuid4()
    with pg_engine_at_0027.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO user_type (id, name, allowed_menus) "
                "VALUES (:id, :name, '[]')"
            ),
            {"id": role_id, "name": f"Bundle Test {role_id}"},
        )

    _run_alembic("upgrade", "head")
    assert _current_revision(pg_engine_at_0027) == "0033_drop_user_role_and_menus"

    with pg_engine_at_0027.connect() as conn:
        column = conn.execute(
            text(
                "SELECT data_type, is_nullable, column_default "
                "FROM information_schema.columns "
                "WHERE table_name = 'role' AND column_name = 'permissions'"
            )
        ).one()
        bundles = (
            conn.execute(
                text("SELECT permissions::text FROM role WHERE id = :id"),
                {"id": role_id},
            )
            .scalars()
            .all()
        )

    assert column.data_type == "json"
    assert column.is_nullable == "NO"
    assert column.column_default == "'[]'::json"
    # Nothing is seeded: the pre-existing row back-fills to the empty bundle.
    assert bundles == ["[]"]

    _run_alembic("downgrade", "0029_add_is_tenant_admin")

    with pg_engine_at_0027.connect() as conn:
        columns = (
            conn.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name = 'role'"
                )
            )
            .scalars()
            .all()
        )
    assert "permissions" not in columns

    _run_alembic("upgrade", "head")


def test_only_the_six_historically_named_rows_carry_permissions(isolated_pg_engine):
    """F1's "NOTHING is seeded", and the one migration that is an exception.

    `0030` shipped the column empty and every migration since kept it empty;
    `0033` is the **one** writer that ever put permissions in a row, and it
    did it once, to preserve the effective sets the retired enum used to
    compute (§7.2 step 1). So the invariant is no longer "no row has
    permissions" but the sharper "**only** the six historically-named rows
    do" — a row an operator creates still starts and stays `[]`.
    """
    with isolated_pg_engine.connect() as conn:
        rows = conn.execute(
            text("SELECT name, permissions::text AS permissions FROM role")
        ).all()

    assert rows
    non_empty = {row.name for row in rows if row.permissions != "[]"}
    assert non_empty == {
        "Administrador (papel)",
        "Diretor (papel)",
        "Gerente (papel)",
        "Convidado (papel)",
        "Morador (papel)",
        "Porteiro (papel)",
    }


# ---------------------------------------------------------------------------
# 0031_add_user_is_superuser (APRAS-47) - the global superuser column
# ---------------------------------------------------------------------------


def test_is_superuser_column_shape_and_conversion(pg_engine_at_0027):
    """`is_superuser` is boolean NOT NULL DEFAULT false at head, every row
    that carried role ADMINISTRATOR before the migration converts to true and
    every other role to false, and downgrading to 0030 removes the column."""
    admin_id = uuid.uuid4()
    director_id = uuid.uuid4()
    with pg_engine_at_0027.begin() as conn:
        for user_id, role in ((admin_id, "ADMINISTRATOR"), (director_id, "DIRECTOR")):
            conn.execute(
                text(
                    'INSERT INTO "user" '
                    "(id, email, hashed_password, full_name, role, is_active, cpf) "
                    "VALUES (:id, :email, 'x', 'Superuser Test', :role, "
                    "true, :cpf)"
                ),
                {
                    "id": user_id,
                    "email": f"superuser-{user_id}@test.com",
                    "role": role,
                    "cpf": str(user_id.int % 10**11).zfill(11),
                },
            )

    _run_alembic("upgrade", "head")
    assert _current_revision(pg_engine_at_0027) == "0033_drop_user_role_and_menus"

    with pg_engine_at_0027.connect() as conn:
        column = conn.execute(
            text(
                "SELECT data_type, is_nullable, column_default "
                "FROM information_schema.columns "
                "WHERE table_name = 'user' AND column_name = 'is_superuser'"
            )
        ).one()
        flags = dict(
            conn.execute(
                text(
                    'SELECT id, is_superuser FROM "user" WHERE id IN (:a, :d)'
                ),
                {"a": admin_id, "d": director_id},
            ).all()
        )

    assert column.data_type == "boolean"
    assert column.is_nullable == "NO"
    assert column.column_default == "false"
    # Every administrator that existed when 0031 ran *was* the global
    # superuser at 0030, which is what makes the swap in `deps` a no-op.
    assert flags[admin_id] is True
    assert flags[director_id] is False

    _run_alembic("downgrade", "0030_add_user_type_permissions")

    with pg_engine_at_0027.connect() as conn:
        columns = (
            conn.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name = 'user'"
                )
            )
            .scalars()
            .all()
        )
    assert "is_superuser" not in columns

    _run_alembic("upgrade", "head")

    with pg_engine_at_0027.connect() as conn:
        restored = (
            conn.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name = 'user' AND column_name = 'is_superuser'"
                )
            )
            .scalars()
            .all()
        )
    assert restored == ["is_superuser"]


def _is_tenant_admin_shape(engine):
    with engine.connect() as conn:
        return conn.execute(
            text(
                "SELECT data_type, is_nullable, column_default "
                "FROM information_schema.columns "
                "WHERE table_name = 'user_tenant_link' "
                "AND column_name = 'is_tenant_admin'"
            )
        ).one()


def test_0031_does_not_touch_is_tenant_admin(isolated_pg_engine):
    """APRAS-47 changes what the capability *means*, never its column."""
    before = _is_tenant_admin_shape(isolated_pg_engine)
    assert before.data_type == "boolean"

    _run_alembic("downgrade", "0030_add_user_type_permissions")
    _run_alembic("upgrade", "head")

    assert _is_tenant_admin_shape(isolated_pg_engine) == before


# ---------------------------------------------------------------------------
# 0032_rename_user_type_to_role (APRAS-49 §2.3) - the pure rename
# ---------------------------------------------------------------------------


def _names(engine, query: str) -> set[str]:
    with engine.connect() as conn:
        return set(conn.execute(text(query)).scalars().all())


_INDEX_NAMES = (
    "SELECT indexname FROM pg_indexes WHERE schemaname = 'public'"
)
_CONSTRAINT_NAMES = (
    "SELECT c.conname FROM pg_constraint c "
    "JOIN pg_class cl ON cl.oid = c.conrelid "
    "JOIN pg_namespace n ON n.oid = cl.relnamespace "
    "WHERE n.nspname = 'public'"
)
_TABLE_NAMES = (
    "SELECT table_name FROM information_schema.tables "
    "WHERE table_schema = 'public'"
)


def _columns(engine, table: str) -> set[str]:
    return _names(
        engine,
        "SELECT column_name FROM information_schema.columns "  # noqa: S608
        f"WHERE table_name = '{table}'",
    )


def _column_type(engine, table: str, column: str) -> str:
    """`udt_name`, so a native enum is distinguishable from a VARCHAR."""
    with engine.connect() as conn:
        return conn.execute(
            text(
                "SELECT udt_name FROM information_schema.columns "
                "WHERE table_name = :table AND column_name = :column"
            ),
            {"table": table, "column": column},
        ).scalar_one()


def _assert_pre_0033_schema_is_back(engine) -> None:
    """The whole schema half of `0033`'s reversibility contract (§7.5).

    Extracted from the persona test rather than inlined there because it is
    a claim about the *schema* and the rest of that test is a claim about
    *rows*; keeping the two apart also keeps either from being read as
    incidental setup for the other.

    The two `role` columns have **different types**, and reproducing that is
    the point: `user.role` is the native `userrole` enum, while `role.role`
    is a plain VARCHAR because `0018` could not reuse a type whose
    `RESIDENT` label `0014` had added in the same transaction. A downgrade
    that gave `role.role` the enum would leave a schema base-to-head cannot
    rebuild.
    """
    columns = _columns(engine, "role")
    assert "role" in columns
    assert "allowed_menus" in columns
    assert "landing_path" not in columns
    assert "role" in _columns(engine, "user")
    assert _column_type(engine, "role", "role") == "varchar"
    assert _column_type(engine, "user", "role") == "userrole"
    assert _userrole_labels(engine) == set(LEGACY_ROLE_NAMES_BY_VALUE)

    with engine.connect() as conn:
        # The journal is dropped by its own replay: leaving it behind would
        # let a second downgrade replay rows that are no longer true.
        assert (
            conn.execute(text("SELECT to_regclass('f5_backfill_journal')")).scalar()
            is None
        )
        folder_default = conn.execute(
            text(
                "SELECT column_default FROM information_schema.columns "
                "WHERE table_name = 'document_folder' "
                "AND column_name = 'allowed_roles_json'"
            )
        ).scalar_one()
    assert folder_default.startswith(
        "'[\"ADMINISTRATOR\", \"DIRECTOR\", \"MANAGER\", \"RESIDENT\"]'"
    )


def test_0032_leaves_no_identifier_spelling_the_retired_name(isolated_pg_engine):
    """ER-1, at the schema level: tables, columns, indexes **and** constraints.

    Postgres carries primary-key and foreign-key constraint names across
    `ALTER TABLE ... RENAME TO` unchanged, so a plain `rename_table` would
    have left six constraints and four indexes still spelling `user_type`.
    `0032` renames them explicitly; this is what proves it did.
    """
    assert {"role", "user_role_link"} <= _names(isolated_pg_engine, _TABLE_NAMES)
    assert "user_type" not in _names(isolated_pg_engine, _TABLE_NAMES)
    assert "user_user_type_link" not in _names(isolated_pg_engine, _TABLE_NAMES)

    assert "role_id" in _columns(isolated_pg_engine, "user_role_link")
    assert "role_id" in _columns(isolated_pg_engine, "task_visible_to_link")

    offenders = sorted(
        name
        for name in _names(isolated_pg_engine, _INDEX_NAMES)
        | _names(isolated_pg_engine, _CONSTRAINT_NAMES)
        if "user_type" in name
    )
    assert not offenders, f"identifiers still spelling the retired name: {offenders}"


def test_0032_round_trips(isolated_pg_engine):
    """`0032` moves no data and drops nothing, so it is *exactly* reversible."""
    _run_alembic("downgrade", "0031_add_user_is_superuser")

    tables = _names(isolated_pg_engine, _TABLE_NAMES)
    assert {"user_type", "user_user_type_link"} <= tables
    assert "role" not in tables
    assert "user_type_id" in _columns(isolated_pg_engine, "user_user_type_link")
    assert "user_type_id" in _columns(isolated_pg_engine, "task_visible_to_link")
    assert {
        "user_type_pkey",
        "fk_user_type_tenant_id",
        "user_user_type_link_pkey",
        "user_user_type_link_user_id_fkey",
        "user_user_type_link_user_type_id_fkey",
        "task_visible_to_link_user_type_id_fkey",
    } <= _names(isolated_pg_engine, _CONSTRAINT_NAMES)

    _run_alembic("upgrade", "head")
    assert "role" in _names(isolated_pg_engine, _TABLE_NAMES)


# ---------------------------------------------------------------------------
# 0033_drop_user_role_and_menus (APRAS-49 §7) - the enum drop
# ---------------------------------------------------------------------------

LEGACY_ROLE_NAMES_BY_VALUE = {
    "ADMINISTRATOR": "Administrador (papel)",
    "DIRECTOR": "Diretor (papel)",
    "MANAGER": "Gerente (papel)",
    "GUEST": "Convidado (papel)",
    "RESIDENT": "Morador (papel)",
    "PORTEIRO": "Porteiro (papel)",
}


def _recorded_bundles() -> dict[str, list[str]]:
    """`tests/data/legacy_role_bundles.json`, the §7.6 artefact.

    It is the **only** surviving statement of what the enum meant, recorded
    from `LEGACY_ROLE_PERMISSIONS` one last time before that map was deleted.
    """
    import json
    import pathlib

    path = pathlib.Path(__file__).parent / "data" / "legacy_role_bundles.json"
    return json.loads(path.read_text(encoding="utf-8"))["bundles"]


def _migration_literal() -> dict[str, list[str]]:
    """`_LEGACY_BUNDLES` out of the migration file, with `ast`.

    Parsed rather than imported: `backend/alembic/` is itself an importable
    package on the test `pythonpath`, so importing a migration module would
    resolve `from alembic import op` against the project directory instead of
    the real library.
    """
    import ast
    import pathlib

    path = (
        pathlib.Path(__file__).parent.parent
        / "alembic"
        / "versions"
        / "0033_drop_user_role_and_menus.py"
    )
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        targets = node.targets if isinstance(node, ast.Assign) else (
            [node.target] if isinstance(node, ast.AnnAssign) else []
        )
        for target in targets:
            if isinstance(target, ast.Name) and target.id == "_LEGACY_BUNDLES":
                return ast.literal_eval(node.value)
    raise AssertionError("_LEGACY_BUNDLES not found in 0033")


NEW_TIER_BY_VALUE = {
    "ADMINISTRATOR": {"tasks:read_all", "tasks:update_any"},
    "DIRECTOR": {"tasks:read_all", "tasks:update_any"},
    "RESIDENT": {"tasks:read_all", "tasks:update_any"},
    "PORTEIRO": {"tasks:read_all", "tasks:update_any"},
    "MANAGER": {"occurrences:read_assigned"},
    "GUEST": set(),
}


def test_0033_literal_matches_the_recording():
    """§7.6: the migration inlines the bundle, and this is what checks it.

    `0033` imports nothing from `app/` — a migration is a historical artefact,
    and if it read `app.core.permissions` its behaviour would change every
    time the catalogue changes. The price of inlining is that the literal can
    drift; the recorded artefact is what makes that a red test rather than a
    silent permission change on every install that migrates.
    """
    recorded = _recorded_bundles()
    literal = _migration_literal()

    assert set(literal) == set(recorded) == set(LEGACY_ROLE_NAMES_BY_VALUE)
    for value, permissions in literal.items():
        assert set(permissions) == set(recorded[value]) | NEW_TIER_BY_VALUE[value], value


def test_0033_drops_the_columns_the_index_and_the_type(isolated_pg_engine):
    """ER-2, the schema half."""
    assert "role" not in _columns(isolated_pg_engine, "user")
    role_columns = _columns(isolated_pg_engine, "role")
    assert "role" not in role_columns
    assert "allowed_menus" not in role_columns
    assert "landing_path" in role_columns
    assert "ix_role_tenant_role" not in _names(isolated_pg_engine, _INDEX_NAMES)
    with isolated_pg_engine.connect() as conn:
        assert conn.execute(text("SELECT to_regtype('userrole')")).scalar() is None
        assert (
            conn.execute(text("SELECT to_regclass('f5_backfill_journal')")).scalar()
            is not None
        )


def test_0033_renames_the_folder_acl_column_and_moves_its_default(
    isolated_pg_engine,
):
    """§6: both defaults become `'[]'`, because neither can name four role ids."""
    columns = _columns(isolated_pg_engine, "document_folder")
    assert "allowed_roles_json" not in columns
    assert "allowed_role_ids_json" in columns

    with isolated_pg_engine.connect() as conn:
        default = conn.execute(
            text(
                "SELECT column_default FROM information_schema.columns "
                "WHERE table_name = 'document_folder' "
                "AND column_name = 'allowed_role_ids_json'"
            )
        ).scalar_one()
    assert default.startswith("'[]'")


def test_0033_sets_the_two_landing_paths(isolated_pg_engine):
    """§7.2 step 4: the only additive schema of the slice, and its two rows."""
    with isolated_pg_engine.connect() as conn:
        rows = conn.execute(
            text("SELECT name, landing_path FROM role WHERE landing_path IS NOT NULL")
        ).all()

    assert {(row.name, row.landing_path) for row in rows} == {
        ("Porteiro (papel)", "/gate"),
        ("Convidado (papel)", "/welcome"),
    }


# ---------------------------------------------------------------------------
# 0033 -- the data cases (ER-2, ER-3)
# ---------------------------------------------------------------------------
#
# These seed **at 0031**, before the rename and before the drop, so the SQL
# below deliberately speaks the pre-F5 schema: `user.role` is the native enum,
# the table is `user_type`, and the link table is `user_user_type_link`. That
# is the whole point — a migration test that could only seed post-migration
# rows would prove nothing about an existing install.

AT_0031 = "0031_add_user_is_superuser"
_CPF = iter(range(10_000_000_000, 10_000_999_999))


@pytest.fixture
def pg_engine_at_0031(migrated_pg_engine):
    _reset_to(migrated_pg_engine, AT_0031)
    yield migrated_pg_engine
    _reset_to(migrated_pg_engine, "head")


def _seed_user(
    conn,
    role: str,
    *,
    email: str,
    is_superuser: bool = False,
    is_active: bool = True,
) -> uuid.UUID:
    """A user at `0031`, with `is_superuser` written **explicitly**.

    Explicit on all ten personas, and nine of them get `False`. This is not
    boilerplate: `0031` runs
    `UPDATE "user" SET is_superuser = true WHERE role = 'ADMINISTRATOR'`, so
    an ADMINISTRATOR seeded "around `0031`" is genuinely ambiguous, and F3
    added a superuser short-circuit to `get_effective_permissions`. Writing
    the flag after the migration has run is what makes the fixture say what
    it means.
    """
    user_id = uuid.uuid4()
    conn.execute(
        text(
            'INSERT INTO "user" '
            "(id, email, hashed_password, full_name, role, is_active, cpf, "
            " is_superuser) "
            "VALUES (:id, :email, 'x', :name, :role, :is_active, :cpf, "
            ":is_superuser)"
        ),
        {
            "id": user_id,
            "email": email,
            "name": f"{role} persona",
            "role": role,
            "is_active": is_active,
            "cpf": str(next(_CPF)),
            "is_superuser": is_superuser,
        },
    )
    return user_id


def _link_tenant(conn, user_id, tenant_id, *, is_tenant_admin: bool = False) -> None:
    conn.execute(
        text(
            "INSERT INTO user_tenant_link (id, user_id, tenant_id, "
            "is_tenant_admin, created_at) "
            "VALUES (:id, :user_id, :tenant_id, :admin, now())"
        ),
        {
            "id": uuid.uuid4(),
            "user_id": user_id,
            "tenant_id": tenant_id,
            "admin": is_tenant_admin,
        },
    )


def _legacy_type_id(conn, tenant_id, role: str):
    return conn.execute(
        text(
            "SELECT id FROM user_type WHERE tenant_id = :tenant_id "
            "AND role = :role"
        ),
        {"tenant_id": tenant_id, "role": role},
    ).scalar()


def _link_type(conn, user_id, type_id) -> None:
    conn.execute(
        text(
            "INSERT INTO user_user_type_link (user_id, user_type_id) "
            "VALUES (:user_id, :type_id)"
        ),
        {"user_id": user_id, "type_id": type_id},
    )


def _upgrade_head_expecting_failure() -> str:
    """Run `alembic upgrade head` and return its stderr, asserting it failed."""
    result = _alembic("upgrade", "head")
    assert result.returncode != 0, (
        "0033 was expected to refuse:\n"
        f"stdout={result.stdout}\nstderr={result.stderr}"
    )
    return result.stderr


def test_0033_refuses_a_user_explicitly_linked_to_a_foreign_legacy_role(
    pg_engine_at_0031,
):
    """ER-3, the **pre**-condition guard (§7.0 a): refuse a *widening*.

    Today the six legacy rows carry `permissions = []`, so an explicit
    membership in `Diretor (papel)` grants a legacy MANAGER **nothing**; it
    only widens the id set `Task.visible_to` intersects. After the backfill
    that same row carries DIRECTOR's whole bundle, and that user would
    silently acquire it — including `tasks:read_all`, i.e. they would stop
    being scoped by `visible_to` at all.

    "Add the manager to `Diretor (papel)` so he sees director-targeted tasks"
    is a natural operator action and the state is reachable through the
    shipped API, so this population is not hypothetical. `0033` refuses it
    **before a single write** rather than accepting it, and there is
    deliberately no override flag: an env var would let the widening ship
    silently, which is the one thing the guard exists to prevent.
    """
    with pg_engine_at_0031.begin() as conn:
        manager = _seed_user(conn, "MANAGER", email="foreign-link@test.com")
        _link_tenant(conn, manager, DEFAULT_TENANT_ID)
        director_type = _legacy_type_id(conn, DEFAULT_TENANT_ID, "DIRECTOR")
        _link_type(conn, manager, director_type)

    stderr = _upgrade_head_expecting_failure()

    # It names the user *and* the role, so the operator can act on it.
    assert "foreign-link@test.com" in stderr
    assert "Diretor (papel)" in stderr
    assert "DELETE FROM user_role_link" in stderr

    # And **nothing was written**: it is a pre-condition, so a refusing
    # install has no row touched and no column dropped.
    #
    # DEVIATION from the spec's §7.0 (a), recorded here rather than in a
    # comment nobody reads: the spec predicts the install is left at `0032`,
    # because the rename is a separate, already-committed migration. This
    # repository's `alembic/env.py` runs the **whole** `upgrade head`
    # invocation in one transaction, so `0032` rolls back with `0033` and the
    # install is left at `0031`. The property that matters is unchanged —
    # nothing written, nothing dropped, "fix and re-run" works — and being
    # left one revision earlier is if anything the safer of the two.
    with pg_engine_at_0031.connect() as conn:
        assert _current_revision(pg_engine_at_0031) == AT_0031
        assert (
            conn.execute(text("SELECT to_regclass('f5_backfill_journal')")).scalar()
            is None
        )
        assert "role" in _columns(pg_engine_at_0031, "user")
        bundles = (
            conn.execute(
                text(
                    "SELECT permissions::text FROM user_type "
                    "WHERE role IS NOT NULL"
                )
            )
            .scalars()
            .all()
        )
    assert set(bundles) == {"[]"}

    # Remove the link and the same migration succeeds. The table is still
    # `user_user_type_link` here: the refusal rolled `0032` back too.
    with pg_engine_at_0031.begin() as conn:
        conn.execute(
            text("DELETE FROM user_user_type_link WHERE user_id = :id"),
            {"id": manager},
        )
    _run_alembic("upgrade", "head")

    with pg_engine_at_0031.connect() as conn:
        names = (
            conn.execute(
                text(
                    "SELECT r.name FROM user_role_link l "
                    "JOIN role r ON r.id = l.role_id WHERE l.user_id = :id"
                ),
                {"id": manager},
            )
            .scalars()
            .all()
        )
    assert names == ["Gerente (papel)"]


def test_0033_does_not_refuse_the_two_neighbouring_cases(pg_engine_at_0031):
    """§7.0 (a) names two shapes it must **not** refuse, and here they are.

    A link to a **non-legacy** row is untouched by the backfill (only the six
    legacy rows get a bundle), and a link to the legacy row that *matches*
    the user's own enum is not a widening — the row gains exactly the bundle
    the enum already granted that user.
    """
    with pg_engine_at_0031.begin() as conn:
        ordinary_id = uuid.uuid4()
        conn.execute(
            text(
                "INSERT INTO user_type (id, tenant_id, name, allowed_menus, "
                "permissions) VALUES (:id, :tenant_id, 'Conselho', '[]', '[]')"
            ),
            {"id": ordinary_id, "tenant_id": DEFAULT_TENANT_ID},
        )
        non_legacy = _seed_user(conn, "RESIDENT", email="non-legacy@test.com")
        _link_tenant(conn, non_legacy, DEFAULT_TENANT_ID)
        _link_type(conn, non_legacy, ordinary_id)

        matching = _seed_user(conn, "MANAGER", email="matching@test.com")
        _link_tenant(conn, matching, DEFAULT_TENANT_ID)
        _link_type(conn, matching, _legacy_type_id(conn, DEFAULT_TENANT_ID, "MANAGER"))

    _run_alembic("upgrade", "head")

    with pg_engine_at_0031.connect() as conn:
        # The matching link is **skipped, not duplicated** (§7.2 step 2).
        count = conn.execute(
            text("SELECT count(*) FROM user_role_link WHERE user_id = :id"),
            {"id": matching},
        ).scalar_one()
        assert count == 1

        # And the non-legacy row's bundle is untouched by the backfill.
        assert (
            conn.execute(
                text("SELECT permissions::text FROM role WHERE id = :id"),
                {"id": ordinary_id},
            ).scalar_one()
            == "[]"
        )


def test_0033_refuses_when_an_active_user_has_no_role_and_no_flag(
    pg_engine_at_0031,
):
    """ER-3, the **post**-condition guard (§7.3): refuse a *narrowing*.

    A pre-condition guard would be satisfied by luck — the enum is NOT NULL,
    so every user trivially has a role. As a post-condition it asserts the
    backfill was **complete**, and it is genuinely reachable: a user with
    zero `user_tenant_link` rows gets zero memberships from §7.2 step 2 and
    trips it. That is exactly the state this fixture constructs.
    """
    with pg_engine_at_0031.begin() as conn:
        stranded = _seed_user(conn, "DIRECTOR", email="stranded@test.com")

    stderr = _upgrade_head_expecting_failure()
    assert "stranded@test.com" in stderr
    assert "is_superuser" in stderr

    with pg_engine_at_0031.begin() as conn:
        _link_tenant(conn, stranded, DEFAULT_TENANT_ID)
    _run_alembic("upgrade", "head")

    with pg_engine_at_0031.connect() as conn:
        names = (
            conn.execute(
                text(
                    "SELECT r.name FROM user_role_link l "
                    "JOIN role r ON r.id = l.role_id WHERE l.user_id = :id"
                ),
                {"id": stranded},
            )
            .scalars()
            .all()
        )
    assert names == ["Diretor (papel)"]


def test_0033_does_not_refuse_an_inactive_or_flagged_user(pg_engine_at_0031):
    """The guard's three escape hatches, each one exercised (§7.3).

    Inactive, superuser and tenant_admin are all "has a way in" — refusing
    them would make the migration unrunnable on any install with a
    deactivated account, which is every install.
    """
    with pg_engine_at_0031.begin() as conn:
        _seed_user(conn, "GUEST", email="inactive@test.com", is_active=False)
        _seed_user(conn, "GUEST", email="root@test.com", is_superuser=True)
        syndic = _seed_user(conn, "RESIDENT", email="syndic@test.com")
        _link_tenant(conn, syndic, DEFAULT_TENANT_ID, is_tenant_admin=True)

    _run_alembic("upgrade", "head")
    assert _current_revision(pg_engine_at_0031) == "0033_drop_user_role_and_menus"


def test_effective_permissions_are_unchanged_by_0033(pg_engine_at_0031):  # noqa: PLR0915
    """ER-3's real ask (§11.2): the migration changes no user's power.

    Ten personas, seeded **at `0031`** with `is_superuser` written explicitly
    on all ten. Personas 1-6 are the *link-less* majority — the shape the
    role-implicit membership produced, and the one a fixture that only
    carries explicit links cannot see. Personas 8 and 9 exist because §7.0
    (a) lets exactly those two shapes through and §7.2 step 2 must **skip**
    rather than duplicate them.

    The assertion is `post == pre | NEW_TIER[role]` for the nine, and the
    whole catalogue for the superuser — a different statement, made by F3's
    short-circuit rather than by the bundle path, and the one that keeps
    ER-3's "exactly" true of every user the test names.
    """
    from sqlmodel import Session

    profiles = ["ADMINISTRATOR", "DIRECTOR", "MANAGER", "PORTEIRO", "RESIDENT", "GUEST"]
    personas: dict[str, tuple[uuid.UUID, str]] = {}

    with pg_engine_at_0031.begin() as conn:
        second_tenant = uuid.uuid4()
        conn.execute(
            text(
                "INSERT INTO tenant (id, name, is_active, created_at, updated_at) "
                "VALUES (:id, 'Condomínio Dois', true, now(), now())"
            ),
            {"id": second_tenant},
        )
        for value, name in LEGACY_ROLE_NAMES_BY_VALUE.items():
            conn.execute(
                text(
                    "INSERT INTO user_type (id, tenant_id, name, allowed_menus, "
                    "permissions, role) "
                    "VALUES (:id, :tenant_id, :name, '[]', '[]', :role)"
                ),
                {
                    "id": uuid.uuid4(),
                    "tenant_id": second_tenant,
                    "name": name,
                    "role": value,
                },
            )

        # 1-6: one per legacy role, **no explicit link**.
        for value in profiles:
            user_id = _seed_user(
                conn, value, email=f"persona-{value.lower()}@test.com"
            )
            _link_tenant(conn, user_id, DEFAULT_TENANT_ID)
            personas[f"plain-{value}"] = (user_id, value)

        # 7: an extra **non-legacy** role carrying one permission.
        extra_id = uuid.uuid4()
        conn.execute(
            text(
                "INSERT INTO user_type (id, tenant_id, name, allowed_menus, "
                "permissions) VALUES (:id, :tenant_id, 'Financeiro', '[]', "
                "'[\"finance:read\"]')"
            ),
            {"id": extra_id, "tenant_id": DEFAULT_TENANT_ID},
        )
        seven = _seed_user(conn, "RESIDENT", email="persona-extra@test.com")
        _link_tenant(conn, seven, DEFAULT_TENANT_ID)
        _link_type(conn, seven, extra_id)
        personas["extra-role"] = (seven, "RESIDENT")

        # 8: explicitly linked to the legacy row that **matches** its enum.
        eight = _seed_user(conn, "MANAGER", email="persona-matching@test.com")
        _link_tenant(conn, eight, DEFAULT_TENANT_ID)
        _link_type(conn, eight, _legacy_type_id(conn, DEFAULT_TENANT_ID, "MANAGER"))
        personas["matching-link"] = (eight, "MANAGER")

        # 9: the same, in a **second** tenant.
        nine = _seed_user(conn, "DIRECTOR", email="persona-second-tenant@test.com")
        _link_tenant(conn, nine, DEFAULT_TENANT_ID)
        _link_tenant(conn, nine, second_tenant)
        _link_type(conn, nine, _legacy_type_id(conn, second_tenant, "DIRECTOR"))
        personas["second-tenant"] = (nine, "DIRECTOR")

        # 10: a superuser.
        ten = _seed_user(
            conn, "ADMINISTRATOR", email="persona-root@test.com", is_superuser=True
        )
        _link_tenant(conn, ten, DEFAULT_TENANT_ID)
        personas["superuser"] = (ten, "ADMINISTRATOR")

    # The fixture asserts the seeded flags *before* it upgrades.
    with pg_engine_at_0031.connect() as conn:
        flags = dict(
            conn.execute(
                text('SELECT email, is_superuser FROM "user" ORDER BY email')
            ).all()
        )
    assert flags["persona-root@test.com"] is True
    assert sum(1 for value in flags.values() if value is False) == 9

    recorded = _recorded_bundles()
    pre = {
        key: set(recorded[value])
        | ({"finance:read"} if key == "extra-role" else set())
        for key, (_user_id, value) in personas.items()
    }

    _run_alembic("upgrade", "head")

    from app.api import deps
    from app.core.permissions import PERMISSIONS
    from app.core.tenant_context import acting_tenant_scope
    from app.models.user import User

    with Session(pg_engine_at_0031) as session, acting_tenant_scope(
        session, DEFAULT_TENANT_ID
    ):
        for key, (user_id, value) in personas.items():
            user = session.get(User, user_id)
            post = deps.get_effective_permissions(user, session)
            if key == "superuser":
                # A *different* statement from `pre | NEW_TIER`: it also
                # carries `packages:my_lots_read`, absent from the legacy
                # ADMINISTRATOR bundle, and `occurrences:read_assigned`.
                assert post == PERMISSIONS, key
                assert len(post) == 159
            else:
                assert post == pre[key] | NEW_TIER_BY_VALUE[value], key

    # Persona 1's number, spelled out: 155 + 2, deliberately not 159.
    with Session(pg_engine_at_0031) as session, acting_tenant_scope(
        session, DEFAULT_TENANT_ID
    ):
        admin = session.get(User, personas["plain-ADMINISTRATOR"][0])
        assert len(deps.get_effective_permissions(admin, session)) == 157

    # Persona 8 has exactly **one** link: the backfill skipped, not duplicated.
    with pg_engine_at_0031.connect() as conn:
        assert (
            conn.execute(
                text("SELECT count(*) FROM user_role_link WHERE user_id = :id"),
                {"id": personas["matching-link"][0]},
            ).scalar_one()
            == 1
        )
        # Persona 9 got one link per tenant it belongs to.
        assert (
            conn.execute(
                text("SELECT count(*) FROM user_role_link WHERE user_id = :id"),
                {"id": personas["second-tenant"][0]},
            ).scalar_one()
            == 2
        )


def test_0033_document_folder_acl_round_trips(pg_engine_at_0031):
    """ER-2, §6: `pre`, `mapped-back post` and `post-downgrade` are identical.

    Four folders across two tenants — the seeded default ACL, a single-role
    ACL, an empty ACL, and one carrying an unknown string. The unknown one is
    the interesting case: the forward rewrite **drops** it from the id list
    (hand-edited or foreign data, dropped and counted, never a hard failure)
    and the journal is what brings it back on the way down.

    The join key is `role.role`, never `role.name`, in both directions. The
    legacy rows' name is the pt-BR label (`"Diretor (papel)"`) and nothing is
    named `"DIRECTOR"`, so a name join would match nothing forward and
    nothing backward — emptying every folder ACL in every tenant on the way
    up and denying every non-staff user on the way down, silently both times.
    """
    import json

    folders: dict[str, list[str]] = {
        "seeded": ["ADMINISTRATOR", "DIRECTOR", "MANAGER", "RESIDENT"],
        "single": ["MANAGER"],
        "empty": [],
        "unknown": ["DIRECTOR", "NOT_A_ROLE"],
    }
    ids: dict[str, uuid.UUID] = {}

    with pg_engine_at_0031.begin() as conn:
        second_tenant = uuid.uuid4()
        conn.execute(
            text(
                "INSERT INTO tenant (id, name, is_active, created_at, updated_at) "
                "VALUES (:id, 'Condomínio ACL', true, now(), now())"
            ),
            {"id": second_tenant},
        )
        for value, name in LEGACY_ROLE_NAMES_BY_VALUE.items():
            conn.execute(
                text(
                    "INSERT INTO user_type (id, tenant_id, name, allowed_menus, "
                    "permissions, role) "
                    "VALUES (:id, :tenant_id, :name, '[]', '[]', :role)"
                ),
                {
                    "id": uuid.uuid4(),
                    "tenant_id": second_tenant,
                    "name": name,
                    "role": value,
                },
            )
        for index, (key, values) in enumerate(folders.items()):
            folder_id = uuid.uuid4()
            ids[key] = folder_id
            conn.execute(
                text(
                    "INSERT INTO document_folder "
                    "(id, tenant_id, name, allowed_roles_json, created_at, "
                    " updated_at) "
                    "VALUES (:id, :tenant_id, :name, :acl, now(), now())"
                ),
                {
                    "id": folder_id,
                    # Two tenants, so the per-tenant mapping is exercised.
                    "tenant_id": DEFAULT_TENANT_ID if index % 2 else second_tenant,
                    "name": f"Pasta {key}",
                    "acl": json.dumps(values),
                },
            )

    def _pairs(column: str) -> dict[str, list[str]]:
        with pg_engine_at_0031.connect() as conn:
            rows = conn.execute(
                text(f"SELECT id, {column} AS acl FROM document_folder")  # noqa: S608
            ).all()
        return {str(row.id): json.loads(row.acl or "[]") for row in rows}

    before = _pairs("allowed_roles_json")

    _run_alembic("upgrade", "head")

    # Post-migration the column holds **role ids**, and every one of them
    # exists in `role`, in that folder's own tenant.
    with pg_engine_at_0031.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT id, tenant_id, allowed_role_ids_json AS acl "
                "FROM document_folder"
            )
        ).all()
        role_rows = conn.execute(
            text("SELECT id, tenant_id, name FROM role")
        ).all()
    name_by_id = {str(row.id): row.name for row in role_rows}
    tenant_by_id = {str(row.id): str(row.tenant_id) for row in role_rows}
    value_by_name = {v: k for k, v in LEGACY_ROLE_NAMES_BY_VALUE.items()}

    mapped: dict[str, list[str]] = {}
    for row in rows:
        parsed = json.loads(row.acl or "[]")
        assert isinstance(parsed, list)
        for role_id in parsed:
            assert role_id in name_by_id, role_id
            assert tenant_by_id[role_id] == str(row.tenant_id)
        mapped[str(row.id)] = [value_by_name[name_by_id[i]] for i in parsed]

    # Identical to `before`, except that the unknown string is dropped by the
    # forward rewrite — which is exactly what §6 says it does.
    for folder_id, values in before.items():
        assert mapped[folder_id] == [v for v in values if v in LEGACY_ROLE_NAMES_BY_VALUE]

    _run_alembic("downgrade", "-1")

    after = _pairs("allowed_roles_json")
    assert after == before, "the journal must restore the original bytes"

    _run_alembic("upgrade", "head")


def test_0033_downgrade_restores_the_schema_and_recomputes_roles(
    pg_engine_at_0031,
):
    """ER-2's reversibility contract (§7.5), over the persona table.

    The bug this ordering fixes is **invisible to a fixture that only carries
    explicit links**. Before `0033` an ordinary DIRECTOR had *no*
    `user_role_link` row at all — the membership was computed from the enum —
    so the link to `Diretor (papel)` is backfill-created for the whole
    ordinary population. Reading memberships *after* the journal replay would
    see an empty set for every one of them and write `GUEST`, demoting every
    non-superuser DIRECTOR/MANAGER/RESIDENT/PORTEIRO in the install on the
    rollback path. Step 4 therefore runs **before** step 5, and this case is
    what proves it.
    """
    personas: dict[str, uuid.UUID] = {}
    with pg_engine_at_0031.begin() as conn:
        for value in ("DIRECTOR", "MANAGER", "RESIDENT", "PORTEIRO", "GUEST"):
            user_id = _seed_user(conn, value, email=f"down-{value.lower()}@test.com")
            _link_tenant(conn, user_id, DEFAULT_TENANT_ID)
            personas[value] = user_id

        # A MANAGER with a **pre-existing** explicit link: it must survive.
        linked = _seed_user(conn, "MANAGER", email="down-linked@test.com")
        _link_tenant(conn, linked, DEFAULT_TENANT_ID)
        manager_type = _legacy_type_id(conn, DEFAULT_TENANT_ID, "MANAGER")
        _link_type(conn, linked, manager_type)
        personas["linked-MANAGER"] = linked

        # An operator-granted permission on a legacy row, before the backfill.
        conn.execute(
            text(
                "UPDATE user_type SET permissions = '[\"finance:read\"]' "
                "WHERE id = :id"
            ),
            {"id": manager_type},
        )

        root = _seed_user(
            conn, "DIRECTOR", email="down-root@test.com", is_superuser=True
        )
        _link_tenant(conn, root, DEFAULT_TENANT_ID)
        personas["superuser"] = root

    _run_alembic("upgrade", "head")

    # A user created **after** `0033`, with one legacy membership.
    with pg_engine_at_0031.begin() as conn:
        newcomer = uuid.uuid4()
        conn.execute(
            text(
                'INSERT INTO "user" '
                "(id, email, hashed_password, full_name, is_active, cpf, "
                " is_superuser) "
                "VALUES (:id, 'down-new@test.com', 'x', 'Newcomer', true, :cpf, "
                "false)"
            ),
            {"id": newcomer, "cpf": str(next(_CPF))},
        )
        resident_role = conn.execute(
            text(
                "SELECT id FROM role WHERE tenant_id = :t AND name = "
                "'Morador (papel)'"
            ),
            {"t": DEFAULT_TENANT_ID},
        ).scalar_one()
        conn.execute(
            text(
                "INSERT INTO user_role_link (user_id, role_id) "
                "VALUES (:u, :r)"
            ),
            {"u": newcomer, "r": resident_role},
        )

    _run_alembic("downgrade", "-1")

    with pg_engine_at_0031.connect() as conn:
        roles = dict(
            conn.execute(text('SELECT email, role::text FROM "user"')).all()
        )
        menus = (
            conn.execute(text("SELECT DISTINCT allowed_menus::text FROM role"))
            .scalars()
            .all()
        )
        bundles = dict(
            conn.execute(
                text("SELECT name, permissions::text FROM role WHERE role IS NOT NULL")
            ).all()
        )
        links = (
            conn.execute(
                text("SELECT user_id FROM user_role_link")
            )
            .scalars()
            .all()
        )

    _assert_pre_0033_schema_is_back(pg_engine_at_0031)

    # The **link-less majority** comes back with the role it had, not GUEST.
    for value in ("DIRECTOR", "MANAGER", "RESIDENT", "PORTEIRO", "GUEST"):
        assert roles[f"down-{value.lower()}@test.com"] == value, value
    # The pre-existing explicit link survives, and its user reads back MANAGER.
    assert roles["down-linked@test.com"] == "MANAGER"
    assert personas["linked-MANAGER"] in links
    # Every **backfill-created** link is gone, and only those. The
    # newcomer's link was created after `0033` and has no journal row, so it
    # survives — which is the correct behaviour and worth asserting, because
    # a replay that deleted every link would be indistinguishable from one
    # that deleted the right ones on a fixture without a post-`0033` user.
    assert set(links) == {personas["linked-MANAGER"], newcomer}
    # The superuser reads back ADMINISTRATOR, by the `is_superuser` clause.
    assert roles["down-root@test.com"] == "ADMINISTRATOR"
    # A post-`0033` user gets the precedence answer over its memberships.
    assert roles["down-new@test.com"] == "RESIDENT"
    # And nobody who was not a GUEST reads back as one.
    assert [email for email, value in roles.items() if value == "GUEST"] == [
        "down-guest@test.com"
    ]

    # `allowed_menus` is `[]` everywhere -- the whole of the loss.
    assert menus == ["[]"]
    # The journal replay emptied the backfilled bundles **without** discarding
    # the permission an operator had granted a legacy row beforehand.
    assert bundles["Gerente (papel)"] == '["finance:read"]'
    assert bundles["Diretor (papel)"] == "[]"

    _run_alembic("upgrade", "head")


def test_0033_downgrade_refuses_when_the_journal_has_been_dropped(
    pg_engine_at_0031,
):
    """§7.0 (b): the journal is **mandatory**, not best-effort.

    The alternative — reconstructing bundles and links from a literal — would
    silently produce a *different* install from the one that existed before
    `0033` and call it a rollback. Refusing is the honest option, and the
    operator is told up front (`AGENTS.md`) that dropping the table is a
    one-way door.
    """
    with pg_engine_at_0031.begin() as conn:
        user_id = _seed_user(conn, "DIRECTOR", email="journal@test.com")
        _link_tenant(conn, user_id, DEFAULT_TENANT_ID)

    _run_alembic("upgrade", "head")

    with pg_engine_at_0031.begin() as conn:
        conn.execute(text("DROP TABLE f5_backfill_journal"))

    result = _alembic("downgrade", "-1")

    assert result.returncode != 0
    assert "f5_backfill_journal is missing" in result.stderr

    # It refuses **before it changes a single thing**: no column recreated,
    # no rename undone, so the database is left at head, untouched.
    assert _current_revision(pg_engine_at_0031) == "0033_drop_user_role_and_menus"
    assert "role" not in _columns(pg_engine_at_0031, "user")
    assert "allowed_menus" not in _columns(pg_engine_at_0031, "role")
