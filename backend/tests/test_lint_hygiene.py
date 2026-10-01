"""Lint hygiene, enforced from the suite rather than from review (APRAS-54).

Three rules, each of which a reviewer would otherwise have to re-derive by
hand from a ~250-file diff:

1. every ``# noqa`` under ``app/`` and ``tests/`` names its codes *and* says
   why the finding is correct as written;
2. there are no more of them than the task landed with (a forward regression
   guard for the *next* task, not a target for this one);
3. ``app/core/clock.py`` is the only module under ``app/`` that reads the
   clock -- the rule that stops a second clock being reintroduced;
4. ``app/core/clock.py`` is also the only module under ``app/`` that *adds or
   drops* a timezone (APRAS-120). Rule 3 keeps one source of the instant;
   this one keeps one source of the conversion between the aware values the
   API speaks and the naive UTC values the columns hold. It is what makes
   ``app/schemas/base.py`` call ``clock.to_api`` instead of converting
   in place, and what stops the next service from "fixing" a comparison with
   a local ``.replace(...)`` that silently moves an instant by the offset of
   whatever machine it runs on.
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
#: line. APRAS-105 raises it by exactly one again, and for exactly the same
#: reason: the public logo route added to that same module carries the
#: `30/minute` limit the operator decided on, so it declares the same unread
#: `request: Request` its sibling does. APRAS-104 §D raises it by exactly one
#: for the fourth time and for the third identical reason: the public
#: cover-photo route in `endpoints/public_projects.py` carries the
#: `300/minute` limit ER11 specifies, so it declares the same unread
#: `request: Request` the two routes in `public_branding.py` do. The spec
#: mandates that directive verbatim, in that module's shape.
NOQA_CAP = 72

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

#: The two ways a module could add or drop a timezone. ``astimezone(`` carries
#: its open parenthesis for the same reason ``datetime.now(`` does -- to catch
#: every argument list. The bare attribute name ``tzinfo`` covers both halves
#: of the pair that matters: reading it to branch, and passing it to
#: ``replace`` to strip or stamp one. Neither is reported by ruff.
TIMEZONE_LITERALS = ("tzinfo", "astimezone(")

#: The single module allowed to contain them.
THE_CLOCK = APP / "core" / "clock.py"

#: This module states the rules, so it necessarily *spells* the things it
#: forbids -- the word "noqa", all three clock literals and both timezone
#: literals appear above as subject matter. It is excluded from its own scans; a rule cannot be its own
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
    """``app/core/clock.py`` is the one place a timezone is read or changed.

    Two scans, because there are two ways to grow a second clock and the
    advice for each is different. Rule 3 is about *reading* the instant; rule
    4 (APRAS-120) is about *converting* between the aware UTC the API speaks
    and the naive UTC the columns hold.

    Rule 4 guards a specific, measured danger: a bare ``astimezone(UTC)``
    applied to a *naive* value assumes the **process's local zone**, so the
    same payload stores a different instant depending on where the server runs
    -- and because CI and production are both UTC, a suite stays green either
    way. ``clock.to_db`` guards that case explicitly; a
    ``.replace(tzinfo=None)`` dropped into a service to silence a
    ``TypeError`` would not, and would ship a defect no other test can see.

    A text scan, not an AST walk, and deliberately so for both rules: it also
    catches a comment or a docstring that *names* one of the spellings, which
    is how the next reader learns the rule without finding the spec. That is
    why ``app/schemas/base.py`` describes its conversion without spelling
    either timezone literal, and why it calls ``clock.to_api`` rather than
    converting in place.
    """
    the_clock = THE_CLOCK.relative_to(BACKEND).as_posix()
    sources = {path: path.read_text(encoding="utf-8") for path in _py_files(APP)}

    readers = {
        path.relative_to(BACKEND).as_posix()
        for path, text in sources.items()
        if any(lit in text for lit in CLOCK_LITERALS)
    }
    assert readers == {the_clock}, (
        "app/core/clock.py must be the only module under app/ containing any "
        f"of {CLOCK_LITERALS}; found: {sorted(readers)}. Use clock.db_now() "
        "for a value that reaches a column, clock.utc_now() for one that does "
        "not, and clock.today_utc() for a date."
    )

    converters = {
        path.relative_to(BACKEND).as_posix()
        for path, text in sources.items()
        if any(lit in text for lit in TIMEZONE_LITERALS)
    }
    assert converters == {the_clock}, (
        "app/core/clock.py must be the only module under app/ containing any "
        f"of {TIMEZONE_LITERALS}; found: {sorted(converters)}. Use "
        "clock.to_db() for a client-supplied instant on its way to a column, "
        "clock.to_api() for a stored instant on its way to a response, and "
        "clock.db_now() for a value the server stamps itself."
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
