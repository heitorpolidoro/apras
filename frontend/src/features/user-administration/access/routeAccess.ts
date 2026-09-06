import type { AccessRule } from "../../../types/permissions";

/**
 * The single place a route's rule is written (APRAS-48 §5.2).
 *
 * `ProtectedRoute` reads it through `useCanAccess` (the **real**, never
 * simulated, permission set) and `Navbar` reads the *same object* through
 * `useCanShowMenu` (the effective, simulated one). A menu and its route can
 * therefore disagree only during an active simulation, and only in the
 * generous direction — see §2.7.
 *
 * `{ module }` is the ordinary rule. `{ anyOf }` appears exactly where a
 * module rule would be wrong, and each occurrence says why.
 */
export const ROUTE_ACCESS: Record<string, AccessRule> = {
  // `landingRedirect` marks the two routes that honour the caller's
  // `landing_path` (IAM F5, APRAS-49 §10.4). Landing is not authorization —
  // a PORTEIRO genuinely holds `tasks:read`, so no permission predicate can
  // express "pin the gatekeeper to the gate" — which is why it is a
  // preference stored on the role row rather than a rule. Its sibling
  // `legacyMenu` died with the menu gate it read (§4.1).
  "/dashboard": { module: "tasks", landingRedirect: true },
  "/categories": { module: "categories", landingRedirect: true },
  "/lots": { module: "lots" },
  // A module rule would add PORTEIRO through `authorizations:gate_lookup`,
  // which is the gatehouse lookup, not the resident-facing screen.
  "/authorizations": { anyOf: ["authorizations:read"] },
  // A module rule would add GUEST/RESIDENT through `gate:logs_read`.
  "/gate": { anyOf: ["gate:checkin"] },
  "/occurrences": { module: "occurrences" },
  "/feedback": { module: "feedback" },
  "/documents": { module: "documents" },
  "/projects": { module: "projects" },
  "/announcements": { module: "announcements" },
  "/finance": { module: "finance" },
  "/packages": { module: "packages" },
  "/reservations": { module: "reservations" },
  // A module rule would be ALL_ROLES: `spaces:read` is held by every legacy
  // role, so it would gate nothing. This screen is the space *administration*.
  "/spaces": {
    anyOf: ["spaces:create", "spaces:update", "spaces:deactivate"],
  },
  "/voting": { module: "votes" },
  "/assets": { module: "assets" },
  "/purchases": { module: "purchases" },
  // `access_control` backs two screens: the read-only monitor and the device
  // administration. One module rule cannot separate them.
  "/gate-monitor": { anyOf: ["access_control:events_read"] },
  "/admin/access-control": { anyOf: ["access_control:device_create"] },
  "/admin/photo-approvals": { anyOf: ["uploads:pending_read"] },
  "/admin/users": { anyOf: ["users:update"] },
  "/users/contact-info": { anyOf: ["users:update_contact"] },
  "/admin/roles": {
    anyOf: ["roles:create", "roles:update", "roles:delete"],
  },
  "/admin/roles/:roleId": {
    anyOf: ["roles:create", "roles:update", "roles:delete"],
  },
  // APRAS-39 §10.3: the per-tenant module switch. The first frontend surface
  // for a superuser-only *backend* route, and by §6.4's convention such
  // routes carry no catalogue permission — so `{ superuser: true }` is the
  // only rule that can express it. `{ anyOf: ["tenants:update"] }` would
  // offer the menu to an acting tenant_admin, whom the API answers 403.
  "/admin/modules": { superuser: true },
  // APRAS-40 §8.3: the tenant-side subscription area. An ordinary `{ module }`
  // rule, and it works because `billing` is a **core** module: APRAS-39's
  // strip never removes `billing:*`, so the rule holds for any `billing:*` a
  // role carries. A manage-only holder therefore reaches the page and the read
  // endpoint is what refuses them — the documented degenerate configuration
  // (§2.2), stated rather than special-cased.
  "/subscription": { module: "billing" },
  // The two commercial operator screens. `{ superuser: true }` for
  // `/admin/modules`' reason: these routes are superuser-guarded and carry no
  // catalogue permission, so no `{ anyOf }` rule can express them, and
  // `{ anyOf: ["tenants:update"] }` is specifically wrong — a tenant_admin
  // holds it through the whole-catalogue short-circuit and the API answers 403.
  "/admin/plans": { superuser: true },
  "/admin/subscriptions": { superuser: true },
  // APRAS-44 §10.2. `{ module: "infractions" }` is specifically **wrong** for
  // `/infractions`: a module rule means "holds any `infractions:*`", so a
  // resident holding only `my_lots_read` would be offered the management list
  // the API answers 403 for. `anyOf` is the shape used on `/gate` and
  // `/spaces` for exactly this situation.
  "/infractions": { anyOf: ["infractions:read"] },
  "/infraction-rules": {
    anyOf: [
      "infractions:rule_create",
      "infractions:rule_update",
      "infractions:rule_deactivate",
    ],
  },
  "/my-infractions": { anyOf: ["infractions:my_lots_read"] },
};

