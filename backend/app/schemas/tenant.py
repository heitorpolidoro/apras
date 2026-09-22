"""Tenant schemas for Pydantic validation (APRAS-41)."""

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TenantBase(BaseModel):
    """Base tenant schema with common fields."""

    name: str = Field(..., min_length=1, max_length=120)


class TenantCreate(TenantBase):
    """Schema for creating a new tenant."""

    is_active: bool = True


class TenantUpdate(BaseModel):
    """Schema for updating an existing tenant. All fields are optional.

    There is no ``DELETE /api/v1/tenants/{id}``: every tenant-scoped foreign
    key is ``ondelete="RESTRICT"``, and deactivation (``is_active: false``)
    is the intended operation.
    """

    name: str | None = Field(None, min_length=1, max_length=120)
    is_active: bool | None = None


class TenantRead(TenantBase):
    """Schema for reading tenant data.

    ``slug`` is here as well as on :class:`TenantProfileRead` (APRAS-66 D-D):
    this is the body of ``POST``/``PATCH``/``GET {id}`` on ``/tenants``, which
    APRAS-67 reads back after creating a condominium to learn the address the
    system derived for it.
    """

    id: UUID
    slug: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SimpleBrandTheme(BaseModel):
    """Two colours; everything else, including ``.dark``, is derived (D-A).

    The hex values carry **no** ``pattern`` here, for the reason
    :class:`TenantProfileUpdate`'s ``slug`` carries none: the rule is expressed
    once, in ``app.core.branding``, which also binds the values read back out
    of the column, so the two cannot disagree. A malformed value therefore
    reaches ``TenantService`` and comes back as ``InvalidBrandThemeError`` --
    still a 422, but from the single judge, and case-insensitively (``#FFE680``
    is accepted and stored lowercase).
    """

    mode: Literal["simple"]
    primary: str
    accent: str

    model_config = ConfigDict(extra="forbid")


class AdvancedBrandTheme(BaseModel):
    """The whole palette, authored (D-A).

    ``dark`` is optional: ``null`` -- the default the UI offers -- means the
    dark scheme is produced by the simple-mode derivation of the authored
    ``primary`` and ``accent``, because no per-variable inversion of a
    hand-authored light palette can preserve either the tenant's intent or its
    contrast. The **13-key** rule lives in ``app.core.branding`` with the hex
    rule, so ``dict[str, str]`` here is shape and not vocabulary.
    """

    mode: Literal["advanced"]
    light: dict[str, str]
    dark: dict[str, str] | None = None

    model_config = ConfigDict(extra="forbid")


#: Discriminated on ``mode``: an unknown mode is refused before the union is
#: even tried, and the two shapes can never be confused for one another.
BrandTheme = Annotated[
    SimpleBrandTheme | AdvancedBrandTheme, Field(discriminator="mode")
]


class TenantProfileRead(BaseModel):
    """The acting condominium's own profile (APRAS-61).

    Deliberately **not** ``TenantRead``: the profile screen shows what an
    administrator of one condominium may see and change about it, and the
    timestamps are operator data. ``logo_url`` is what the surface exists for.

    ``brand_theme`` is what the tenant chose, normalised; ``theme`` is what
    ``app.core.branding.build_theme`` derives from it (APRAS-68) -- 17 CSS
    custom properties per scheme, **derived on read and never stored**, so a
    change to the derivation reaches every tenant without a data migration.
    Both are ``null`` for a condominium with no colours, and the client then
    injects no element at all.
    """

    id: UUID
    name: str
    #: The condominium's address, the ``<slug>`` of ``/c/<slug>`` (APRAS-66).
    slug: str
    is_active: bool
    logo_url: str | None = None
    brand_theme: BrandTheme | None = None
    theme: dict[str, dict[str, str]] | None = None

    model_config = ConfigDict(from_attributes=True)


