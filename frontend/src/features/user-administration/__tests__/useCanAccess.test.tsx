import { renderHook, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type React from "react";
import apiClient from "../../../api/client";
import * as AuthHook from "../context/AuthContext";
import { useSimulation } from "../context/SimulationContext";
import { useRoles } from "../../../hooks/useRoles";
import { useCanAccess, useCanShowMenu, useEffectivePermissionSet, usePermissionSet,  } from "../access/useCanAccess";
import { type User } from "../../../types/auth";

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

const ADMIN: Partial<User> = {
  id: "admin-1",
  email: "admin@test.com",
  full_name: "Admin",
  is_superuser: true,
  is_active: true,
  roles: [],
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
  vi.mocked(useRoles).mockReturnValue({ data: [] } as never);
  mockAuth();
});

describe("usePermissionSet / useCanAccess", () => {
  it("resolves the acting tenant's permissions from /permissions/me", async () => {
    answerPermissions(["finance:read", "roles:update"]);

    const { result } = renderHook(() => usePermissionSet(), {
      wrapper: wrapper(),
    });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.has("finance:read")).toBe(true);
    expect(result.current.has("votes:cast")).toBe(false);
    expect([...result.current.all].sort()).toEqual([
      "finance:read",
      "roles:update",
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
    answerPermissions(["roles:update"]);
    vi.mocked(useSimulation).mockReturnValue({
      ...NOT_SIMULATING,
      simulatedRoleIds: ["resident-type"],
      isSimulating: true,
    });
    vi.mocked(useRoles).mockReturnValue({
      data: [
        {
          id: "resident-type",
          name: "Morador (papel)",
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
    expect(result.current.real.has("roles:update")).toBe(true);
    expect(result.current.real.has("tasks:read")).toBe(false);
  });

  it("useEffectivePermissionSet tolerates a role with no bundle and an unloaded list", async () => {
    // Two defensive branches on the same line: `useRoles()` may not have
    // settled (`roles ?? []`) and a `RoleRead` may carry no `permissions`
    // (the field is optional so every pre-F2 fixture keeps type-checking).
    // Neither may throw while an administrator is previewing a role.
    answerPermissions(["roles:update"]);
    vi.mocked(useSimulation).mockReturnValue({
      ...NOT_SIMULATING,
      simulatedRoleIds: ["type-a"],
      isSimulating: true,
    });
    vi.mocked(useRoles).mockReturnValue({ data: undefined } as never);

    const unloaded = renderHook(() => useEffectivePermissionSet(), {
      wrapper: wrapper(),
    });
    await waitFor(() => expect(unloaded.result.current.isLoading).toBe(false));
    expect([...unloaded.result.current.all]).toEqual([]);

    vi.mocked(useRoles).mockReturnValue({
      data: [{ id: "type-a", name: "Sem bundle" }],
    } as never);

    const noBundle = renderHook(() => useEffectivePermissionSet(), {
      wrapper: wrapper(),
    });
    await waitFor(() => expect(noBundle.result.current.isLoading).toBe(false));
    expect([...noBundle.result.current.all]).toEqual([]);
  });

  it("useEffectivePermissionSet unions the simulated roles' permissions while simulating", async () => {
    answerPermissions(["roles:update"]);
    vi.mocked(useSimulation).mockReturnValue({
      ...NOT_SIMULATING,
      simulatedRoleIds: ["type-a", "type-b"],
      isSimulating: true,
    });
    vi.mocked(useRoles).mockReturnValue({
      data: [
        {
          id: "type-a",
          name: "A",
          permissions: ["tasks:read"],
        },
        {
          id: "type-b",
          name: "B",
          permissions: ["occurrences:read"],
        },
        {
          id: "type-c",
          name: "C",
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
    answerPermissions(["roles:update"]);

    const { result } = renderHook(
      () => ({
        held: useCanAccess({
          anyOf: ["roles:create", "roles:update"],
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

  it("a rule is now exactly its permission predicate (IAM F5 §4.1)", async () => {
    // This case used to assert that `{ module, legacyMenu }` ANDed the
    // `allowed_menus` gate on top of the permission: a DIRECTOR whose roles
    // granted no `tasks` menu key was refused even though the permission was
    // held, because `deps.assert_menu_access` would have answered 403.
    //
    // F5 deleted that gate from all 12 handlers, so the door and the API now
    // agree by construction and `legacyMenu` is not a field of `AccessRule`
    // any more. The widening this causes is enumerated in §4.2 and pinned by
    // `backend/tests/test_menu_gate_removal.py`.
    mockAuth({ ...ADMIN });
    answerPermissions(["tasks:read"]);
    vi.mocked(useRoles).mockReturnValue({
      data: [{ id: "type-1", name: "Board" }],
    } as never);

    const { result } = renderHook(() => useCanAccess({ module: "tasks" }), {
      wrapper: wrapper(),
    });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.allowed).toBe(true);
  });
});
