"""Create this app's database if the server we point at does not have it yet.

Idempotent. A no-op in standalone mode, where the bundled Postgres creates the
database from POSTGRES_DB on first init -- it matters when POSTGRES_URL points at
a server this repo does not own (poli-runner's shared Postgres), which has never
heard of `apras`.

Creating a database cannot be done from a connection to that database, so this
connects to the always-present `postgres` maintenance database on the same server.
Run as `python -m app.ensure_db`.
"""

from urllib.parse import urlparse, urlunparse

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

from app.core.config import settings


def ensure_database() -> None:
    url = urlparse(settings.database_url)
    name = url.path.lstrip("/")
    if not name:
        raise SystemExit("POSTGRES_URL has no database name")

    admin = urlunparse(url._replace(path="/postgres"))
    conn = psycopg2.connect(admin)
    try:
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (name,))
            if cur.fetchone():
                print(f"database {name!r} already exists")
                return
            # Identifiers cannot be parameterised; the name comes from our own
            # POSTGRES_URL, and quoting it blocks the obvious injection anyway.
            cur.execute(f'CREATE DATABASE "{name}"')
            print(f"created database {name!r}")
    finally:
        conn.close()


if __name__ == "__main__":
    ensure_database()
