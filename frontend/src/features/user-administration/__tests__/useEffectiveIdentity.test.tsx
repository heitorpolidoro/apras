import { renderHook } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { useEffectiveIdentity } from "../context/useEffectiveIdentity";
import { useAuth } from "../context/AuthContext";
import { useSimulation } from "../context/SimulationContext";
import { UserRole } from "../../../types/auth";

vi.mock("../context/AuthContext", () => ({
  useAuth: vi.fn(),
}));

vi.mock("../context/SimulationContext", () => ({
  useSimulation: vi.fn(),
}));

describe("useEffectiveIdentity", () => {
  it("returns the real user's role and UserType ids when not simulating", () => {
    vi.mocked(useAuth).mockReturnValue({
      user: {
        id: "u1",
        email: "a@b.com",
        full_name: "A B",
        role: UserRole.DIRECTOR,
        is_active: true,
        user_types: [{ id: "type-1", name: "Board" }],
      },
      isAuthenticated: true,
      isLoading: false,
      login: vi.fn(),
      logout: vi.fn(),
    } as any); // skipcq: JS-0323
    vi.mocked(useSimulation).mockReturnValue({
      simulatedRole: null,
      simulatedUserTypeIds: [],
      isSimulating: false,
      setSimulatedRole: vi.fn(),
      setSimulatedUserTypeIds: vi.fn(),
      stopSimulation: vi.fn(),
    });

    const { result } = renderHook(() => useEffectiveIdentity());

    expect(result.current).toEqual({
      role: UserRole.DIRECTOR,
      userTypeIds: ["type-1"],
      isSimulating: false,
    });
  });

  it("returns an empty userTypeIds array when the real user has no user_types", () => {
    vi.mocked(useAuth).mockReturnValue({
      user: {
        id: "u1",
        email: "a@b.com",
        full_name: "A B",
        role: UserRole.ADMINISTRATOR,
        is_active: true,
      },
      isAuthenticated: true,
      isLoading: false,
      login: vi.fn(),
      logout: vi.fn(),
    } as any); // skipcq: JS-0323
    vi.mocked(useSimulation).mockReturnValue({
      simulatedRole: null,
      simulatedUserTypeIds: [],
      isSimulating: false,
      setSimulatedRole: vi.fn(),
      setSimulatedUserTypeIds: vi.fn(),
      stopSimulation: vi.fn(),
    });

    const { result } = renderHook(() => useEffectiveIdentity());
    expect(result.current.userTypeIds).toEqual([]);
    expect(result.current.role).toBe(UserRole.ADMINISTRATOR);
  });

  it("returns the simulated role and UserType ids when simulating, ignoring the real user", () => {
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
      simulatedRole: UserRole.MANAGER,
      simulatedUserTypeIds: ["type-9"],
      isSimulating: true,
      setSimulatedRole: vi.fn(),
      setSimulatedUserTypeIds: vi.fn(),
      stopSimulation: vi.fn(),
    });

    const { result } = renderHook(() => useEffectiveIdentity());

    expect(result.current).toEqual({
      role: UserRole.MANAGER,
      userTypeIds: ["type-9"],
      isSimulating: true,
    });
  });

  it("falls back to the real user when isSimulating is true but simulatedRole is somehow null", () => {
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
      simulatedRole: null,
      simulatedUserTypeIds: [],
      isSimulating: true,
      setSimulatedRole: vi.fn(),
      setSimulatedUserTypeIds: vi.fn(),
      stopSimulation: vi.fn(),
    });

    const { result } = renderHook(() => useEffectiveIdentity());
    expect(result.current.role).toBe(UserRole.ADMINISTRATOR);
    expect(result.current.isSimulating).toBe(false);
  });
});
