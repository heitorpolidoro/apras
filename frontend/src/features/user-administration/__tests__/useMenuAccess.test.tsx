import { renderHook } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { useMenuAccess } from "../context/useMenuAccess";
import { useAuth } from "../context/AuthContext";
import { useSimulation } from "../context/SimulationContext";
import { useUserTypes } from "../../../hooks/useUserTypes";
import { UserRole } from "../../../types/auth";

vi.mock("../context/AuthContext", () => ({
  useAuth: vi.fn(),
}));

vi.mock("../context/SimulationContext", () => ({
  useSimulation: vi.fn(),
}));

vi.mock("../../../hooks/useUserTypes", () => ({
  useUserTypes: vi.fn(),
}));

const notSimulating = {
  simulatedRole: null,
  simulatedUserTypeIds: [],
  isSimulating: false,
  setSimulatedRole: vi.fn(),
  setSimulatedUserTypeIds: vi.fn(),
  stopSimulation: vi.fn(),
};

describe("useMenuAccess", () => {
  it("returns true for ADMINISTRATOR regardless of UserTypes", () => {
    vi.mocked(useAuth).mockReturnValue({
      user: {
        id: "admin-1",
        email: "a@b.com",
        full_name: "Admin",
        role: UserRole.ADMINISTRATOR,
        is_active: true,
      },
      isAuthenticated: true,
      isLoading: false,
      login: vi.fn(),
      logout: vi.fn(),
    } as any); // skipcq: JS-0323
    vi.mocked(useSimulation).mockReturnValue(notSimulating);
    vi.mocked(useUserTypes).mockReturnValue({ data: [] } as any); // skipcq: JS-0323

    const { result } = renderHook(() => useMenuAccess("tasks"));
    expect(result.current).toBe(true);
  });

  it("returns true when a matching UserType grants the menu key", () => {
    vi.mocked(useAuth).mockReturnValue({
      user: {
        id: "u1",
        email: "a@b.com",
        full_name: "Director",
        role: UserRole.DIRECTOR,
        is_active: true,
        user_types: [{ id: "type-1", name: "Board" }],
      },
      isAuthenticated: true,
      isLoading: false,
      login: vi.fn(),
      logout: vi.fn(),
    } as any); // skipcq: JS-0323
    vi.mocked(useSimulation).mockReturnValue(notSimulating);
    vi.mocked(useUserTypes).mockReturnValue({
      data: [{ id: "type-1", name: "Board", allowed_menus: ["tasks"] }],
    } as any); // skipcq: JS-0323

    const { result } = renderHook(() => useMenuAccess("tasks"));
    expect(result.current).toBe(true);
  });

  it("returns false when no UserType grants the menu key", () => {
    vi.mocked(useAuth).mockReturnValue({
      user: {
        id: "u1",
        email: "a@b.com",
        full_name: "Director",
        role: UserRole.DIRECTOR,
        is_active: true,
        user_types: [{ id: "type-1", name: "Board" }],
      },
      isAuthenticated: true,
      isLoading: false,
      login: vi.fn(),
      logout: vi.fn(),
    } as any); // skipcq: JS-0323
    vi.mocked(useSimulation).mockReturnValue(notSimulating);
    vi.mocked(useUserTypes).mockReturnValue({
      data: [{ id: "type-1", name: "Board", allowed_menus: ["categories"] }],
    } as any); // skipcq: JS-0323

    const { result } = renderHook(() => useMenuAccess("tasks"));
    expect(result.current).toBe(false);
  });

  it("returns false when the user has zero UserTypes assigned", () => {
    vi.mocked(useAuth).mockReturnValue({
      user: {
        id: "u1",
        email: "a@b.com",
        full_name: "Director",
        role: UserRole.DIRECTOR,
        is_active: true,
      },
      isAuthenticated: true,
      isLoading: false,
      login: vi.fn(),
      logout: vi.fn(),
    } as any); // skipcq: JS-0323
    vi.mocked(useSimulation).mockReturnValue(notSimulating);
    vi.mocked(useUserTypes).mockReturnValue({
      data: [{ id: "type-1", name: "Board", allowed_menus: ["tasks"] }],
    } as any); // skipcq: JS-0323

    const { result } = renderHook(() => useMenuAccess("tasks"));
    expect(result.current).toBe(false);
  });

  it("returns false while UserTypes are still loading (data undefined)", () => {
    vi.mocked(useAuth).mockReturnValue({
      user: {
        id: "u1",
        email: "a@b.com",
        full_name: "Director",
        role: UserRole.DIRECTOR,
        is_active: true,
        user_types: [{ id: "type-1", name: "Board" }],
      },
      isAuthenticated: true,
      isLoading: false,
      login: vi.fn(),
      logout: vi.fn(),
    } as any); // skipcq: JS-0323
    vi.mocked(useSimulation).mockReturnValue(notSimulating);
    vi.mocked(useUserTypes).mockReturnValue({ data: undefined } as any); // skipcq: JS-0323

    const { result } = renderHook(() => useMenuAccess("tasks"));
    expect(result.current).toBe(false);
  });

  it("respects an active simulation, using the simulated identity", () => {
    vi.mocked(useAuth).mockReturnValue({
      user: {
        id: "admin-1",
        email: "admin@b.com",
        full_name: "Admin",
        role: UserRole.ADMINISTRATOR,
        is_active: true,
      },
      isAuthenticated: true,
      isLoading: false,
      login: vi.fn(),
      logout: vi.fn(),
    } as any); // skipcq: JS-0323
    vi.mocked(useSimulation).mockReturnValue({
      simulatedRole: UserRole.DIRECTOR,
      simulatedUserTypeIds: ["type-1"],
      isSimulating: true,
      setSimulatedRole: vi.fn(),
      setSimulatedUserTypeIds: vi.fn(),
      stopSimulation: vi.fn(),
    });
    vi.mocked(useUserTypes).mockReturnValue({
      data: [{ id: "type-1", name: "Board", allowed_menus: ["categories"] }],
    } as any); // skipcq: JS-0323

    // Simulated identity is DIRECTOR + type-1 (no "tasks"): denied, even
    // though the real user is an always-passing ADMINISTRATOR.
    const { result } = renderHook(() => useMenuAccess("tasks"));
    expect(result.current).toBe(false);
  });
});
