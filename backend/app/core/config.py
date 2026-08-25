from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from pydantic_settings import BaseSettings, SettingsConfigDict

_PSYCOPG2_VALID_PARAMS = frozenset({
    "sslmode", "sslcert", "sslkey", "sslrootcert", "sslcrl",
    "application_name", "connect_timeout", "options",
    "keepalives", "keepalives_idle", "keepalives_interval", "keepalives_count",
})


def _clean_db_url(url: str) -> str:
    if not url.startswith(("postgres://", "postgresql://")):
        return url
    parsed = urlparse(url.replace("postgres://", "postgresql://", 1))
    kept = {k: v[0] for k, v in parse_qs(parsed.query).items() if k in _PSYCOPG2_VALID_PARAMS}
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

    # CORS
    BACKEND_CORS_ORIGINS: list[str] = [
        "https://nexdom.vercel.app",
        "https://nexdom-front.vercel.app",
        "https://nexdom-app.vercel.app",
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

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)


settings = Settings()
