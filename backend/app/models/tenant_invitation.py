"""The administrator invitation (APRAS-71 D1).

`tenant_invitation` is a **global** table, like `tenant`, `user`,
`user_tenant_link` and `plan`. It carries a `tenant_id`, but that column
names a tenant from **outside** the row -- the invitation is issued by a
superuser on a route with no acting tenant and consumed by an anonymous
caller -- so it is a reference and not a request-scoping key, exactly as on
`user_tenant_link`. `app.core.tenant_context` excludes both from its
discovery for that reason; were this table scoped, the two public routes
would read nothing at all.

**The raw token is never stored.** The column is `token_hash`, the SHA-256
hex of 32 random bytes. SHA-256 rather than bcrypt because the token is 256
bits of entropy -- not guessable, and needing an indexable exact-match
lookup, which bcrypt would turn into a table scan. Storing the raw value
would make any database dump an account takeover.

**There is no `status` column.** State is derived: `accepted_at IS NOT NULL`
is accepted, otherwise `expires_at <= db_now()` is expired, otherwise
pending. A stored third field can disagree with the two timestamps; the two
timestamps cannot disagree with themselves.
"""

from datetime import datetime
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel

from app.core import clock


class TenantInvitation(SQLModel, table=True):
    """One invitation for one address to administer one condominium.

    The invited person becomes the condominium's **administrator in the
    system** (`user_tenant_link.is_tenant_admin`): a system role, not one of
    the condominium's own elected offices, which this flow never grants.
    """

    __tablename__ = "tenant_invitation"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    #: ``RESTRICT``, like every other reference to a tenant: a condominium
    #: with invitations must not be deletable out from under them.
    tenant_id: UUID = Field(
        foreign_key="tenant.id", ondelete="RESTRICT", nullable=False, index=True
    )
    #: Stored ``.strip().lower()`` by ``InvitationService``, so the
    #: supersede lookup of D4 and the existing-account lookup of D8 compare
    #: the same spelling the user typed in either case.
    email: str = Field(index=True, nullable=False)
    #: 64 hex characters. Unique, because two invitations resolving to the
    #: same token would make "single use" ambiguous.
    token_hash: str = Field(max_length=64, unique=True, index=True, nullable=False)
    expires_at: datetime = Field(nullable=False)
    #: **The single-use marker**: NULL means not yet consumed.
    accepted_at: datetime | None = Field(default=None, nullable=True)
    #: ``SET NULL``: an invitation is a historical record and must outlive
    #: the account it created being removed.
    accepted_user_id: UUID | None = Field(
        default=None, foreign_key="user.id", ondelete="SET NULL", nullable=True
    )
    invited_by_user_id: UUID = Field(
        foreign_key="user.id", ondelete="RESTRICT", nullable=False
    )
    created_at: datetime = Field(default_factory=clock.db_now, nullable=False)
    updated_at: datetime = Field(default_factory=clock.db_now, nullable=False)
