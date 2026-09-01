import { render, within } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import type { FC } from "react";
import * as AuthHook from "../context/AuthContext";
import * as TenantHook from "../context/useTenant";
import * as SimulationHook from "../context/SimulationContext";
import {
  useAdminCapability,
  useEffectiveAdminCapability,
} from "../context/useAdminCapability";
import { UserRole, type User } from "../../../types/auth";

vi.mock("../../../hooks/useUserTypes", () => ({
  useUserTypes: vi.fn(() => ({ data: [] })),
}));

const TENANT_A = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa";

const mockAuth = (user: Partial<User>) => {
  vi.spyOn(AuthHook, "useAuth").mockReturnValue({
    user: user as User,
    isAuthenticated: true,
    isLoading: false,
    login: vi.fn() as never,
    logout: vi.fn(),
  });
};

const mockTenant = (isActingTenantAdmin: boolean) => {
  vi.spyOn(TenantHook, "useTenant").mockReturnValue({
    tenants: [],
    actingTenantId: TENANT_A,
    actingTenant: null,
    isActingTenantAdmin,
    isLoading: false,
    setActingTenant: vi.fn(),
  });
};

const mockSimulation = (simulatedRole: UserRole | null) => {
  vi.spyOn(SimulationHook, "useSimulation").mockReturnValue({
    simulatedRole,
    simulatedUserTypeIds: [],
    isSimulating: simulatedRole !== null,
    setSimulatedRole: vi.fn(),
    setSimulatedUserTypeIds: vi.fn(),
    stopSimulation: vi.fn(),
  });
};

const Probe: FC = () => (
  <div>
    <span data-testid="real">{String(useAdminCapability())}</span>
    <span data-testid="effective">{String(useEffectiveAdminCapability())}</span>
  </div>
);

/** Scoped to its own render, so a test may re-render under a new mock. */
const capabilities = () => {
  const view = render(<Probe />);
  const read = within(view.container);
  return {
    real: read.getByTestId("real").textContent,
    effective: read.getByTestId("effective").textContent,
  };
};

describe("useAdminCapability", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    mockSimulation(null);
  });

  it("grants the capability to a global ADMINISTRATOR in any tenant", () => {
    mockAuth({ id: "u1", role: UserRole.ADMINISTRATOR, tenants: [] });
    // Not a tenant_admin anywhere: the role alone must carry it.
    mockTenant(false);

    expect(capabilities()).toEqual({ real: "true", effective: "true" });
  });

  it("grants it to a tenant_admin only in the tenant that granted it", () => {
    mockAuth({ id: "u2", role: UserRole.RESIDENT });

    mockTenant(true);
    expect(capabilities()).toEqual({ real: "true", effective: "true" });

    // Same user, acting elsewhere: the capability is not a role and does not
    // travel with the identity.
    mockTenant(false);
    expect(capabilities()).toEqual({ real: "false", effective: "false" });
  });

  it("withholds the effective capability while a simulation is active", () => {
    // A real ADMINISTRATOR simulating DIRECTOR still sees no admin menu, but
    // route gating (the real variant) keeps working so they can end the
    // simulation.
    mockAuth({ id: "u3", role: UserRole.ADMINISTRATOR });
    mockTenant(true);
    mockSimulation(UserRole.DIRECTOR);

    expect(capabilities()).toEqual({ real: "true", effective: "false" });
  });
});
