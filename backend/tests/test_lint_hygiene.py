"""Lint hygiene, enforced from the suite rather than from review (APRAS-54).

Three rules, each of which a reviewer would otherwise have to re-derive by
hand from a ~250-file diff:

1. every ``# noqa`` under ``app/`` and ``tests/`` names its codes *and* says
   why the finding is correct as written;
2. there are no more of them than the task landed with (a forward regression
   guard for the *next* task, not a target for this one);
3. ``app/core/clock.py`` is the only module under ``app/`` that reads the
   clock -- the rule that stops a second clock being reintroduced.
"""

from __future__ import annotations

import re
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
APP = BACKEND / "app"
TESTS = BACKEND / "tests"

#: The number of ``noqa`` comment lines APRAS-54 landed with, under ``app/`` +
#: ``tests/`` -- 49 and 19. The base was 94 and the ceiling the task was
#: allowed is 108; the number below is what it actually needed, which came in
#: under the floor the spec estimated because the ``tests/**`` per-file
#: ignores (``ARG002`` above all) retired whole classes of per-line comment.
#:
#: It may fall freely. Raising it is a decision that belongs in a task's spec,
#: not in a diff -- APRAS-60 §17 raised it by exactly one, for the `E711` its
#: `parent_id == None` folder lookup needs and that `voting_service` already
#: spells the same way. APRAS-74 raises it by exactly one more, for the
#: `ARG001` on `public_branding.get_public_tenant_branding`: `slowapi`'s
#: `@limiter.limit` decorator looks the request up by *parameter name*, so
#: the handler must declare a `request: Request` it never reads. The spec
#: mandates that directive verbatim, in the shape `endpoints/invitations.py`
#: already carries for the same decorator; the alternative -- adding
#: `ARG001` to the `app/api/v1/endpoints/**` per-file ignores -- would
#: silence every genuinely unused argument across 35 routers to save one
#: line.
NOQA_CAP = 70

#: A ``noqa: CODE[, CODE...]`` directive followed by two spaces and a reason.
NOQA_OK = re.compile(r"#\s*noqa:\s*[A-Z]+[0-9]+(\s*,\s*[A-Z]+[0-9]+)*\s+#\s+\S")

#: Any ``noqa`` directive, well-formed or not.
NOQA_ANY = re.compile(r"#\s*noqa")

#: The three ways this codebase could read a clock. ``datetime.now(`` is
#: listed with its open parenthesis so it catches *every* argument list,
#: ``datetime.now(UTC)`` included: an aware read written straight into a naive
#: column is exactly the bug ``clock.db_now()`` exists to prevent, and ruff
#: flags none of them.
CLOCK_LITERALS = ("datetime.utcnow", "date.today(", "datetime.now(")

#: The single module allowed to contain them.
THE_CLOCK = APP / "core" / "clock.py"

#: This module states the rules, so it necessarily *spells* the things it
#: forbids -- the word "noqa" and all three clock literals appear above as
#: subject matter. It is excluded from its own scans; a rule cannot be its own
#: counterexample.
SELF = Path(__file__).resolve()


def _py_files(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*.py") if p.resolve() != SELF)


def test_every_noqa_names_its_codes_and_its_reason() -> None:
    """A bare ``# noqa`` silences a finding without saying which, or why."""
    offenders: list[str] = []
    for root in (APP, TESTS):
        for path in _py_files(root):
            for lineno, line in enumerate(
                path.read_text(encoding="utf-8").splitlines(), start=1
            ):
                if NOQA_ANY.search(line) and not NOQA_OK.search(line):
                    rel = path.relative_to(BACKEND)
                    offenders.append(f"{rel}:{lineno}: {line.strip()}")

    assert not offenders, (
        "every `# noqa` under app/ and tests/ must read "
        "`# noqa: CODE[, CODE]  # reason`:\n" + "\n".join(offenders)
    )


def test_noqa_count_is_within_the_cap() -> None:
    """The cap is a ratchet: this suite may lower it, never raise it silently."""
    total = sum(
        len(NOQA_ANY.findall(path.read_text(encoding="utf-8")))
        for root in (APP, TESTS)
        for path in _py_files(root)
    )
    assert total <= NOQA_CAP, (
        f"{total} `# noqa` comments under app/ + tests/, cap is {NOQA_CAP}. "
        "Fix the finding, or raise the cap in a spec that says why."
    )
    assert NOQA_CAP <= 108, "APRAS-54's ceiling; a rise needs its own task"


def test_clock_py_is_the_only_clock_in_app() -> None:
    """``app/core/clock.py`` is the one place the current instant is read.

    A text scan, not an AST walk, and deliberately so: it also catches a
    comment or a docstring that *names* one of the three spellings, which is
    how the next reader learns the rule without finding the spec.
    """
    readers = {
        path.relative_to(BACKEND).as_posix()
        for path in _py_files(APP)
        if any(lit in path.read_text(encoding="utf-8") for lit in CLOCK_LITERALS)
    }

    assert readers == {THE_CLOCK.relative_to(BACKEND).as_posix()}, (
        "app/core/clock.py must be the only module under app/ containing any "
        f"of {CLOCK_LITERALS}; found: {sorted(readers)}. Use clock.db_now() "
        "for a value that reaches a column, clock.utc_now() for one that does "
        "not, and clock.today_utc() for a date."
    )


def test_the_clock_reads_the_clock_exactly_once() -> None:
    """Inside ``clock.py`` the permitted occurrence is ``utc_now``'s own read.

    ``db_now`` and ``today_utc`` derive from it, so there is one source of the
    instant rather than three that can drift.
    """
    source = THE_CLOCK.read_text(encoding="utf-8")
    assert source.count("datetime.now(") == 1
    assert "datetime.utcnow" not in source
    assert "date.today(" not in source
