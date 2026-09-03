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
  /** The first non-null `landing_path` among my roles in this tenant,
   *  ordered by role name, or null (IAM F5, APRAS-49 §10.4). It follows the
   *  **effective** (simulation-aware) identity because landing is a
   *  preference; route *access* stays on the real set. */
  landing_path?: string | null;
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
 * `landingRedirect` marks the two routes that honour the caller's
 * `landing_path` (IAM F5, APRAS-49 §10.4). It is typed `never` on the
 * `{ anyOf }` arm so a third one cannot be added by accident. F5 deleted its
 * sibling `legacyMenu` together with the menu gate it read (§4.1).
 */
export type AccessRule =
  | { module: string; landingRedirect?: boolean }
  | {
      anyOf: readonly PermissionKey[];
      landingRedirect?: never;
    };
