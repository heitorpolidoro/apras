export const UserRole = {
  ADMINISTRATOR: "ADMINISTRATOR",
  DIRECTOR: "DIRECTOR",
  MANAGER: "MANAGER",
  GUEST: "GUEST",
  RESIDENT: "RESIDENT",
  PORTEIRO: "PORTEIRO",
} as const;

export type UserRole = (typeof UserRole)[keyof typeof UserRole];

export interface UserType {
  id: string;
  name: string;
  allowed_menus: string[];
  /** Set only for the 5 role-linked types seeded by the APRAS-9 backend
   * migration; undefined/null for regular admin-created types. */
  role?: string | null;
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
  is_active: boolean;
}

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  user_types?: UserType[];
  user_type_ids?: string[] | null;
  cpf?: string;
  phone?: string;
  address?: string;
  /** The caller's own tenant memberships (`GET /auth/me` only, APRAS-38).
   *  Optional so every pre-existing `User` fixture keeps type-checking. */
  tenants?: TenantMembership[];
}
