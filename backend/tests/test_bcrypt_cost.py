"""The bcrypt cost factor: lowered for this suite, floored in production.

APRAS-108 cuts the suite's wall clock by lowering bcrypt's cost to 4 for the
test process only (``tests/conftest.py`` mutates the shared hasher). A production
bcrypt at cost 4 is a severe *silent* defect: every hash still verifies, no
endpoint changes behaviour, nothing logs. So the production floor lives in a
literal module constant with no configuration route at all, and the tests below
are what keep it that way.

Two routes could carry a value below 12 into production, and each gets a test:

1. deploy-time configuration -- an environment row or a ``.env`` entry. A
   subprocess proves that route is inert (``test_environment_cannot_lower_...``),
   and two static checks keep it closed against a future edit.
2. a code change -- caught by the ``>= 12`` ratchet on the constant plus
   ``test_the_constant_is_the_cost_actually_used``, which reads the cost out of a
   hash a fresh interpreter really computed.

That last test is what the bcrypt-5 bump changed most. passlib is gone (see
``app/core/security.BcryptHasher`` for why: 1.7.4 is its last release, from
2020, and it cannot initialise a bcrypt 5 backend at all), so there is no
``CryptContext.to_dict()`` to interrogate and no ``bcrypt__rounds`` key to count
occurrences of. The pin is now behavioural instead of lexical, which is
strictly stronger: counting tokens in ``security.py`` proved the constant was
*spelled* at the call site, whereas ``$2b$12$`` at the head of a real hash
proves 12 is the cost that was *applied*.

``tests/test_lint_hygiene.py`` is the precedent for enforcing a source-level
rule from the suite. The scan root here is ``app/``, so this module is free to
spell the tokens it forbids.
"""

from __future__ import annotations

import ast
import importlib.util
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from app.core import security
from app.core.config import Settings

BACKEND = Path(__file__).resolve().parent.parent
APP = BACKEND / "app"
SECURITY_PY = APP / "core" / "security.py"

#: The production floor. The constant in ``security.py`` may rise above this
#: (the test is a ratchet); it may never fall below it.
PRODUCTION_FLOOR = 12

#: The cost ``tests/conftest.py`` puts in force for this process.
TEST_ROUNDS = 4

#: A hash generated at cost 12, for password ``prod-era-password`` -- a stand-in
#: for every password already stored in production. It is checked in precisely
#: so a cost-4 hasher can be proven not to invalidate it.
PROD_ERA_HASH = "$2b$12$N7D1OMxeQ7i0SlTfVHsOBeqdzlUkVcv5iuFRBxtccYZ23TS2Ui5cq"
PROD_ERA_PASSWORD = "prod-era-password"

#: Every plausible spelling a deploy might use to try to configure the cost.
#: None of them is read anywhere, and that is the assertion.
CANDIDATE_ENV_NAMES = (
    "BCRYPT_ROUNDS",
    "BCRYPT_TEST_ROUNDS",
    "PASSLIB_BCRYPT_ROUNDS",
)

#: The APIs for deciding a stored hash is stale and rewriting it. passlib's
#: ``deprecated="auto"`` context had both; under a cost-4 hasher they call a
#: stored cost-12 hash stale, so one caller plus one production
#: misconfiguration would silently *downgrade* real users' hashes at login.
#: ``BcryptHasher`` implements neither, and no module under ``app/`` names
#: either -- both halves are asserted below.
REHASH_APIS = ("needs_update", "verify_and_update")


@dataclass(frozen=True)
class _FreshImport:
    """What a brand-new interpreter says about the cost it will really use."""

    constant: int
    hasher_rounds: int
    hash_prefix: str


#: Printed by the child, in this order. ``get_password_hash`` is called for
#: real: the cost bcrypt embeds in its output is the only evidence that cannot
#: be satisfied by a decorative constant.
_PROBE = (
    "from app.core import security\n"
    "print(security.BCRYPT_ROUNDS)\n"
    "print(security.password_hasher.rounds)\n"
    "print(security.get_password_hash('probe-password')[:7])\n"
)


