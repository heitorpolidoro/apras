import { renderHook, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type React from "react";
import apiClient from "../../../api/client";
import * as AuthHook from "../context/AuthContext";
import { useSimulation } from "../context/SimulationContext";
import { useUserTypes } from "../../../hooks/useUserTypes";
import {
  useCanAccess,
  useCanShowMenu,
  useEffectivePermissionSet,
  usePermissionSet,
} from "../access/useCanAccess";
import { UserRole, type User } from "../../../types/auth";

/**
 * The two permission sets of §2.7, exercised through the real query stack:
 * `apiClient` is the only mock on the data path, so `api/permissions.ts`,
 * `usePermissionQueries.ts` and `useCanAccess.ts` all run for real.
 */
vi.mock("../../../api/client", () => ({
  default: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}));

vi.mock("../context/SimulationContext", () => ({
  useSimulation: vi.fn(),
}));

vi.mock("../../../hooks/useUserTypes", () => ({
  useUserTypes: vi.fn(),
}));

const mockedGet = vi.mocked(apiClient.get);

const NOT_SIMULATING = {
  simulatedRole: null,
  simulatedUserTypeIds: [],
  isSimulating: false,
  setSimulatedRole: vi.fn(),
  setSimulatedUserTypeIds: vi.fn(),
  stopSimulation: vi.fn(),
};

const ADMIN: Partial<User> = {
  id: "admin-1",
  email: "admin@test.com",
  full_name: "Admin",
  role: UserRole.ADMINISTRATOR,
  is_active: true,
  user_types: [],
};

const wrapper = (): React.FC<{ children: React.ReactNode }> => {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
};

const mockAuth = (user: Partial<User> = ADMIN, isLoading = false) => {
  vi.spyOn(AuthHook, "useAuth").mockReturnValue({
    user: user as User,
    isAuthenticated: true,
    isLoading,
    login: vi.fn() as never,
    logout: vi.fn(),
  } as never);
};

const answerPermissions = (permissions: string[]) => {
  mockedGet.mockImplementation(((url: string) => {
    if (url === "/permissions/me") {
      return Promise.resolve({ data: { tenant_id: "t-1", permissions } });
    }
    return Promise.resolve({ data: [] });
  }) as never);
};

beforeEach(() => {
  vi.clearAllMocks();
  mockedGet.mockReset();
  vi.mocked(useSimulation).mockReturnValue(NOT_SIMULATING);
  vi.mocked(useUserTypes).mockReturnValue({ data: [] } as never);
  mockAuth();
});

describe("usePermissionSet / useCanAccess", () => {
  it("resolves the acting tenant's permissions from /permissions/me", async () => {
    answerPermissions(["finance:read", "user_types:update"]);

    const { result } = renderHook(() => usePermissionSet(), {
      wrapper: wrapper(),
    });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.has("finance:read")).toBe(true);
    expect(result.current.has("votes:cast")).toBe(false);
    expect([...result.current.all].sort()).toEqual([
      "finance:read",
      "user_types:update",
    ]);
    expect(mockedGet).toHaveBeenCalledWith("/permissions/me");
  });

  it("is loading until the query settles", async () => {
    let release: (value: unknown) => void = () => undefined;
    mockedGet.mockImplementation(
      (() => new Promise((resolve) => (release = resolve))) as never,
    );

    const { result } = renderHook(() => useCanAccess({ module: "finance" }), {
      wrapper: wrapper(),
    });

    expect(result.current.isLoading).toBe(true);
    expect(result.current.allowed).toBe(false);

    release({ data: { tenant_id: "t-1", permissions: ["finance:read"] } });
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.allowed).toBe(true);
  });

  it("falls back to an empty set when the query errors", async () => {
    mockedGet.mockImplementation((() =>
      Promise.reject(new Error("boom"))) as never);

    const { result } = renderHook(() => useCanAccess({ module: "finance" }), {
      wrapper: wrapper(),
    });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.allowed).toBe(false);
  });

  it("hasModule matches on the permission prefix", async () => {
    answerPermissions(["finance:transaction_create"]);

    const { result } = renderHook(() => usePermissionSet(), {
      wrapper: wrapper(),
    });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.hasModule("finance")).toBe(true);
    // A prefix that is not a whole module segment must not match.
    expect(result.current.hasModule("fin")).toBe(false);
    expect(result.current.hasModule("votes")).toBe(false);
  });

  it("usePermissionSet ignores an active simulation", async () => {
    answerPermissions(["user_types:update"]);
    vi.mocked(useSimulation).mockReturnValue({
      ...NOT_SIMULATING,
      simulatedRole: UserRole.RESIDENT,
      simulatedUserTypeIds: ["resident-type"],
      isSimulating: true,
    });
    vi.mocked(useUserTypes).mockReturnValue({
      data: [
        {
          id: "resident-type",
          name: "Morador (papel)",
          allowed_menus: [],
          role: UserRole.RESIDENT,
          permissions: ["tasks:read"],
        },
      ],
    } as never);

    const { result } = renderHook(
      () => ({
        real: usePermissionSet(),
        effective: useEffectivePermissionSet(),
      }),
      { wrapper: wrapper() },
    );

    await waitFor(() => expect(result.current.real.isLoading).toBe(false));
    expect(result.current.real.has("user_types:update")).toBe(true);
    expect(result.current.real.has("tasks:read")).toBe(false);
  });

  it("useEffectivePermissionSet unions the simulated groups' permissions while simulating", async () => {
    answerPermissions(["user_types:update"]);
    vi.mocked(useSimulation).mockReturnValue({
      ...NOT_SIMULATING,
      simulatedRole: UserRole.RESIDENT,
      simulatedUserTypeIds: ["type-a", "type-b"],
      isSimulating: true,
    });
    vi.mocked(useUserTypes).mockReturnValue({
      data: [
        {
          id: "type-a",
          name: "A",
          allowed_menus: [],
          permissions: ["tasks:read"],
        },
        {
          id: "type-b",
          name: "B",
          allowed_menus: [],
          permissions: ["occurrences:read"],
        },
        {
          id: "type-c",
          name: "C",
          allowed_menus: [],
          permissions: ["finance:read"],
        },
      ],
    } as never);

    const { result } = renderHook(
      () => ({
        effective: useEffectivePermissionSet(),
        menu: useCanShowMenu({ module: "occurrences" }),
        route: useCanAccess({ module: "occurrences" }),
      }),
      { wrapper: wrapper() },
    );

    await waitFor(() => expect(result.current.effective.isLoading).toBe(false));
    expect([...result.current.effective.all].sort()).toEqual([
      "occurrences:read",
      "tasks:read",
    ]);
    // The simulated user's menu is shown …
    expect(result.current.menu.allowed).toBe(true);
    // … while the administrator's own route access is unchanged.
    expect(result.current.route.allowed).toBe(false);
  });

  it("evaluates an anyOf rule against the real set", async () => {
    answerPermissions(["user_types:update"]);

    const { result } = renderHook(
      () => ({
        held: useCanAccess({
          anyOf: ["user_types:create", "user_types:update"],
        }),
        notHeld: useCanAccess({ anyOf: ["uploads:pending_read"] }),
        noRule: useCanAccess(undefined),
      }),
      { wrapper: wrapper() },
    );

    await waitFor(() => expect(result.current.held.isLoading).toBe(false));
    expect(result.current.held.allowed).toBe(true);
    expect(result.current.notHeld.allowed).toBe(false);
    // No rule at all means "authenticated is enough" (e.g. `/welcome`).
    expect(result.current.noRule.allowed).toBe(true);
  });

  it("ANDs the legacy menu gate when the rule carries legacyMenu", async () => {
    answerPermissions(["tasks:read"]);
    // A DIRECTOR whose groups grant no `tasks` menu key: the permission is
    // held, but `deps.assert_menu_access` would still answer 403 (§2.3).
    mockAuth({ ...ADMIN, role: UserRole.DIRECTOR });
    vi.mocked(useUserTypes).mockReturnValue({
      data: [{ id: "type-1", name: "Board", allowed_menus: [] }],
    } as never);

    const { result } = renderHook(
      () => ({
        withMenu: useCanAccess({ module: "tasks", legacyMenu: "tasks" }),
        withoutMenu: useCanAccess({ module: "tasks" }),
      }),
      { wrapper: wrapper() },
    );

    await waitFor(() => expect(result.current.withMenu.isLoading).toBe(false));
    expect(result.current.withMenu.allowed).toBe(false);
    expect(result.current.withoutMenu.allowed).toBe(true);
  });
});
