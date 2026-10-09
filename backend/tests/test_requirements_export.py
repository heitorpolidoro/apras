"""`requirements.txt` is an export of `uv.lock`, and nothing else was checking it.

`backend/requirements.txt` is not a convenience copy: `backend/vercel.json`
routes `/(.*)` to `index.py`, and Vercel's Python runtime installs from
`requirements.txt` -- it never reads `pyproject.toml` or `uv.lock`. The
Dockerfile and CI take the other path (`uv sync --frozen`), so the whole suite
runs against the *lock*. That asymmetry means the export can drift arbitrarily
far from what is tested and every job stays green, which is exactly what
happened: APRAS-120 moved `sqlmodel` to 0.0.47 in `pyproject.toml` and
`uv.lock` while the export still asked for 0.0.38, on which a `table=True`
model with a `NaiveDatetime` column cannot even be defined.

Looking at it also showed the drift predated the task. At `cd8de18` the export
disagreed with the lock on 19 transitive pins, and the set it named was not
installable at all: it pinned `pydantic==2.13.5` next to
`pydantic-core==2.49.0`, while `pydantic` 2.13.5 requires
`pydantic-core==2.46.5`. A deploy from it fails during install.

So the first rule below is parity, in both directions, against the lock -- the
one artifact the suite actually exercises. It is deliberately not "the export
parses" or "the export mentions sqlmodel": the only property worth asserting
is that the file Vercel installs resolves to the versions the tests ran on.

APRAS-121 adds the rules that make regeneration a *mechanism* rather than a
habit, and they are all textual properties of files in the working tree:

1. **one definition of the export command** --
   `backend/scripts/export_requirements.sh` is the only place the invocation is
   written, and no workflow, no test module and not `AGENTS.md` may spell one
   of its own. `backend/requirements.txt` is excluded because `uv` writes the
   invocation into the header it generates (that is the property rule 2 reads),
   and `docs/**` is excluded because specs and reviews quote commands as prose.
2. **the generated header quotes the script's own command**, which only means
   anything because the script passes a fixed argument list: no conditional
   flags, no `--directory`, nothing interpolated from the environment. A header
   that depended on who ran the script could not be asserted against at all.
3. **one uv version for every producer of the export.** The bytes of the export
   -- header, `# via` annotations, ordering, marker rendering -- are
   uv-version artefacts, so the `UV_PIN` literal in the script and the
   `version:` literal of the `setup-uv` step in each of the two workflow jobs
   that run the script are asserted to be the same string. The script is the
   source of truth and the other two are compared *to it*, individually, so
   editing any one of the three alone is red.
4. **the privileged workflow's shape.** `requirements-export.yml` holds a
   Contents:write push credential, so the properties that keep it from
   executing pull-request code -- the base-sha fetch, the out-of-tree copy, no
   lock command, no cache -- are asserted here rather than left to review.

Every assertion in this module reads text from the working tree:
`backend/requirements.txt`, `backend/uv.lock`, `backend/scripts/export_requirements.sh`,
`.github/workflows/*`, `backend/tests/*.py` and `AGENTS.md`. There is no
network I/O and no `uv` subprocess, and the last three tests in the file assert
that by AST rather than by promise -- a guard that can go red for a reason
outside this repository is a guard someone deletes.
"""

from __future__ import annotations

import ast
import re
import tomllib
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND.parent
REQUIREMENTS = BACKEND / "requirements.txt"
UV_LOCK = BACKEND / "uv.lock"
EXPORT_SCRIPT = BACKEND / "scripts" / "export_requirements.sh"
TESTS_DIR = BACKEND / "tests"
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"
CI_WORKFLOW = WORKFLOWS_DIR / "ci.yml"
EXPORT_WORKFLOW = WORKFLOWS_DIR / "requirements-export.yml"
DEPENDABOT_YML = REPO_ROOT / ".github" / "dependabot.yml"
PYPROJECT = BACKEND / "pyproject.toml"
AGENTS_MD = REPO_ROOT / "AGENTS.md"
THIS_MODULE = Path(__file__).resolve()

#: A pinned requirement line, e.g. ``sqlmodel==0.0.47`` or
#: ``colorama==0.4.6 ; sys_platform == 'win32'``. The export emits exact pins
#: only, so anything looser is itself a finding.
PIN = re.compile(r"^(?P<name>[A-Za-z0-9._-]+)==(?P<version>[^\s;]+)")

#: Export and lock normalise distribution names differently in principle
#: (``Mako`` vs ``mako``); compare on the normalised form, per PEP 503.
_NON_ALNUM_RUN = re.compile(r"[-_.]+")


def code_text(text: str) -> str:
    """`text` with comment-only lines dropped, line numbering preserved.

    Lines become empty rather than disappearing so that a line number in a
    failure message still refers to the real file. Shell comments inside a
    `run:` body are comments too, and dropping them is the point: a required
    command that has been commented out is not a command.
    """
    stripped = "\n".join(
        "" if line.lstrip().startswith("#") else line for line in text.splitlines()
    )
    # The trailing newline is preserved too, so the line count is identical
    # and `test_the_code_text_helper_drops_comments_and_only_comments` can
    # assert that equality rather than an inequality that tolerates drift.
    return stripped + "\n" if text.endswith("\n") else stripped


def _canonical(name: str) -> str:
    return _NON_ALNUM_RUN.sub("-", name).lower()


def _export_pins() -> dict[str, str]:
    pins: dict[str, str] = {}
    for line in REQUIREMENTS.read_text(encoding="utf-8").splitlines():
        match = PIN.match(line)
        if match:
            pins[_canonical(match.group("name"))] = match.group("version")
    return pins


def _lock_versions() -> dict[str, str]:
    lock = tomllib.loads(UV_LOCK.read_text(encoding="utf-8"))
    return {
        _canonical(package["name"]): package["version"]
        for package in lock["package"]
        # The root project itself is a virtual package in the lock and has no
        # pin in the export -- it *is* the thing being installed.
        if "virtual" not in package.get("source", {})
    }


#: Quoted into every "regenerate this" message, so no failure here has to spell
#: out an invocation the guard below forbids spelling out.
REGENERATE_WITH = "bash backend/scripts/export_requirements.sh"


# ==========================================================================
# 1. Parity with the lock (APRAS-120).
# ==========================================================================


def test_every_export_pin_matches_the_locked_version() -> None:
    """A pin the lock does not name, or names at another version, is drift.

    This is the assertion that would have caught `sqlmodel==0.0.38` surviving
    APRAS-120, and the 19 pre-existing transitive mismatches behind it.
    """
    locked = _lock_versions()
    mismatched = [
        f"{name}: requirements.txt=={version} but uv.lock=={locked.get(name, '<absent>')}"
        for name, version in sorted(_export_pins().items())
        if locked.get(name) != version
    ]
    assert not mismatched, (
        "backend/requirements.txt disagrees with backend/uv.lock. It is the "
        "install manifest for the Vercel deployment and must be regenerated, "
        f"never hand-edited:\n  {REGENERATE_WITH}\n" + "\n".join(mismatched)
    )


def test_every_locked_package_is_pinned_in_the_export() -> None:
    """Parity has to hold the other way too, or a dependency can go missing.

    A package dropped from the export installs on Vercel only by accident, as
    somebody else's transitive dependency and at whatever version that
    resolution happens to pick.
    """
    pinned = _export_pins()
    missing = sorted(name for name in _lock_versions() if name not in pinned)
    assert not missing, (
        "backend/uv.lock locks packages that backend/requirements.txt does "
        f"not pin, so the Vercel install is unconstrained in them: {missing}"
    )


