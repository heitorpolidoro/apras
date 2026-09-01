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
    alembic_bin = os.path.join(os.path.dirname(sys.executable), "alembic")
    env = {**os.environ, "POSTGRES_URL": TEST_POSTGRES_URL, "SECRET_KEY": "test-migration-secret"}
    result = subprocess.run(
        [alembic_bin, *args],
        cwd=_BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"alembic {' '.join(args)} failed:\nstdout={result.stdout}\nstderr={result.stderr}"
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


def test_userrole_enum_contains_resident(migrated_pg_engine):
    """The Postgres userrole enum must include RESIDENT after migrating to head."""
    with migrated_pg_engine.connect() as conn:
        labels = (
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
    assert set(labels) == {
        "ADMINISTRATOR",
        "DIRECTOR",
        "MANAGER",
        "GUEST",
        "RESIDENT",
        "PORTEIRO",
    }


def test_userrole_enum_contains_porteiro(migrated_pg_engine):
    """The Postgres userrole enum must include PORTEIRO after migrating to
    head (APRAS-12), not just the Python-side ``UserRole`` enum (APRAS-27
    lesson: a Python enum addition is not proof the DB was ever migrated)."""
    with migrated_pg_engine.connect() as conn:
        labels = (
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
    assert "PORTEIRO" in labels


def test_insert_user_with_porteiro_role_succeeds(migrated_pg_engine):
    """Regression test: inserting role='PORTEIRO' must not raise
    psycopg2.errors.InvalidTextRepresentation against real Postgres."""
    user_id = uuid.uuid4()
    with migrated_pg_engine.begin() as conn:
        conn.execute(
            text(
                'INSERT INTO "user" '
                "(id, email, hashed_password, full_name, role, is_active, cpf) "
                "VALUES (:id, :email, 'x', 'Porteiro Regression Test', "
                "'PORTEIRO', true, :cpf)"
            ),
            {"id": user_id, "email": f"porteiro-{user_id}@test.com", "cpf": "12345678909"},
        )

    with migrated_pg_engine.connect() as conn:
        role = conn.execute(
            text('SELECT role FROM "user" WHERE id = :id'), {"id": user_id}
        ).scalar_one()
    assert role == "PORTEIRO"


def test_insert_user_with_resident_role_succeeds(migrated_pg_engine):
    """Regression test: inserting role='RESIDENT' must not raise
    psycopg2.errors.InvalidTextRepresentation against real Postgres."""
    user_id = uuid.uuid4()
    with migrated_pg_engine.begin() as conn:
        conn.execute(
            text(
                'INSERT INTO "user" '
                "(id, email, hashed_password, full_name, role, is_active, cpf) "
                "VALUES (:id, :email, 'x', 'Resident Regression Test', "
                "'RESIDENT', true, :cpf)"
            ),
            {"id": user_id, "email": f"resident-{user_id}@test.com", "cpf": "52998224725"},
        )

    with migrated_pg_engine.connect() as conn:
        role = conn.execute(
            text('SELECT role FROM "user" WHERE id = :id'), {"id": user_id}
        ).scalar_one()
    assert role == "RESIDENT"


# ---------------------------------------------------------------------------
# 0018_add_role_to_user_type (APRAS-9) – seeded role-linked UserType rows
# ---------------------------------------------------------------------------


def test_user_type_role_seeds_five_rows(migrated_pg_engine):
    """Exactly one UserType row per UserRole value is seeded, each starting
    with allowed_menus == [] and a "(papel)"-suffixed name."""
    with migrated_pg_engine.connect() as conn:
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


def test_user_type_role_unique_constraint_rejects_duplicate_role(migrated_pg_engine):
    """A second UserType row with the same non-null role is rejected."""
    with pytest.raises(Exception, match="duplicate key|unique constraint"):
        with migrated_pg_engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO user_type (id, name, allowed_menus, role) "
                    "VALUES (:id, 'Duplicate Director', '[]', 'DIRECTOR')"
                ),
                {"id": uuid.uuid4()},
            )


def test_user_type_role_unique_constraint_allows_multiple_null_roles(
    migrated_pg_engine,
):
    """Multiple admin-created UserTypes with role=NULL are all allowed: a
    UNIQUE constraint never treats two NULLs as duplicates of each other."""
    id_a, id_b = uuid.uuid4(), uuid.uuid4()
    with migrated_pg_engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO user_type (id, name, allowed_menus, role) "
                "VALUES (:id, :name, '[]', NULL)"
            ),
            {"id": id_a, "name": f"Admin Type A {id_a}"},
        )
        conn.execute(
            text(
                "INSERT INTO user_type (id, name, allowed_menus, role) "
                "VALUES (:id, :name, '[]', NULL)"
            ),
            {"id": id_b, "name": f"Admin Type B {id_b}"},
        )

    with migrated_pg_engine.connect() as conn:
        count = conn.execute(
            text(
                "SELECT count(*) FROM user_type WHERE id = :a OR id = :b"
            ),
            {"a": id_a, "b": id_b},
        ).scalar_one()
    assert count == 2


