"""Importing ``app.main`` must survive a filesystem where ``static/uploads``
cannot be created.

Vercel functions run on a read-only filesystem. Until 2026-09-07 ``app.main``
called ``Path("static/uploads").mkdir(...)`` at import time, which raised
``OSError`` there and took every route down (``FUNCTION_INVOCATION_FAILED`` on
``/health`` and on CORS preflights alike). The directory used to be tracked in
git, which masked the call until ``1709a42`` git-ignored it.

The failure is reproduced here without a read-only mount: a regular *file*
named ``static`` makes ``mkdir(parents=True)`` raise ``OSError``
(``FileExistsError`` / ``NotADirectoryError`` are subclasses). The import runs
in a subprocess so the module-level code executes fresh, from that cwd.
"""

import os
import subprocess
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent


def _import_app_main_from(cwd: Path) -> subprocess.CompletedProcess[str]:
    # ``Settings`` reads ``.env`` from the cwd; the subprocess runs elsewhere,
    # so the two required settings are supplied explicitly. The engine is
    # created lazily, so the URL is never connected to.
    env = {**os.environ, "PYTHONPATH": str(BACKEND_ROOT)}
    env.setdefault("SECRET_KEY", "test-secret")
    env.setdefault("POSTGRES_URL", "postgresql://apras:apras@127.0.0.1:1/never")
    return subprocess.run(
        [
            sys.executable,
            "-c",
            "import app.main as m; print('mounted' if any(getattr(r, 'name', None) == 'uploads' for r in m.app.routes) else 'unmounted')",
        ],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def test_import_survives_an_uncreatable_uploads_dir(tmp_path: Path) -> None:
    (tmp_path / "static").write_text("not a directory")

    result = _import_app_main_from(tmp_path)

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "unmounted"


def test_uploads_are_mounted_when_the_dir_is_creatable(tmp_path: Path) -> None:
    result = _import_app_main_from(tmp_path)

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "mounted"
    assert (tmp_path / "static" / "uploads").is_dir()