# ==========================================================================
# 2. One definition of the export command.
# ==========================================================================

#: The needle, in fragments. It is assembled at run time *on purpose*: the
#: guard forbids a contiguous "<uv> <subcommand>" literal anywhere under
#: `backend/tests/`, and this module is under `backend/tests/`. Carving out
#: `__file__` instead would make the one file most likely to need the rule
#: next the one file exempt from it.
_NEEDLE_TOOL = "uv"
_NEEDLE_GAP = r"[ \t]+"
_NEEDLE_SUBCOMMAND = "export"

#: Global options may sit between the tool and the subcommand, each optionally
#: taking one value: `--directory backend`, `--project .`, `-q`. Requiring
#: adjacency left a documented hole -- code review round 1 planted a second
#: definition with `--directory backend` between the two words and the sweep
#: did not see it; `test_the_guard_does_not_fire_on_the_neighbouring_shapes`
#: now carries that form as a case. Each alternative must start with a dash,
#: so `uv pip install ... $RUNNER_TEMP/export-check` and `uv venv --python
#: 3.13 .../export-check` still do not match: their first token after the tool
#: is not an option, so the subcommand slot has to be filled by `pip`/`venv`.
_NEEDLE_OPTIONS = r"(?:[ \t]+-{1,2}\S+(?:[ \t]+[^-\s]\S*)?)*"

#: Word boundaries on both sides, and matched **per line**. Both matter.
#: Without `\b` on the right, `--export-format` and `export-check` would
#: match; matched across newlines, an `astral-sh/setup-uv` reference followed
#: on a later line by a shell `export FOO=...` would match -- and that shape
#: is plausible in exactly the two workflow files APRAS-121 writes.
NEEDLE = re.compile(
    rf"\b{_NEEDLE_TOOL}\b{_NEEDLE_OPTIONS}{_NEEDLE_GAP}{_NEEDLE_SUBCOMMAND}\b"
)


def _guarded_files() -> list[Path]:
    """Every file the "one definition" rule covers, in a stable order.

    `backend/requirements.txt` is absent by construction: `uv` writes the
    invocation into the header it generates, and that is the very property
    `test_the_generated_header_quotes_the_scripts_own_command` asserts.
    `docs/**` is absent too -- documentation quotes commands as prose.
    """
    files = [path for path in sorted(WORKFLOWS_DIR.iterdir()) if path.is_file()]
    files += sorted(TESTS_DIR.glob("*.py"))
    files.append(AGENTS_MD)
    return files


def _invocations_in(text: str) -> list[int]:
    """1-based line numbers of `text` that spell an export invocation."""
    return [
        number
        for number, line in enumerate(text.splitlines(), 1)
        if NEEDLE.search(line)
    ]


def test_the_guard_pattern_is_not_spelled_out_in_this_file() -> None:
    """(a) This module holds no contiguous literal of the thing it forbids.

    Without this, the guard below is one careless docstring away from failing
    on itself, and the next person's fix is an `__file__` exclusion that
    hollows the rule out.
    """
    source = THIS_MODULE.read_text(encoding="utf-8")
    assert not NEEDLE.search(source), (
        "this module spells an export invocation contiguously on these lines, "
        f"so it fails its own guard: {_invocations_in(source)}"
    )


def test_the_guard_finds_an_invocation_when_one_is_planted() -> None:
    """(b) The detector is not vacuous: planted text in both shapes is flagged.

    The real-tree sweep below passes when nothing matches, which is also what a
    broken pattern does. These two fixtures are the difference, and they go
    through `_invocations_in` -- the same entry point the sweep calls.
    """
    workflow_shaped = "\n".join(
        [
            "    - name: Export the requirements",
            "      run: |",
            "        cd backend",
            f"        {_NEEDLE_TOOL} {_NEEDLE_SUBCOMMAND} --format requirements-txt -o requirements.txt",
        ]
    )
    assert _invocations_in(workflow_shaped) == [4], workflow_shaped

    test_shaped = "\n".join(
        [
            "FAILURE = (",
            f'    "regenerate it: cd backend && {_NEEDLE_TOOL}\t{_NEEDLE_SUBCOMMAND} --no-hashes"',
            ")",
        ]
    )
    assert _invocations_in(test_shaped) == [2], test_shaped


def test_the_guard_does_not_fire_on_the_neighbouring_shapes() -> None:
    """The two false positives the pattern is shaped against, pinned as cases.

    A later maintainer loosening `\\b` or switching to a multi-line match turns
    one of these red, which is the point.
    """
    across_newlines = (
        "      uses: astral-sh/setup-uv@v8.1.0\n"
        "      run: |\n"
        "        export UV_NO_PROGRESS=1"
    )
    assert _invocations_in(across_newlines) == [], across_newlines

    suffixed = f"        {_NEEDLE_TOOL} {_NEEDLE_SUBCOMMAND}er --help"
    assert _invocations_in(suffixed) == [], suffixed

    # The two real lines `ci.yml` carries whose *path arguments* contain the
    # subcommand as a word. `_NEEDLE_OPTIONS` widened the pattern, so these
    # are the cases that keep the widening from becoming a false positive on
    # this repository's own CI.
    for benign in (
        (
            f'        {_NEEDLE_TOOL} venv --python 3.13 "$RUNNER_TEMP/'
            f'{_NEEDLE_SUBCOMMAND}-check"'
        ),
        (
            f"        {_NEEDLE_TOOL} pip install --dry-run --python "
            f'"$RUNNER_TEMP/{_NEEDLE_SUBCOMMAND}-check" -r '
            "backend/requirements.txt"
        ),
        f"        {_NEEDLE_TOOL} lock --check",
        f"        {_NEEDLE_TOOL} sync --all-groups",
    ):
        assert _invocations_in(benign) == [], benign

    # And the three shapes the guard *is* about, so none of the cases above
    # can be satisfied by a pattern that matches nothing at all.
    for real in (
        f"        {_NEEDLE_TOOL}  {_NEEDLE_SUBCOMMAND} --frozen",
        f"        {_NEEDLE_TOOL} --directory backend {_NEEDLE_SUBCOMMAND} --frozen",
        f"        {_NEEDLE_TOOL} -q --no-progress {_NEEDLE_SUBCOMMAND} --frozen",
    ):
        assert _invocations_in(real) == [1], real


def test_the_export_script_is_the_only_definition_of_the_command() -> None:
    """No workflow, no test module and not `AGENTS.md` spells its own.

    The script is where it lives. Anything else that spells it is a second
    definition, and two definitions of a command whose output is committed
    byte-for-byte diverge silently.
    """
    guarded = _guarded_files()
    assert len(guarded) > 5, (
        f"only {len(guarded)} guarded files found, so this sweep is barely "
        f"sweeping: {[str(path) for path in guarded]}"
    )
    offenders = [
        f"{path.relative_to(REPO_ROOT)}:{number}"
        for path in guarded
        for number in _invocations_in(path.read_text(encoding="utf-8"))
    ]
    assert not offenders, (
        "the export invocation is defined in "
        f"{EXPORT_SCRIPT.relative_to(REPO_ROOT)} and nowhere else; these "
        f"places spell one of their own: {offenders}"
    )


