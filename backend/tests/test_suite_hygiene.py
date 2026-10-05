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
import importlib
import pathlib
import re
import subprocess
import sys
import typing
from datetime import datetime

from pydantic import BaseModel

from app.schemas.base import ApiModel

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


def _ci_jobs() -> dict[str, list[str]]:
    """Every job in `ci.yml`, as `name -> the lines of its block`.

    Read by indentation for the same reason `_run_blocks` is: the backend has
    no YAML dependency and the file is machine-generated by nobody. A job key
    is a two-space-indented mapping key inside the top-level `jobs:` block.
    """
    lines = CI_YML.read_text(encoding="utf-8").splitlines()
    jobs: dict[str, list[str]] = {}
    current: str | None = None
    in_jobs = False
    for line in lines:
        if re.match(r"^jobs:\s*$", line):
            in_jobs = True
            continue
        if not in_jobs:
            continue
        if line.strip() and not line.startswith(" "):  # a new top-level key
            break
        match = re.match(r"^  ([A-Za-z0-9_-]+):\s*$", line)
        if match:
            current = match.group(1)
            jobs[current] = []
            continue
        if current is not None:
            jobs[current].append(line)
    return jobs


def test_every_ci_job_carries_a_timeout_minutes_declaration() -> None:
    """Every job, not just `backend`, or the next hang holds a runner for 6h.

    This *replaces* `test_the_backend_job_still_carries_its_job_level_backstop`,
    which searched the whole file for one `timeout-minutes:` line and so passed
    no matter which job carried it -- it survived deleting a declaration, which
    is the mutation it was supposed to catch (APRAS-119 §6b).

    `backend` is asserted by name as well as by the sweep, so nothing is lost
    in the replacement: without that, a scan that silently found no jobs at all
    would pass here.
    """
    jobs = _ci_jobs()
    assert "backend" in jobs, (
        f"the ci.yml job scan found {sorted(jobs)} and no `backend` job. That "
        "is a broken scan, not a workflow without backend tests."
    )
    without = sorted(
        name
        for name, body in jobs.items()
        if not any(re.match(r"^\s+timeout-minutes:\s*\d+\s*$", line) for line in body)
    )
    assert not without, (
        f"these ci.yml jobs carry no `timeout-minutes`: {without}. Each one can "
        "still burn GitHub's six-hour default, and a job killed that way is "
        "*cancelled*, which publishes no logs at all."
    )


# ---------------------------------------------------------------------------
# The shutdown watchdog, and the node id that made one necessary (APRAS-119)
# ---------------------------------------------------------------------------

#: The hook the watchdog must be armed from. `pytest-cov` writes `coverage.xml`
#: and evaluates `--cov-fail-under` inside its own `pytest_runtestloop`
#: wrapper, after the yield, so arming anywhere later -- `pytest_sessionfinish`,
#: `pytest_unconfigure`, `atexit` -- leaves the coverage write *outside* the
#: watchdog's window. That is the one thing this assertion is for.
ARMING_HOOK = "pytest_runtestloop"


def _function_named(tree: ast.Module, name: str) -> ast.FunctionDef | None:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    return None


