import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import SimulationBanner from "../components/SimulationBanner";
import { useSimulation } from "../context/SimulationContext";
import { useRoles } from "../../../hooks/useRoles";

vi.mock("../context/SimulationContext", () => ({
  useSimulation: vi.fn(),
}));

vi.mock("../../../hooks/useRoles", () => ({
  useRoles: vi.fn(),
}));

const makeSimulation = (overrides: Partial<ReturnType<typeof useSimulation>> = {}) => ({
  simulatedRoleIds: [],
  isSimulating: false,
  setSimulatedRoleIds: vi.fn(),
  stopSimulation: vi.fn(),
  ...overrides,
});

describe("SimulationBanner", () => {
  it("renders nothing when not simulating", () => {
    vi.mocked(useSimulation).mockReturnValue(makeSimulation());
    vi.mocked(useRoles).mockReturnValue({ data: [] } as any); // skipcq: JS-0323
    const { container } = render(<SimulationBanner />);
    expect(container.firstChild).toBeNull();
  });

  it("shows the simulated role names once simulating", () => {
    vi.mocked(useSimulation).mockReturnValue(
      makeSimulation({
        simulatedRoleIds: ["type-1"],
        isSimulating: true,
      }),
    );
    vi.mocked(useRoles).mockReturnValue({
      data: [{ id: "type-1", name: "Board Member" }],
    } as any); // skipcq: JS-0323

    render(<SimulationBanner />);
    // IAM F5 (APRAS-49 §10.3): `simulation.bannerLabel` lost its
    // `{{role}}` interpolation with the enum. A simulation *is* the role
    // names it selects, so there is nothing else to name.
    expect(
      screen.getByText("Visualizando como: Board Member", { exact: false }),
    ).toBeInTheDocument();
  });

  it("shows the 'no role' fallback when no Roles are selected", () => {
    vi.mocked(useSimulation).mockReturnValue(
      makeSimulation({ isSimulating: true }),
    );
    vi.mocked(useRoles).mockReturnValue({ data: [] } as any); // skipcq: JS-0323

    render(<SimulationBanner />);
    expect(
      screen.getByText("Visualizando como: nenhum papel", { exact: false }),
    ).toBeInTheDocument();
  });

  it("falls back to the 'no role' label while the role list is still loading", () => {
    // `useRoles()` may not have settled when the banner first paints; a
    // simulation must still announce itself rather than crash or show a
    // half-rendered label.
    vi.mocked(useSimulation).mockReturnValue(
      makeSimulation({ simulatedRoleIds: ["type-1"], isSimulating: true }),
    );
    vi.mocked(useRoles).mockReturnValue({ data: undefined } as any); // skipcq: JS-0323

    render(<SimulationBanner />);

    expect(
      screen.getByText("Visualizando como: nenhum papel", { exact: false }),
    ).toBeInTheDocument();
  });

  it("calls stopSimulation when 'Encerrar simulação' is clicked", () => {
    const stopSimulation = vi.fn();
    vi.mocked(useSimulation).mockReturnValue(
      makeSimulation({
        isSimulating: true,
        stopSimulation,
      }),
    );
    vi.mocked(useRoles).mockReturnValue({ data: [] } as any); // skipcq: JS-0323

    render(<SimulationBanner />);
    fireEvent.click(screen.getByText("Encerrar simulação"));
    expect(stopSimulation).toHaveBeenCalledOnce();
  });
});
