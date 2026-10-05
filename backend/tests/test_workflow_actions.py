"""`astral-sh/setup-uv` must pin uv by a literal `version:`, and only ever
pass inputs the pinned ref actually declares.

Every `setup-uv` step in this repository used to pass `pyproject-file:`, an
input `astral-sh/setup-uv@v8.1.0` **does not declare**. GitHub does not fail a
step for an undeclared input; it prints a warning and carries on, so all four
steps silently installed floating-latest uv. On run `36924174723` (head
`25e9dc6`, 2026-10-01) that was uv **0.12.21**, against the 0.12.19 the
development machine runs.

The runner said so in as many words, and that warning is the provenance of the
allow-list below -- it enumerates the action's declared inputs *for the exact
pinned ref*, which no file in this repository can do as authoritatively::

    ##[warning]Unexpected input(s) 'pyproject-file', valid inputs are
    ['version', 'version-file', ...]
    Could not determine uv version from uv.toml or pyproject.toml.
    Falling back to latest.
    Successfully installed uv version 0.12.21

What this module guards, and why each piece exists:

1. **no undeclared input** on any `setup-uv` step, checked against an
   allow-list keyed by the exact `uses:` ref. A ref the map does not know is
   itself a failure, with the command to re-derive its inputs in the message --
   so the map cannot rot silently, and the staleness window is exactly the
   commit that bumps the ref.
2. **every step pins `version:`, and all the literals are the same string.**
   The agreement assertion is the pin's only backstop and it compares literals,
   so one literal is carried across every step.
3. **four anti-vacuity assertions.** This module parses the workflow text by
   hand -- `pyyaml` is not a dependency of this project and adding one is out
   of scope -- which makes exactly one failure mode load-bearing: a parser that
   discovers nothing, or an empty `with:` mapping, would make every other
   assertion here pass while guarding nothing. So the discovered step count is
   compared against a *derived* scan of the tree (never a hard-coded number),
   both step spellings present in this repository are required to be
   exercised, every parsed mapping must be non-empty, and an inline
   fake-workflow fixture carrying `pyproject-file:` must be *flagged* by the
   same `parse_setup_uv_steps` entry point the real-tree scan calls.

The module is offline by construction: it reads workflow text and `AGENTS.md`
and nothing else -- no network, no `subprocess`, no `uv` invocation. A guard
that can go red for a reason outside this repository is a guard someone
deletes, and `scripts/assert_no_skips.py` leaves no legitimate "network
unavailable" escape anyway.
"""

from __future__ import annotations

import ast
import pathlib
import re
from dataclasses import dataclass

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"
AGENTS_MD = REPO_ROOT / "AGENTS.md"
THIS_MODULE = pathlib.Path(__file__).resolve()

#: The marker a `setup-uv` step is found by. Everything that counts steps --
#: the parser and the derived-count scan alike -- keys off this one string.
SETUP_UV = "astral-sh/setup-uv@"

#: The literal every `setup-uv` step must pin. Adopted verbatim from
#: APRAS-121, which needs the *producing* uv of `backend/requirements.txt` to
#: be the developer's; the other steps carry the same string so that the
#: agreement assertion below has something to compare.
EXPECTED_UV_VERSION = "0.12.19"

#: The declared inputs of `astral-sh/setup-uv`, keyed by the exact `uses:` ref.
#:
#: Provenance of the `v8.1.0` entry: these are **exactly the 24 names the
#: runner printed** in its `Unexpected input(s)` warning on run
#: ``36924174723`` -- jobs ``110577272457`` (Backend Lint),
#: ``110577272946`` (Backend Tests) and ``110577272967`` (Backend Migration
#: Tests). The runner resolves the action at that ref, so its own list beats
#: any transcription of `action.yml`. `checksum` is in it, which is why
#: APRAS-121's step may pass `checksum:` and still satisfy this guard.
#:
#: To add an entry for a new ref, re-derive the names with::
#:
#:     gh api repos/astral-sh/setup-uv/contents/action.yml?ref=<ref> \
#:       --jq '.content' | base64 -d
DECLARED_INPUTS: dict[str, frozenset[str]] = {
    "v8.1.0": frozenset(
        {
            "version",
            "version-file",
            "python-version",
            "activate-environment",
            "venv-path",
            "no-project",
            "working-directory",
            "checksum",
            "github-token",
            "enable-cache",
            "cache-dependency-glob",
            "restore-cache",
            "save-cache",
            "cache-suffix",
            "cache-local-path",
            "prune-cache",
            "cache-python",
            "ignore-nothing-to-cache",
            "ignore-empty-workdir",
            "tool-dir",
            "tool-bin-dir",
            "manifest-file",
            "add-problem-matchers",
            "resolution-strategy",
        }
    ),
}