def test_the_shutdown_watchdog_is_armed_from_the_hook_that_brackets_coverage() -> None:
    """The armed call itself, by AST -- never the word `faulthandler`.

    A test that greps `conftest.py` for `faulthandler` passes against a comment
    mentioning it, and `docs/audits/APRAS-111-test-suite-audit.md` records
    nineteen tests in this repository that asserted exactly that much. So what
    is matched here is the `faulthandler.dump_traceback_later(...)` **call
    node**, reached from the arming hook's own body, with its `exit` keyword --
    the three things that make the watchdog produce a stack instead of nothing:
    the hook that brackets the coverage write, the call, and `exit=True`, which
    is what ends the process rather than leaving the job to be cancelled with
    the stack trapped in an unpublished log.
    """
    tree = ast.parse((TESTS / "conftest.py").read_text(encoding="utf-8"))
    hook = _function_named(tree, ARMING_HOOK)
    assert hook is not None, (
        f"tests/conftest.py declares no `{ARMING_HOOK}` hook, so nothing arms "
        "the shutdown watchdog over the post-test-loop window"
    )

    decorators = [ast.unparse(decorator) for decorator in hook.decorator_list]
    assert any(
        "wrapper=True" in decorator and "trylast=True" in decorator
        for decorator in decorators
    ), (
        f"`{ARMING_HOOK}` must be declared "
        "`@pytest.hookimpl(wrapper=True, trylast=True)` -- pytest calls "
        "later-registered hookimpls first, so without `trylast` this conftest "
        "wrapper is the *outer* one and its post-yield code runs after "
        f"pytest-cov's, i.e. after the coverage write. Found: {decorators}"
    )

    armed = [
        node
        for node in ast.walk(hook)
        if isinstance(node, ast.Call)
        and ast.unparse(node.func) == "faulthandler.dump_traceback_later"
    ]
    assert armed, (
        f"`{ARMING_HOOK}` does not call "
        "`faulthandler.dump_traceback_later(...)`. Nothing else in the suite "
        "can produce a stack for a process that passes its tests and then "
        "never exits: `pytest-timeout` caps one *test*, and `ci.yml`'s "
        "`timeout` wrapper fails the step with whatever was printed, which on "
        "jobs 110014916546 and 110405490008 was not even a completed step."
    )
    exits = [
        keyword
        for call in armed
        for keyword in call.keywords
        if keyword.arg == "exit"
        and isinstance(keyword.value, ast.Constant)
        and keyword.value.value is True
    ]
    assert exits, (
        "the armed `faulthandler.dump_traceback_later(...)` call must pass "
        "`exit=True`. Without it the stack is dumped and the process keeps "
        "hanging, so the job is still cancelled and the dump is still in a log "
        f"GitHub never publishes. Found: {[ast.unparse(c) for c in armed]}"
    )

    # `wrapper=True` is new-style: a wrapper that falls off the end makes the
    # hook result `None`.
    yielded = [
        node.targets[0].id
        for node in hook.body
        if isinstance(node, ast.Assign)
        and isinstance(node.value, ast.Yield)
        and isinstance(node.targets[0], ast.Name)
    ]
    returned = [
        node.value.id
        for node in ast.walk(hook)
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Name)
    ]
    wrapper_contract = (
        f"`{ARMING_HOOK}` is a new-style (`wrapper=True`) hook wrapper, so it "
        "must return the value it received from `yield`; this one assigns "
        f"{yielded} and returns {returned}"
    )
    assert yielded, wrapper_contract
    assert set(yielded) <= set(returned), wrapper_contract


#: The ceiling on a collected node id, in characters. It exists because one id
#: in this tree used to be **2,097,259** characters long: a `parametrize` case
#: whose payload was `b"x" * (LOGO_MAX_FILE_SIZE + 1)` and which had no `ids=`,
#: so pytest built the id out of the payload. Every other id in the tree fits
#: in 316 characters, so 1024 leaves generous room for a long parametrised id
#: and none at all for a payload.
MAX_NODE_ID = 1024

#: The vacuity floor. The suite collects ~4195 cases; a collection that errored
#: or that resolved nothing must not pass this test by finding no long ids.
MIN_COLLECTED = 4000

#: `capture_output=True` with no timeout blocks until the child's pipes close,
#: which is the hang this whole module exists to prevent.
COLLECT_TIMEOUT = 300