/**
 * The protected paths that deliberately carry no rule: being authenticated is
 * the whole gate. `/welcome` is the GUEST landing page, so gating it on a
 * permission a GUEST does not hold would be a redirect loop.
 */
export const AUTHENTICATED_ONLY_PATHS: readonly string[] = ["/welcome"];

export interface NavItem {
  path: string;
  labelKey: string;
  access: AccessRule;
}

/**
 * The navigation bar, in display order. Every entry's `access` **is** the
 * `ROUTE_ACCESS` entry of its `path` (asserted by `routeAccess.test.ts`), so a
 * menu can never outlive or contradict its route's rule.
 */
export const NAV_ITEMS: readonly NavItem[] = [
  { path: "/dashboard", labelKey: "nav.tasks" },
  { path: "/categories", labelKey: "nav.categories" },
  { path: "/lots", labelKey: "nav.lots" },
  { path: "/authorizations", labelKey: "nav.authorizations" },
  { path: "/gate", labelKey: "nav.gate" },
  { path: "/occurrences", labelKey: "nav.occurrences" },
  { path: "/packages", labelKey: "nav.packages" },
  { path: "/voting", labelKey: "nav.voting" },
  { path: "/feedback", labelKey: "nav.feedback" },
  { path: "/reservations", labelKey: "nav.reservations" },
  { path: "/spaces", labelKey: "nav.manageSpaces" },
  { path: "/documents", labelKey: "nav.documents" },
  { path: "/projects", labelKey: "projects.navItem" },
  { path: "/announcements", labelKey: "nav.announcements" },
  { path: "/finance", labelKey: "nav.finance" },
  { path: "/assets", labelKey: "nav.assets" },
  { path: "/purchases", labelKey: "nav.purchases" },
  { path: "/users/contact-info", labelKey: "nav.contactInfo" },
  { path: "/admin/users", labelKey: "nav.administration" },
  { path: "/admin/roles", labelKey: "nav.roles" },
  { path: "/admin/photo-approvals", labelKey: "nav.photoApprovals" },
  { path: "/admin/access-control", labelKey: "nav.accessControl" },
  { path: "/gate-monitor", labelKey: "nav.gateMonitor" },
  { path: "/admin/modules", labelKey: "nav.modules" },
  { path: "/subscription", labelKey: "nav.subscription" },
  { path: "/admin/plans", labelKey: "nav.plans" },
  { path: "/admin/subscriptions", labelKey: "nav.tenantSubscriptions" },
  { path: "/infractions", labelKey: "nav.infractions" },
  { path: "/infraction-rules", labelKey: "nav.infractionRules" },
  { path: "/my-infractions", labelKey: "nav.myInfractions" },
].map((item) => ({ ...item, access: ROUTE_ACCESS[item.path] }));