#: The command that re-derives an unknown ref's inputs, quoted into the
#: failure message so the next person does not have to find it here.
REDERIVE_COMMAND = (
    "gh api repos/astral-sh/setup-uv/contents/action.yml?ref={ref} "
    "--jq '.content' | base64 -d"
)

_USES_SETUP_UV = re.compile(
    r"^(?P<lead>\s*(?:-\s+)?)uses:\s*astral-sh/setup-uv@(?P<ref>\S+)"
)
_MAPPING_ENTRY = re.compile(r"^(?P<key>[A-Za-z0-9_.-]+):(?P<rest>\s.*)?$")


@dataclass(frozen=True)
class SetupUvStep:
    """One `uses: astral-sh/setup-uv@<ref>` step and its parsed `with:` block."""

    source: str
    line: int
    ref: str
    inputs: dict[str, str]

    @property
    def where(self) -> str:
        return f"{self.source}:{self.line}"


def _content_column(line: str) -> int:
    """Column the step's *content* starts at, list dash or not.

    `ci.yml` spells a step as `- name:` followed by an unprefixed `uses:` on
    the next line; `migrate.yml` spells it as a bare `- uses:`. Both put the
    step's keys at the same column once the `- ` is accounted for, and this is
    what lets one parser read both spellings.
    """
    stripped = line.lstrip(" ")
    indent = len(line) - len(stripped)
    return indent + 2 if stripped.startswith("- ") else indent


def parse_setup_uv_steps(text: str, source: str) -> list[SetupUvStep]:
    """Every `setup-uv` step in `text`, with its `with:` mapping.

    The single `text` -> steps entry point. The real-tree scan and the inline
    fixture test below both go through *this* function: a fixture that proved
    something about a separate string-parsing helper would prove nothing about
    the path that reads the actual workflows.
    """
    lines = text.splitlines()
    steps: list[SetupUvStep] = []

    for index, line in enumerate(lines):
        match = _USES_SETUP_UV.match(line)
        if match is None:
            continue
        step_column = _content_column(line)
        inputs = _parse_with_block(lines, index + 1, step_column)
        steps.append(
            SetupUvStep(
                source=source,
                line=index + 1,
                ref=match.group("ref"),
                inputs=inputs,
            )
        )
    return steps


def _parse_with_block(lines: list[str], start: int, step_column: int) -> dict[str, str]:
    """The `with:` mapping of the step whose keys sit at `step_column`."""
    inputs: dict[str, str] = {}
    in_with = False

    for line in lines[start:]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        column = _content_column(line)
        if column < step_column or (in_with and column == step_column):
            break
        if column == step_column:
            # Another key of the same step. `with:` opens the block; any other
            # key (`run:`, `if:`, ...) means we have not reached it yet.
            if line.strip() == "with:":
                in_with = True
            elif line.lstrip().startswith("- "):
                break
            continue
        if not in_with:
            continue
        entry = _MAPPING_ENTRY.match(line.strip())
        if entry is not None:
            inputs[entry.group("key")] = (entry.group("rest") or "").strip()
    return inputs


def workflow_files() -> list[pathlib.Path]:
    """Every workflow file in the tree, in a stable order."""
    return sorted(
        path
        for path in WORKFLOWS_DIR.iterdir()
        if path.is_file() and path.suffix in {".yml", ".yaml"}
    )


def discovered_steps() -> list[SetupUvStep]:
    """Every `setup-uv` step in `.github/workflows/`, derived from the tree."""
    steps: list[SetupUvStep] = []
    for path in workflow_files():
        steps.extend(parse_setup_uv_steps(path.read_text(encoding="utf-8"), path.name))
    return steps


def scanned_occurrence_count() -> int:
    """How many times `astral-sh/setup-uv@` appears, parser not involved.

    Deliberately computed by a dumb substring count over the same files the
    parser reads, so the two sides of the anti-vacuity equality are produced
    by genuinely different code.
    """
    return sum(
        path.read_text(encoding="utf-8").count(SETUP_UV) for path in workflow_files()
    )


def undeclared_inputs(step: SetupUvStep) -> set[str]:
    """The step's `with:` keys that its pinned ref does not declare.

    Raises `KeyError` for a ref the allow-list does not know -- callers turn
    that into a failure naming the re-derivation command, because an unknown
    ref means the guard has no idea what is declared and must not pass.
    """
    return set(step.inputs) - set(DECLARED_INPUTS[step.ref])


# --------------------------------------------------------------------------
# The inline fake-workflow fixture (§D3.4).
#
# Not read from disk and not derived from the real tree: it must keep carrying
# `pyproject-file:` forever, which the real tree must never do again. It
# deliberately uses the bare `- uses:` spelling with an interleaved non-`with:`
# key, so the block-finding logic is exercised and not just the happy path.
# --------------------------------------------------------------------------
FAKE_WORKFLOW_WITH_UNDECLARED_INPUT = """
jobs:
  fake:
    steps:
    - uses: actions/checkout@v6

    - uses: astral-sh/setup-uv@v8.1.0
      id: pinned-uv
      with:
        version: "0.12.19"
        enable-cache: false
        pyproject-file: backend/pyproject.toml

    - run: uv sync --all-groups
"""