def test_the_generated_header_still_carries_an_invocation() -> None:
    """(c) The guard passes *with* the generated header in place.

    The exclusion of `backend/requirements.txt` is load-bearing rather than
    decorative: the header really does contain the text the guard forbids
    elsewhere, so a sweep that reached it would be permanently red.
    """
    header = REQUIREMENTS.read_text(encoding="utf-8").splitlines()[:2]
    assert _invocations_in("\n".join(header)) == [2], header
    assert REQUIREMENTS not in _guarded_files(), (
        "the generated export is inside the guard's reach, which makes the "
        "sweep above unsatisfiable"
    )


# ==========================================================================
# 3. The header quotes the script's own, fixed, invocation.
# ==========================================================================

#: A line of the script that *is* the invocation: at column 0, starting with
#: the tool name. The version probe reads `uv --version` inside a command
#: substitution, so it never starts a line.
_SCRIPT_INVOCATION = re.compile(rf"^{_NEEDLE_TOOL}\s+\S.*$")


def _script_invocation() -> str:
    lines = EXPORT_SCRIPT.read_text(encoding="utf-8").splitlines()
    found = [line for line in lines if _SCRIPT_INVOCATION.match(line)]
    assert len(found) == 1, (
        f"expected exactly one top-level `{_NEEDLE_TOOL}` invocation in "
        f"{EXPORT_SCRIPT.relative_to(REPO_ROOT)}, found {found}. More than one "
        "means the command the header quotes depends on which branch ran."
    )
    return found[0]


def test_the_export_script_exists_and_is_executable() -> None:
    assert EXPORT_SCRIPT.is_file(), EXPORT_SCRIPT
    assert EXPORT_SCRIPT.stat().st_mode & 0o111, (
        f"{EXPORT_SCRIPT.relative_to(REPO_ROOT)} is not executable "
        f"(mode {EXPORT_SCRIPT.stat().st_mode & 0o777:o})"
    )


