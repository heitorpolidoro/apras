import { describe, it, expect } from "vitest";
// Vite's `?raw` import, so the assertion is about the file the bundler ships
// and needs no Node builtins under the app's `tsconfig` (types: vite/client).
import APP_SOURCE from "../../../App.tsx?raw";
import { AUTHENTICATED_ONLY_PATHS, NAV_ITEMS, ROUTE_ACCESS,  } from "../access/routeAccess";

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

  it("only /dashboard and /categories carry landingRedirect, and nothing carries legacyMenu", () => {
    const withLegacyMenu = Object.entries(ROUTE_ACCESS)
      .filter(([, rule]) => "legacyMenu" in rule)
      .map(([path]) => path)
      .sort();
    const withLanding = Object.entries(ROUTE_ACCESS)
      .filter(([, rule]) => "landingRedirect" in rule && rule.landingRedirect)
      .map(([path]) => path)
      .sort();

    // `legacyMenu` died with the `allowed_menus` gate (IAM F5, §4.1); its
    // sibling `landingRedirect` survives on exactly the same two routes,
    // because landing is a preference rather than authorization (§10.4).
    expect(withLegacyMenu).toEqual([]);
    expect(withLanding).toEqual(["/categories", "/dashboard"]);
  });

  it("the two role routes share one rule shape", () => {
    expect(ROUTE_ACCESS["/admin/roles"]).toEqual(
      ROUTE_ACCESS["/admin/roles/:roleId"],
    );
  });
});
