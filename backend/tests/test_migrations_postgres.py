"""Postgres-only regression test for the ``userrole`` enum (APRAS-27).

SQLite (used by the rest of the test suite via ``conftest.py``) stores enum
columns as a plain ``VARCHAR`` with no native constraint, so it cannot catch
``psycopg2.errors.InvalidTextRepresentation``-style failures that only occur
against a real PostgreSQL ``userrole`` enum type. These tests exercise the
Alembic migration chain against a real Postgres instance to prove that
``RESIDENT`` (added by migration ``0014_add_resident_userrole``) and
``PORTEIRO`` (added by migration ``0018_add_porteiro_userrole``, APRAS-12)
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
    """Downgrading 0018 removes exactly the 5 seeded role rows and the role
    column, without touching admin-created (role IS NULL) types."""
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
    # "-1": later migrations (0019+, including APRAS-11's 0021) have moved
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
    """Downgrading the head migration (currently 0018_add_porteiro_userrole)
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
    _run_alembic("downgrade", "0023_add_space_reservation_tables")

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

    _run_alembic("downgrade", "0023_add_space_reservation_tables")

    with migrated_pg_engine.connect() as conn:
        visible_to_id = conn.execute(
            text("SELECT visible_to_id FROM task WHERE id = :id"), {"id": task_id}
        ).scalar_one()

    assert visible_to_id in (type_a, type_b)

    # Restore head so other tests in this module are unaffected by ordering.
    _run_alembic("upgrade", "head")