class TenantProfileUpdate(BaseModel):
    """The writable half of the profile: the name, and only the name.

    ``is_active`` is absent on purpose (APRAS-61): deactivating a condominium
    stays a superuser act on ``PATCH /api/v1/tenants/{tenant_id}``. The bounds
    are ``TenantUpdate``'s, not a second opinion about them.

    ``slug`` (APRAS-66 D-C) carries **no** ``pattern`` and no length bound
    here on purpose: the 3-64 rule is expressed once, in
    ``app.core.slug.is_valid_slug``, which also binds generated slugs, so the
    two cannot disagree. A malformed value therefore reaches
    ``TenantService`` and comes back as ``InvalidSlugError`` -- still a 422,
    but from the single judge. The field being **absent** is what leaves the
    slug untouched: a rename alone never regenerates it (D-C.2).

    ``brand_theme`` (APRAS-68) follows the same shape in the other direction:
    **absent** leaves the colours alone, and an explicit ``null`` clears them,
    which is what the screen's "voltar ao padrão" sends.
    """

    name: str | None = Field(None, min_length=1, max_length=120)
    slug: str | None = None
    brand_theme: BrandTheme | None = None


class ModuleStateRead(BaseModel):
    """One module's state in one tenant (APRAS-39 §6.1)."""

    module: str  # "finance"
    is_core: bool  # in CORE_MODULES: cannot be disabled
    is_active: bool  # not in tenant.disabled_modules


class TenantModulesRead(BaseModel):
    """Every module and its state in one tenant, sorted by ``module``.

    Storage is negative (``tenant.disabled_modules``, ``[]`` = everything on)
    but the read is positive: the *active* set is enumerable per tenant,
    which is what ER-1 asks for. The same body answers ``GET`` and ``PUT``,
    so the client re-renders from the server's answer rather than from an
    optimistic guess.
    """

    tenant_id: UUID
    modules: list[ModuleStateRead]  # all 26, sorted by `module`


class TenantModulesUpdate(BaseModel):
    """The complete desired state, declaratively (``PUT``, not ``PATCH``).

    This schema validates *shape* -- a list of strings. Vocabulary
    (catalogue membership, core-ness) is validated in
    ``TenantService.set_modules``, where the catalogue lives and where a
    rejection can be a 400 rather than FastAPI's 422 (§6.3).
    """

    disabled_modules: list[str]


class TenantMemberCreate(BaseModel):
    """Schema for linking an existing user to a tenant.

    ``is_tenant_admin`` is optional so a link and a grant can be one call
    (APRAS-43); it defaults to ``False``, i.e. a plain member.
    """

    user_id: UUID
    is_tenant_admin: bool = False


class TenantMemberUpdate(BaseModel):
    """Schema for granting/revoking the tenant_admin capability (APRAS-43).

    Exactly one field, on purpose: this route grants a capability and must
    never become a general membership editor.
    """

    is_tenant_admin: bool


class TenantMemberRead(BaseModel):
    """Schema for reading one membership, flattened with the user's details."""

    user_id: UUID
    email: str
    full_name: str
    # The user's role **names** in the acting tenant, sorted (IAM F5,
    # APRAS-49 §8.2). One shape for all three summary schemas, one i18n
    # treatment (join with ", "), no new nested model.
    roles: list[str] = []
    linked_at: datetime
    is_tenant_admin: bool

    model_config = ConfigDict(from_attributes=True)


class TenantMembershipSummary(BaseModel):
    """One membership of the *calling* user, for ``GET /api/v1/auth/me``.

    Distinct from :class:`TenantMemberRead`, which describes *another* user's
    membership of a named tenant and carries their email/roles, and from
    :class:`TenantRead`, which describes the tenant entity and must stay
    caller-independent (it is also the response of ``POST``/``PATCH``/
    ``GET {id}``, where a caller-relative field would be a category error).
    """

    tenant_id: UUID
    name: str
    is_active: bool
    is_tenant_admin: bool
