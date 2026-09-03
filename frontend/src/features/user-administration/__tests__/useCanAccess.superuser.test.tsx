import { renderHook, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type React from "react";
import apiClient from "../../../api/client";
import * as AuthHook from "../context/AuthContext";
import { useSimulation } from "../context/SimulationContext";
import { useRoles } from "../../../hooks/useRoles";
import {
  useCanAccess,
  useCanShowMenu,
  useEffectivePermissionSet,
} from "../access/useCanAccess";
import { type User } from "../../../types/auth";
import { ROUTE_ACCESS } from "../access/routeAccess";

/**
 * The third `AccessRule` shape and the simulation arm's module intersection
 * (APRAS-39 §10.1, §10.2).
 *
 * `{ superuser: true }` exists because `/admin/modules` is the first frontend
 * surface for a superuser-only *backend* route, and such routes carry no
 * catalogue permission by convention — so no `{ anyOf }` rule can express it.
 * The flag is read from `useAuth()`, never from the simulated identity, so
 * "view-as" cannot open an operator screen.
 */

vi.mock("../../../api/client", () => ({
  default: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}));

vi.mock("../context/SimulationContext", () => ({
  useSimulation: vi.fn(),
}));

vi.mock("../../../hooks/useRoles", () => ({
  useRoles: vi.fn(),
}));

const mockedGet = vi.mocked(apiClient.get);

const NOT_SIMULATING = {
  simulatedRoleIds: [],
  isSimulating: false,
  setSimulatedRoleIds: vi.fn(),
  stopSimulation: vi.fn(),
};

const wrapper = (): React.FC<{ children: React.ReactNode }> => {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
};

const mockAuth = (user: Partial<User>) => {
  vi.spyOn(AuthHook, "useAuth").mockReturnValue({
    user: user as User,
    isAuthenticated: true,
    isLoading: false,
    login: vi.fn() as never,
    logout: vi.fn(),
  } as never);
};

const answerPermissions = (permissions: string[], disabled: string[] = []) => {
  mockedGet.mockImplementation(((url: string) => {
    if (url === "/permissions/me") {
      return Promise.resolve({
        data: {
          tenant_id: "t-1",
          permissions,
          landing_path: null,
          disabled_modules: disabled,
        },
      });
    }
    return Promise.resolve({ data: [] });
  }) as never);
};

beforeEach(() => {
  vi.clearAllMocks();
  mockedGet.mockReset();
  vi.mocked(useSimulation).mockReturnValue(NOT_SIMULATING);
  vi.mocked(useRoles).mockReturnValue({ data: [] } as never);
});

describe.each([
  ["/admin/modules"],
  ["/admin/plans"],
  ["/admin/subscriptions"],
])("the %s rule resolves through the flag alone", (path) => {
  it("allows a superuser and refuses a whole-catalogue tenant_admin", async () => {
    // One case per `{ superuser: true }` route, read out of `ROUTE_ACCESS`
    // rather than restated: a route that silently changed shape would stop
    // being covered here rather than quietly passing.
    const rule = ROUTE_ACCESS[path];
    expect(rule).toEqual({ superuser: true });

    mockAuth({ id: "root", is_superuser: true, roles: [] });
    answerPermissions([]);
    const asSuperuser = renderHook(() => useCanAccess(rule), {
      wrapper: wrapper(),
    });
    await waitFor(() => expect(asSuperuser.result.current.isLoading).toBe(false));
    expect(asSuperuser.result.current.allowed).toBe(true);

    mockAuth({ id: "sindico", is_superuser: false, roles: [] });
    answerPermissions(["tenants:update", "billing:read", "billing:manage"]);
    const asTenantAdmin = renderHook(() => useCanAccess(rule), {
      wrapper: wrapper(),
    });
    await waitFor(() =>
      expect(asTenantAdmin.result.current.isLoading).toBe(false),
    );
    expect(asTenantAdmin.result.current.allowed).toBe(false);
  });
});

describe("the /subscription rule holds for any billing:*", () => {
  it("admits a billing:read holder and refuses a user with neither string", async () => {
    const rule = ROUTE_ACCESS["/subscription"];
    expect(rule).toEqual({ module: "billing" });

    mockAuth({ id: "diretor", is_superuser: false, roles: [] });
    answerPermissions(["billing:read"]);
    const granted = renderHook(() => useCanAccess(rule), { wrapper: wrapper() });
    await waitFor(() => expect(granted.result.current.isLoading).toBe(false));
    expect(granted.result.current.allowed).toBe(true);

    answerPermissions(["tasks:read"]);
    const refused = renderHook(() => useCanAccess(rule), { wrapper: wrapper() });
    await waitFor(() => expect(refused.result.current.isLoading).toBe(false));
    expect(refused.result.current.allowed).toBe(false);
  });
});

describe("the { superuser: true } access rule", () => {
  it("allows a superuser", async () => {
    mockAuth({ id: "root", is_superuser: true, roles: [] });
    answerPermissions([]);

    const { result } = renderHook(() => useCanAccess({ superuser: true }), {
      wrapper: wrapper(),
    });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.allowed).toBe(true);
  });

  it("refuses a tenant_admin, who holds the whole catalogue but not the flag", async () => {
    // The precise reason `{ anyOf: ["tenants:update"] }` would be wrong: an
    // acting tenant_admin *does* hold that string through the
    // whole-catalogue short-circuit, while the API answers them 403.
    mockAuth({ id: "sindico", is_superuser: false, roles: [] });
    answerPermissions(["tenants:update", "tenants:members_set_admin"]);

    const { result } = renderHook(() => useCanAccess({ superuser: true }), {
      wrapper: wrapper(),
    });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.allowed).toBe(false);
  });

  it("is never simulated: the menu hook reads the real auth flag too", async () => {
    mockAuth({ id: "root", is_superuser: true, roles: [] });
    vi.mocked(useSimulation).mockReturnValue({
      ...NOT_SIMULATING,
      simulatedRoleIds: ["r-guest"],
      isSimulating: true,
    });
    vi.mocked(useRoles).mockReturnValue({
      data: [{ id: "r-guest", name: "Convidado", permissions: [] }],
    } as never);
    answerPermissions([]);

    const { result } = renderHook(() => useCanShowMenu({ superuser: true }), {
      wrapper: wrapper(),
    });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    // Simulating a guest must not close the operator screen, exactly as it
    // must not open one for a non-superuser.
    expect(result.current.allowed).toBe(true);
  });

  it("refuses a non-superuser even while simulating a role", async () => {
    mockAuth({ id: "sindico", is_superuser: false, roles: [] });
    vi.mocked(useSimulation).mockReturnValue({
      ...NOT_SIMULATING,
      simulatedRoleIds: ["r-all"],
      isSimulating: true,
    });
    vi.mocked(useRoles).mockReturnValue({
      data: [{ id: "r-all", name: "Tudo", permissions: ["tenants:update"] }],
    } as never);
    answerPermissions(["tenants:update"]);

    const { result } = renderHook(() => useCanShowMenu({ superuser: true }), {
      wrapper: wrapper(),
    });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.allowed).toBe(false);
  });
});

