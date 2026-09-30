"""The suite must not be able to hang a CI job silently.

`Backend Tests` was cancelled at 55m0s twice in a row (jobs 109644454563 and
109661776896) on a commit whose backend tree was byte-identical to one that
had passed in 10m57s minutes earlier -- the diff was six files, all of them
under `frontend/src`. Neither run said where it stopped, because a job killed
by `timeout-minutes` is *cancelled*, and GitHub publishes no logs for a
cancelled job.

The fix is three guards, and this module is what keeps them in place:

1. every `subprocess.run` in the test tree passes a `timeout` -- an unbounded
   child that never exits is a parent that never exits, and five of the seven
   call sites had none;
2. `pytest.ini` caps a single test and asks for `pytest-timeout`'s `thread`
   method, which dumps every thread's stack on the way out;
3. both backend pytest invocations in `ci.yml` are wrapped in `timeout`, so
   the next hang fails a *step* -- which keeps its log -- instead of
   cancelling the job, which does not.

A fourth rule is about the leak that was found while looking for the hang:
every engine the test tree builds is disposed. `tests/conftest.py`'s per-test
engine was not, and `StaticPool` holds the one connection that *is* an
in-memory SQLite database, so ~4000 of them were closed by the garbage
collector whenever it got round to them -- which is what produced the
`ResourceWarning: unclosed database` flood, and which made the process's real
connection count a function of GC timing rather than of the suite.
"""

from __future__ import annotations

import ast
import configparser
import pathlib
import re

BACKEND = pathlib.Path(__file__).resolve().parent.parent
TESTS = BACKEND / "tests"
SCRIPTS = BACKEND / "scripts"
PYTEST_INI = BACKEND / "pytest.ini"
PYPROJECT = BACKEND / "pyproject.toml"
CI_YML = BACKEND.parent / ".github" / "workflows" / "ci.yml"

#: The ceiling on `pytest.ini`'s per-test cap. It exists so the cap cannot be
#: raised into irrelevance: at 600s a run of the ~4100 collected cases would
#: still be killed by `ci.yml`'s 30-minute wrapper long before the cap fired,
#: and the point of the cap is to name the *one* test that is stuck.
MAX_PER_TEST_TIMEOUT = 600


def _py_files(root: pathlib.Path) -> list[pathlib.Path]:
    return sorted(root.rglob("*.py"))


def test_every_subprocess_run_in_the_test_tree_passes_a_timeout() -> None:
    """A child with no timeout is a hang with no upper bound.

    `subprocess.run(..., capture_output=True)` with no `timeout` blocks the
    parent for as long as the child lives *and* until its pipes close. Two of
    these start a fresh interpreter, one of them a whole nested pytest
    collection; `alembic upgrade` is the fifth. None of them can be allowed to
    own the runner.
    """
    offenders: list[str] = []
    for path in _py_files(TESTS) + _py_files(SCRIPTS):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if ast.unparse(node.func) not in {
                "subprocess.run",
                "subprocess.check_output",
            }:
                continue
            if not any(keyword.arg == "timeout" for keyword in node.keywords):
                offenders.append(
                    f"{path.relative_to(BACKEND)}:{node.lineno} "
                    f"{ast.unparse(node.func)}(...) has no timeout="
                )
    assert not offenders, "unbounded subprocess call(s):\n" + "\n".join(offenders)


def test_every_engine_built_in_the_test_tree_is_disposed() -> None:
    """A module that calls `create_engine` also calls `dispose`.

    Deliberately per *module* rather than per call site: the two shapes in use
    are a fixture that disposes in its teardown and a context manager that
    disposes in its `finally`, and no AST rule distinguishes either from a
    leak without re-implementing escape analysis. Per module is enough to make
    a forgotten `dispose()` fail here, which is the regression this guards.
    """
    offenders: list[str] = []
    for path in _py_files(TESTS):
        if path.resolve() == pathlib.Path(__file__).resolve():
            continue
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        builds = [
            node.lineno
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and ast.unparse(node.func).endswith("create_engine")
        ]
        if not builds:
            continue
        disposes = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and ast.unparse(node.func).endswith(".dispose")
        ]
        if not disposes:
            offenders.append(
                f"{path.relative_to(BACKEND)} builds an engine at line(s) "
                f"{builds} and never disposes one"
            )
    assert not offenders, "undisposed engine(s):\n" + "\n".join(offenders)


