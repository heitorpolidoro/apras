import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import SimulationControls from "../components/SimulationControls";
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

describe("SimulationControls", () => {
  beforeEach(() => {
    vi.mocked(useRoles).mockReturnValue({
      data: [{ id: "type-1", name: "Board Member" }],
    } as any); // skipcq: JS-0323
  });

  it("renders the toggle button and no panel by default", () => {
    vi.mocked(useSimulation).mockReturnValue(makeSimulation());
    render(<SimulationControls />);
    expect(screen.getByText("Simular")).toBeInTheDocument();
    expect(screen.queryByText("Papel")).not.toBeInTheDocument();
  });

  it("opens the panel with role and Role controls when the toggle is clicked", () => {
    vi.mocked(useSimulation).mockReturnValue(makeSimulation());
    render(<SimulationControls />);
    fireEvent.click(screen.getByText("Simular"));
    expect(screen.getByText("Papéis")).toBeInTheDocument();
  });

  it("does not show 'Encerrar simulação' before a role is picked", () => {
    vi.mocked(useSimulation).mockReturnValue(makeSimulation());
    render(<SimulationControls />);
    fireEvent.click(screen.getByText("Simular"));
    expect(screen.queryByText("Encerrar simulação")).not.toBeInTheDocument();
  });

  it("renders an empty multi-select while the role list is still loading", () => {
    vi.mocked(useSimulation).mockReturnValue(makeSimulation());
    vi.mocked(useRoles).mockReturnValue({ data: undefined } as any); // skipcq: JS-0323

    render(<SimulationControls />);
    fireEvent.click(screen.getByText("Simular"));

    expect(screen.getByText("Papéis")).toBeInTheDocument();
  });

  it("offers every role of the tenant, not a hard-coded three (§10.2)", () => {
    // `SIMULATABLE_ROLES` was `[DIRECTOR, MANAGER, GUEST]` — the enum values
    // an administrator was allowed to preview. IAM F5 replaced it with the
    // rows from `useRoles()`, which is strictly more and needs no second
    // vocabulary.
    vi.mocked(useSimulation).mockReturnValue(makeSimulation());
    render(<SimulationControls />);
    fireEvent.click(screen.getByText("Simular"));

    expect(screen.queryByLabelText("Papel")).not.toBeInTheDocument();
    expect(screen.getByText("Papéis")).toBeInTheDocument();
  });

  it("shows 'Encerrar simulação' once a role is active and calls stopSimulation when clicked", () => {
    const stopSimulation = vi.fn();
    vi.mocked(useSimulation).mockReturnValue(
      makeSimulation({
        isSimulating: true,
        stopSimulation,
      }),
    );
    render(<SimulationControls />);
    fireEvent.click(screen.getByText("Simular"));
    fireEvent.click(screen.getByText("Encerrar simulação"));
    expect(stopSimulation).toHaveBeenCalledOnce();
  });

  it("passes the selected Role ids through to setSimulatedRoleIds", () => {
    const setSimulatedRoleIds = vi.fn();
    vi.mocked(useSimulation).mockReturnValue(
      makeSimulation({ setSimulatedRoleIds }),
    );
    render(<SimulationControls />);
    fireEvent.click(screen.getByText("Simular"));
    fireEvent.click(screen.getByRole("button", { name: /Selecionar papéis/i }));
    fireEvent.click(screen.getByRole("checkbox"));
    expect(setSimulatedRoleIds).toHaveBeenCalledWith(["type-1"]);
  });
});
