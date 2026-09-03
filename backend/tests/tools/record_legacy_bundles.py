"""Record the legacy `UserRole -> permissions` bundles (IAM F5, APRAS-49 §7.6).

The committed, *only* producer of `tests/data/legacy_role_bundles.json`, and a
sibling of `record_parity_baseline.py` in shape and in discipline::

    cd backend
    uv run python -m tests.tools.record_legacy_bundles \
        --out tests/data/legacy_role_bundles.json

It is run **once**, at the F5 merge base, *before*
`app.core.permissions.LEGACY_ROLE_PERMISSIONS` is deleted. After that deletion
the recorded file is the **only** surviving statement of what the `UserRole`
enum used to mean, and three otherwise-impossible tests read it:

* `tests/test_migrations_postgres.py` -- that migration `0033`'s inlined
  literal is the map that existed;
* `tests/test_migrations_postgres.py::test_effective_permissions_are_unchanged_by_0033`
  -- that the migration's effect on effective permissions is exactly
  `pre | NEW_TIER`;
* `tests/matrix_world.py` -- that the six parity profiles carry the legacy
  bundles.

The written payload carries **no timestamp, no hostname and no absolute
path**: like the parity baseline, the file must be a pure function of the tree
at `merge_base_sha`.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

#: Relative, never absolute: the `_meta` block must not leak a path.
GENERATOR = "tests/tools/record_legacy_bundles.py"
DEFAULT_OUT = "tests/data/legacy_role_bundles.json"

#: The **F5 merge base**, where `LEGACY_ROLE_PERMISSIONS` still exists. The
#: recording describes that tree, so the recipe below re-derives it from that
#: tree and not from the branch.
MERGE_BASE_SHA = "a016365763137603b059c72d2c29bb4a1ebf54f9"

#: The rename this slice performs, applied **by the recorder** so the file is
#: reproducible from the merge base (APRAS-49 §2.1).
#:
#: At `MERGE_BASE_SHA` the catalogue still spells the four strings
#: `user_types:*`; every consumer of this file compares against the *live*
#: catalogue, which spells them `roles:*`. Encoding the substitution here is
#: what lets the `regenerate` command below produce a byte-identical file
#: rather than one that differs by four strings and cannot be checked.
RENAMED_BY_F5: dict[str, str] = {
    "user_types:read": "roles:read",
    "user_types:create": "roles:create",
    "user_types:update": "roles:update",
    "user_types:delete": "roles:delete",
}

#: Copies the tool into the worktree first -- it does not exist at the merge
#: base -- exactly as `record_parity_baseline`'s recipe does.
REGENERATE = (
    "git worktree add /tmp/apras-legacy-bundles {sha} && "
    "cp -R backend/tests/tools /tmp/apras-legacy-bundles/backend/tests/ && "
    "(cd /tmp/apras-legacy-bundles/backend && "
    "POSTGRES_URL=sqlite:// SECRET_KEY=legacy-bundles "
    "uv run python -m tests.tools.record_legacy_bundles --out /tmp/regen.json)"
    " && diff /tmp/regen.json backend/tests/data/legacy_role_bundles.json"
)


def build() -> dict:
    """The recorded payload: `_meta` plus six sorted bundles."""
    # Imported here, not at module scope, so `--help` works on a tree where
    # the map has already been deleted (and fails loudly when it is used).
    from app.core.permissions import LEGACY_ROLE_PERMISSIONS  # noqa: PLC0415

    return {
        "_meta": {
            "generator": GENERATOR,
            "merge_base_sha": MERGE_BASE_SHA,
            "source": "app/core/permissions.py::LEGACY_ROLE_PERMISSIONS",
            "note": (
                "The last recording of the UserRole enum's meaning. "
                "LEGACY_ROLE_PERMISSIONS is deleted by IAM F5 (APRAS-49); "
                "this file is what survives it. Recorded on the post-rename "
                "catalogue, so the four `user_types:*` strings appear here "
                "under their `roles:*` names (APRAS-49 §2.1): the rename is a "
                "pure rename and the consumers of this file compare against "
                "the live catalogue. `RENAMED_BY_F5` in the generator applies "
                "that substitution, so the `regenerate` command below "
                "reproduces this file byte-for-byte from the merge base."
            ),
            "regenerate": REGENERATE.format(sha=MERGE_BASE_SHA),
        },
        "bundles": {
            role.value: sorted(
                RENAMED_BY_F5.get(permission, permission)
                for permission in permissions
            )
            for role, permissions in sorted(
                LEGACY_ROLE_PERMISSIONS.items(), key=lambda item: item[0].value
            )
        },
    }


def main(argv: list[str] | None = None) -> int:
    """Write the recording to `--out`."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=DEFAULT_OUT)
    args = parser.parse_args(argv)

    payload = build()
    Path(args.out).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(f"wrote {args.out}: {len(payload['bundles'])} bundles")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
