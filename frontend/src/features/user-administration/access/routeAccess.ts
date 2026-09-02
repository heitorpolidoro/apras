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
  // TRANSITIONAL (IAM F4 -> F5): `legacyMenu` is the one place the frontend
  // still consults `allowed_menus`, because `deps.assert_menu_access` is
  // still enforced on 12 handlers (8 in tasks.py, 4 in categories.py). Making
  // these two purely permission-derived would show a door the backend does
  // not open. `landingRedirect` is the GUEST -> /welcome and
  // PORTEIRO -> /gate landing rule, which is not authorization: a PORTEIRO
  // genuinely holds `tasks:read`, so no permission predicate can express
  // "pin the gatekeeper to the gate". Both fields die with F5 (§11).
  "/dashboard": { module: "tasks", legacyMenu: "tasks", landingRedirect: true },
  "/categories": {
    module: "categories",
    legacyMenu: "categories",
    landingRedirect: true,
  },
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
  "/admin/groups": {
    anyOf: ["user_types:create", "user_types:update", "user_types:delete"],
  },
  "/admin/groups/:groupId": {
    anyOf: ["user_types:create", "user_types:update", "user_types:delete"],
  },
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
  { path: "/admin/groups", labelKey: "nav.groups" },
  { path: "/admin/photo-approvals", labelKey: "nav.photoApprovals" },
  { path: "/admin/access-control", labelKey: "nav.accessControl" },
  { path: "/gate-monitor", labelKey: "nav.gateMonitor" },
].map((item) => ({ ...item, access: ROUTE_ACCESS[item.path] }));