def test_no_collected_node_id_can_carry_a_payload() -> None:
    """One 2 MiB line is 68.8 minutes of runner time. Measured, not estimated.

    This is the guard on APRAS-119's root cause. A `parametrize` case with a
    large binary payload and no `ids=` gets a node id built out of that
    payload, and any output naming the case -- a warnings-summary entry, a
    failure header, `-v` -- then emits it as a single line. On job
    108767062588 three such lines took 68.78, 68.77 and 68.76 minutes to clear
    the GitHub Actions log pipeline, and the job was cancelled at 365 minutes
    having passed every test in 17m26s.

    Collected for real in a subprocess rather than reasoned about from the
    AST: the thing that matters is the id pytest actually *builds*, and only
    pytest builds it. One interpreter start, no database -- collection does not
    run fixtures.
    """
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "--collect-only",
            "-q",
            "-p",
            "no:cacheprovider",
            "-o",
            "addopts=",
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(BACKEND),
        timeout=COLLECT_TIMEOUT,
    )
    assert result.returncode == 0, result.stdout[:4000] + "\n" + result.stderr[:4000]
    ids = [line for line in result.stdout.splitlines() if line.startswith("tests/")]
    assert len(ids) >= MIN_COLLECTED, (
        f"the nested collection reported only {len(ids)} node ids, under the "
        f"floor of {MIN_COLLECTED}. That is a broken collection, not a small "
        "suite, and a broken collection must not pass this test by finding no "
        "oversized ids."
    )
    offenders = sorted(
        f"{len(node_id)} chars: {node_id[:80]}..."
        for node_id in ids
        if len(node_id) > MAX_NODE_ID
    )
    assert not offenders, (
        f"these collected node ids exceed {MAX_NODE_ID} characters, so pytest "
        "built them out of their parameters instead of out of a name: "
        f"{offenders}. Give the `parametrize` an explicit `ids=`. A single "
        "2 MiB line took ~68.8 minutes to clear the GitHub Actions log "
        "pipeline on job 108767062588."
    )


# ---------------------------------------------------------------------------
# A test that needs no database must build none (APRAS-120 §5)
# ---------------------------------------------------------------------------


def _autouse_fixtures_requesting(conftest: pathlib.Path, dependency: str) -> list[str]:
    """`autouse` fixtures in `conftest` that take `dependency` as a parameter.

    An AST walk rather than a text scan, because the thing being asserted is a
    *decorator argument* paired with a *parameter name*, and both have to be
    read structurally to be read at all.
    """
    tree = ast.parse(conftest.read_text(encoding="utf-8"))
    offenders: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        is_autouse = any(
            isinstance(decorator, ast.Call)
            and any(
                kw.arg == "autouse"
                and isinstance(kw.value, ast.Constant)
                and kw.value.value is True
                for kw in decorator.keywords
            )
            for decorator in node.decorator_list
        )
        if not is_autouse:
            continue
        params = [arg.arg for arg in node.args.args] + [
            arg.arg for arg in node.args.kwonlyargs
        ]
        if dependency in params:
            offenders.append(f"{node.name}:{node.lineno}")
    return offenders


def test_no_autouse_fixture_in_conftest_requests_the_session() -> None:
    """An autouse fixture that takes `session` makes every test a database test.

    `default_tenant_fixture` was exactly that, and the cost was not merely
    wasted work. It seeded a row with a `commit()`, so when sqlmodel 0.0.47
    made a bare `datetime` annotation reject a naive bind parameter, that one
    commit failed in **setup** for every test in the suite -- including the 22
    modules that read source files and touch no database at all.
    `tests/test_lint_hygiene.py` could not run, and the failure named a
    fixture rather than the column that caused it.

    The seed now lives inside `session_fixture`, which makes "every test
    database contains the default tenant" a property of the database instead
    of of fixture ordering, and leaves a database-free module database-free.
    This test is what keeps it that way: the next autouse fixture that reaches
    for `session` has to justify itself here first.
    """
    offenders = _autouse_fixtures_requesting(TESTS / "conftest.py", "session")
    assert not offenders, (
        "these autouse fixtures in tests/conftest.py request `session`, so "
        "every test in the suite -- including the modules that touch no "
        f"database -- builds a SQLite engine: {offenders}. Move the work into "
        "`session_fixture` if every database needs it, or drop `autouse` and "
        "let the tests that need it ask."
    )


# ---------------------------------------------------------------------------
# No read schema can opt out of the UTC offset by accident (APRAS-120 §6)
# ---------------------------------------------------------------------------