def test_the_workflows_directory_is_there_to_read():
    assert WORKFLOWS_DIR.is_dir(), WORKFLOWS_DIR
    assert workflow_files(), f"no workflow files under {WORKFLOWS_DIR}"


# --- anti-vacuity 1: the parser finds everything a dumb scan finds ---------


def test_discovered_step_count_equals_a_scan_of_the_tree():
    """No literal count: both sides are derived from the tree at run time.

    4 steps today, 5 once APRAS-121's `requirements-export.yml` exists -- and
    this assertion is indifferent to which, by construction.
    """
    scanned = scanned_occurrence_count()
    discovered = discovered_steps()
    assert scanned > 0, (
        f"no `{SETUP_UV}` occurrence anywhere under {WORKFLOWS_DIR}; either the "
        "action is gone (then delete this module) or the scan is broken"
    )
    assert len(discovered) == scanned, (
        f"parser found {len(discovered)} `setup-uv` steps but a plain substring "
        f"scan found {scanned} occurrences of `{SETUP_UV}`: "
        f"{[step.where for step in discovered]}"
    )


# --- anti-vacuity 2: both step spellings are exercised ---------------------


def test_both_step_spellings_in_this_repository_are_exercised():
    """`ci.yml` uses `- name:` + `uses:`; `migrate.yml` uses a bare `- uses:`.

    The count equality above cannot catch a parser blind to one spelling,
    because both of its sides derive from the same text.
    """
    sources = {step.source for step in discovered_steps()}
    assert "ci.yml" in sources, sources
    assert "migrate.yml" in sources, sources


# --- anti-vacuity 3: no step parses to an empty mapping -------------------


def test_every_discovered_step_has_a_non_empty_with_mapping():
    steps = discovered_steps()
    assert steps, "no `setup-uv` step discovered at all"
    for step in steps:
        assert step.inputs, f"{step.where}: parsed an empty `with:` mapping"
        assert "enable-cache" in step.inputs, (
            f"{step.where}: parsed `with:` keys {sorted(step.inputs)} with no "
            "`enable-cache`, which every step in this repository passes -- the "
            "parser is reading the wrong block"
        )


# --- anti-vacuity 4: the detector really flags an undeclared key ----------


def test_the_parser_flags_an_undeclared_input_in_the_inline_fixture():
    """The same `parse_setup_uv_steps` the real scan calls, on fake text.

    Assertions 1-3 are all satisfiable by a parser that only ever extracts
    `version` and `enable-cache`, which would then pass the undeclared-input
    guard below vacuously. This is what rules that out, permanently.
    """
    steps = parse_setup_uv_steps(
        FAKE_WORKFLOW_WITH_UNDECLARED_INPUT, "fake-workflow.yml"
    )
    assert len(steps) == 1, steps
    step = steps[0]
    assert step.ref == "v8.1.0", step
    assert step.inputs == {
        "version": '"0.12.19"',
        "enable-cache": "false",
        "pyproject-file": "backend/pyproject.toml",
    }, step.inputs
    assert undeclared_inputs(step) == {"pyproject-file"}, undeclared_inputs(step)


# --- the guard proper ------------------------------------------------------


def test_the_allow_list_entry_for_v8_1_0_is_the_runner_s_own_24_names():
    entry = DECLARED_INPUTS["v8.1.0"]
    assert len(entry) == 24, sorted(entry)
    assert "checksum" in entry, (
        "APRAS-121's step passes `checksum:`, which v8.1.0 declares; dropping it "
        "from the allow-list would fail that step for no reason"
    )
    assert "pyproject-file" not in entry, (
        "`pyproject-file` is the input this whole module exists because "
        "v8.1.0 does not declare it"
    )


def test_no_setup_uv_step_passes_an_input_its_ref_does_not_declare():
    for step in discovered_steps():
        if step.ref not in DECLARED_INPUTS:
            raise AssertionError(
                f"{step.where}: `setup-uv` ref {step.ref!r} has no allow-list "
                f"entry, so nothing here knows what it declares. Re-derive its "
                f"inputs with:\n    {REDERIVE_COMMAND.format(ref=step.ref)}\n"
                f"and add the entry to DECLARED_INPUTS in {THIS_MODULE.name}."
            )
        undeclared = undeclared_inputs(step)
        assert not undeclared, (
            f"{step.where}: `setup-uv@{step.ref}` does not declare "
            f"{sorted(undeclared)}; GitHub ignores undeclared inputs with a "
            "warning rather than failing, so the step quietly does something "
            "other than what it reads as"
        )


