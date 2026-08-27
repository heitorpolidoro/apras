"""Postgres-only regression test for the ``userrole`` enum (APRAS-27).

SQLite (used by the rest of the test suite via ``conftest.py``) stores enum
columns as a plain ``VARCHAR`` with no native constraint, so it cannot catch
``psycopg2.errors.InvalidTextRepresentation``-style failures that only occur
against a real PostgreSQL ``userrole`` enum type. These tests exercise the
Alembic migration chain against a real Postgres instance to prove that
``RESIDENT`` (added by migration ``0014_add_resident_userrole``) is actually
insertable.

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
    assert set(labels) == {"ADMINISTRATOR", "DIRECTOR", "MANAGER", "GUEST", "RESIDENT"}


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


def test_downgrade_is_a_safe_noop(migrated_pg_engine):
    """Downgrading 0014 must not remove the enum value or fail (matching the
    precedent set by 0003_add_guest_to_userrole_enum.py: Postgres cannot drop
    enum values, so the downgrade is a documented no-op)."""
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
    # RESIDENT remains in the type even though the migration is "downgraded",
    # since Postgres has no DROP VALUE for enums.
    assert "RESIDENT" in labels

    # Restore head so other tests in this module are unaffected by ordering.
    _run_alembic("upgrade", "head")
