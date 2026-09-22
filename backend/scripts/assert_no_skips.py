"""Fail the job if the Postgres migration module did not really run.

`tests/test_migrations_postgres.py` self-skips when `TEST_POSTGRES_URL` is
unset or unreachable, and a fully-skipped pytest run exits 0. Between
APRAS-27 and APRAS-50 that is how the module's whole case list stayed
invisible inside a green check. This reads the JUnit XML the job just produced
and refuses a run in which the module was collected-but-skipped, or not
collected at all.
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

#: A **floor**, not an equality: the case count the rewritten module collects
#: after APRAS-58 squashed the 39-revision history into one, verified against
#: a real Postgres run rather than counted by eye. A later task that adds a
#: case must not have to touch this file, while a task that deletes the module
#: -- or silences it by deselecting cases -- cannot pass. Raised from 20 to
#: 22 by APRAS-64, which added the money-column precision case and the
#: `Decimal` round-trip: `test_the_floor_is_the_modules_real_case_count`
#: collects the module for real and pins the floor to that count.
#:
#: Raised from 22 to 26 by APRAS-66, which added the second revision
#: (`0002_tenant_slug`) and with it four cases: the `no app import` guard on
#: the new revision, the backfilled `condominio-padrao`, the NOT NULL unique
#: index on `tenant.slug`, and the pre-upgrade row whose two-character name
#: must come back inside the 3-64 rule. The two rewritten history cases
#: replaced their predecessors one for one, so they add nothing here.
#:
#: Raised from 26 to 29 by APRAS-71, which added the third revision
#: (`0003_tenant_invitation`) and with it three cases: the live table with
#: its unique `token_hash` index, the absence of any raw-credential column,
#: and the real `downgrade` back to `0002_tenant_slug`. Widening the "no
#: `app` import" guard from the head revision to every revision replaced one
#: case with one case, so it adds nothing here. Measured with
#: `uv run pytest tests/test_migrations_postgres.py --collect-only -q`,
#: never typed from memory -- `test_the_floor_is_the_modules_real_case_count`
#: compares this number to the real collection by **equality**.
#:
#: Raised from 29 to 33 by APRAS-73, which added the fourth revision
#: (`0005_purchase_line_items`, on `0003_tenant_invitation`) and with it four
#: cases: the two `purchase_quote` price columns gone at head, the fold of a
#: pre-upgrade quote into exactly one quote-owned line, the over-long and
#: blank request titles that fold has to survive, and the **lossy**
#: downgrade, whose surviving `position = 0` row and whose `perda`/`backup`
#: docstring are both pinned. Appending the revision to `EXPECTED_HISTORY`
#: added no case -- the history cases loop over the tuple.
#:
#: Raised from 33 to 36 by APRAS-68, which added the fifth revision
#: (`0006_tenant_brand_theme`, on `0005_purchase_line_items`) and with it
#: three cases: the nullable JSON column with no server default, the
#: pre-upgrade row that comes back `NULL` because there is no backfill, and
#: the real `downgrade` back one revision. The spec wrote this revision as
#: `0004` on `0003_tenant_invitation`; APRAS-73 landed first, so the incoming
#: revision renumbered itself rather than leave two Alembic heads, and the
#: digits skip `0004`.
#:
#: Measured after the change, against the index this commit carries and not
#: against a worktree that also holds another task's in-flight revision:
#: `uv run pytest tests/test_migrations_postgres.py --collect-only -q`.
MIN_CASES = 36


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
        tree = ET.parse(path)  # noqa: S314  # our own pytest JUnit output, not untrusted input
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