def test_no_workflow_passes_pyproject_file_to_anything():
    offenders = [
        f"{path.name}:{number}"
        for path in workflow_files()
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
        if "pyproject-file" in line
    ]
    assert not offenders, f"`pyproject-file` is not an input of setup-uv: {offenders}"


def test_every_setup_uv_step_pins_a_literal_version():
    for step in discovered_steps():
        assert "version" in step.inputs, (
            f"{step.where}: no `version:` input, so this step installs "
            "floating-latest uv"
        )
        assert "version-file" not in step.inputs, (
            f"{step.where}: `version-file:` needs a `required-version` in a "
            "project file, which APRAS-121 declined -- the pin is a literal"
        )


def test_all_setup_uv_version_literals_are_the_same_string():
    literals = {step.where: step.inputs.get("version") for step in discovered_steps()}
    distinct = set(literals.values())
    assert len(distinct) == 1, (
        f"the `version:` literals disagree: {literals}. One uv version in CI is "
        "one thing to reason about, and this comparison is the pin's only "
        "backstop -- bump every literal in the same commit"
    )
    assert distinct == {f'"{EXPECTED_UV_VERSION}"'}, literals


def test_every_setup_uv_step_keeps_the_cache_disabled():
    for step in discovered_steps():
        assert step.inputs.get("enable-cache") == "false", (
            f"{step.where}: expected `enable-cache: false`, got "
            f"{step.inputs.get('enable-cache')!r}"
        )


# --- the AGENTS.md claims (§D5) -------------------------------------------

#: The sentences `AGENTS.md` must carry, asserted verbatim. They state the two
#: reasons one literal is shared -- the agreement assertion compares literals,
#: and one uv version in CI is one thing to reason about -- and deliberately
#: *not* the re-resolution hypothesis of the spec's §D1, which is unmeasured.
AGENTS_MD_CLAIMS = (
    "uv is pinned by a literal `version:` on every `astral-sh/setup-uv` step",
    "`pyproject-file` is not an input of `astral-sh/setup-uv`",
    (
        "One literal is shared by every step for two reasons: the agreement "
        "assertion compares literals"
    ),
    "one uv version in CI is one thing to reason about",
    (
        "The pin is bumped deliberately by the maintainer, in one commit that "
        "edits every `version:` literal together"
    ),
    "No bot does it",
    "the signal is the local `UV_PIN` refusal",
)


def test_agents_md_documents_the_pin_and_its_bump_ritual():
    # Whitespace-collapsed, because a claim is a sentence and `AGENTS.md` wraps
    # its prose: asserting the raw text would make a reflow a red test.
    text = " ".join(AGENTS_MD.read_text(encoding="utf-8").split())
    missing = [claim for claim in AGENTS_MD_CLAIMS if claim not in text]
    assert not missing, f"AGENTS.md is missing these claims verbatim: {missing}"


# --- the module's own offline contract ------------------------------------

#: Importing any of these would make a red test possible with no change in
#: this repository.
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


#: The only three receivers a `read_text` call in this module may have: a
#: workflow path yielded by `workflow_files()`, `AGENTS.md`, and this module's
#: own source. Notably absent is the export script APRAS-121 owns -- this task
#: neither reads nor restates its `UV_PIN`.
PERMITTED_READ_RECEIVERS = frozenset({"path", "AGENTS_MD", "THIS_MODULE"})

#: Attribute calls that would reach the network or a child process.
FORBIDDEN_CALLS = frozenset(
    {"system", "popen", "urlopen", "check_output", "check_call", "call", "request"}
)


def test_this_module_imports_nothing_that_could_reach_the_network():
    tree = ast.parse(THIS_MODULE.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert not imported & FORBIDDEN_IMPORTS, sorted(imported & FORBIDDEN_IMPORTS)


def test_this_module_makes_no_subprocess_or_network_call():
    tree = ast.parse(THIS_MODULE.read_text(encoding="utf-8"))
    called = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    assert not called & FORBIDDEN_CALLS, sorted(called & FORBIDDEN_CALLS)


def test_this_module_reads_only_the_workflows_and_agents_md():
    """Every `read_text` receiver is one of three names, checked by AST.

    The runtime half of the same claim is below it: `workflow_files()` cannot
    return a path outside `.github/workflows/`.
    """
    tree = ast.parse(THIS_MODULE.read_text(encoding="utf-8"))
    receivers = {
        ast.unparse(node.func.value)
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "read_text"
    }
    assert receivers, "no `read_text` call found; this check has stopped checking"
    assert receivers <= PERMITTED_READ_RECEIVERS, sorted(
        receivers - PERMITTED_READ_RECEIVERS
    )

    for path in workflow_files():
        assert path.parent == WORKFLOWS_DIR, path
