import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import SimulationControls from "../components/SimulationControls";
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

describe("SimulationControls", () => {
  beforeEach(() => {
    vi.mocked(useUserTypes).mockReturnValue({
      data: [{ id: "type-1", name: "Board Member" }],
    } as any); // skipcq: JS-0323
  });

  it("renders the toggle button and no panel by default", () => {
    vi.mocked(useSimulation).mockReturnValue(makeSimulation());
    render(<SimulationControls />);
    expect(screen.getByText("Simular")).toBeInTheDocument();
    expect(screen.queryByText("Papel")).not.toBeInTheDocument();
  });

  it("opens the panel with role and UserType controls when the toggle is clicked", () => {
    vi.mocked(useSimulation).mockReturnValue(makeSimulation());
    render(<SimulationControls />);
    fireEvent.click(screen.getByText("Simular"));
    expect(screen.getByText("Papel")).toBeInTheDocument();
    expect(screen.getByText("Tipos de Usuário")).toBeInTheDocument();
  });

  it("does not show 'Encerrar simulação' before a role is picked", () => {
    vi.mocked(useSimulation).mockReturnValue(makeSimulation());
    render(<SimulationControls />);
    fireEvent.click(screen.getByText("Simular"));
    expect(screen.queryByText("Encerrar simulação")).not.toBeInTheDocument();
  });

  it("calls setSimulatedRole when a role is selected", () => {
    const setSimulatedRole = vi.fn();
    vi.mocked(useSimulation).mockReturnValue(
      makeSimulation({ setSimulatedRole }),
    );
    render(<SimulationControls />);
    fireEvent.click(screen.getByText("Simular"));
    fireEvent.change(screen.getByLabelText("Papel"), {
      target: { value: UserRole.MANAGER },
    });
    expect(setSimulatedRole).toHaveBeenCalledWith(UserRole.MANAGER);
  });

  it("calls setSimulatedRole with null when the placeholder option is reselected", () => {
    const setSimulatedRole = vi.fn();
    vi.mocked(useSimulation).mockReturnValue(
      makeSimulation({ simulatedRole: UserRole.MANAGER, isSimulating: true, setSimulatedRole }),
    );
    render(<SimulationControls />);
    fireEvent.click(screen.getByText("Simular"));
    fireEvent.change(screen.getByLabelText("Papel"), {
      target: { value: "" },
    });
    expect(setSimulatedRole).toHaveBeenCalledWith(null);
  });

  it("shows 'Encerrar simulação' once a role is active and calls stopSimulation when clicked", () => {
    const stopSimulation = vi.fn();
    vi.mocked(useSimulation).mockReturnValue(
      makeSimulation({
        simulatedRole: UserRole.GUEST,
        isSimulating: true,
        stopSimulation,
      }),
    );
    render(<SimulationControls />);
    fireEvent.click(screen.getByText("Simular"));
    fireEvent.click(screen.getByText("Encerrar simulação"));
    expect(stopSimulation).toHaveBeenCalledOnce();
  });

  it("passes the selected UserType ids through to setSimulatedUserTypeIds", () => {
    const setSimulatedUserTypeIds = vi.fn();
    vi.mocked(useSimulation).mockReturnValue(
      makeSimulation({ setSimulatedUserTypeIds }),
    );
    render(<SimulationControls />);
    fireEvent.click(screen.getByText("Simular"));
    fireEvent.click(screen.getByRole("button", { name: /Selecionar tipos/i }));
    fireEvent.click(screen.getByRole("checkbox"));
    expect(setSimulatedUserTypeIds).toHaveBeenCalledWith(["type-1"]);
  });
});
