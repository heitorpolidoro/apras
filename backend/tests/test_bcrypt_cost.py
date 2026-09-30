"""The bcrypt cost factor: lowered for this suite, floored in production.

APRAS-108 cuts the suite's wall clock by lowering bcrypt's cost to 4 for the
test process only (``tests/conftest.py`` mutates the shared ``CryptContext``).
A production bcrypt at cost 4 is a severe *silent* defect: every hash still
verifies, no endpoint changes behaviour, nothing logs. So the production floor
lives in a literal module constant with no configuration route at all, and the
tests below are what keep it that way.

Two routes could carry a value below 12 into production, and each gets a test:

1. deploy-time configuration -- an environment row or a ``.env`` entry. A
   subprocess proves that route is inert (``test_environment_cannot_lower_...``),
   and two static checks keep it closed against a future edit.
2. a code change -- caught by the ``>= 12`` ratchet on the constant plus the
   source check that the constant is the value actually handed to passlib.

``tests/test_lint_hygiene.py`` is the precedent for enforcing a source-level
rule from the suite. The scan root here is ``app/``, so this module is free to
spell the tokens it forbids.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from app.core import security
from app.core.config import Settings

BACKEND = Path(__file__).resolve().parent.parent
APP = BACKEND / "app"
SECURITY_PY = APP / "core" / "security.py"
CONFIG_PY = APP / "core" / "config.py"

#: The production floor. The constant in ``security.py`` may rise above this
#: (the test is a ratchet); it may never fall below it.
PRODUCTION_FLOOR = 12

#: The cost ``tests/conftest.py`` puts in force for this process.
TEST_ROUNDS = 4

#: A hash generated at cost 12, for password ``prod-era-password`` -- a stand-in
#: for every password already stored in production. It is checked in precisely
#: so a cost-4 context can be proven not to invalidate it.
PROD_ERA_HASH = "$2b$12$N7D1OMxeQ7i0SlTfVHsOBeqdzlUkVcv5iuFRBxtccYZ23TS2Ui5cq"
PROD_ERA_PASSWORD = "prod-era-password"

#: Every plausible spelling a deploy might use to try to configure the cost.
#: None of them is read anywhere, and that is the assertion.
CANDIDATE_ENV_NAMES = (
    "BCRYPT_ROUNDS",
    "BCRYPT_TEST_ROUNDS",
    "PASSLIB_BCRYPT_ROUNDS",
)

#: passlib's own APIs for deciding a stored hash is stale and rewriting it.
#: ``needs_update`` on a cost-12 hash returns True under a cost-4 context, so
#: one caller plus one production misconfiguration would silently *downgrade*
#: real users' stored hashes at login. No caller exists; this keeps it so.
REHASH_APIS = ("needs_update", "verify_and_update")


def _strip_comments(source: str) -> str:
    """Drop, from every line, the ``#`` and everything after it.

    The counting rule in the token checks below is defined on the result. The
    comment that documents the constant must be free to name ``rounds``,
    ``BCRYPT_ROUNDS`` and ``bcrypt__rounds`` as often as it needs to, or the
    rule would forbid its own mandated explanation. ``security.py`` has no
    docstring naming these tokens, so comment-stripping is the whole
    normalisation and no AST walk is needed.
    """
    return "\n".join(line.split("#", 1)[0] for line in source.splitlines())


def _py_files(root: Path) -> list[Path]:
    return sorted(root.rglob("*.py"))


def test_environment_cannot_lower_the_production_cost() -> None:
    """Route 1: no environment variable configures the cost.

    Asserted from a fresh interpreter, so ``conftest.py`` -- and therefore this
    suite's own override -- is not loaded. The child sees every candidate name
    set to 4 and must still report 12.
    """
    env = dict(os.environ, **{name: str(TEST_ROUNDS) for name in CANDIDATE_ENV_NAMES})
    env["PYTHONPATH"] = str(BACKEND)

    # Fixed argv, no shell, and the interpreter is this one: `S603`/`S607` are
    # already ignored for `tests/**` (pyproject), as for test_migrations_postgres.
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from app.core.security import pwd_context\n"
                "print(pwd_context.to_dict()['bcrypt__rounds'])\n"
            ),
        ],
        cwd=BACKEND,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        # Bounded for the reason `tests/test_assert_no_skips.py` states at
        # length: an unbounded `capture_output=True` child is a parent that can
        # hang for the whole of the job's `timeout-minutes`, and a cancelled
        # job publishes no logs. One interpreter start and one import.
        timeout=60,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == str(PRODUCTION_FLOOR), (
        "a fresh import of app.core.security, with "
        f"{list(CANDIDATE_ENV_NAMES)} all set to {TEST_ROUNDS}, must still "
        f"build its CryptContext at {PRODUCTION_FLOOR} rounds; it reported "
        f"{result.stdout.strip()!r}. The cost must not be configurable by "
        "environment -- see APRAS-108 D1."
    )


def test_the_production_floor_constant_is_a_ratchet() -> None:
    """Route 2: the constant may rise above 12, never below it."""
    assert security.BCRYPT_ROUNDS >= PRODUCTION_FLOOR, (
        f"app/core/security.py lowered the production bcrypt cost to "
        f"{security.BCRYPT_ROUNDS}; {PRODUCTION_FLOOR} is the floor. The test "
        "suite lowers the *context* from conftest.py, never this constant."
    )


def test_the_constant_is_the_value_handed_to_passlib() -> None:
    """The constant must not become decorative beside a separate literal.

    Occurrences, not lines, and case-sensitive: lowercase ``rounds`` appears
    once (the keyword argument), ``BCRYPT_ROUNDS`` twice (its assignment and
    that argument's value -- its uppercase ``ROUNDS`` is invisible to the
    case-sensitive lowercase count).
    """
    stripped = _strip_comments(SECURITY_PY.read_text(encoding="utf-8"))

    assert stripped.count("rounds") == 1, (
        "outside comments, app/core/security.py must name lowercase `rounds` "
        f"exactly once -- the bcrypt__rounds keyword argument; found "
        f"{stripped.count('rounds')}."
    )
    assert stripped.count("BCRYPT_ROUNDS") == 2, (
        "outside comments, app/core/security.py must name BCRYPT_ROUNDS "
        "exactly twice -- the assignment and the keyword argument's value; "
        f"found {stripped.count('BCRYPT_ROUNDS')}."
    )
    for token in ("os.environ", "getenv"):
        assert token not in stripped, (
            f"app/core/security.py must not read {token}: configuration is the "
            "deploy-time route this task exists to close."
        )


def test_config_declares_no_cost_field() -> None:
    """Declaring the field is what would *create* the deploy-time override.

    ``Settings`` is ``case_sensitive=True`` and its resolved ``extra`` is
    ``forbid``, so an undeclared ``BCRYPT_ROUNDS`` row never reaches the code
    today. ``backend/.env.production`` exists on disk, which makes that route
    concrete rather than hypothetical.
    """
    offenders = [
        name
        for name in Settings.model_fields
        if "BCRYPT" in name.upper() or "ROUNDS" in name.upper()
    ]
    assert not offenders, (
        "app/core/config.py must declare no settings field naming BCRYPT or "
        f"ROUNDS; found {offenders}. Such a field would let an environment row "
        "weaken production bcrypt with no code change and no diff."
    )


def test_app_never_rehashes_a_stored_password() -> None:
    """No module under ``app/`` may decide a stored hash is stale."""
    callers = {
        path.relative_to(BACKEND).as_posix(): token
        for path in _py_files(APP)
        for token in REHASH_APIS
        if token in path.read_text(encoding="utf-8")
    }
    assert not callers, (
        f"no *.py file under app/ may name {list(REHASH_APIS)}; found "
        f"{sorted(callers)}. Under a cost-4 context passlib reports a stored "
        "cost-12 hash as needing an update, so a caller here plus one "
        "production misconfiguration would silently downgrade real users' "
        "hashes at login."
    )


def test_a_production_era_hash_still_verifies() -> None:
    """bcrypt carries its cost in the hash; verification reads it, not ours."""
    assert security.verify_password(PROD_ERA_PASSWORD, PROD_ERA_HASH) is True
    assert security.verify_password("not-the-password", PROD_ERA_HASH) is False


def test_hashes_made_in_the_suite_use_the_lowered_cost() -> None:
    """Without this, a silent revert to cost 12 would cost ~460 s per run."""
    hashed = security.get_password_hash("some-password")
    assert hashed.startswith(f"$2b${TEST_ROUNDS:02d}$"), (
        f"hashes created inside the suite must be cost {TEST_ROUNDS}; got "
        f"{hashed[:7]!r}. Is the pwd_context.update(bcrypt__rounds="
        f"{TEST_ROUNDS}) line in tests/conftest.py still in force?"
    )
    assert security.verify_password("some-password", hashed) is True
