from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from pydantic_settings import BaseSettings, SettingsConfigDict

_PSYCOPG2_VALID_PARAMS = frozenset(
    {
        "sslmode",
        "sslcert",
        "sslkey",
        "sslrootcert",
        "sslcrl",
        "application_name",
        "connect_timeout",
        "options",
        "keepalives",
        "keepalives_idle",
        "keepalives_interval",
        "keepalives_count",
    }
)


def _clean_db_url(url: str) -> str:
    if not url.startswith(("postgres://", "postgresql://")):
        return url
    parsed = urlparse(url.replace("postgres://", "postgresql://", 1))
    kept = {
        k: v[0]
        for k, v in parse_qs(parsed.query).items()
        if k in _PSYCOPG2_VALID_PARAMS
    }
    return urlunparse(parsed._replace(query=urlencode(kept)))


class Settings(BaseSettings):
    PROJECT_NAME: str = "APRAS"
    ENVIRONMENT: str = "production"

    # Database
    POSTGRES_URL: str
    POSTGRES_URL_NON_POOLING: str | None = None
    SQL_ECHO: bool = False

    @property
    def database_url(self) -> str:
        return _clean_db_url(self.POSTGRES_URL)

    @property
    def migration_database_url(self) -> str:
        return _clean_db_url(self.POSTGRES_URL_NON_POOLING or self.POSTGRES_URL)

    # Security
    SECRET_KEY: str
    SECRET_KEYS: list[str] = []
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    # How long an administrator invitation stays usable (APRAS-71 D2).
    # Seven days, env-overridable: deliberately not the 15 minutes of
    # `security.create_password_reset_token`, because the invitee has to
    # receive mail and pick a moment to sit down with it.
    INVITATION_EXPIRE_HOURS: int = 168

    # CORS
    BACKEND_CORS_ORIGINS: list[str] = [
        "https://apras.vercel.app",
        "https://apras-front.vercel.app",
        "https://apras-app.vercel.app",
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:5173",
        "http://localhost:5175",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5175",
    ]

    # Storage (APRAS-94). Vercel's own variable name: linking a Blob store to
    # the project injects `BLOB_READ_WRITE_TOKEN`, so production needs no extra
    # configuration step. Absent -- local development, CI, the test suite --
    # every upload keeps going to local disk exactly as before.
    BLOB_READ_WRITE_TOKEN: str | None = None

    # Where this API answers from, seen from a browser (APRAS-105 §D). The
    # obras report is rendered here and displayed inside an `<iframe srcDoc>`
    # on the *frontend's* origin, so every URL the report emits has to be
    # absolute: a relative one resolves against the parent document and
    # silently loads nothing.
    #
    # Three settings, read by `app.core.urls.public_api_base_url` in the order
    # below -- they are its first three rungs, and a local `http://localhost:8000`
    # is the fourth. All three are declared here rather than read from `os.environ`,
    # because `model_config` below sets `case_sensitive=True`: pydantic then
    # reads the two variables Vercel injects under their exact names with no
    # extra code, and every rung stays overridable in a test by the same
    # mechanism the rest of the suite already uses.
    #
    # `PUBLIC_API_BASE_URL` is the explicit override, for a backend served
    # from a domain of our own.
    PUBLIC_API_BASE_URL: str = ""
    # Injected by Vercel: the project's production domain, stable across
    # deployments. This is what makes production correct with no new
    # environment variable for anybody to forget.
    VERCEL_PROJECT_PRODUCTION_URL: str = ""
    # Injected by Vercel: *this* deployment's domain, so a preview names
    # itself. Neither carries a scheme, hence the `https://` the builder adds.
    VERCEL_URL: str = ""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)


settings = Settings()
