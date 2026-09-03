import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type React from "react";
import { RootRedirect } from "../App";
import ProtectedRoute from "../features/user-administration/components/ProtectedRoute";
import { ROUTE_ACCESS } from "../features/user-administration/access/routeAccess";
import * as AuthHook from "../features/user-administration/context/AuthContext";
import { useSimulation } from "../features/user-administration/context/SimulationContext";
import { useRoles } from "../hooks/useRoles";
import apiClient from "../api/client";
import pt from "../i18n/locales/pt.json";

/**
 * The landing chain against the **real** `ProtectedRoute` and the **real**
 * `ROUTE_ACCESS` (code review round 1, findings 2 and 3).
 *
 * `RootRedirect.test.tsx` mounts bare `<div>`s at the chain's targets, so it
 * cannot see the two ways the chain was defeated in round 1:
 *
 *  * **`landingRedirect` bounced it back.** `/dashboard` and `/categories`
 *    both carry `landingRedirect: true`, so landing a caller there sent them
 *    straight to the `landing_path` the chain had just rejected. The redirect
 *    now fires only when the landing target is itself accessible, judged by
 *    the same `useCanOpenPath` the chain uses.
 *  * **The cold load never evaluated.** `useMyPermissions` is
 *    disabled-and-pending until the acting tenant resolves, so a `<Navigate>`
 *    on the first render left before the set ever arrived. `RootRedirect`
 *    now holds a spinner until the query settles.
 *
 * The persona is the spec's own: migration `0033` seeds
 * `_LANDING_PATHS = {"PORTEIRO": "/gate", "GUEST": "/welcome"}`, and §10.4
 * reasons explicitly about a PORTEIRO in a tenant that has `gate` off.
 */

vi.mock("../api/client", () => ({
  default: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}));

vi.mock("../features/user-administration/context/SimulationContext", () => ({
  useSimulation: vi.fn(),
}));

vi.mock("../hooks/useRoles", () => ({
  useRoles: vi.fn(() => ({ data: [] })),
}));

const mockedGet = vi.mocked(apiClient.get);

const NOT_SIMULATING = {
  simulatedRoleIds: [],
  isSimulating: false,
  setSimulatedRoleIds: vi.fn(),
  stopSimulation: vi.fn(),
};

const t = (key: string): string =>
  key
    .split(".")
    .reduce<unknown>(
      (node, part) => (node as Record<string, unknown>)?.[part],
      pt,
    ) as string;

/** `useActingTenantReady()` is `!useAuth().isLoading`, so this gates the query. */
const auth = (isLoading = false) => {
  vi.spyOn(AuthHook, "useAuth").mockReturnValue({
    isAuthenticated: true,
    isLoading,
    user: {
      id: "porteiro-1",
      email: "porteiro@example.com",
      full_name: "Porteiro",
      is_active: true,
      is_superuser: false,
      roles: [],
    },
    login: vi.fn(),
    logout: vi.fn(),
  } as never);
};

const answer = (
  permissions: string[],
  landing_path: string | null,
  disabled_modules: string[] = [],
  never = false,
) => {
  mockedGet.mockImplementation(((url: string) => {
    if (url === "/permissions/me") {
      return never
        ? new Promise(() => undefined)
        : Promise.resolve({
            data: {
              tenant_id: "00000000-0000-0000-0000-000000000001",
              permissions,
              landing_path,
              disabled_modules,
            },
          });
    }
    return Promise.resolve({ data: [] });
  }) as never);
};

/** `/` plus the real `ProtectedRoute` at every route the chain can pick. */
const renderApp = () => {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const Wrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
  const guarded = (path: string, label: string) => (
    <Route
      path={path}
      element={
        <ProtectedRoute requiredAccess={ROUTE_ACCESS[path]}>
          <div>{label}</div>
        </ProtectedRoute>
      }
    />
  );
  return render(
    <MemoryRouter initialEntries={["/"]}>
      <Routes>
        <Route path="/" element={<RootRedirect />} />
        {guarded("/dashboard", "Dashboard Content")}
        {guarded("/categories", "Categories Content")}
        {guarded("/gate", "Gate Content")}
        {guarded("/lots", "Lots Content")}
        <Route
          path="/welcome"
          element={
            <ProtectedRoute>
              <div>Welcome Content</div>
            </ProtectedRoute>
          }
        />
      </Routes>
    </MemoryRouter>,
    { wrapper: Wrapper },
  );
};

beforeEach(() => {
  vi.clearAllMocks();
  mockedGet.mockReset();
  vi.mocked(useSimulation).mockReturnValue(NOT_SIMULATING);
  vi.mocked(useRoles).mockReturnValue({ data: [] } as never);
  auth();
});

