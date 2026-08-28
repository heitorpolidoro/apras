import { renderHook } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { useEffectiveIdentity } from "../context/useEffectiveIdentity";
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
    vi.mocked(useSimulation).mockReturnValue(notSimulating);
    vi.mocked(useUserTypes).mockReturnValue({ data: [] } as any); // skipcq: JS-0323

    const { result } = renderHook(() => useEffectiveIdentity());

    expect(result.current).toEqual({
      role: UserRole.DIRECTOR,
      userTypeIds: ["type-1"],
      isSimulating: false,
    });
  });

  it("returns an empty userTypeIds array when the real user has no user_types and no role-type exists", () => {
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
    vi.mocked(useSimulation).mockReturnValue(notSimulating);
    vi.mocked(useUserTypes).mockReturnValue({ data: [] } as any); // skipcq: JS-0323

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
    vi.mocked(useUserTypes).mockReturnValue({ data: [] } as any); // skipcq: JS-0323

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
    vi.mocked(useUserTypes).mockReturnValue({ data: [] } as any); // skipcq: JS-0323

    const { result } = renderHook(() => useEffectiveIdentity());
    expect(result.current.role).toBe(UserRole.ADMINISTRATOR);
    expect(result.current.isSimulating).toBe(false);
  });

  // ── APRAS-9: role-type fold-in ────────────────────────────────────────

  it("folds in the role-matching UserType id for the real user, with zero explicit UserTypes", () => {
    vi.mocked(useAuth).mockReturnValue({
      user: {
        id: "u1",
        email: "director@b.com",
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
      data: [
        { id: "role-type-director", name: "Diretor (papel)", allowed_menus: [], role: "DIRECTOR" },
        { id: "role-type-manager", name: "Gerente (papel)", allowed_menus: [], role: "MANAGER" },
      ],
    } as any); // skipcq: JS-0323

    const { result } = renderHook(() => useEffectiveIdentity());

    expect(result.current.userTypeIds).toEqual(["role-type-director"]);
  });

  it("unions the role-type id with explicit UserType ids for the real user, without duplicates", () => {
    vi.mocked(useAuth).mockReturnValue({
      user: {
        id: "u1",
        email: "director@b.com",
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
      data: [
        { id: "type-1", name: "Board", allowed_menus: [] },
        { id: "role-type-director", name: "Diretor (papel)", allowed_menus: [], role: "DIRECTOR" },
      ],
    } as any); // skipcq: JS-0323

    const { result } = renderHook(() => useEffectiveIdentity());

    expect(new Set(result.current.userTypeIds)).toEqual(
      new Set(["type-1", "role-type-director"]),
    );
    expect(result.current.userTypeIds.length).toBe(2);
  });

  it("folds in the role-matching UserType id for a simulated role, with zero simulated UserTypes", () => {
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
      simulatedUserTypeIds: [],
      isSimulating: true,
      setSimulatedRole: vi.fn(),
      setSimulatedUserTypeIds: vi.fn(),
      stopSimulation: vi.fn(),
    });
    vi.mocked(useUserTypes).mockReturnValue({
      data: [
        { id: "role-type-manager", name: "Gerente (papel)", allowed_menus: [], role: "MANAGER" },
      ],
    } as any); // skipcq: JS-0323

    const { result } = renderHook(() => useEffectiveIdentity());

    expect(result.current).toEqual({
      role: UserRole.MANAGER,
      userTypeIds: ["role-type-manager"],
      isSimulating: true,
    });
  });
});
