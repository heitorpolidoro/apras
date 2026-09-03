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
  /** The acting tenant's turned-off modules, sorted (APRAS-39 §7).
   *
   *  Required, not optional: `MyPermissionsRead` defaults it to `[]`, so the
   *  backend always sends it and a `?? []` at every consumer would be
   *  defending against a payload that cannot occur.
   *
   *  `permissions` is **already** stripped by the backend, so gating never
   *  reads this — which is what keeps a superuser (unstripped by design)
   *  fully functional in a tenant that has modules off while still being
   *  *told* which ones are. Two consumers cannot derive it: the simulation
   *  arm of `useEffectivePermissionSet`, which builds its set from the role
   *  rows rather than from this payload, and the "module not enabled"
   *  variant of the restricted-access message. */
  disabled_modules: string[];
}

/** One module's state in one tenant (APRAS-39 §6.1). */
export interface ModuleState {
  module: string;
  /** In `CORE_MODULES`: identity, membership and the authorization
   *  vocabulary itself. The API refuses to disable these. */
  is_core: boolean;
  is_active: boolean;
}

/**
 * `GET`/`PUT /tenants/{id}/modules`. Storage is negative
 * (`tenant.disabled_modules`, `[]` = everything on) but the read is
 * positive, so the *active* set is enumerable per tenant.
 */
export interface TenantModules {
  tenant_id: string;
  /** All 26, sorted by `module`. */
  modules: ModuleState[];
}

/**
 * How a route or a menu decides. Three shapes, deliberately.
 *
 * `{ module }` is the ordinary rule — *any* permission of the module, which
 * is what "gate the screen on the domain that backs it" means. `{ anyOf }` is
 * for the handful of places where one module backs two screens, or where the
 * module's `read` is held by every legacy role and would therefore gate
 * nothing (`routeAccess.ts` names each of them).
 *
 * `{ superuser: true }` (APRAS-39 §10.1) is the smallest honest extension of
 * F4's "exactly two shapes": `/admin/modules` is the first frontend surface
 * for a **superuser-only backend route**, and by §6.4's convention such
 * routes carry no catalogue permission — so no `{ anyOf }` rule can express
 * it. `{ anyOf: ["tenants:update"] }` is specifically wrong: that string is
 * in `SUPERUSER_ONLY_PERMISSIONS`, but an acting tenant_admin still holds it
 * through the whole-catalogue short-circuit, so the rule would offer the menu
 * to a user the API answers 403.
 *
 * `landingRedirect` marks the two routes that honour the caller's
 * `landing_path` (IAM F5, APRAS-49 §10.4). It is typed `never` on the other
 * two arms so a third one cannot be added by accident. F5 deleted its
 * sibling `legacyMenu` together with the menu gate it read (§4.1).
 */
export type AccessRule =
  | { module: string; landingRedirect?: boolean; superuser?: never }
  | {
      anyOf: readonly PermissionKey[];
      landingRedirect?: never;
      superuser?: never;
    }
  | { superuser: true; landingRedirect?: never };
