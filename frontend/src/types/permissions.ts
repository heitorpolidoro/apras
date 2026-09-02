import type { MenuKey } from "../features/user-administration/context/useMenuAccess";

/** A `<module>:<action>` permission string, e.g. `"finance:read"`. */
export type PermissionKey = string;

/** One `GET /permissions/` row: pre-split by the backend (APRAS-48 §3.1). */
export interface PermissionDescriptor {
  permission: PermissionKey;
  module: string;
  action: string;
  superuser_only: boolean;
}

/** The `GET /permissions/me` payload: my effective set in the acting tenant. */
export interface MyPermissions {
  tenant_id: string;
  permissions: PermissionKey[];
}

/**
 * How a route or a menu decides. Exactly two shapes, deliberately.
 *
 * `{ module }` is the ordinary rule — *any* permission of the module, which
 * is what "gate the screen on the domain that backs it" means. `{ anyOf }` is
 * for the handful of places where one module backs two screens, or where the
 * module's `read` is held by every legacy role and would therefore gate
 * nothing (`routeAccess.ts` names each of them).
 *
 * `legacyMenu` and `landingRedirect` are **TRANSITIONAL (IAM F4 -> F5)** and
 * are only ever set on the two entries `routeAccess.ts` marks; they are typed
 * `never` on the `{ anyOf }` arm so a third one cannot be added by accident.
 */
export type AccessRule =
  | { module: string; legacyMenu?: MenuKey; landingRedirect?: boolean }
  | {
      anyOf: readonly PermissionKey[];
      legacyMenu?: never;
      landingRedirect?: never;
    };
