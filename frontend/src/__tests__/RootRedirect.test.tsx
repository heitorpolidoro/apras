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

  it("renders General Dashboard directly at / for callers with no overriding landing", () => {
    withLanding(null, ["tasks:read"]);

    renderRoot();

    expect(screen.getByText("Painel Geral")).toBeInTheDocument();
    expect(screen.getByText("Bem-vindo ao painel central do seu condomínio.")).toBeInTheDocument();
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

  it("lands a multi-role user on the first landing_path by role name when overriding", () => {
    // A role specifying a non-root landing (like /gate) redirects to it if accessible
    withLanding("/gate", ["gate:checkin"]);

    renderRoot();

    expect(screen.getByText("Gate Page")).toBeInTheDocument();
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
describe("RootRedirect landing behavior (APRAS-56)", () => {
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
          <Route path="/tasks" element={<div>Tasks Page</div>} />
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

  it("honours landing_path when its route is accessible and not root", () => {
    withPermissions(["gate:checkin"], "/gate");

    renderWide();

    expect(screen.getByText("Gate Page")).toBeInTheDocument();
  });

  it("renders General Dashboard at / when landing_path is /", () => {
    withPermissions(["tasks:read"], "/");

    renderWide();

    expect(screen.getByText("Painel Geral")).toBeInTheDocument();
  });

  it("renders General Dashboard directly at / when landing module is disabled", () => {
    // When a specific landing path (e.g. /gate) is inaccessible due to disabled module,
    // RootRedirect stays at / and renders GeneralDashboardPage
    withPermissions(
      ["tasks:read", "lots:read"],
      "/gate",
      ["gate"],
    );

    renderWide();

    expect(screen.getByText("Painel Geral")).toBeInTheDocument();
    expect(screen.queryByText("Gate Page")).toBeNull();
  });

  it("renders General Dashboard at / when landing_path is null", () => {
    withPermissions(["tasks:read"]);

    renderWide();

    expect(screen.getByText("Painel Geral")).toBeInTheDocument();
  });
});