def _pytest_ini() -> configparser.SectionProxy:
    parser = configparser.ConfigParser()
    parser.read(PYTEST_INI, encoding="utf-8")
    return parser["pytest"]


def test_pytest_ini_caps_a_single_test() -> None:
    """Without a cap the first stuck test owns the job until it is cancelled."""
    section = _pytest_ini()
    assert "timeout" in section, f"{PYTEST_INI.name} declares no `timeout`"
    timeout = int(section["timeout"])
    assert 0 < timeout <= MAX_PER_TEST_TIMEOUT, timeout


def test_pytest_ini_uses_the_thread_timeout_method() -> None:
    """`signal` is not enough, and the difference is the whole point.

    pytest-timeout's default method raises `SIGALRM` in the *main* thread, so
    it cannot interrupt a wait inside a helper thread -- which is exactly the
    shape a leaked `TestClient` portal or an unjoined pool thread produces.
    The `thread` method dumps every stack and ends the process, which is the
    evidence the two cancelled runs could not produce.
    """
    assert _pytest_ini().get("timeout_method") == "thread"


def test_pytest_timeout_is_a_declared_dev_dependency() -> None:
    """The ini options above are inert without the plugin that reads them."""
    text = PYPROJECT.read_text(encoding="utf-8")
    assert re.search(r'"pytest-timeout[><=~]', text), (
        "pytest.ini asks for a per-test timeout; pyproject.toml must declare "
        "pytest-timeout in its dev group or the setting is silently ignored"
    )


def _run_blocks() -> list[tuple[int, str]]:
    """Every `run: |` block in `ci.yml`, as `(first line number, body)`.

    Read by indentation rather than with a YAML parser: the backend has no
    YAML dependency, adding one for a four-line scan is not worth it, and the
    file is machine-generated by nobody.
    """
    lines = CI_YML.read_text(encoding="utf-8").splitlines()
    blocks: list[tuple[int, str]] = []
    for index, line in enumerate(lines):
        match = re.match(r"^(\s*)-?\s*(?:name:.*)?run:\s*\|\s*$", line)
        if match is None:
            continue
        indent = len(match.group(1))
        body: list[str] = []
        for following in lines[index + 1 :]:
            if following.strip() and len(following) - len(following.lstrip()) <= indent:
                break
            body.append(following)
        blocks.append((index + 1, "\n".join(body)))
    return blocks


def test_every_ci_pytest_invocation_is_wrapped_in_timeout() -> None:
    """The guard that makes the next hang readable.

    `timeout-minutes` cancels the job and GitHub publishes no logs for a
    cancelled job; `timeout` fails the step, and a failed step keeps
    everything pytest printed -- including pytest-timeout's thread dump.
    """
    invocations = [
        (lineno, body) for lineno, body in _run_blocks() if "uv run pytest" in body
    ]
    assert invocations, "no `uv run pytest` step found in ci.yml"
    unwrapped = [
        f"{CI_YML.name}:{lineno}"
        for lineno, body in invocations
        if "timeout --signal=INT" not in body
    ]
    assert not unwrapped, "pytest invocation(s) not wrapped in `timeout`: " + ", ".join(
        unwrapped
    )


def test_the_backend_job_still_carries_its_job_level_backstop() -> None:
    """The wrapper is the first guard, not a replacement for the last one."""
    assert re.search(
        r"^\s*timeout-minutes:\s*\d+\s*$",
        CI_YML.read_text(encoding="utf-8"),
        re.MULTILINE,
    )
