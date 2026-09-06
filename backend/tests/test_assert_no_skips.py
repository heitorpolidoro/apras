"""APRAS-50: the guard that makes "the migration job ran" checkable.

`tests/test_migrations_postgres.py` self-skips when `TEST_POSTGRES_URL` is
unset or unreachable, and a fully-skipped pytest run exits **0**. That is how
53 cases stayed invisible inside a green `Backend Tests` check between
APRAS-27 and APRAS-50, and it is the exact failure mode a race on the service
container's health check would reintroduce.

`scripts/assert_no_skips.py` is the second line of defence, so it is the one
piece of new code this task ships and the one piece that needs its own tests:
a guard nobody has seen fail is a guess. These cases pin every way it must
refuse -- a skip, a short collection, an empty collection, a missing file --
and the two ways it must not (a run above the floor, and skips belonging to
some *other* module).
"""

import importlib.util
import pathlib
import subprocess
import sys

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "assert_no_skips.py"

#: The literal `classname` pytest writes for the module, verified against a
#: real run of it rather than guessed (`migration-test-results.xml`, 53/53).
MODULE_CLASSNAME = "tests.test_migrations_postgres"


def _load():
    """Import the CLI helper by path -- `scripts/` is deliberately not a package."""
    spec = importlib.util.spec_from_file_location("assert_no_skips", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _junit(
    tmp_path,
    *,
    passed: int = 53,
    skipped: int = 0,
    classname: str = MODULE_CLASSNAME,
    extra: str = "",
) -> str:
    """A JUnit XML shaped exactly like the one pytest writes for the module."""
    cases = [
        f'<testcase classname="{classname}" name="test_case_{index}" time="1.0" />'
        for index in range(passed)
    ]
    cases += [
        f'<testcase classname="{classname}" name="test_skipped_{index}" time="0.0">'
        '<skipped type="pytest.skip" message="TEST_POSTGRES_URL not set" />'
        "</testcase>"
        for index in range(skipped)
    ]
    path = tmp_path / "migration-test-results.xml"
    path.write_text(
        '<?xml version="1.0" encoding="utf-8"?><testsuites><testsuite name="pytest" '
        f'errors="0" failures="0" skipped="{skipped}" tests="{passed + skipped}">'
        + "".join(cases)
        + extra
        + "</testsuite></testsuites>",
        encoding="utf-8",
    )
    return str(path)


def test_the_guard_script_exists_outside_the_test_tree():
    """It is a CI helper, not a test: `pytest.ini`'s `testpaths = tests` must miss it."""
    assert SCRIPT.exists(), SCRIPT
    assert SCRIPT.parent.name == "scripts"


def test_the_floor_is_the_case_count_at_e188866():
    assert _load().MIN_CASES == 53


def test_a_full_green_run_is_accepted(tmp_path, capsys):
    """53 collected, none skipped: exactly what the green CI run must produce."""
    assert _load().main([_junit(tmp_path)]) == 0
    assert "collected=53 skipped=0" in capsys.readouterr().out


def test_the_floor_is_a_floor_and_not_an_equality(tmp_path, capsys):
    """A later task that *adds* a case must not have to touch the guard."""
    assert _load().main([_junit(tmp_path, passed=60)]) == 0
    assert "collected=60 skipped=0" in capsys.readouterr().out


def test_one_skipped_case_fails_the_job_and_is_named(tmp_path, capsys):
    """The whole point: a skip is invisible in a green check unless something looks."""
    assert _load().main([_junit(tmp_path, passed=52, skipped=1)]) != 0
    output = capsys.readouterr().out
    assert "skipped=1" in output
    assert "test_skipped_0" in output


def test_a_fully_skipped_run_fails_the_job(tmp_path, capsys):
    """Today's bug, reintroduced by a race on the service container's health check."""
    assert _load().main([_junit(tmp_path, passed=0, skipped=53)]) != 0
    assert "skipped=53" in capsys.readouterr().out


def test_a_short_collection_fails_the_job(tmp_path, capsys):
    """Deselecting or deleting cases to make the job green is excluded outright."""
    assert _load().main([_junit(tmp_path, passed=52)]) != 0
    output = capsys.readouterr().out
    assert "collected=52" in output
    assert "53" in output


def test_a_run_that_never_collected_the_module_fails_and_says_so(tmp_path, capsys):
    """`collected=0` is a different diagnosis from `collected=52`, so it reads
    differently: the module was not collected at all (renamed, moved, or the
    pytest step never reached it)."""
    assert _load().main([_junit(tmp_path, passed=0)]) != 0
    output = capsys.readouterr().out
    assert "collected=0" in output
    assert "not collected at all" in output


def test_only_this_module_counts_towards_the_verdict(tmp_path, capsys):
    """A skip in some *other* module is not this guard's business."""
    other = (
        '<testcase classname="tests.test_something_else" name="test_x" time="0.0">'
        '<skipped type="pytest.skip" message="unrelated" /></testcase>'
    )
    assert _load().main([_junit(tmp_path, extra=other)]) == 0
    assert "collected=53 skipped=0" in capsys.readouterr().out


def test_the_selector_is_the_dotted_module_and_not_the_filename(tmp_path, capsys):
    """A selector that matched `test_migrations_postgres.py` would report
    `collected=0` -- failing closed, but wasting a CI round trip on a
    diagnosis that is not the real one."""
    assert (
        _load().main([_junit(tmp_path, classname="test_migrations_postgres.py")]) != 0
    )
    assert "collected=0" in capsys.readouterr().out


def test_a_missing_xml_fails_legibly_rather_than_with_a_traceback(tmp_path, capsys):
    """Under `if: always()` a missing file means the pytest step died before any
    case ran -- an environment or collection error, which is a failure."""
    missing = str(tmp_path / "nope.xml")
    assert _load().main([missing]) != 0
    output = capsys.readouterr().out
    assert missing in output
    assert "no JUnit XML" in output


def test_it_reports_its_own_usage_when_given_no_argument(capsys):
    assert _load().main([]) != 0
    assert "usage" in capsys.readouterr().out.lower()


def test_unparseable_xml_fails_legibly_rather_than_with_a_traceback(tmp_path, capsys):
    """A truncated artifact (killed runner, disk full) is not a pass."""
    path = tmp_path / "migration-test-results.xml"
    path.write_text("<testsuites><testsuite>", encoding="utf-8")
    assert _load().main([str(path)]) != 0
    assert "could not be parsed" in capsys.readouterr().out


def test_the_cli_entry_point_exits_non_zero_without_a_traceback():
    """The workflow calls it as a script; `main`'s return value must reach the
    shell as an exit status, and a missing file must not print a traceback."""
    result = subprocess.run(  # noqa: S603
        [sys.executable, str(SCRIPT), "--missing--.xml"],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(SCRIPT.parents[1]),
    )
    assert result.returncode != 0
    assert "Traceback" not in result.stderr


def test_the_cli_entry_point_exits_zero_on_a_green_artifact(tmp_path):
    result = subprocess.run(  # noqa: S603
        [sys.executable, str(SCRIPT), _junit(tmp_path)],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(SCRIPT.parents[1]),
    )
    assert result.returncode == 0, result.stderr
    assert "collected=53 skipped=0" in result.stdout
