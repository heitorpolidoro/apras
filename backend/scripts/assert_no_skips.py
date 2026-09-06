"""Fail the job if the Postgres migration module did not really run.

`tests/test_migrations_postgres.py` self-skips when `TEST_POSTGRES_URL` is
unset or unreachable, and a fully-skipped pytest run exits 0. Between
APRAS-27 and APRAS-50 that is how 53 cases stayed invisible inside a green
check. This reads the JUnit XML the job just produced and refuses a run in
which the module was collected-but-skipped, or not collected at all.
"""

import os
import sys
import xml.etree.ElementTree as ET

#: The literal `classname` attribute pytest writes for every case in
#: `tests/test_migrations_postgres.py`, verified against a real run of the
#: module rather than guessed. Matching on the filename or on a bare module
#: name would select nothing: the guard would still fail closed on
#: `collected=0`, but on the wrong diagnosis and one CI round trip later.
MODULE_CLASSNAME = "tests.test_migrations_postgres"

#: A **floor**, not an equality: the case count at `e188866`. A later task
#: that adds a case must not have to touch this file, while a task that
#: deletes the module -- or silences it by deselecting cases -- cannot pass.
MIN_CASES = 53


def _verdict(collected: int, skipped: list[str]) -> list[str]:
    """Every reason to refuse this run, in the order a reader wants them."""
    problems = []
    if skipped:
        problems.append(
            f"{len(skipped)} case(s) were skipped, so the module did not really "
            "run against Postgres: " + ", ".join(sorted(skipped))
        )
    if collected == 0:
        problems.append(
            f"the module was not collected at all: no testcase has classname "
            f"{MODULE_CLASSNAME!r}. Either the pytest step never reached it, or "
            "the module was renamed or removed."
        )
    elif collected < MIN_CASES:
        problems.append(
            f"only {collected} case(s) were collected, below the floor of "
            f"{MIN_CASES}. Cases were deselected, deleted or silenced."
        )
    return problems


def main(argv):
    if len(argv) != 1:
        print("usage: assert_no_skips.py <junit-xml-path>")
        return 2

    path = argv[0]
    if not os.path.exists(path):
        print(
            f"FAIL: the pytest step produced no JUnit XML at {path}. Under "
            "`if: always()` that means it died before any case ran -- a "
            "collection or environment error, not a pass."
        )
        return 1

    try:
        tree = ET.parse(path)  # noqa: S314
    except ET.ParseError as exc:
        print(f"FAIL: {path} could not be parsed as JUnit XML ({exc}).")
        return 1

    cases = [
        case
        for case in tree.getroot().iter("testcase")
        if case.get("classname") == MODULE_CLASSNAME
    ]
    skipped = [
        case.get("name", "<unnamed>")
        for case in cases
        if case.find("skipped") is not None
    ]

    print(f"collected={len(cases)} skipped={len(skipped)}")

    problems = _verdict(len(cases), skipped)
    if problems:
        for problem in problems:
            print(f"FAIL: {problem}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
