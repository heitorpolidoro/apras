"""FastAPI application entry point."""

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.exception_handlers import domain_exception_handler
from app.core.exceptions import DomainError
from app.core.limiter import limiter
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded


def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:  # noqa: ARG001
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
        import json

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
    allow_origin_regex=r"https://(nexdom|apras)-(front|app)-.*\.vercel\.app|https://(nexdom|apras)-app\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/")
def read_root() -> dict[str, str]:
    """Root endpoint."""
    return {"message": "Welcome to APRAS API"}
