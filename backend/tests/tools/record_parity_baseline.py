"""Record the `role x route x verb` parity baseline (IAM F2, APRAS-46 §6.4).

The committed, *only* producer of `tests/data/parity_matrix_baseline.json`.

    cd backend
    uv run python -m tests.tools.record_parity_baseline \
        --out tests/data/parity_matrix_baseline.json

It imports the §6.2 harness from `tests/matrix_world.py` unchanged, so the
recorded file and the assertions in `tests/test_permission_parity_matrix.py`
are produced by one implementation of the world. It reads only
`app.main.app`, `ROUTE_PERMISSIONS` and that harness -- never a guard, never a
role set -- so it is production-independent by construction.

**It refuses to run when the production tree is dirty.** Before building
anything it shells out to `git status --porcelain -- app/` and exits `2`
without writing when the output is non-empty. That is the mechanical half of
"the baseline is pre-swap": once a single `app/` file has been edited or
staged, the recorder cannot be run at all, so §10's implementation order is
enforced rather than requested. There is no `--allow-dirty` flag. The
regeneration worktree of `_meta.regenerate` copies in only `tests/` files, so
it still passes the check.

The written payload carries **no timestamp, no hostname and no absolute
path**: the file must be a pure function of the tree at `merge_base_sha`.
Only integer status codes are recorded -- no ids, no bodies, no timings --
which is what makes byte-identity achievable even though the world's UUIDs
are random on every run.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

# The recorder is executed as `python -m tests.tools.record_parity_baseline`
# from `backend/`, so `tests` is importable as a package.
from tests.matrix_world import (
    CELLS,
    cell_client,
    matrix_engine,
    neutralised_storage,
    run_cell,
    seed_once,
)

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Callable

#: Relative, never absolute: the `_meta` block must not leak a path.
GENERATOR = "tests/tools/record_parity_baseline.py"
HARNESS = "tests/matrix_world.py"
DEFAULT_OUT = "tests/data/parity_matrix_baseline.json"

#: `POSTGRES_URL` and `SECRET_KEY` are inlined because `backend/.env` is
#: git-ignored and therefore absent from a fresh worktree, while
#: `app.core.config.Settings` requires both at import time. Neither reaches a
#: recorded value: the matrix builds its own SQLite file and the JWT key only
#: has to round-trip within the run.
REGENERATE = (
    "git worktree add /tmp/apras-parity {sha} && "
    "cp -R backend/tests/matrix_world.py backend/tests/tools "
    "/tmp/apras-parity/backend/tests/ && "
    "(cd /tmp/apras-parity/backend && POSTGRES_URL=sqlite:// "
    "SECRET_KEY=parity-matrix uv run python -m "
    "tests.tools.record_parity_baseline --out /tmp/regen.json) && "
    "diff /tmp/regen.json backend/tests/data/parity_matrix_baseline.json"
)


def _git(*args: str) -> str:
    return subprocess.run(  # noqa: S603
        ["git", *args],  # noqa: S607
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def assert_clean_production_tree(run_git: Callable[..., str] = _git) -> None:
    """Exit `2` when `git status --porcelain -- app/` is non-empty.

    Injectable so `test_recorder_refuses_a_dirty_production_tree` can pin both
    branches without touching the working tree.
    """
    porcelain = run_git("status", "--porcelain", "--", "app/").strip()
    if porcelain:
        print(
            "refusing to record: the production tree is dirty.\n"
            "The parity baseline must be recorded before any `app/` file is\n"
            "edited or staged (APRAS-46 §6.4). Offending paths:\n"
            f"{porcelain}",
            file=sys.stderr,
        )
        raise SystemExit(2)


def head_sha(run_git: Callable[..., str] = _git) -> str:
    """`git rev-parse HEAD` — the merge base, since this runs before the swap."""
    return run_git("rev-parse", "HEAD").strip()


def record(sha: str) -> dict:
    """Run all 1080 cells and return the serialisable payload."""
    cells: dict[str, dict[str, dict[str, int]]] = {}
    with tempfile.TemporaryDirectory() as tmp:
        database_path = str(Path(tmp) / "matrix.sqlite3")
        with matrix_engine(database_path) as engine, neutralised_storage():
            world = seed_once(engine)
            for role, method, path in CELLS:
                with cell_client(engine) as client:
                    status = run_cell(client, world, role, method, path)
                cells.setdefault(role, {}).setdefault(method, {})[path] = status
    return {
        "_meta": {
            "merge_base_sha": sha,
            "generator": GENERATOR,
            "harness": HARNESS,
            "cell_count": len(CELLS),
            "regenerate": REGENERATE.format(sha=sha),
        },
        "cells": cells,
    }


def serialise(payload: dict) -> str:
    """The one serialisation, so the file is byte-stable across machines."""
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=DEFAULT_OUT)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)

    assert_clean_production_tree()

    out = Path(args.out)
    if out.exists() and not args.overwrite:
        print(f"refusing to overwrite {out} (pass --overwrite)", file=sys.stderr)
        return 1

    payload = record(head_sha())
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(serialise(payload), encoding="utf-8")
    print(f"recorded {payload['_meta']['cell_count']} cells to {out}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