def test_the_export_script_fails_fast() -> None:
    """`set -euo pipefail`, and `-e` in particular.

    Added in round 2 for the same reason as the workflow's version: dropping
    `-e` alone was invisible to the suite. Here it would mean a failed version
    probe or a failed `cd` falling through to the export, which is how a
    differently-headed or wrongly-rooted file gets written instead of a
    refusal.
    """
    lines = [
        line
        for line in EXPORT_SCRIPT.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    assert lines[0] == "set -euo pipefail", lines[:3]


def test_the_invocation_is_frozen_and_takes_nothing_from_its_caller() -> None:
    """`--frozen` is a security requirement, not a preference.

    A non-frozen export is permitted to re-resolve, which reads
    head-controlled `pyproject.toml` and can invoke a head-controlled PEP 517
    build backend -- arbitrary code execution inside the one job that holds a
    push credential. The fixed argument list is what makes the generated
    header, and therefore the byte-for-byte check in CI, independent of who
    invoked the script and from where.
    """
    invocation = _script_invocation()
    assert " --frozen" in invocation, invocation
    assert "--directory" not in invocation, invocation
    for interpolation in ("$", "`", "{{"):
        assert interpolation not in invocation, (
            f"the invocation takes {interpolation!r} from its environment, so "
            f"the header `{_NEEDLE_TOOL}` writes is not invocation-site "
            f"independent: {invocation}"
        )


def test_the_generated_header_quotes_the_scripts_own_command() -> None:
    """Line 2 of the committed export is the script's invocation, verbatim.

    `uv` writes the argv it was handed into the header, so this equality is
    what ties the committed bytes to the single definition. It is also the
    check that catches a script edit whose export was never regenerated.
    """
    lines = REQUIREMENTS.read_text(encoding="utf-8").splitlines()
    assert lines[0].startswith("# This file was autogenerated by "), lines[0]
    quoted = lines[1].lstrip("#").strip()
    assert quoted == _script_invocation(), (
        "line 2 of backend/requirements.txt does not quote the script's "
        f"command.\n  header: {quoted}\n  script: {_script_invocation()}\n"
        f"Regenerate it with:\n  {REGENERATE_WITH}"
    )


# ==========================================================================
# 4. One uv version for every producer of the export.
# ==========================================================================

_UV_PIN_LITERAL = re.compile(r'^UV_PIN="(?P<version>[^"]+)"$', re.MULTILINE)
_JOB_KEY = re.compile(r"^  (?P<name>[A-Za-z0-9_-]+):$")
_SETUP_UV = "astral-sh/setup-uv@"
_VERSION_INPUT = re.compile(r'^version:\s*"(?P<version>[^"]+)"$')


def _job_block(job: str, *, keep_comments: bool = False) -> list[str]:
    """The lines of one top-level job of `ci.yml`, by name.

    Named rather than left to taste because `ci.yml` holds four `setup-uv`
    steps and a `node-version:`; "the `version:` in ci.yml" would be three
    different answers.

    Comment lines are blanked by default. `ci.yml`'s `backend` job carries a
    sixty-line commentary that discusses `setup-uv`, `version:` and the job's
    own name, so a locator reading raw text here could be satisfied by prose
    -- the exact finding code review round 1 raised against section 5.
    `keep_comments=True` is for the one sweep whose subject *is* forbidden
    text, where a mention in a comment must also be a failure.
    """
    text = CI_WORKFLOW.read_text(encoding="utf-8")
    lines = (text if keep_comments else code_text(text)).splitlines()
    starts = [
        number for number, line in enumerate(lines) if _JOB_KEY.match(line) is not None
    ]
    for index, start in enumerate(starts):
        if _JOB_KEY.match(lines[start]).group("name") != job:
            continue
        end = starts[index + 1] if index + 1 < len(starts) else len(lines)
        return lines[start + 1 : end]
    raise AssertionError(f"no job named {job!r} in {CI_WORKFLOW.name}")


def _setup_uv_version(lines: list[str], where: str) -> str:
    """The `version:` input of the single `setup-uv` step in `lines`."""
    found: list[str] = []
    for index, line in enumerate(lines):
        if _SETUP_UV not in line or line.lstrip().startswith("#"):
            continue
        for follower in lines[index + 1 :]:
            stripped = follower.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if follower.lstrip().startswith("- "):
                break
            match = _VERSION_INPUT.match(stripped)
            if match is not None:
                found.append(match.group("version"))
                break
    assert len(found) == 1, (
        f"expected exactly one `{_SETUP_UV}` step with a quoted `version:` in "
        f"{where}, found {found}"
    )
    return found[0]


def script_uv_pin() -> str:
    text = EXPORT_SCRIPT.read_text(encoding="utf-8")
    matches = _UV_PIN_LITERAL.findall(text)
    assert len(matches) == 1, (
        'expected exactly one `UV_PIN="..."` literal in '
        f"{EXPORT_SCRIPT.relative_to(REPO_ROOT)}, found {matches}"
    )
    return matches[0]


def test_the_backend_job_locator_really_lands_on_the_backend_job() -> None:
    """Anti-vacuity for `_job_block`: a locator that found nothing, or found
    the whole file, would make the three pin comparisons below meaningless.
    """
    block = _job_block("backend")
    assert any(line.strip() == "name: Backend Tests" for line in block), block[:5]
    assert not any(line.strip().startswith("name: Backend Lint") for line in block), (
        "the `backend` job block bled into a neighbouring job"
    )
    assert sum(1 for line in block if _SETUP_UV in line) == 1, block
    # The comment lines really are gone, so neither assertion above can be
    # satisfied by `ci.yml`'s commentary about this job.
    assert not any(line.lstrip().startswith("#") for line in block), (
        "the job block still carries comment lines"
    )
    # ... and the locator can tell the jobs apart at all.
    other = _job_block("backend-lint")
    assert any(line.strip().startswith("name: Backend Lint") for line in other), other[
        :5
    ]
    assert block != other


def test_the_ci_backend_job_pins_the_scripts_uv_version() -> None:
    """The asserting job and the script must agree, or the diff check lies.

    The script is the single source of truth, so the workflow literal is
    compared *to it*. Editing either one alone is red.
    """
    pinned = _setup_uv_version(_job_block("backend"), "the `backend` job of ci.yml")
    assert pinned == script_uv_pin(), (
        f"ci.yml's `backend` job installs uv {pinned} while "
        f"{EXPORT_SCRIPT.relative_to(REPO_ROOT)} refuses anything but "
        f"UV_PIN={script_uv_pin()}. The export's bytes are a uv-version "
        "artefact: bump both literals in one commit."
    )


def test_the_backend_job_no_longer_passes_an_undeclared_project_file() -> None:
    """`pyproject-file:` is not an input of `astral-sh/setup-uv@v8.1.0`.

    Passing it is not an override; it is a warning and floating-latest uv. The
    repository-wide version of this claim is
    `test_workflow_actions.py`; this one is specifically about the job that
    asserts the export's bytes.
    """
    # `keep_comments=True`: this sweep's subject is forbidden *text*, so a
    # comment naming the input is a failure too, exactly as the repository-wide
    # version in `test_workflow_actions.py` treats it.
    block = _job_block("backend", keep_comments=True)
    assert not [line for line in block if "pyproject-file" in line], block


def test_the_pin_is_not_also_declared_in_pyproject() -> None:
    """`[tool.uv] required-version` was declined, and the reason is structural.

    `backend/pyproject.toml` is head-controlled, and the rule for the
    privileged job is that no head file chooses its toolchain.
    """
    pyproject = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    assert "required-version" not in pyproject.get("tool", {}).get("uv", {}), (
        "backend/pyproject.toml declares a uv `required-version`; it is "
        "head-controlled, so it must not be able to refuse the toolchain the "
        "privileged workflow pinned"
    )


# ==========================================================================
# 5. The shape of the privileged workflow.
#
# Round 1 of code review rejected this section, and the finding is the reason
# everything below parses rather than greps. Both properties the old
# anti-vacuity anchor asserted -- `pull_request_target` and `contents: write`
# -- were already satisfied by the workflow's own **security-model comment**,
# so downgrading the trigger to `pull_request:` (a read-only token and no
# secrets on a dependabot pull request: the mechanism silently dead) and
# widening the permission set to `write-all` both left the suite green. Seven
# more properties the spec fixes -- `persist-credentials: false`, the fork
# gate, the branch gate, the head-*sha* checkout, the `checksum:` pin, the
# `paths:` filter, `cancel-in-progress` -- had no assertion at all, and the
# fork gate is the single control keeping a fork pull request out of a job
# holding a `master`-capable PAT.
#
# A comment cannot satisfy a parsed mapping. So this section reads the
# workflow through `parse_workflow_yaml`, and where it must still read text it
# reads **code text**: the file with comment-only lines removed, which is also
# what makes a *commented-out* required line (`# git push origin ...` with a
# `git push --mirror origin` under it) a failure rather than a pass.
# ==========================================================================


def export_workflow_text() -> str:
    """The workflow's raw bytes, comments and all."""
    return EXPORT_WORKFLOW.read_text(encoding="utf-8")


def export_workflow_code() -> str:
    return code_text(export_workflow_text())


# --------------------------------------------------------------------------
# A YAML subset parser, because this project has no `pyyaml` and acquiring one
# would put it in `backend/requirements.txt` -- the file this task exists to
# keep honest -- and therefore in the Vercel install.
#
# It handles exactly what GitHub workflow files use: block mappings, block
# sequences (at the parent's column or deeper), inline flow sequences, single
# and double quoted scalars, and `|` / `>` block scalars. A block scalar's
# body is captured **raw**, which is what keeps a `run:` step's shell out of
# the structure: it is the string value of one key, never a mapping anyone can
# assert against by accident.
#
# A hand-rolled parser is itself a vacuity risk -- one that discovered nothing
# would make every assertion below pass. Four things rule that out, in the
# `--- the parser's own anti-vacuity ---` block: the parsed step count is
# compared against a dumb regex scan of the same file, every parsed step must
# be a non-empty mapping, the `run:` block count must match the file's
# `run: |` count, and an inline fixture plants every property this section
# asserts into a comment and into a `run:` body and requires the parser *not*
# to see any of them.
# --------------------------------------------------------------------------

_BLOCK_SCALAR = re.compile(
    r"^(?P<key>[A-Za-z0-9_.-]+):[ \t]*(?P<style>[|>][+-]?)[ \t]*$"
)
_KEY_VALUE = re.compile(r"^(?P<key>[A-Za-z0-9_.-]+):(?:[ \t]+(?P<value>.*))?$")
_FLOW_SEQUENCE = re.compile(r"^\[(?P<items>.*)\]$")


class WorkflowParseError(AssertionError):
    """The parser refuses rather than guessing, so a miss cannot read as a pass."""


def _indent_of(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _is_skippable(line: str) -> bool:
    return not line.strip() or line.lstrip().startswith("#")


def _strip_trailing_comment(value: str) -> str:
    """Drop a ` # ...` tail that is not inside a quoted scalar."""
    quote = ""
    for index, char in enumerate(value):
        if quote:
            if char == quote:
                quote = ""
        elif char in "\"'":
            quote = char
        elif char == "#" and index and value[index - 1] in " \t":
            return value[:index]
    return value


def _scalar(raw: str) -> str | list[str]:
    value = _strip_trailing_comment(raw).strip()
    flow = _FLOW_SEQUENCE.match(value)
    if flow is not None:
        return [
            _scalar(item) for item in flow.group("items").split(",") if item.strip()
        ]
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def _next_content(lines: list[str], index: int) -> int:
    while index < len(lines) and _is_skippable(lines[index]):
        index += 1
    return index


def _consume_block_scalar(
    lines: list[str], index: int, parent_indent: int, style: str
) -> tuple[str, int]:
    body: list[str] = []
    while index < len(lines):
        line = lines[index]
        if line.strip() and _indent_of(line) <= parent_indent:
            break
        body.append(line)
        index += 1
    while body and not body[-1].strip():
        body.pop()
    if not body:
        return "", index
    strip = min(_indent_of(line) for line in body if line.strip())
    dedented = [line[strip:] if line.strip() else "" for line in body]
    # `|` keeps the newlines (a shell script); `>` folds them (an `if:`
    # expression, which GitHub evaluates as one line).
    joiner = "\n" if style.startswith("|") else " "
    return joiner.join(dedented).strip() if joiner == " " else "\n".join(
        dedented
    ) + "\n", index


def _parse_mapping(
    lines: list[str], index: int, indent: int, item_starts: set[int]
) -> tuple[dict[str, object], int]:
    mapping: dict[str, object] = {}
    first = True
    while True:
        index = _next_content(lines, index)
        if index >= len(lines):
            break
        column = _indent_of(lines[index])
        if column < indent:
            break
        if column > indent:
            raise WorkflowParseError(
                f"line {index + 1}: unexpected indent {column} inside a mapping "
                f"at column {indent}: {lines[index]!r}"
            )
        if index in item_starts and not first:
            break  # the next item of the enclosing sequence
        first = False
        stripped = lines[index].strip()
        block = _BLOCK_SCALAR.match(stripped)
        if block is not None:
            body, index = _consume_block_scalar(
                lines, index + 1, indent, block.group("style")
            )
            mapping[block.group("key")] = body
            continue
        entry = _KEY_VALUE.match(stripped)
        if entry is None:
            raise WorkflowParseError(f"line {index + 1}: cannot parse {lines[index]!r}")
        key = entry.group("key")
        raw = entry.group("value")
        index += 1
        if raw is None or not raw.strip():
            child, index = _parse_node(lines, index, indent, item_starts)
            mapping[key] = child
        else:
            mapping[key] = _scalar(raw)
    return mapping, index


def _parse_sequence(
    lines: list[str], index: int, indent: int, item_starts: set[int]
) -> tuple[list[object], int]:
    items: list[object] = []
    while True:
        index = _next_content(lines, index)
        if (
            index >= len(lines)
            or _indent_of(lines[index]) != indent
            or index not in item_starts
        ):
            break
        stripped = lines[index].strip()
        if _KEY_VALUE.match(stripped) or _BLOCK_SCALAR.match(stripped):
            item, index = _parse_mapping(lines, index, indent, item_starts)
            items.append(item)
        else:
            items.append(_scalar(stripped))
            index += 1
    return items, index


def _parse_node(
    lines: list[str], index: int, parent_indent: int, item_starts: set[int]
) -> object:
    """A mapping, a sequence, or `None` for a key with no block under it."""
    probe = _next_content(lines, index)
    if probe >= len(lines):
        return None, index
    column = _indent_of(lines[probe])
    if probe in item_starts and column >= parent_indent:
        # YAML lets a sequence sit at its key's own column -- `ci.yml`'s
        # `steps:` does -- or indented under it, as this file's `paths:` does.
        # Checked before the mapping branch, because a sequence item's own
        # line is also "more indented than the key".
        return _parse_sequence(lines, probe, column, item_starts)
    if column > parent_indent:
        return _parse_mapping(lines, probe, column, item_starts)
    return None, index


def parse_workflow_yaml(text: str) -> dict[str, object]:
    """The subset of YAML workflow files use, as nested dicts and lists.

    The single text -> structure entry point. The real-tree assertions and the
    inline fixture below both go through *this* function, so a fixture that
    proved something about a different code path would prove nothing.
    """
    normalised: list[str] = []
    item_starts: set[int] = set()
    for number, line in enumerate(text.splitlines()):
        stripped = line.lstrip(" ")
        if stripped.startswith("- "):
            item_starts.add(number)
            normalised.append(" " * (_indent_of(line) + 2) + stripped[2:])
        elif stripped.rstrip() == "-":
            item_starts.add(number)
            normalised.append(" " * (_indent_of(line) + 2))
        else:
            normalised.append(line)
    document, _ = _parse_mapping(normalised, 0, 0, item_starts)
    if not document:
        raise WorkflowParseError("parsed an empty document")
    return document


# --------------------------------------------------------------------------
# Accessors. Each one raises rather than returning a default, so a renamed job
# or a dropped step is a loud failure and never a silently skipped assertion.
# --------------------------------------------------------------------------

#: The job's name, the one step name every accessor keys off, and the
#: `uses:` refs the two action steps must carry.
REGENERATE_JOB = "regenerate"
CHECKOUT_ACTION = "actions/checkout@v6"
SETUP_UV_ACTION = "astral-sh/setup-uv@v8.1.0"


def export_workflow() -> dict[str, object]:
    return parse_workflow_yaml(export_workflow_text())


def regenerate_job() -> dict[str, object]:
    jobs = export_workflow()["jobs"]
    assert isinstance(jobs, dict), jobs
    assert set(jobs) == {REGENERATE_JOB}, jobs
    return jobs[REGENERATE_JOB]


def regenerate_steps() -> list[dict[str, object]]:
    steps = regenerate_job()["steps"]
    assert isinstance(steps, list), steps
    assert steps, steps
    return steps


def step_using(action: str) -> dict[str, object]:
    matching = [step for step in regenerate_steps() if step.get("uses") == action]
    assert len(matching) == 1, (
        f"expected exactly one step with `uses: {action}`, found {len(matching)}"
    )
    return matching[0]


def step_named(prefix: str) -> dict[str, object]:
    matching = [
        step
        for step in regenerate_steps()
        if str(step.get("name", "")).startswith(prefix)
    ]
    assert len(matching) == 1, (
        f"expected exactly one step whose name starts with {prefix!r}, "
        f"found {[step.get('name') for step in regenerate_steps()]}"
    )
    return matching[0]


# --- the parser's own anti-vacuity ----------------------------------------

#: Every property section 5 asserts, planted where it must *not* count: once
#: in a comment and once inside a `run:` body. If the parser reported any of
#: these, every structural assertion below would be satisfiable by prose --
#: which is exactly the round-1 finding, as a permanent test case.
FAKE_WORKFLOW_WITH_THE_PROPERTIES_ONLY_IN_PROSE = """
name: Decoy
# This decoy's comment talks about pull_request_target and contents: write,
# about persist-credentials: false, and about
# github.event.pull_request.head.repo.full_name == github.repository.

on:
  push:
    branches: [ master ]

permissions: write-all

jobs:
  decoy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v6
      with:
        fetch-depth: 0
    - name: Talk about the properties without having them
      run: |
        echo "pull_request_target"
        echo "contents: write"
        echo "persist-credentials: false"
        echo "checksum: 23bf5552"
"""


def test_the_parser_does_not_mistake_prose_for_structure() -> None:
    """The round-1 finding, pinned as a test that can never pass vacuously."""
    document = parse_workflow_yaml(FAKE_WORKFLOW_WITH_THE_PROPERTIES_ONLY_IN_PROSE)

    # Every needle the old grep-based test used is present in this text...
    for needle in (
        "pull_request_target",
        "contents: write",
        "persist-credentials: false",
        "github.event.pull_request.head.repo.full_name == github.repository",
    ):
        assert needle in FAKE_WORKFLOW_WITH_THE_PROPERTIES_ONLY_IN_PROSE, needle

    # ... and the parser reports none of them.
    assert set(document["on"]) == {"push"}, document["on"]
    assert document["permissions"] == "write-all", document["permissions"]
    job = document["jobs"]["decoy"]
    assert "if" not in job, job
    checkout = job["steps"][0]
    assert checkout["with"] == {"fetch-depth": "0"}, checkout
    assert "persist-credentials" not in checkout["with"], checkout
    talker = job["steps"][1]
    assert set(talker) == {"name", "run"}, talker
    assert "checksum" not in talker, talker


def test_the_parser_finds_every_step_a_dumb_scan_finds() -> None:
    """No literal count: both sides are derived from the file at run time."""
    lines = export_workflow_text().splitlines()
    scanned = [
        number
        for number, line in enumerate(lines, 1)
        if re.match(r"^    - (?:name|uses):", line)
    ]
    steps = regenerate_steps()
    assert scanned, "a plain scan found no step at all; the scan is broken"
    assert len(steps) == len(scanned), (
        f"the parser found {len(steps)} steps but a plain scan found "
        f"{len(scanned)} at lines {scanned}"
    )
    for step in steps:
        assert isinstance(step, dict), step
        assert step, f"a step parsed to an empty mapping: {steps}"
        assert "uses" in step or "run" in step, step


def test_the_parser_captures_every_run_body_as_one_scalar() -> None:
    """`run: |` bodies must land in the structure as strings, not mappings.

    This is what keeps a step's shell out of the structural assertions, so it
    has to be measured rather than assumed.
    """
    declared = export_workflow_text().count("run: |")
    bodies = [step["run"] for step in regenerate_steps() if "run" in step]
    assert declared > 0, "the workflow declares no `run: |` block at all"
    assert len(bodies) == declared, (declared, len(bodies))
    for body in bodies:
        assert isinstance(body, str), body
        assert body.strip(), body


# --- the trigger, the permissions and the gate ----------------------------


def test_the_workflow_triggers_only_on_pull_request_target() -> None:
    """`pull_request` cannot work here and must not be reachable by accident.

    A `pull_request` run on a dependabot pull request gets a read-only
    `GITHUB_TOKEN` and no Actions secrets, so the mechanism would be silently
    dead -- a run that exists and does nothing, which is the failure mode this
    whole task is built against.
    """
    triggers = export_workflow()["on"]
    assert set(triggers) == {"pull_request_target"}, triggers
    trigger = triggers["pull_request_target"]
    assert trigger["types"] == ["opened", "synchronize", "reopened"], trigger
    assert trigger["paths"] == ["backend/**"], trigger


def test_the_workflow_grants_contents_write_and_nothing_else() -> None:
    """Spec §2: "`permissions:` is `contents: write` and nothing else"."""
    assert export_workflow()["permissions"] == {"contents": "write"}, export_workflow()[
        "permissions"
    ]


def test_the_workflow_serialises_runs_per_pull_request() -> None:
    """A superseded head sha must not race its successor into a push."""
    concurrency = export_workflow()["concurrency"]
    assert "github.event.pull_request.number" in concurrency["group"], concurrency
    assert concurrency["cancel-in-progress"] == "true", concurrency


#: The job gate, as a set of conjuncts. Compared as a set so a reflow is not a
#: red test, and compared *exactly* so neither gate can be dropped and nothing
#: can be added -- in particular nothing reading the acting account, which is
#: what makes a dependabot-shaped branch exercise the identical path.
#:
#: The same-repository conjunct is the load-bearing one: a fork can name its
#: branch `dependabot/uv/anything`, so the branch prefix alone is
#: attacker-satisfiable, and this job holds a PAT that can push to `master`.
EXPECTED_GATE = frozenset(
    {
        "startsWith(github.head_ref, 'dependabot/uv/')",
        "github.event.pull_request.head.repo.full_name == github.repository",
    }
)


def test_the_job_gate_is_the_branch_prefix_and_the_same_repository_only() -> None:
    gate = regenerate_job()["if"]
    assert isinstance(gate, str), gate
    assert gate, "the job carries no `if:` gate at all"
    conjuncts = frozenset(part.strip() for part in gate.split("&&"))
    assert conjuncts == EXPECTED_GATE, (
        f"the job gate is {sorted(conjuncts)}; it must be exactly "
        f"{sorted(EXPECTED_GATE)}. Dropping the same-repository conjunct opens "
        "this job -- which holds a push credential -- to any fork pull request "
        "whose branch happens to start with `dependabot/uv/`."
    )
    assert len(conjuncts) == len(gate.split("&&")), (
        f"duplicate conjuncts in the gate: {gate}"
    )


# --- the checkout and the toolchain ---------------------------------------

#: Asserted as an exact mapping rather than key by key: an exact mapping is
#: the only form in which *deleting* `persist-credentials: false` is a
#: failure, and that deletion is the realistic regression -- nobody writes
#: `persist-credentials: true`, they just drop the line, after which
#: `actions/checkout` persists the workflow token into a tree built from
#: pull-request data.
EXPECTED_CHECKOUT_INPUTS = {
    # The head *sha*, never `github.head_ref`: a ref is mutable and can be
    # moved between the gate's evaluation and the checkout.
    "ref": "${{ github.event.pull_request.head.sha }}",
    "persist-credentials": "false",
    "fetch-depth": "1",
}


def test_the_head_checkout_is_a_sha_and_carries_no_credential() -> None:
    assert step_using(CHECKOUT_ACTION)["with"] == EXPECTED_CHECKOUT_INPUTS, step_using(
        CHECKOUT_ACTION
    ).get("with")


def test_there_is_exactly_one_checkout_step() -> None:
    """`actions/checkout`'s `path:` cannot escape the workspace, and a base
    checkout written first is deleted by the `git clean -ffdx` of the head
    checkout that follows. The base script is fetched by sha instead.
    """
    checkouts = [
        step
        for step in regenerate_steps()
        if str(step.get("uses", "")).startswith("actions/checkout@")
    ]
    assert len(checkouts) == 1, checkouts


#: sha256 of `uv-x86_64-unknown-linux-gnu.tar.gz` at tag `0.12.19`, from the
#: release's own `.sha256` sidecar. `setup-uv@v8.1.0` validates its download
#: against a caller-supplied checksum or its baked table, and that table has
#: no entry for a uv newer than the action's tag -- in which case validation
#: returns silently. Every other `setup-uv` step in this repository lives with
#: that; this is the one job holding a push credential, so it does not.
EXPECTED_UV_CHECKSUM = (
    "23bf5552d220e0842b65c862097b2ebaeba0064b74eda5e565e77fd25969d8c8"
)


def test_the_setup_uv_step_pins_the_version_and_the_artefact_checksum() -> None:
    inputs = step_using(SETUP_UV_ACTION)["with"]
    assert set(inputs) == {"version", "checksum", "enable-cache"}, inputs
    assert inputs["version"] == script_uv_pin(), (inputs, script_uv_pin())
    assert inputs["checksum"] == EXPECTED_UV_CHECKSUM, inputs
    assert inputs["enable-cache"] == "false", inputs


def test_the_export_workflow_pins_the_scripts_uv_version() -> None:
    """The same claim as above, phrased against the script as source of truth.

    Kept separate because its failure message is the one a reader needs when
    the two literals drift, and because `script_uv_pin()` is the assertion
    R3 names.
    """
    pinned = step_using(SETUP_UV_ACTION)["with"]["version"]
    assert pinned == script_uv_pin(), (
        f"requirements-export.yml installs uv {pinned} while "
        f"{EXPORT_SCRIPT.relative_to(REPO_ROOT)} refuses anything but "
        f"UV_PIN={script_uv_pin()}. This is the job that regenerates the "
        "export on a dependabot PR: a mismatch is a refusal, by design."
    )


# --- the three shell steps ------------------------------------------------

#: Fragments the workflow must carry verbatim, matched against **code text**
#: so that commenting one out is a failure. Each one is a property the spec
#: fixed rather than left to the implementer, in the exact form the file must
#: use -- a paraphrase would pass review and still be wrong at run time.
REQUIRED_FRAGMENTS = (
    # The base copy is fetched, never assumed to be an ancestor of the head.
    'git fetch --no-tags --depth=1 origin "$BASE_SHA"',
    'git show "$BASE_SHA":backend/scripts/export_requirements.sh',
    # Executed out of the work tree, by absolute path, never through PATH.
    'bash "$RUNNER_TEMP/export_requirements.sh"',
    # A detached, shallow head has no upstream and `HEAD` is not a branch.
    'git push origin HEAD:refs/heads/"$HEAD_REF"',
    # The commit is attributed to a GitHub account, so
    # `require_extra_approval_for_unattributed_changes` is not engaged.
    "heitor.polidoro@gmail.com",
    # The commit carries only the export, whatever else is in the tree.
    "-- backend/requirements.txt",
)

#: Text the workflow's *code* must not carry, each with the reason. Matched
#: against code text, so the security-model comment may discuss `uv lock` and
#: the acting account without tripping the sweep -- a comment is not a step.
FORBIDDEN_FRAGMENTS = {
    "actions/cache": (
        "a pull_request_target run writes to the base-branch cache scope, so "
        "caching here is a write path from a PR branch into master's CI inputs"
    ),
    "uv lock": (
        "a lock command reads head-controlled pyproject.toml and can reach a "
        "PEP 517 backend out of the head tree; the freshness check lives in "
        "Backend Tests, which holds no secret"
    ),
    "uv sync": "this job installs nothing",
    "commit -a": "the commit must carry only backend/requirements.txt",
    "github.actor": (
        "the gate is the branch name, so a dependabot-shaped branch exercises "
        "the identical path with nothing relaxed"
    ),
    "github.triggering_actor": "same reason as github.actor",
    "pull_request.user": "same reason as github.actor",
    "persist-credentials: true": "the head checkout must carry no credential",
    "set -x": "tracing a step that handles a token prints the token",
}


def test_the_code_text_helper_drops_comments_and_only_comments() -> None:
    """Anti-vacuity for every code-text sweep below.

    A `code_text` that returned the empty string would make the forbidden
    sweep pass and the required sweep fail loudly; one that returned its input
    unchanged would silently restore the round-1 finding. Neither is possible
    with this pinned.
    """
    sample = (
        "# a comment mentioning actions/cache and persist-credentials: true\n"
        "    code: here\n"
        "        # an indented shell comment\n"
        "        git push origin HEAD\n"
    )
    assert code_text(sample).splitlines() == [
        "",
        "    code: here",
        "",
        "        git push origin HEAD",
    ]
    code = export_workflow_code()
    assert code.count("\n") == export_workflow_text().count("\n"), (
        "code_text changed the line count, so a reported line number would lie"
    )
    assert len(code) < len(export_workflow_text()), (
        "code_text removed nothing from a file with a 60-line comment header"
    )
    assert "runs-on: ubuntu-latest" in code, (
        "code_text removed a real line, not a comment"
    )


def test_every_shell_step_fails_fast() -> None:
    """`set -euo pipefail` on the first line of every `run:` body.

    Added in round 2: the sweep found that dropping the `-e` alone left the
    suite green, and in the push step that matters specifically. Without it a
    failing commit falls through to the push and then to the
    `export regenerated; pushed <sha>` summary line, so the job would report
    an outcome it never reached -- the one thing section 2's observable exists
    to make impossible.
    """
    for step in regenerate_steps():
        if "run" not in step:
            continue
        body = code_text(str(step["run"])).strip()
        assert body.startswith("set -euo pipefail"), (
            f"{step.get('name')!r} does not open with `set -euo pipefail`:\n"
            f"{body[:200]}"
        )


def test_the_export_workflow_carries_every_fixed_form() -> None:
    code = export_workflow_code()
    missing = [fragment for fragment in REQUIRED_FRAGMENTS if fragment not in code]
    assert not missing, (
        f"{EXPORT_WORKFLOW.name} is missing these verbatim forms (comments do "
        f"not count): {missing}"
    )


def test_the_export_workflow_carries_nothing_forbidden() -> None:
    code = export_workflow_code()
    offenders = {
        fragment: reason
        for fragment, reason in FORBIDDEN_FRAGMENTS.items()
        if fragment in code
    }
    assert not offenders, f"{EXPORT_WORKFLOW.name}: {offenders}"


def test_the_export_workflow_names_the_script_when_the_base_lacks_it() -> None:
    """Until this lands on `master` that is the state of every base sha, and a
    bare `git`/`cp` error would read as a broken workflow rather than as a
    mechanism that is not deployed yet.
    """
    body = code_text(step_named("Take the export script")["run"])
    failures = [
        line
        for line in body.splitlines()
        if "::error::" in line and "backend/scripts/export_requirements.sh" in line
    ]
    assert failures, (
        "the base-sha step has no `::error::` line naming "
        f"backend/scripts/export_requirements.sh:\n{body}"
    )
    # Asserted on *this step's* body rather than on the file, so it cannot be
    # satisfied by the `exit 1` that belongs to the push step's token guard.
    assert "exit 1" in body, body


def test_the_export_workflow_fails_when_the_push_token_is_absent() -> None:
    """An absent secret must fail the job, not skip it quietly.

    This repository already learned from `SONAR_TOKEN` that a
    dependabot-context run sees a different secret list than it expects.
    """
    carriers = [
        step
        for step in regenerate_steps()
        if "REQUIREMENTS_EXPORT_TOKEN" in str(step.get("env", ""))
    ]
    assert len(carriers) == 1, (
        "the push secret must be in exactly one step's `env:`, found "
        f"{[step.get('name') for step in carriers]}"
    )
    body = code_text(carriers[0]["run"])
    assert '-z "${GIT_PUSH_TOKEN:-}"' in body, (
        f"nothing in the push step tests the token for empty:\n{body}"
    )
    assert "REQUIREMENTS_EXPORT_TOKEN" in body, (
        "the failure message does not name the secret the operator must mint"
    )


#: The two outcome phrases, asserted verbatim: "ran and found nothing to do"
#: must be distinguishable from "never triggered", and a paraphrase in either
#: branch takes that distinction away.
SUMMARY_PHRASES = (
    "export regenerated; pushed",
    "export already matches the lock; nothing to push",
)


def test_every_reachable_path_writes_exactly_one_summary_line() -> None:
    """One `$GITHUB_STEP_SUMMARY` write per outcome, and only those two.

    The failure mode this repository keeps reproducing is a workflow that
    silently does nothing, where a no-op run and a run that never happened
    look identical. Two writes on one path would be as bad as none: the
    summary would stop being readable as a single verdict.
    """
    writes = [
        line.strip()
        for step in regenerate_steps()
        for line in code_text(str(step.get("run", ""))).splitlines()
        if "GITHUB_STEP_SUMMARY" in line and "echo" in line
    ]
    assert len(writes) == len(SUMMARY_PHRASES), writes
    for phrase in SUMMARY_PHRASES:
        matching = [write for write in writes if phrase in write]
        assert len(matching) == 1, (phrase, writes)
        assert "$BASE_SHA" in matching[0], (
            f"the {phrase!r} summary line does not name the base sha: {matching[0]}"
        )
    # Nothing else may write to the summary, or "exactly one line" is false.
    assert all(
        any(phrase in write for phrase in SUMMARY_PHRASES) for write in writes
    ), writes


# ==========================================================================
# 5b. The three checks APRAS-121 adds to `Backend Tests`.
#
# Added in round 2. The round-1 suite asserted nothing at all about them, so
# deleting the regenerate-and-diff step -- the only thing that makes a
# hand-edited export a red required check -- left every test green. Same shape
# as the review's finding 2, found by the sweep it asked for.
#
# Read through the same parser as section 5, so a step named in `ci.yml`'s
# sixty-line commentary is not a step.
# ==========================================================================

#: The three steps, in the order §3 of the spec fixes, and the step they must
#: all precede. Placed first they still report a verdict when the known
#: `Backend Tests` hang recurs, which is the whole reason the order is fixed.
LOCK_CHECK_STEP = "Assert the lock is fresh"
REGENERATE_STEP = "Regenerate the export and assert"
DRY_RUN_STEP = "Dry-run the committed export"
PYTEST_STEP = "Run tests with coverage"


def ci_backend_steps() -> list[dict[str, object]]:
    steps = parse_workflow_yaml(CI_WORKFLOW.read_text(encoding="utf-8"))["jobs"][
        "backend"
    ]["steps"]
    assert isinstance(steps, list), steps
    assert len(steps) > 5, steps
    return steps


def _ci_step_index(prefix: str) -> int:
    matching = [
        index
        for index, step in enumerate(ci_backend_steps())
        if str(step.get("name", "")).startswith(prefix)
    ]
    assert len(matching) == 1, (
        f"expected exactly one `Backend Tests` step named {prefix!r}, found "
        f"{[step.get('name') for step in ci_backend_steps()]}"
    )
    return matching[0]


def _ci_step_run(prefix: str) -> str:
    step = ci_backend_steps()[_ci_step_index(prefix)]
    body = step.get("run")
    assert isinstance(body, str), (prefix, step)
    assert body.strip(), (prefix, step)
    assert step.get("continue-on-error") is None, (
        f"{prefix}: a required check must not be `continue-on-error`"
    )
    return code_text(body)


def test_the_three_export_checks_run_in_order_before_pytest() -> None:
    order = [
        _ci_step_index(LOCK_CHECK_STEP),
        _ci_step_index(REGENERATE_STEP),
        _ci_step_index(DRY_RUN_STEP),
        _ci_step_index(PYTEST_STEP),
    ]
    assert order == sorted(order), (
        f"the three export checks must precede the wrapped pytest step, in "
        f"the spec's order; got indices {order}"
    )


def test_the_lock_freshness_check_is_the_form_the_spec_chose() -> None:
    """`uv lock --check`, and not the `--locked` export variant.

    Any `uv` + whitespace + `export` text in a workflow is what section 2's
    guard forbids, which is why the freshness assertion is spelled this way.
    """
    body = _ci_step_run(LOCK_CHECK_STEP)
    assert "uv lock --check" in body, body
    assert "cd backend" in body, body


def test_the_regenerate_and_diff_step_runs_the_script_and_fails_on_a_diff() -> None:
    """The byte-level check: without it a hand-edited export is only caught at
    pin level, which cannot see the generated header, the ordering or the
    environment markers.
    """
    body = _ci_step_run(REGENERATE_STEP)
    assert "bash backend/scripts/export_requirements.sh" in body, body
    assert "git diff --exit-code -- backend/requirements.txt" in body, body


def test_the_dry_run_is_isolated_from_the_projects_own_virtualenv() -> None:
    """By the time this runs, `uv sync --all-groups` has filled
    `backend/.venv` with the lock's full contents, so a dry run against *that*
    would be a materially weaker, differently-behaving check.
    """
    body = _ci_step_run(DRY_RUN_STEP)
    assert 'uv venv --python 3.13 "$RUNNER_TEMP/export-check"' in body, body
    assert '--python "$RUNNER_TEMP/export-check"' in body, body
    assert "-r backend/requirements.txt" in body, body
    assert ".venv" not in body, (
        "the dry run must not reach the project's own virtualenv:\n" + body
    )
    # `--python 3.13` is written out rather than inherited, so the interpreter
    # is readable here and does not move when `backend/.python-version` does.
    assert ".python-version" not in body, body


# ==========================================================================
# 6. The documentation corrections.
# ==========================================================================


def test_dependabot_yml_no_longer_claims_the_ecosystem_regenerates_the_export() -> None:
    """The comment used to say uv updates the three files "together".

    It does not: it bumps the export line by line, with no resolver behind it,
    which is how `cd8de18` landed `pydantic==2.13.5` beside
    `pydantic-core==2.49.0`.
    """
    raw = DEPENDABOT_YML.read_text(encoding="utf-8")
    text = " ".join(raw.split())
    assert "`pyproject.toml`, `uv.lock` and the export together" not in text, (
        "dependabot.yml still claims the uv ecosystem regenerates the export"
    )
    # Located, not merely present: the claim belongs to the `uv` ecosystem
    # block, and a mention anywhere in the file -- the `npm` block's comments,
    # say -- would not be the correction R10 asks for.
    uv_block_start = raw.index('package-ecosystem: "uv"')
    npm_block_start = raw.index('package-ecosystem: "npm"')
    assert uv_block_start < npm_block_start, "dependabot.yml reordered"
    naming = raw.index("requirements-export.yml")
    assert naming < npm_block_start, (
        "dependabot.yml names requirements-export.yml only outside the uv "
        f"ecosystem block (offset {naming}, npm block at {npm_block_start})"
    )


#: Asserted verbatim, whitespace-collapsed because `AGENTS.md` wraps prose.
AGENTS_MD_CLAIMS = (
    "`backend/requirements.txt` is never hand-edited",
    "`backend/scripts/export_requirements.sh` is the only way to regenerate it",
)


def test_agents_md_names_the_script_as_the_only_regeneration_path() -> None:
    text = " ".join(AGENTS_MD.read_text(encoding="utf-8").split())
    missing = [claim for claim in AGENTS_MD_CLAIMS if claim not in text]
    assert not missing, f"AGENTS.md is missing these claims verbatim: {missing}"


# ==========================================================================
# 7. This module's own offline contract.
# ==========================================================================

#: Importing any of these would make a red test here possible with no change
#: in this repository.
FORBIDDEN_IMPORTS = frozenset(
    {
        "subprocess",
        "socket",
        "urllib",
        "http",
        "requests",
        "httpx",
        "ftplib",
        "asyncio",
    }
)

#: Attribute calls that would reach the network or a child process.
FORBIDDEN_CALLS = frozenset(
    {"system", "popen", "urlopen", "check_output", "check_call", "call", "request"}
)

#: Every receiver a `read_text` call in this module may have. All of them are
#: paths in the working tree, and `path` is only ever a workflow file or a test
#: module yielded by `_guarded_files()`.
#: Bare names only. Every path this module reads is a module-level constant
#: or a `path` yielded by `_guarded_files()`, so this set stays readable and
#: a new read has to introduce a named constant rather than an inline
#: expression -- which is also why no quoting variants are enumerated here.
PERMITTED_READ_RECEIVERS = frozenset(
    {
        "REQUIREMENTS",
        "UV_LOCK",
        "EXPORT_SCRIPT",
        "EXPORT_WORKFLOW",
        "DEPENDABOT_YML",
        "PYPROJECT",
        "AGENTS_MD",
        "CI_WORKFLOW",
        "THIS_MODULE",
        "path",
    }
)


def _module_tree() -> ast.Module:
    return ast.parse(THIS_MODULE.read_text(encoding="utf-8"))


def test_this_module_imports_nothing_that_could_reach_the_network() -> None:
    imported: set[str] = set()
    for node in ast.walk(_module_tree()):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert not imported & FORBIDDEN_IMPORTS, sorted(imported & FORBIDDEN_IMPORTS)


def test_this_module_makes_no_subprocess_or_network_call() -> None:
    called = {
        node.func.attr
        for node in ast.walk(_module_tree())
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    assert not called & FORBIDDEN_CALLS, sorted(called & FORBIDDEN_CALLS)


def test_this_module_reads_only_files_in_the_working_tree() -> None:
    receivers = {
        ast.unparse(node.func.value)
        for node in ast.walk(_module_tree())
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "read_text"
    }
    assert receivers, "no `read_text` call found; this check has stopped checking"
    assert receivers <= PERMITTED_READ_RECEIVERS, sorted(
        receivers - PERMITTED_READ_RECEIVERS
    )

    # The runtime half of the same claim: nothing `_guarded_files()` yields
    # lives outside the two directories and the one file it names.
    for path in _guarded_files():
        assert path == AGENTS_MD or path.parent in {WORKFLOWS_DIR, TESTS_DIR}, path
