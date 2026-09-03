import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { RootRedirect } from "../App";
import { useMyPermissions } from "../hooks/usePermissionQueries";
import * as AuthHook from "../features/user-administration/context/AuthContext";

/**
 * IAM F5 (APRAS-49 §10.4): the landings became **data**.
 *
 * `RootRedirect` was a three-way switch on the enum. F4 recorded these
 * redirects as role-shaped and un-expressible in permissions, and it was
 * right: a PORTEIRO holds `tasks:read` and `gate:checkin`, and so do A/D/M,
 * so no predicate over the catalogue separates "pin the gatekeeper to the
 * gate" from "the board can also open the gate". Landing is a *preference*,
 * not authorization — so it lives on the role row and arrives through
 * `GET /permissions/me`.
 *
 * The navigations asserted below are the ones this module always asserted;
 * only the fixture moved from a role value to a `landing_path`.
 */

vi.mock("../hooks/usePermissionQueries", () => ({
  useMyPermissions: vi.fn(),
}));

/**
 * `RootRedirect` reads the caller's real `is_superuser` since APRAS-39: the
 * fallback chain walks `NAV_ITEMS`, one of whose entries (`/admin/modules`)
 * is gated by `{ superuser: true }`. Everyone here is an ordinary user, so
 * that entry never wins and the pre-existing expectations are unchanged.
 */
const mockAuth = (isSuperuser = false) => {
  vi.spyOn(AuthHook, "useAuth").mockReturnValue({
    user: { id: "u-1", is_superuser: isSuperuser, roles: [] },
    isAuthenticated: true,
    isLoading: false,
    login: vi.fn(),
    logout: vi.fn(),
  } as never);
};

/**
 * Since APRAS-39 §10.4 the landing has to be *accessible*, not merely
 * requested — otherwise a tenant with `tasks` off would strand everyone on a
 * restricted `/dashboard`. So each fixture now carries the permission its
 * landing route's rule asks for. The claim these cases make is unchanged:
 * the backend picks, and the frontend honours whatever it picked.
 */
const withLanding = (landing_path: string | null, permissions: string[] = []) => {
  vi.mocked(useMyPermissions).mockReturnValue({
    data: {
      tenant_id: "00000000-0000-0000-0000-000000000001",
      permissions,
      landing_path,
      disabled_modules: [],
    },
    isPending: false,
    isError: false,
  } as never);
};

const renderRoot = () =>
  render(
    <MemoryRouter initialEntries={["/"]}>
      <Routes>
        <Route path="/" element={<RootRedirect />} />
        <Route path="/dashboard" element={<div>Dashboard Page</div>} />
        <Route path="/welcome" element={<div>Welcome Page</div>} />
        <Route path="/gate" element={<div>Gate Page</div>} />
      </Routes>
    </MemoryRouter>,
  );

describe("RootRedirect", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockAuth();
  });

  it("sends a caller whose landing_path is /welcome there", () => {
    withLanding("/welcome");

    renderRoot();

    expect(screen.getByText("Welcome Page")).toBeInTheDocument();
    expect(screen.queryByText("Dashboard Page")).toBeNull();
  });

  it("sends a caller whose landing_path is /gate there", () => {
    withLanding("/gate", ["gate:checkin"]);

    renderRoot();

    expect(screen.getByText("Gate Page")).toBeInTheDocument();
    expect(screen.queryByText("Dashboard Page")).toBeNull();
    expect(screen.queryByText("Welcome Page")).toBeNull();
  });

  it("sends everyone else to /dashboard (unchanged behaviour)", () => {
    withLanding(null, ["tasks:read"]);

    renderRoot();

    expect(screen.getByText("Dashboard Page")).toBeInTheDocument();
  });

  it("holds a spinner while the query is still settling", () => {
    // **Re-specified by APRAS-39** (code review round 1, finding 3). This
    // case used to assert `/dashboard` — a guess made before the permission
    // set existed. That guess is now a bug rather than a default: navigating
    // here unmounts `RootRedirect`, so the fallback chain would never run on
    // a cold load, which is the only path most users take. The component
    // holds the render instead, exactly as `ProtectedRoute` does.
    vi.mocked(useMyPermissions).mockReturnValue({
      data: undefined,
      isPending: true,
      isError: false,
    } as never);

    const { container } = renderRoot();

    expect(container.querySelector(".animate-spin")).not.toBeNull();
    expect(screen.queryByText("Dashboard Page")).toBeNull();
  });

  it("lands a multi-role user on the first landing_path by role name", () => {
    // "First non-null, ordered by role name" is total and deterministic, but
    // it is only *identical* to the retired enum switch for users with one
    // landing-carrying role: a user holding both `Administrador (papel)` and
    // `Porteiro (papel)` lands on `/dashboard`, where the switch — keyed on a
    // single global value — would also have. The backend picks; this asserts
    // the frontend honours whatever it picked, and nothing more.
    withLanding("/dashboard", ["tasks:read"]);

    renderRoot();

    expect(screen.getByText("Dashboard Page")).toBeInTheDocument();
    expect(screen.queryByText("Gate Page")).toBeNull();
  });
});