def test_user_type_role_downgrade_removes_seeded_rows_only(migrated_pg_engine):
    """Downgrading past 0018 removes exactly the 5 seeded role rows and the
    role column, without touching admin-created (role IS NULL) types.

    Targets the explicit revision id rather than a relative "-N" step count:
    later migrations (0019, 0020, 0021, ...) keep getting chained on top of
    0018 as new features land, so a relative offset silently drifts out of
    sync with the actual head every time that happens."""
    survivor_id = uuid.uuid4()
    survivor_name = f"Survivor {survivor_id}"
    with migrated_pg_engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO user_type (id, name, allowed_menus, role) "
                "VALUES (:id, :name, '[]', NULL)"
            ),
            {"id": survivor_id, "name": survivor_name},
        )

    # Target 0018's own down_revision explicitly rather than a relative
    # "-1": later migrations (0019+, including APRAS-11's 0024) have moved
    # head further away from 0018 since this test was written, so "-1"
    # would silently downgrade whatever migration currently happens to sit
    # at head instead of 0018 itself.
    _run_alembic("downgrade", "0017_add_user_type_allowed_menus")

    with migrated_pg_engine.connect() as conn:
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
        remaining_names = conn.execute(text("SELECT name FROM user_type")).scalars().all()

    assert "role" not in columns
    assert survivor_name in remaining_names
    assert not any("(papel)" in name for name in remaining_names)

    # Restore head so the module-scoped engine's state is unaffected for
    # any other test relying on it.
    _run_alembic("upgrade", "head")


def test_downgrade_is_a_safe_noop(migrated_pg_engine):
    """Downgrading the head migration (currently 0020_add_porteiro_userrole)
    must not remove the enum value or fail (matching the precedent set by
    0003_add_guest_to_userrole_enum.py / 0014_add_resident_userrole.py:
    Postgres cannot drop enum values, so the downgrade is a documented
    no-op)."""
    _run_alembic("downgrade", "-1")

    with migrated_pg_engine.connect() as conn:
        labels = (
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
    # RESIDENT and PORTEIRO both remain in the type even though the
    # migration is "downgraded", since Postgres has no DROP VALUE for enums.
    assert "RESIDENT" in labels
    assert "PORTEIRO" in labels

    # Restore head so other tests in this module are unaffected by ordering.
    _run_alembic("upgrade", "head")


# ---------------------------------------------------------------------------
# 0024_task_visible_to_m2m (APRAS-11) – Task.visible_to becomes many-to-many
# ---------------------------------------------------------------------------


def test_task_visible_to_id_backfilled_into_join_table(migrated_pg_engine):
    """A task's existing single `visible_to_id` becomes a one-row
    `task_visible_to_link` entry after upgrading past 0021, and the
    `visible_to_id` column itself is dropped."""
    _run_alembic("downgrade", "0023_add_reservation_tables")

    user_type_id = uuid.uuid4()
    user_id = uuid.uuid4()
    task_id = uuid.uuid4()
    with migrated_pg_engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO user_type (id, name, allowed_menus) "
                "VALUES (:id, :name, '[]')"
            ),
            {"id": user_type_id, "name": f"Migration Type {user_type_id}"},
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
            {"id": task_id, "created_by_id": user_id, "visible_to_id": user_type_id},
        )

    _run_alembic("upgrade", "head")

    with migrated_pg_engine.connect() as conn:
        links = conn.execute(
            text(
                "SELECT task_id, user_type_id FROM task_visible_to_link "
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
    assert links[0].user_type_id == user_type_id
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
                "(id, email, hashed_password, full_name, role, is_active, cpf) "
                "VALUES (:id, :email, 'x', 'Downgrade Test', 'ADMINISTRATOR', "
                "true, :cpf)"
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
                text(
                    "INSERT INTO user_type (id, name, allowed_menus) "
                    "VALUES (:id, :name, '[]')"
                ),
                {"id": type_id, "name": f"{name} {type_id}"},
            )
        conn.execute(
            text(
                "INSERT INTO task_visible_to_link (task_id, user_type_id) "
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
    "user_type",
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
    "user_user_type_link",
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
    assert _current_revision(isolated_pg_engine) == "0031_add_user_is_superuser"


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
    assert _current_revision(pg_engine_at_0027) == "0031_add_user_is_superuser"

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
    """`permissions` is json NOT NULL DEFAULT '[]' at head, a `user_type` row
    seeded before the migration back-fills to `[]`, and downgrading to 0029
    removes the column again."""
    user_type_id = uuid.uuid4()
    with pg_engine_at_0027.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO user_type (id, name, allowed_menus) "
                "VALUES (:id, :name, '[]')"
            ),
            {"id": user_type_id, "name": f"Bundle Test {user_type_id}"},
        )

    _run_alembic("upgrade", "head")
    assert _current_revision(pg_engine_at_0027) == "0031_add_user_is_superuser"

    with pg_engine_at_0027.connect() as conn:
        column = conn.execute(
            text(
                "SELECT data_type, is_nullable, column_default "
                "FROM information_schema.columns "
                "WHERE table_name = 'user_type' AND column_name = 'permissions'"
            )
        ).one()
        bundles = (
            conn.execute(
                text("SELECT permissions::text FROM user_type WHERE id = :id"),
                {"id": user_type_id},
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
                    "WHERE table_name = 'user_type'"
                )
            )
            .scalars()
            .all()
        )
    assert "permissions" not in columns

    _run_alembic("upgrade", "head")


def test_no_user_type_row_has_permissions_after_migration(isolated_pg_engine):
    """NOTHING is seeded, including by any earlier migration's seeded rows."""
    with isolated_pg_engine.connect() as conn:
        non_empty = conn.execute(
            text(
                "SELECT count(*) FROM user_type "
                "WHERE permissions::text <> '[]'"
            )
        ).scalar_one()

    assert non_empty == 0


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
    assert _current_revision(pg_engine_at_0027) == "0031_add_user_is_superuser"

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