#: The vacuity floor for the schema scan below. 74 classes qualify on this
#: tree, and the floor sits four under it **deliberately**: 74 is a census, not
#: a target, and a test about *inheritance* must not redden because somebody
#: legitimately deleted a dated field. 70 is still far above anything a broken
#: scan produces -- one that fails to resolve inheritance finds 63, one that
#: resolves nothing finds 0 -- so neither can pass here.
#:
#: If the real count ever drops below 70, re-measure the census and restate
#: this floor with the new number and the reason. It is never to be lowered to
#: whatever the run happened to produce.
DATED_SCHEMA_FLOOR = 70


def _mentions_datetime(annotation: object, seen: set[object] | None = None) -> bool:
    """Whether `datetime` appears anywhere inside a resolved annotation.

    Recurses through `Annotated` metadata, union members and `list`/`dict`
    arguments, because `datetime | None`, `list[Something]` and
    `Annotated[datetime, AfterValidator(...)]` are all ways a field is dated
    without its annotation *being* `datetime`.
    """
    if seen is None:
        seen = set()
    if annotation is datetime:
        return True
    try:
        if annotation in seen:
            return False
        seen.add(annotation)
    except TypeError:  # unhashable annotation; recursion below still terminates
        pass
    if any(_mentions_datetime(arg, seen) for arg in typing.get_args(annotation)):
        return True
    metadata = getattr(annotation, "__metadata__", ())
    return any(_mentions_datetime(item, seen) for item in metadata)


def _schema_classes() -> list[type[BaseModel]]:
    """Every pydantic class *defined* in a module of `app/schemas/`.

    Import-based and not an AST walk, deliberately: only a real import
    resolves `model_fields`, and `model_fields` is the only view that includes
    fields a class **inherits**. Measured on this tree, the declaration-only
    view finds 63 classes and this one finds 74 -- and the 11 it adds are all
    response schemas that inherit a dated field from a sibling, i.e. exactly
    the classes the offset must not miss and exactly the ones an AST scan
    cannot see.

    Filtering on `__module__` keeps each class attributed to the module that
    defines it, so a class imported into a second module is counted once.
    """
    classes: list[type[BaseModel]] = []
    for path in sorted((BACKEND / "app" / "schemas").glob("*.py")):
        if path.stem == "__init__":
            continue
        module = importlib.import_module(f"app.schemas.{path.stem}")
        classes.extend(
            value
            for value in vars(module).values()
            if isinstance(value, type)
            and issubclass(value, BaseModel)
            and value.__module__ == module.__name__
        )
    return list(dict.fromkeys(classes))


def test_every_dated_schema_class_inherits_api_model() -> None:
    """A schema with a `datetime` field serialises it with its UTC offset.

    This is the test that makes the display fix survive the next read schema
    somebody adds. `ApiModel` carries the `"*"` json serialiser; a class that
    goes back to `BaseModel` -- or a new one written against `BaseModel` out of
    habit -- would silently ship offsetless datetimes again, and the only
    symptom is a three-hour error in the browser that no other backend test
    looks at.

    The floor is asserted first so a scan that resolves nothing cannot pass by
    finding no offenders.
    """
    dated = [
        cls
        for cls in _schema_classes()
        if any(
            _mentions_datetime(field.annotation) for field in cls.model_fields.values()
        )
    ]

    assert len(dated) >= DATED_SCHEMA_FLOOR, (
        f"the schema scan found only {len(dated)} dated classes, under the "
        f"floor of {DATED_SCHEMA_FLOOR}. That is a broken scan, not a tidy "
        "schema package: a scan that cannot resolve inherited fields finds 63 "
        "and one that resolves nothing finds 0. Re-measure the census and "
        "restate the floor in the spec that changes it."
    )

    offenders = sorted(
        f"{cls.__module__.rsplit('.', 1)[-1]}.{cls.__name__}"
        for cls in dated
        if not issubclass(cls, ApiModel)
    )
    assert not offenders, (
        "these schema classes have a `datetime` among their resolved fields "
        "but do not inherit `app.schemas.base.ApiModel`, so their datetimes "
        f"serialise without a UTC offset: {offenders}. The browser reads an "
        "offsetless string as local time, which is a three-hour display error "
        "on every one of them."
    )