/**
 * The fallback chain APRAS-39 §10.4 adds.
 *
 * `landing_path ?? "/dashboard"` can now point at a route the caller cannot
 * open — a tenant with `tasks` off strands everyone on a restricted
 * `/dashboard`. The chain is: `landing_path` if its route is accessible →
 * `/dashboard` if accessible → the first `NAV_ITEMS` entry the caller may
 * see → `/welcome`.
 *
 * **Determinism:** "the first entry" means the first in `NAV_ITEMS`
 * *declaration order*, a module-level array literal and therefore stable
 * across renders, reloads and machines. The chain is a `.find()` over that
 * array — never over a `Set` or `Object.keys` — so two users with the same
 * permission set always land on the same path, and reordering `NAV_ITEMS` is
 * the only thing that can change a landing. These cases assert the specific
 * path, so a reorder is caught.
 */
describe("RootRedirect fallback chain (APRAS-39)", () => {
  const withPermissions = (
    permissions: string[],
    landing_path: string | null = null,
    disabled_modules: string[] = [],
  ) => {
    vi.mocked(useMyPermissions).mockReturnValue({
      data: {
        tenant_id: "00000000-0000-0000-0000-000000000001",
        permissions,
        landing_path,
        disabled_modules,
      },
      isPending: false,
      isError: false,
    } as never);
  };

  const renderWide = () =>
    render(
      <MemoryRouter initialEntries={["/"]}>
        <Routes>
          <Route path="/" element={<RootRedirect />} />
          <Route path="/dashboard" element={<div>Dashboard Page</div>} />
          <Route path="/welcome" element={<div>Welcome Page</div>} />
          <Route path="/gate" element={<div>Gate Page</div>} />
          <Route path="/lots" element={<div>Lots Page</div>} />
          <Route path="/occurrences" element={<div>Occurrences Page</div>} />
          <Route path="/finance" element={<div>Finance Page</div>} />
        </Routes>
      </MemoryRouter>,
    );

  beforeEach(() => {
    vi.clearAllMocks();
    mockAuth();
  });

  it("honours landing_path when its route is accessible", () => {
    withPermissions(["gate:checkin"], "/gate");

    renderWide();

    expect(screen.getByText("Gate Page")).toBeInTheDocument();
  });

  it("lands on the first accessible nav item when the landing module is disabled", () => {
    // `tasks` off: `landing_path` (/dashboard) and `/dashboard` both fail.
    // `/lots` precedes `/occurrences` in NAV_ITEMS declaration order, so the
    // answer is `/lots` and asserting the *specific* path is what catches a
    // reorder.
    withPermissions(
      ["lots:read", "occurrences:read"],
      "/dashboard",
      ["tasks"],
    );

    renderWide();

    expect(screen.getByText("Lots Page")).toBeInTheDocument();
    expect(screen.queryByText("Dashboard Page")).toBeNull();
    expect(screen.queryByText("Occurrences Page")).toBeNull();
  });

  it("lands on /welcome when every module the user's role covers is disabled", () => {
    // The empty-set terminal is real: PORTEIRO's 14 permissions span five
    // modules (`gate`, `lots`, `packages`, `reservations`, `tasks`) and all
    // five are toggleable, so a tenant that buys only the finance package
    // leaves its porteiros with an empty effective set. `/welcome` carries no
    // rule at all, so this is a landing, not a redirect loop.
    withPermissions([], "/gate", [
      "gate",
      "lots",
      "packages",
      "reservations",
      "tasks",
    ]);

    renderWide();

    expect(screen.getByText("Welcome Page")).toBeInTheDocument();
  });

  it("still prefers /dashboard when it is accessible and landing_path is null", () => {
    withPermissions(["tasks:read"]);

    renderWide();

    expect(screen.getByText("Dashboard Page")).toBeInTheDocument();
  });
});
