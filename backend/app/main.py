"""FastAPI application entry point."""

import json
from pathlib import Path, PurePosixPath

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from starlette.responses import Response
from starlette.types import Scope

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.exception_handlers import domain_exception_handler
from app.core.exceptions import DomainError
from app.core.limiter import limiter
from app.core.uploads import INLINE_SAFE_EXTENSIONS


class HardenedStaticFiles(StaticFiles):
    """``StaticFiles`` that never lets a browser sniff, and can force a download.

    Two mounts differ in exactly one predicate, so this is one class with one
    flag rather than two:

    * ``/static/uploads`` holds **client-supplied** bytes, some of which were
      written before APRAS-65 with an extension the client chose. It is mounted
      with ``force_download=True``: anything outside
      :data:`~app.core.uploads.INLINE_SAFE_EXTENSIONS` is served as
      ``application/octet-stream`` with ``Content-Disposition: attachment``, so
      a planted ``.svg`` or ``.html`` downloads instead of executing in this
      origin.
    * ``/static/generated`` holds output this application rendered itself and
      is mounted with ``force_download=False``, so an assembly minute renders
      in the tab the Document Center opens.

    ``X-Content-Type-Options: nosniff`` is correct for both and is added to
    every response: without it a browser may sniff HTML out of bytes we
    labelled ``application/octet-stream`` and undo the flag above.

    The suffix consulted here is the one **already on disk**. That is not the
    bug APRAS-65 fixes in ``save_file`` -- it is the mitigation for files that
    predate the fix, where the on-disk suffix is all there is to go on.
    """

    def __init__(self, *args, force_download: bool = False, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.force_download = force_download

    async def get_response(self, path: str, scope: Scope) -> Response:
        response = await super().get_response(path, scope)
        response.headers["X-Content-Type-Options"] = "nosniff"
        if self.force_download and not self._is_inline_safe(path):
            response.headers["Content-Type"] = "application/octet-stream"
            response.headers["Content-Disposition"] = "attachment"
        return response

    @staticmethod
    def _is_inline_safe(path: str) -> bool:
        return PurePosixPath(path).suffix.lower() in INLINE_SAFE_EXTENSIONS


def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:  # noqa: ARG001  # slowapi's handler signature is fixed; `request` is unused here
    """Handle rate limit exceeded errors."""
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={"error": "Rate limit exceeded", "detail": exc.detail},
    )


def get_origins() -> list[str]:
    """Parse and return CORS origins from settings."""
    raw_origins = settings.BACKEND_CORS_ORIGINS
    if not raw_origins:
        return []

    if isinstance(raw_origins, str):
        try:
            origins = json.loads(raw_origins)
        except json.JSONDecodeError:
            origins = [o.strip() for o in raw_origins.split(",")]
    else:
        origins = [str(o) for o in raw_origins]

    return origins


app = FastAPI(title=settings.PROJECT_NAME)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)
app.add_exception_handler(DomainError, domain_exception_handler)

# CORS Configuration
origins = get_origins()

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https://apras-(front|app)-.*\.vercel\.app|https://apras-app\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")

# Both trees are created in one block and both mounts stand or fall together:
# a filesystem that refuses one refuses the other, and a half-mounted pair
# would serve generated output from the tree that forces downloads.
static_dirs: tuple[Path, Path] | None = (
    Path("static/uploads"),
    Path("static/generated"),
)
try:
    for static_dir in static_dirs:
        static_dir.mkdir(parents=True, exist_ok=True)
except OSError:
    # Read-only filesystem (e.g. a Vercel function): the directories cannot be
    # created, and uploads are served from external storage there. Importing
    # must never fail on this — a crash here takes every route down.
    static_dirs = None
if static_dirs is not None:
    uploads_dir, generated_dir = static_dirs
    app.mount(
        "/static/uploads",
        HardenedStaticFiles(directory=str(uploads_dir), force_download=True),
        name="uploads",
    )
    app.mount(
        "/static/generated",
        HardenedStaticFiles(directory=str(generated_dir), force_download=False),
        name="generated",
    )


@app.get("/")
def read_root() -> dict[str, str]:
    """Root endpoint."""
    return {"message": "Welcome to APRAS API"}
