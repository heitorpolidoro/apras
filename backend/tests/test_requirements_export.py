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

So the rule below is parity, in both directions, against the lock -- the one
artifact the suite actually exercises. It is deliberately not "the export
parses" or "the export mentions sqlmodel": the only property worth asserting
is that the file Vercel installs resolves to the versions the tests ran on.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
REQUIREMENTS = BACKEND / "requirements.txt"
UV_LOCK = BACKEND / "uv.lock"

#: A pinned requirement line, e.g. ``sqlmodel==0.0.47`` or
#: ``colorama==0.4.6 ; sys_platform == 'win32'``. The export emits exact pins
#: only, so anything looser is itself a finding.
PIN = re.compile(r"^(?P<name>[A-Za-z0-9._-]+)==(?P<version>[^\s;]+)")

#: Export and lock normalise distribution names differently in principle
#: (``Mako`` vs ``mako``); compare on the normalised form, per PEP 503.
_NON_ALNUM_RUN = re.compile(r"[-_.]+")


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
        "never hand-edited:\n"
        "  cd backend && uv export --format requirements-txt --no-hashes "
        "-o requirements.txt\n" + "\n".join(mismatched)
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