def _fresh_import(**env_overrides: str) -> _FreshImport:
    """Import ``app.core.security`` in a child interpreter and report its cost.

    A child, not this process: ``conftest.py`` is not loaded there, so the
    suite's own cost-4 override cannot mask what production would do.
    """
    env = dict(os.environ, **env_overrides)
    env["PYTHONPATH"] = str(BACKEND)

    # Fixed argv, no shell, and the interpreter is this one: `S603`/`S607` are
    # already ignored for `tests/**` (pyproject), as for test_migrations_postgres.
    result = subprocess.run(
        [sys.executable, "-c", _PROBE],
        cwd=BACKEND,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        # Bounded for the reason `tests/test_assert_no_skips.py` states at
        # length: an unbounded `capture_output=True` child is a parent that can
        # hang for the whole of the job's `timeout-minutes`, and a cancelled
        # job publishes no logs. One interpreter start, one import, one hash at
        # the production cost (~0.25 s).
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    lines = result.stdout.split()
    assert len(lines) == 3, f"probe printed {lines!r}, expected 3 values"
    return _FreshImport(
        constant=int(lines[0]),
        hasher_rounds=int(lines[1]),
        hash_prefix=lines[2],
    )


def _code_without_docstrings(path: Path) -> str:
    """Return ``path``'s source with every comment and docstring removed.

    The token checks below are defined on the result, because the comment and
    docstrings that document the constant must be free to name the very things
    the rule forbids -- ``security.py`` explains at length that it reads no
    environment, and a lexical rule that forbade saying so would forbid its own
    mandated explanation. ``ast.unparse`` drops comments for free; the docstring
    deletion is explicit.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(
            node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef
        ):
            continue
        body = node.body
        if (
            body
            and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)
        ):
            node.body = body[1:] or [ast.Pass()]
    return ast.unparse(tree)


def _py_files(root: Path) -> list[Path]:
    return sorted(root.rglob("*.py"))


def test_environment_cannot_lower_the_production_cost() -> None:
    """Route 1: no environment variable configures the cost.

    The child sees every candidate name set to 4 and must still build its hasher
    at the constant's value and stamp that value into a hash it really computes.

    Asserted against the constant rather than against the literal 12, because
    the floor is a ratchet: a deliberate raise to 13 is allowed, and a test that
    demanded exactly 12 here would make the *upper* side of the ratchet a
    failure too. What this test is about is that the environment changed nothing.
    """
    overrides = {name: str(TEST_ROUNDS) for name in CANDIDATE_ENV_NAMES}
    report = _fresh_import(**overrides)
    expected = security.BCRYPT_ROUNDS

    # Anchor: the ratchet still holds, so "unchanged" also means "not weak".
    assert expected >= PRODUCTION_FLOOR

    assert report.hasher_rounds == expected, (
        "a fresh import of app.core.security, with "
        f"{list(CANDIDATE_ENV_NAMES)} all set to {TEST_ROUNDS}, must still build "
        f"its hasher at BCRYPT_ROUNDS ({expected}); it reported "
        f"{report.hasher_rounds}. The cost must not be configurable by "
        "environment -- see APRAS-108 D1."
    )
    assert report.hash_prefix == f"$2b${expected:02d}$", (
        "and the hash that same interpreter computed must carry cost "
        f"{expected}; it began {report.hash_prefix!r}."
    )


def test_the_production_floor_constant_is_a_ratchet() -> None:
    """Route 2: the constant may rise above 12, never below it."""
    assert security.BCRYPT_ROUNDS >= PRODUCTION_FLOOR, (
        f"app/core/security.py lowered the production bcrypt cost to "
        f"{security.BCRYPT_ROUNDS}; {PRODUCTION_FLOOR} is the floor. The test "
        "suite lowers the *hasher* from conftest.py, never this constant."
    )


def test_the_constant_is_the_cost_actually_used() -> None:
    """The constant must not become decorative beside a separate literal.

    Read from a child interpreter, with no environment overrides at all, so
    this is production's own arithmetic: the constant, the cost the hasher
    carries, and the cost bcrypt wrote into a real hash must be one number.
    """
    report = _fresh_import()

    # Anchor: the child really did produce a bcrypt hash before anything below
    # reads a cost out of its prefix.
    assert report.hash_prefix.startswith("$2b$"), (
        f"probe did not return a bcrypt 2b hash; got {report.hash_prefix!r}"
    )
    applied_cost = int(report.hash_prefix.removeprefix("$2b$").rstrip("$"))

    assert report.constant == report.hasher_rounds == applied_cost, (
        "app/core/security.py must hand BCRYPT_ROUNDS to the hasher and nothing "
        f"else: the constant is {report.constant}, the hasher carries "
        f"{report.hasher_rounds}, and the cost bcrypt actually applied is "
        f"{applied_cost}. A constant that does not reach the hasher is a floor "
        "that floors nothing."
    )
    assert applied_cost >= PRODUCTION_FLOOR, (
        f"the cost a fresh interpreter applies is {applied_cost}; "
        f"{PRODUCTION_FLOOR} is the floor."
    )


def test_security_module_reads_no_environment_for_the_cost() -> None:
    """Keeps route 1 closed against a future edit to ``security.py``."""
    code = _code_without_docstrings(SECURITY_PY)

    # Anchor: assert the thing exists before asserting what it lacks. Without
    # this, a `_code_without_docstrings` that silently returned "" would make
    # every absence below vacuously true.
    # Written against the constant's current value rather than the literal 12,
    # because the ratchet above deliberately allows the cost to *rise*: an
    # anchor spelling `= 12` would turn a legitimate increase into a failure
    # here, which is a second, silent floor.
    assert f"BCRYPT_ROUNDS = {security.BCRYPT_ROUNDS}" in code, (
        "the stripped source of app/core/security.py must still contain the "
        "constant's assignment; the checks below are meaningless otherwise."
    )

    for token in ("os.environ", "getenv"):
        assert token not in code, (
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


def test_the_hasher_implements_no_rehash_api() -> None:
    """Having no such method beats having no caller for one.

    passlib's context offered ``needs_update``/``verify_and_update`` whether we
    wanted them or not, so the passlib-era guarantee could only ever be "no
    caller exists". ``BcryptHasher`` simply does not implement them.
    """
    # Anchor: the hasher is a real, usable hasher before we assert what it
    # lacks -- an empty object would pass every `hasattr` check below.
    assert callable(security.password_hasher.hash)
    assert callable(security.password_hasher.verify)
    assert security.password_hasher.verify(
        "anchor-password", security.password_hasher.hash("anchor-password")
    )

    present = [api for api in REHASH_APIS if hasattr(security.password_hasher, api)]
    assert not present, (
        f"the password hasher must implement none of {list(REHASH_APIS)}; it "
        f"has {present}. Under this suite's cost-4 hasher such a method calls a "
        "stored cost-12 hash stale, so one caller plus one production "
        "misconfiguration would silently downgrade real users' hashes at login."
    )


def test_app_never_rehashes_a_stored_password() -> None:
    """And no *code* under ``app/`` may call one either.

    Comments and docstrings are stripped first, for the same reason as in
    ``test_security_module_reads_no_environment_for_the_cost``: ``security.py``
    documents at length that its hasher has neither method, and a rule that
    forbade saying so would forbid its own explanation.
    """
    # Anchor: the scan walked the package and its stripping really does leave
    # code behind -- an empty result would make the absence below vacuous.
    files = _py_files(APP)
    assert SECURITY_PY in files, (
        f"the app/ scan found {len(files)} files but not {SECURITY_PY}"
    )
    sources = {path: _code_without_docstrings(path) for path in files}
    assert "def verify_password" in sources[SECURITY_PY], (
        "the stripped source of app/core/security.py must still contain its "
        "function definitions; the scan below is meaningless otherwise."
    )

    callers = {
        path.relative_to(BACKEND).as_posix(): token
        for path, code in sources.items()
        for token in REHASH_APIS
        if token in code
    }
    assert not callers, (
        f"no *.py file under app/ may call {list(REHASH_APIS)}; found "
        f"{sorted(callers)}."
    )


def test_passlib_is_not_installed() -> None:
    """The bump's whole point: nothing may reintroduce the dead dependency.

    passlib 1.7.4 (2020-10-08, its last release) cannot initialise a bcrypt 5
    backend, so ``passlib[bcrypt]`` back in ``pyproject.toml`` would resolve
    bcrypt back below 5 and undo this change silently.
    """
    # Anchor: find_spec really does locate an installed distribution here.
    assert importlib.util.find_spec("bcrypt") is not None, (
        "bcrypt itself must be importable; otherwise the absence below proves "
        "nothing about passlib."
    )
    assert importlib.util.find_spec("passlib") is None, (
        "passlib is installed again. It is unmaintained and incompatible with "
        "bcrypt 5: it probes its backend by hashing an over-long secret, which "
        "bcrypt 5 rejects, and reads a version attribute bcrypt 5 removed. "
        "app/core/security.BcryptHasher replaced it."
    )


def test_a_production_era_hash_still_verifies() -> None:
    """bcrypt carries its cost in the hash; verification reads it, not ours."""
    assert security.password_hasher.rounds == TEST_ROUNDS, (
        "this test is only meaningful under the suite's lowered cost; "
        f"the hasher carries {security.password_hasher.rounds}."
    )
    assert security.verify_password(PROD_ERA_PASSWORD, PROD_ERA_HASH) is True
    assert security.verify_password("not-the-password", PROD_ERA_HASH) is False


def test_hashes_made_in_the_suite_use_the_lowered_cost() -> None:
    """Without this, a silent revert to cost 12 would cost ~460 s per run."""
    hashed = security.get_password_hash("some-password")
    assert hashed.startswith(f"$2b${TEST_ROUNDS:02d}$"), (
        f"hashes created inside the suite must be cost {TEST_ROUNDS}; got "
        f"{hashed[:7]!r}. Is the `password_hasher.rounds = {TEST_ROUNDS}` line "
        "in tests/conftest.py still in force?"
    )
    assert security.verify_password("some-password", hashed) is True
