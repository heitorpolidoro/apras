import { renderHook } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { useMenuAccess } from "../context/useMenuAccess";
import { useAuth } from "../context/AuthContext";
import { useSimulation } from "../context/SimulationContext";
import { useUserTypes } from "../../../hooks/useUserTypes";
import { UserRole } from "../../../types/auth";

/**
 * `GET /api/v1/auth/me` is a global route and returns the caller's
 * `user_types` from **every** tenant — a named residual of APRAS-42/43,
 * deliberately not fixed here (there is no acting tenant on a global route to
 * filter by). This module pins the reason that residual is not a
 * privilege-escalation hole in practice.
 */
vi.mock("../context/AuthContext", () => ({ useAuth: vi.fn() }));
vi.mock("../context/SimulationContext", () => ({ useSimulation: vi.fn() }));
vi.mock("../../../hooks/useUserTypes", () => ({ useUserTypes: vi.fn() }));

const notSimulating = {
  simulatedRole: null,
  simulatedUserTypeIds: [],
  isSimulating: false,
  setSimulatedRole: vi.fn(),
  setSimulatedUserTypeIds: vi.fn(),
  stopSimulation: vi.fn(),
};

const TENANT_A_TYPE = {
  id: "type-in-tenant-a",
  name: "Conselho A",
  allowed_menus: [],
};
const TENANT_B_TYPE = {
  id: "type-in-tenant-b",
  name: "Conselho B",
  allowed_menus: ["tasks", "categories"],
};

describe("useMenuAccess across tenants", () => {
  it("a UserType from another tenant grants no menu in the acting tenant", () => {
    // The user carries both types on /auth/me: the tenant-B one is the only
    // one whose allowed_menus would grant anything.
    vi.mocked(useAuth).mockReturnValue({
      user: {
        id: "u1",
        email: "resident@test.com",
        full_name: "Morador",
        role: UserRole.RESIDENT,
        is_active: true,
        user_types: [TENANT_A_TYPE, TENANT_B_TYPE],
      },
      isAuthenticated: true,
      isLoading: false,
      login: vi.fn(),
      logout: vi.fn(),
    } as never);
    vi.mocked(useSimulation).mockReturnValue(notSimulating);
    // `GET /user-types/` is tenant-scoped, so acting in tenant A it returns
    // only tenant A's rows. The tenant-B id therefore matches no row and the
    // intersection in useMenuAccess grants nothing.
    vi.mocked(useUserTypes).mockReturnValue({ data: [TENANT_A_TYPE] } as never);

    const { result: tasks } = renderHook(() => useMenuAccess("tasks"));
    const { result: categories } = renderHook(() =>
      useMenuAccess("categories"),
    );

    expect(tasks.current).toBe(false);
    expect(categories.current).toBe(false);
  });

  it("the same UserType does grant the menu while acting in its own tenant", () => {
    // The negative above must not be vacuous: switch the scoped list to
    // tenant B's rows and the very same user gains the menu.
    vi.mocked(useAuth).mockReturnValue({
      user: {
        id: "u1",
        email: "resident@test.com",
        full_name: "Morador",
        role: UserRole.RESIDENT,
        is_active: true,
        user_types: [TENANT_A_TYPE, TENANT_B_TYPE],
      },
      isAuthenticated: true,
      isLoading: false,
      login: vi.fn(),
      logout: vi.fn(),
    } as never);
    vi.mocked(useSimulation).mockReturnValue(notSimulating);
    vi.mocked(useUserTypes).mockReturnValue({ data: [TENANT_B_TYPE] } as never);

    const { result } = renderHook(() => useMenuAccess("tasks"));

    expect(result.current).toBe(true);
  });
});
