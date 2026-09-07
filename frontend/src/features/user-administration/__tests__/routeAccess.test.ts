import { describe, it, expect } from "vitest";
// Vite's `?raw` import, so the assertion is about the file the bundler ships
// and needs no Node builtins under the app's `tsconfig` (types: vite/client).
import APP_SOURCE from "../../../App.tsx?raw";
import {
  AUTHENTICATED_ONLY_PATHS,
  NAV_GROUPS,
  NAV_ITEMS,
  ROUTE_ACCESS,
} from "../access/routeAccess";

/**
 * The `<Route path="…">` entries of `App.tsx` whose element mounts a
 * `<ProtectedRoute>`. Read from the source so a route added without a rule is
 * a test failure rather than an unguarded page.
 */
const protectedPaths = (): string[] =>
  APP_SOURCE.split("<Route")
    .slice(1)
    // Each chunk runs from one `<Route` to the next, so it holds exactly that
    // route's `path` and its element. `App.tsx` nests no `<Route>`.
    .filter((chunk: string) => chunk.includes("<ProtectedRoute"))
    .map((chunk: string) => /^\s+path="([^"]+)"/.exec(chunk)?.[1])
    .filter((path): path is string => Boolean(path));

describe("ROUTE_ACCESS / NAV_ITEMS", () => {
  it("every NAV_ITEMS entry reuses the ROUTE_ACCESS rule of its path", () => {
    for (const item of NAV_ITEMS) {
      expect(ROUTE_ACCESS[item.path]).toBeDefined();
      // Identity, not equality: one object, so a menu and its route can never
      // drift apart (§5.2).
      expect(item.access).toBe(ROUTE_ACCESS[item.path]);
    }
  });

  it("every protected path in App.tsx has a ROUTE_ACCESS entry", () => {
    const paths = protectedPaths();
    expect(paths.length).toBeGreaterThan(20);
    const unruled = paths.filter(
      (path) =>
        !ROUTE_ACCESS[path] && !AUTHENTICATED_ONLY_PATHS.includes(path),
    );
    expect(unruled).toEqual([]);
  });

  it("only /categories, /dashboard, and /tasks carry landingRedirect, and nothing carries legacyMenu", () => {
    const withLegacyMenu = Object.entries(ROUTE_ACCESS)
      .filter(([, rule]) => "legacyMenu" in rule)
      .map(([path]) => path)
      .sort();
    const withLanding = Object.entries(ROUTE_ACCESS)
      .filter(([, rule]) => "landingRedirect" in rule && rule.landingRedirect)
      .map(([path]) => path)
      .sort();

    // `legacyMenu` died with the `allowed_menus` gate (IAM F5, §4.1); its
    // sibling `landingRedirect` survives on exactly the landing-honouring routes,
    // because landing is a preference rather than authorization (§10.4).
    expect(withLegacyMenu).toEqual([]);
    expect(withLanding).toEqual(["/categories", "/dashboard", "/tasks"]);
  });

  it("the two role routes share one rule shape", () => {
    expect(ROUTE_ACCESS["/admin/roles"]).toEqual(
      ROUTE_ACCESS["/admin/roles/:roleId"],
    );
  });

  it("the three APRAS-40 routes carry the rules §8.3 declares", () => {
    // `/subscription` is an ordinary `{ module }` rule, and it works only
    // because `billing` is a **core** module: APRAS-39's strip never removes
    // `billing:*`, so a role that carries either string reaches the page.
    expect(ROUTE_ACCESS["/subscription"]).toEqual({ module: "billing" });
    // The two operator screens are superuser-guarded and carry no catalogue
    // permission, so no `{ anyOf }` rule can express them.
    // `{ anyOf: ["tenants:update"] }` is specifically wrong: a tenant_admin
    // holds it through the whole-catalogue short-circuit and the API answers
    // 403.
    expect(ROUTE_ACCESS["/admin/plans"]).toEqual({ superuser: true });
    expect(ROUTE_ACCESS["/admin/subscriptions"]).toEqual({ superuser: true });

    const paths = NAV_ITEMS.map((item) => item.path);
    expect(paths).toContain("/subscription");
    expect(paths).toContain("/admin/plans");
    expect(paths).toContain("/admin/subscriptions");
  });

  it("NAV_GROUPS covers all 30 NAV_ITEMS with zero omissions and zero duplicates", () => {
    expect(NAV_GROUPS).toHaveLength(7);
    const navItemPaths = NAV_ITEMS.map((item) => item.path);
    expect(navItemPaths).toHaveLength(30);

    const allGroupPaths = NAV_GROUPS.flatMap((group) => group.itemPaths);
    expect(allGroupPaths).toHaveLength(30);

    // No duplicates within all groups combined
    const uniqueGroupPaths = new Set(allGroupPaths);
    expect(uniqueGroupPaths.size).toBe(30);

    // Exact match of paths between NAV_GROUPS and NAV_ITEMS
    expect([...allGroupPaths].sort()).toEqual([...navItemPaths].sort());
  });
});