describe("the simulation arm intersects with the active modules", () => {
  it("drops a disabled module's permissions from the simulated preview", async () => {
    // Without this, an operator simulating a role in a tenant with `finance`
    // off would preview a menu the real user cannot have.
    mockAuth({ id: "root", is_superuser: true, roles: [] });
    vi.mocked(useSimulation).mockReturnValue({
      ...NOT_SIMULATING,
      simulatedRoleIds: ["r-1"],
      isSimulating: true,
    });
    vi.mocked(useRoles).mockReturnValue({
      data: [
        {
          id: "r-1",
          name: "Morador",
          permissions: ["finance:read", "tasks:read"],
        },
      ],
    } as never);
    answerPermissions([], ["finance"]);

    const { result } = renderHook(() => useEffectivePermissionSet(), {
      wrapper: wrapper(),
    });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    await waitFor(() =>
      expect(result.current.has("tasks:read")).toBe(true),
    );
    expect(result.current.has("finance:read")).toBe(false);
    expect(result.current.hasModule("finance")).toBe(false);
  });

  it("keeps the whole union when no module is disabled", async () => {
    mockAuth({ id: "root", is_superuser: true, roles: [] });
    vi.mocked(useSimulation).mockReturnValue({
      ...NOT_SIMULATING,
      simulatedRoleIds: ["r-1"],
      isSimulating: true,
    });
    vi.mocked(useRoles).mockReturnValue({
      data: [
        {
          id: "r-1",
          name: "Morador",
          permissions: ["finance:read", "tasks:read"],
        },
      ],
    } as never);
    answerPermissions([]);

    const { result } = renderHook(() => useEffectivePermissionSet(), {
      wrapper: wrapper(),
    });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    await waitFor(() =>
      expect(result.current.has("finance:read")).toBe(true),
    );
    expect(result.current.has("tasks:read")).toBe(true);
  });
});
