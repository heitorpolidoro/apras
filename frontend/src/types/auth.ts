export interface Role {
  id: string;
  name: string;
  /** The role's permission bundle (IAM F2 put it on `RoleRead`).
   *  Optional so every pre-existing `Role` fixture keeps type-checking. */
  permissions?: string[];
}

/** One membership of the *calling* user, as returned by `GET /auth/me`. */
export interface TenantMembership {
  tenant_id: string;
  name: string;
  is_active: boolean;
  /** The APRAS-43 capability, scoped to this membership only. */
  is_tenant_admin: boolean;
}

/** A tenant the caller may act in, as returned by `GET /tenants`. */
export interface Tenant {
  id: string;
  name: string;
  /** The condominium's address, derived from the name by the backend
   *  (APRAS-66). Non-optional: every `TenantRead` body carries it. */
  slug: string;
  is_active: boolean;
  /** ISO-8601, as `TenantRead` serialises it (APRAS-41). Non-optional for the
   *  same reason as `slug`. `updated_at` is deliberately **not** declared —
   *  nothing renders it, and a field no screen reads is a field no fixture
   *  should have to invent. */
  created_at: string;
}

export interface User {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  roles?: Role[];
  role_ids?: string[] | null;
  cpf?: string;
  phone?: string;
  address?: string;
  /** The caller's own tenant memberships (`GET /auth/me` only, APRAS-38).
   *  Optional so every pre-existing `User` fixture keeps type-checking. */
  tenants?: TenantMembership[];
  /** The caller's **own** global flag (`GET /auth/me` only, IAM F5 §8.3).
   *  `UserRead` deliberately does not carry it, so `GET /users/` payloads
   *  never expose who the superusers are. The one consumer is
   *  `context/tenantState.ts`, which runs before an acting tenant exists and
   *  so cannot ask `/permissions/me`. */
  is_superuser?: boolean;
}
