#!/usr/bin/env bash
#
# Regenerate backend/requirements.txt from backend/uv.lock.
#
# This script is the *only* place the export command is written down.
# `backend/requirements.txt` is the install manifest for the Vercel backend
# deployment (`backend/vercel.json` routes `/(.*)` to `index.py`, and Vercel's
# Python runtime reads neither `pyproject.toml` nor `uv.lock`), so it is the
# one shipped artifact no green CI job exercises. It is never hand-edited:
# dependabot's `uv` ecosystem bumps it line by line with no resolver behind it,
# which is how `cd8de18` landed `pydantic==2.13.5` next to
# `pydantic-core==2.49.0` -- not merely stale, but uninstallable.
#
# Two properties of the invocation below are load-bearing, and
# `backend/tests/test_requirements_export.py` asserts both:
#
#   * `--frozen`. The export is produced from `uv.lock` as committed and may
#     never re-resolve. Re-resolution reads `pyproject.toml` and, for any
#     dependency whose metadata comes from a source distribution, runs a PEP
#     517 build backend out of the project tree -- arbitrary code execution.
#     `.github/workflows/requirements-export.yml` runs this script on a
#     pull request's tree while holding a Contents:write push credential, so
#     "it only reads data" is a requirement there, not a nicety.
#
#     To be precise about what the frozen path does still read, because the
#     stronger claim would be wrong: it reads `pyproject.toml` (and would read
#     `uv.toml`) for project discovery and `[tool.uv]` configuration. What it
#     does not do is obtain *dependency metadata*, which is the only thing
#     that reaches a build backend. The residual is a pull request adding
#     `[tool.uv] required-version`, which makes this script's `uv` refuse to
#     run -- the job then errors and pushes nothing, so it fails closed.
#
#   * a **fixed argument list**: no conditional flags, no `--directory`, and
#     nothing interpolated from the environment. `uv` writes the argv it was
#     handed into the header comment of the file it generates, so a fixed argv
#     is what makes that header -- and therefore CI's byte-for-byte
#     regenerate-and-diff check -- independent of who ran the script and from
#     where.
#
# The pin below is this repository's single source of truth for the uv version
# that produces the export. The export's bytes (the generated header, the
# `# via` annotations, the ordering, the way environment markers are rendered)
# are uv-version artefacts, so a different uv produces a different file and the
# diff check in `Backend Tests` goes red for no cause in the project. Refusing
# up front is the readable failure; a differently-headed export is not.
#
# `.github/workflows/ci.yml` (the `backend` job) and
# `.github/workflows/requirements-export.yml` pass the same literal to
# `astral-sh/setup-uv`, and
# `backend/tests/test_requirements_export.py` compares theirs against this one.
# Editing any one of the three alone is a red test, by design: bump them
# together in a single commit. Nothing bumps them automatically -- dependabot
# does not update a `version:` string input -- so the signal that a bump is due
# is this refusal, fired on a developer who upgraded uv locally.
#
# Deliberately *not* `[tool.uv] required-version` in `backend/pyproject.toml`:
# that file can be edited by a pull request, and the rule for the privileged
# workflow is that no pull-request-controlled file chooses its toolchain.

set -euo pipefail

UV_PIN="0.12.19"

if ! command -v uv >/dev/null 2>&1; then
  echo "error: uv is not on PATH; this script needs uv ${UV_PIN}." >&2
  exit 1
fi

# `uv --version` prints e.g. `uv 0.12.19 (Homebrew 2026-09-24 aarch64-apple-darwin)`.
# Reading that string is the only thing this check does: it opens no project
# file and resolves nothing.
found_version="$(uv --version | awk '{print $2}')"

if [ "$found_version" != "$UV_PIN" ]; then
  echo "error: this script is pinned to uv UV_PIN=${UV_PIN}, but uv --version reports ${found_version}." >&2
  echo "       The export's bytes are a uv-version artefact, so a different uv" >&2
  echo "       would produce a file CI's diff check rejects. Install uv ${UV_PIN}," >&2
  echo "       or bump UV_PIN here together with the version: literal in" >&2
  echo "       .github/workflows/ci.yml and .github/workflows/requirements-export.yml." >&2
  exit 1
fi

# Relative to the **working directory**, not to this file: the copy that
# `.github/workflows/requirements-export.yml` executes is taken from the base
# ref into `$RUNNER_TEMP`, deliberately outside the work tree, so a path
# resolved from `$BASH_SOURCE` would point at the runner's temp directory and
# not at the project. Run this from the repository root -- which is where both
# workflows and a developer in a clean checkout already are.
if [ ! -f backend/pyproject.toml ]; then
  echo "error: run this from the repository root; backend/pyproject.toml is not under $(pwd)." >&2
  exit 1
fi

cd backend

uv export --format requirements-txt --no-hashes --frozen -o requirements.txt