describe("the landing chain against the real ProtectedRoute", () => {
  it("does not bounce a PORTEIRO back onto /gate when the gate module is off", async () => {
    // Round 1's reproduction, now a pin. The chain rejects `/gate`, picks
    // `/dashboard` — and `/dashboard` carries `landingRedirect: true`, which
    // used to send the caller straight back to the disabled `/gate`.
    answer(["tasks:read", "lots:read"], "/gate", ["gate"]);

    renderApp();

    expect(await screen.findByText("Dashboard Content")).toBeInTheDocument();
    expect(screen.queryByText(t("common.moduleUnavailable"))).toBeNull();
    expect(screen.queryByText("Gate Content")).toBeNull();
  });

  it("still honours the landing redirect when the landing is accessible", async () => {
    // The behaviour APRAS-12 shipped and APRAS-49 made data-driven must not
    // regress: with `gate` on, a PORTEIRO opening `/` ends at `/gate`.
    answer(["tasks:read", "lots:read", "gate:checkin"], "/gate");

    renderApp();

    expect(await screen.findByText("Gate Content")).toBeInTheDocument();
  });

  it("bounces a caller who navigates directly to /dashboard when the landing is open", async () => {
    // The landing redirect is `ProtectedRoute`'s, not `RootRedirect`'s, so it
    // has to keep firing on a direct navigation too.
    answer(["tasks:read", "gate:checkin"], "/gate");
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={["/dashboard"]}>
          <Routes>
            <Route
              path="/dashboard"
              element={
                <ProtectedRoute requiredAccess={ROUTE_ACCESS["/dashboard"]}>
                  <div>Dashboard Content</div>
                </ProtectedRoute>
              }
            />
            <Route
              path="/gate"
              element={
                <ProtectedRoute requiredAccess={ROUTE_ACCESS["/gate"]}>
                  <div>Gate Content</div>
                </ProtectedRoute>
              }
            />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    );

    expect(await screen.findByText("Gate Content")).toBeInTheDocument();
  });

  it("keeps a caller on /dashboard when their landing module is off", async () => {
    // The same direct navigation, with `gate` disabled: the bounce must not
    // fire, and the caller sees the page they asked for.
    answer(["tasks:read"], "/gate", ["gate"]);
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={["/dashboard"]}>
          <Routes>
            <Route
              path="/dashboard"
              element={
                <ProtectedRoute requiredAccess={ROUTE_ACCESS["/dashboard"]}>
                  <div>Dashboard Content</div>
                </ProtectedRoute>
              }
            />
            <Route
              path="/gate"
              element={
                <ProtectedRoute requiredAccess={ROUTE_ACCESS["/gate"]}>
                  <div>Gate Content</div>
                </ProtectedRoute>
              }
            />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    );

    expect(await screen.findByText("Dashboard Content")).toBeInTheDocument();
  });

  it("lands on /welcome when every module the persona's role covers is off", async () => {
    // PORTEIRO's 14 permissions span five modules, all toggleable. A tenant
    // that buys only the finance package leaves them with an empty set.
    answer([], "/gate", ["gate", "lots", "packages", "reservations", "tasks"]);

    renderApp();

    expect(await screen.findByText("Welcome Content")).toBeInTheDocument();
  });
});

describe("the cold-load sequence: disabled -> loading -> settled", () => {
  it("holds a spinner while the acting tenant is still resolving", () => {
    // `useMyPermissions` is `enabled: useActingTenantReady()`, i.e. disabled
    // *and* pending while auth is loading. A <Navigate> on this render would
    // unmount RootRedirect before the set ever arrived — which is exactly how
    // the chain came to never execute on the primary path.
    auth(true);
    answer(["tasks:read"], "/gate", ["gate"]);

    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    const { container } = render(
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={["/"]}>
          <Routes>
            <Route path="/" element={<RootRedirect />} />
            <Route path="/dashboard" element={<div>Dashboard Content</div>} />
            <Route path="/gate" element={<div>Gate Content</div>} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    );

    expect(container.querySelector(".animate-spin")).not.toBeNull();
    expect(screen.queryByText("Gate Content")).toBeNull();
    expect(screen.queryByText("Dashboard Content")).toBeNull();
    // The query never even fired: it is disabled until the tenant resolves.
    expect(mockedGet).not.toHaveBeenCalled();
  });

  it("holds a spinner while the request is in flight, then evaluates", async () => {
    // One continuous mount, deliberately: the whole point of finding 3 is
    // that `RootRedirect` must still be mounted when the data arrives. A
    // re-render with a fresh client would prove nothing, because it would
    // give the chain a second chance the real cold load never gets.
    let settle: (value: unknown) => void = () => undefined;
    const inFlight = new Promise((resolve) => {
      settle = resolve;
    });
    mockedGet.mockImplementation(((url: string) => {
      if (url === "/permissions/me") return inFlight;
      return Promise.resolve({ data: [] });
    }) as never);

    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    const { container } = render(
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={["/"]}>
          <Routes>
            <Route path="/" element={<RootRedirect />} />
            <Route path="/dashboard" element={<div>Dashboard Content</div>} />
            <Route path="/gate" element={<div>Gate Content</div>} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    );

    expect(container.querySelector(".animate-spin")).not.toBeNull();
    expect(screen.queryByText("Gate Content")).toBeNull();

    // ...and once it settles, the chain runs and rejects the disabled landing.
    settle({
      data: {
        tenant_id: "00000000-0000-0000-0000-000000000001",
        permissions: ["tasks:read"],
        landing_path: "/gate",
        disabled_modules: ["gate"],
      },
    });

    await waitFor(() =>
      expect(screen.getByText("Dashboard Content")).toBeInTheDocument(),
    );
    expect(screen.queryByText("Gate Content")).toBeNull();
  });
});
