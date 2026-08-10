import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import SimulationBanner from "../components/SimulationBanner";
import { useSimulation } from "../context/SimulationContext";
import { useUserTypes } from "../../../hooks/useUserTypes";
import { UserRole } from "../../../types/auth";

vi.mock("../context/SimulationContext", () => ({
  useSimulation: vi.fn(),
}));

vi.mock("../../../hooks/useUserTypes", () => ({
  useUserTypes: vi.fn(),
}));

const makeSimulation = (overrides: Partial<ReturnType<typeof useSimulation>> = {}) => ({
  simulatedRole: null,
  simulatedUserTypeIds: [],
  isSimulating: false,
  setSimulatedRole: vi.fn(),
  setSimulatedUserTypeIds: vi.fn(),
  stopSimulation: vi.fn(),
  ...overrides,
});

describe("SimulationBanner", () => {
  it("renders nothing when not simulating", () => {
    vi.mocked(useSimulation).mockReturnValue(makeSimulation());
    vi.mocked(useUserTypes).mockReturnValue({ data: [] } as any); // skipcq: JS-0323
    const { container } = render(<SimulationBanner />);
    expect(container.firstChild).toBeNull();
  });

  it("shows the simulated role and UserType names once simulating", () => {
    vi.mocked(useSimulation).mockReturnValue(
      makeSimulation({
        simulatedRole: UserRole.MANAGER,
        simulatedUserTypeIds: ["type-1"],
        isSimulating: true,
      }),
    );
    vi.mocked(useUserTypes).mockReturnValue({
      data: [{ id: "type-1", name: "Board Member" }],
    } as any); // skipcq: JS-0323

    render(<SimulationBanner />);
    expect(
      screen.getByText("Visualizando como: Gerente (Board Member)"),
    ).toBeInTheDocument();
  });

  it("shows the 'no user type' fallback when no UserTypes are selected", () => {
    vi.mocked(useSimulation).mockReturnValue(
      makeSimulation({ simulatedRole: UserRole.GUEST, isSimulating: true }),
    );
    vi.mocked(useUserTypes).mockReturnValue({ data: [] } as any); // skipcq: JS-0323

    render(<SimulationBanner />);
    expect(
      screen.getByText("Visualizando como: Convidado (nenhum tipo de usuário)"),
    ).toBeInTheDocument();
  });

  it("calls stopSimulation when 'Encerrar simulação' is clicked", () => {
    const stopSimulation = vi.fn();
    vi.mocked(useSimulation).mockReturnValue(
      makeSimulation({
        simulatedRole: UserRole.DIRECTOR,
        isSimulating: true,
        stopSimulation,
      }),
    );
    vi.mocked(useUserTypes).mockReturnValue({ data: [] } as any); // skipcq: JS-0323

    render(<SimulationBanner />);
    fireEvent.click(screen.getByText("Encerrar simulação"));
    expect(stopSimulation).toHaveBeenCalledOnce();
  });
});
