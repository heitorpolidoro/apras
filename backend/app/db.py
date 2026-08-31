from sqlmodel import Session, create_engine

from app.core.config import settings

# Importing the tenant context registers the session-level read filter and
# write stamp (APRAS-42). It is imported here so the listeners exist for
# anything that can obtain a session, including `app/seed.py` and Alembic —
# both of which build plain `Session(engine)` objects and are therefore
# deliberately unaffected by them.
from app.core.tenant_context import REQUEST_SCOPED_KEY

engine = create_engine(settings.database_url, echo=getattr(settings, "SQL_ECHO", False))


def get_session():
    """
    Generator for database sessions.

    The session is marked *request scoped*, which arms the fail-closed guard
    in `app.core.tenant_context`: querying a tenant-scoped model on it before
    an acting tenant (or an explicit global scope) has been resolved raises
    instead of returning every tenant's rows.

    Yields:
        Session: A SQLModel session.
    """
    with Session(engine) as session:
        session.info[REQUEST_SCOPED_KEY] = True
        yield session
