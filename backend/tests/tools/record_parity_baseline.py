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
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

# The recorder is executed as `python -m tests.tools.record_parity_baseline`
# from `backend/`, so `tests` is importable as a package.
from app.core.permissions import ROUTE_PERMISSIONS
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

#: The frozen IAM F2 artefact. The recorder refuses to write it, full stop
#: (APRAS-40 §9.2.1): new routes get their own additive file. F2's own
#: `_meta.regenerate` writes to /tmp/regen.json, so it is unaffected.
FROZEN = "tests/data/parity_matrix_baseline.json"

#: The scoped invocation, emitted verbatim as `_meta.regenerate` when
#: `--routes` is given, so `meta["merge_base_sha"] in meta["regenerate"]` holds
#: and the string is executable exactly as written. There is **no**
#: `git worktree add` here, and that is honest: the named routes do not exist
#: at the merge base, so no worktree at that sha can reproduce these cells.
#: The sha names the branch point the route delta is measured from -- the
#: provenance of the accounting, not of the statuses.
SCOPED_REGENERATE = (
    "cd backend && POSTGRES_URL=sqlite:// SECRET_KEY=parity-matrix "
    "uv run python -m tests.tools.record_parity_baseline "
    "--out {out} --merge-base {sha}{routes}"
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


def select_cells(routes: list[str] | None) -> list[tuple[str, str, str]]:
    """`CELLS` filtered to the named `"METHOD /path"` routes.

    `None` or an empty list means all of them, i.e. today's behaviour. An
    unknown route is `SystemExit(2)` naming it, never a silently empty
    recording.
    """
    if not routes:
        return list(CELLS)
    wanted = {tuple(spec.split(" ", 1)) for spec in routes}
    unknown = sorted(wanted - set(ROUTE_PERMISSIONS))
    if unknown:
        print(f"unknown routes: {unknown}", file=sys.stderr)
        raise SystemExit(2)
    return [cell for cell in CELLS if (cell[1], cell[2]) in wanted]


def resolve_merge_base(sha: str | None, run_git: Callable[..., str] = _git) -> str:
    """`sha` if the repository knows it, else `SystemExit(2)`; default HEAD."""
    if sha is None:
        return head_sha(run_git)
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        print(f"--merge-base must be a 40-hex sha, got {sha!r}", file=sys.stderr)
        raise SystemExit(2)
    try:
        run_git("rev-parse", "--verify", f"{sha}^{{commit}}")
    except subprocess.CalledProcessError:
        print(f"--merge-base names no commit: {sha}", file=sys.stderr)
        raise SystemExit(2) from None
    return sha


def record(
    sha: str,
    cells: list[tuple[str, str, str]] | None = None,
    regenerate: str | None = None,
) -> dict:
    """Run `cells` (all 1080 by default) and return the serialisable payload."""
    cells = list(CELLS) if cells is None else cells
    recorded: dict[str, dict[str, dict[str, int]]] = {}
    with tempfile.TemporaryDirectory() as tmp:
        database_path = str(Path(tmp) / "matrix.sqlite3")
        with matrix_engine(database_path) as engine, neutralised_storage():
            world = seed_once(engine)
            for role, method, path in cells:
                with cell_client(engine) as client:
                    status = run_cell(client, world, role, method, path)
                recorded.setdefault(role, {}).setdefault(method, {})[path] = status
    return {
        "_meta": {
            "merge_base_sha": sha,
            "generator": GENERATOR,
            "harness": HARNESS,
            "cell_count": len(cells),
            "regenerate": regenerate or REGENERATE.format(sha=sha),
        },
        "cells": recorded,
    }


def serialise(payload: dict) -> str:
    """The one serialisation, so the file is byte-stable across machines."""
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def refuse_the_frozen_baseline(out: Path) -> None:
    """Exit `2` when `--out` resolves to the frozen F2 artefact.

    Before anything is built, `--overwrite` or not: the F2 baseline records
    what production answered at `02c2025…` and re-recording it would turn the
    star test of IAM F2 into a tautology, silently. New routes get their own
    additive file (APRAS-40 §9.2.1).
    """
    backend_root = Path(__file__).resolve().parent.parent.parent
    if out.resolve() == (backend_root / FROZEN).resolve():
        print(
            f"refusing to write the frozen IAM F2 baseline {FROZEN}.\n"
            "It is byte-identical by contract (APRAS-40 §9.2.1). Record new "
            "routes into their own file with --out and --routes.",
            file=sys.stderr,
        )
        raise SystemExit(2)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=DEFAULT_OUT)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--routes", action="append", default=None)
    parser.add_argument("--merge-base", default=None)
    args = parser.parse_args(argv)

    out = Path(args.out)
    refuse_the_frozen_baseline(out)
    assert_clean_production_tree()

    if out.exists() and not args.overwrite:
        print(f"refusing to overwrite {out} (pass --overwrite)", file=sys.stderr)
        return 1

    sha = resolve_merge_base(args.merge_base)
    cells = select_cells(args.routes)
    regenerate = None
    if args.routes:
        regenerate = SCOPED_REGENERATE.format(
            out=args.out,
            sha=sha,
            routes="".join(f" --routes '{spec}'" for spec in args.routes),
        )

    payload = record(sha, cells=cells, regenerate=regenerate)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(serialise(payload), encoding="utf-8")
    print(f"recorded {payload['_meta']['cell_count']} cells to {out}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
