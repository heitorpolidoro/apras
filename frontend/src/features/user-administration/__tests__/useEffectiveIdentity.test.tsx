import { renderHook } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { useEffectiveIdentity } from "../context/useEffectiveIdentity";
import { useAuth } from "../context/AuthContext";
import { useSimulation } from "../context/SimulationContext";
import type { Role, User } from "../../../types/auth";

/**
 * **Rewritten by IAM F5 (APRAS-49 §10.3), and this is the last slice where a
 * "byte-identical" claim is made about this file.**
 *
 * F4 preserved APRAS-35's real-vs-simulated split verbatim and kept this
 * module untouched as proof. It cannot stay untouched here: the hook lost
 * both its `role` field and its `useRoles()` query, because the enum is gone
 * and the role-implicit membership it used to fold in became a real
 * `user_role_link` row at migration time (`0033`, §7.2 step 2). What
 * survives is the **invariant**, and it is re-pinned rather than restated:
 *
 * * this hook is display-only and returns the *effective* ids;
 * * authorization reads the *real* set through `useCanAccess`, which imports
 *   neither this hook nor `useSimulation` —
 *   `ProtectedRoute.permissions.test.tsx::keeps route access on the real
 *   permission set while simulating` is the mechanical statement of that,
 *   and it keeps passing unchanged.
 */

vi.mock("../context/AuthContext", () => ({ useAuth: vi.fn() }));
vi.mock("../context/SimulationContext", () => ({ useSimulation: vi.fn() }));

const notSimulating = {
  simulatedRoleIds: [],
  isSimulating: false,
  setSimulatedRoleIds: vi.fn(),
  stopSimulation: vi.fn(),
};

const authAs = (roles?: Role[], extra: Partial<User> = {}) => {
  vi.mocked(useAuth).mockReturnValue({
    user: {
      id: "u1",
      email: "a@b.com",
      full_name: "A B",
      is_active: true,
      roles,
      ...extra,
    },
    isAuthenticated: true,
    isLoading: false,
    login: vi.fn(),
    logout: vi.fn(),
  } as never);
};

describe("useEffectiveIdentity", () => {
  it("returns the real user's role ids when not simulating", () => {
    authAs([{ id: "type-1", name: "Board" }]);
    vi.mocked(useSimulation).mockReturnValue(notSimulating);

    const { result } = renderHook(() => useEffectiveIdentity());

    expect(result.current).toEqual({ roleIds: ["type-1"], isSimulating: false });
  });

  it("returns every membership, including the historically-named row", () => {
    // The APRAS-9 "fold-in" this module used to test is gone: `Diretor
    // (papel)` is an ordinary membership now, indistinguishable from any
    // other, so there is nothing left to fold and nothing to deduplicate.
    authAs([
      { id: "role-director", name: "Diretor (papel)" },
      { id: "type-1", name: "Board" },
    ]);
    vi.mocked(useSimulation).mockReturnValue(notSimulating);

    const { result } = renderHook(() => useEffectiveIdentity());

    expect(result.current.roleIds).toEqual(["role-director", "type-1"]);
  });

  it("returns an empty list for a user with no memberships", () => {
    authAs(undefined, { is_superuser: true });
    vi.mocked(useSimulation).mockReturnValue(notSimulating);

    const { result } = renderHook(() => useEffectiveIdentity());

    expect(result.current).toEqual({ roleIds: [], isSimulating: false });
  });

  it("returns the simulated ids when simulating, ignoring the real user", () => {
    authAs([{ id: "real-1", name: "Real" }], { is_superuser: true });
    vi.mocked(useSimulation).mockReturnValue({
      simulatedRoleIds: ["type-9"],
      isSimulating: true,
      setSimulatedRoleIds: vi.fn(),
      stopSimulation: vi.fn(),
    });

    const { result } = renderHook(() => useEffectiveIdentity());

    expect(result.current).toEqual({ roleIds: ["type-9"], isSimulating: true });
  });

  it("has no query of its own: the memberships come from `useAuth`", () => {
    // The hook used to call `useRoles()` to resolve the role-implicit
    // membership. Deleting that query is what makes this hook a pure
    // function of two contexts, and it is why nothing here mocks it.
    authAs([{ id: "type-1", name: "Board" }]);
    vi.mocked(useSimulation).mockReturnValue(notSimulating);

    const { result, rerender } = renderHook(() => useEffectiveIdentity());
    const first = result.current.roleIds;
    rerender();

    expect(result.current.roleIds).toEqual(first);
  });
});
