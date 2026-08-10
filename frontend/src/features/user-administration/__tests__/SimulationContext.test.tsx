import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { SimulationProvider, useSimulation } from "../context/SimulationContext";
import { UserRole } from "../../../types/auth";
import { getSimulationState } from "../context/simulationState";

const TestComponent = () => {
  const {
    simulatedRole,
    simulatedUserTypeIds,
    isSimulating,
    setSimulatedRole,
    setSimulatedUserTypeIds,
    stopSimulation,
  } = useSimulation();

  return (
    <div>
      <div data-testid="role">{simulatedRole ?? "none"}</div>
      <div data-testid="user-types">{simulatedUserTypeIds.join(",")}</div>
      <div data-testid="is-simulating">{String(isSimulating)}</div>
      <button onClick={() => setSimulatedRole(UserRole.MANAGER)}>
        Simulate Manager
      </button>
      <button onClick={() => setSimulatedRole(UserRole.GUEST)}>
        Simulate Guest
      </button>
      <button onClick={() => setSimulatedUserTypeIds(["type-1", "type-2"])}>
        Set UserTypes
      </button>
      <button onClick={stopSimulation}>Stop</button>
    </div>
  );
};

describe("SimulationContext", () => {
  beforeEach(() => {
    sessionStorage.clear();
  });

  it("starts with no simulated role and isSimulating false", () => {
    render(
      <SimulationProvider>
        <TestComponent />
      </SimulationProvider>,
    );
    expect(screen.getByTestId("role").textContent).toBe("none");
    expect(screen.getByTestId("is-simulating").textContent).toBe("false");
  });

  it("activates simulation once a role is picked", async () => {
    render(
      <SimulationProvider>
        <TestComponent />
      </SimulationProvider>,
    );
    fireEvent.click(screen.getByText("Simulate Manager"));
    await waitFor(() =>
      expect(screen.getByTestId("role").textContent).toBe(UserRole.MANAGER),
    );
    expect(screen.getByTestId("is-simulating").textContent).toBe("true");
  });

  it("updates the UserType id selection independently of the role", async () => {
    render(
      <SimulationProvider>
        <TestComponent />
      </SimulationProvider>,
    );
    fireEvent.click(screen.getByText("Set UserTypes"));
    await waitFor(() =>
      expect(screen.getByTestId("user-types").textContent).toBe(
        "type-1,type-2",
      ),
    );
  });

  it("stopSimulation clears both the role and the UserType selection", async () => {
    render(
      <SimulationProvider>
        <TestComponent />
      </SimulationProvider>,
    );
    fireEvent.click(screen.getByText("Simulate Manager"));
    fireEvent.click(screen.getByText("Set UserTypes"));
    await waitFor(() =>
      expect(screen.getByTestId("is-simulating").textContent).toBe("true"),
    );

    fireEvent.click(screen.getByText("Stop"));
    await waitFor(() =>
      expect(screen.getByTestId("is-simulating").textContent).toBe("false"),
    );
    expect(screen.getByTestId("role").textContent).toBe("none");
    expect(screen.getByTestId("user-types").textContent).toBe("");
  });

  it("persists the simulated role and UserTypes to sessionStorage", async () => {
    render(
      <SimulationProvider>
        <TestComponent />
      </SimulationProvider>,
    );
    fireEvent.click(screen.getByText("Simulate Guest"));
    fireEvent.click(screen.getByText("Set UserTypes"));

    await waitFor(() =>
      expect(sessionStorage.getItem("simulation.role")).toBe(UserRole.GUEST),
    );
    expect(sessionStorage.getItem("simulation.userTypeIds")).toBe(
      JSON.stringify(["type-1", "type-2"]),
    );
  });

  it("restores a previously persisted simulation on mount", () => {
    sessionStorage.setItem("simulation.role", UserRole.DIRECTOR);
    sessionStorage.setItem("simulation.userTypeIds", JSON.stringify(["type-9"]));

    render(
      <SimulationProvider>
        <TestComponent />
      </SimulationProvider>,
    );

    expect(screen.getByTestId("role").textContent).toBe(UserRole.DIRECTOR);
    expect(screen.getByTestId("user-types").textContent).toBe("type-9");
    expect(screen.getByTestId("is-simulating").textContent).toBe("true");
  });

  it("treats an invalid persisted role as not simulating rather than throwing", () => {
    sessionStorage.setItem("simulation.role", "NOT_A_REAL_ROLE");

    render(
      <SimulationProvider>
        <TestComponent />
      </SimulationProvider>,
    );

    expect(screen.getByTestId("role").textContent).toBe("none");
    expect(screen.getByTestId("is-simulating").textContent).toBe("false");
  });

  it("treats malformed persisted UserType ids as an empty selection", () => {
    sessionStorage.setItem("simulation.userTypeIds", "not-json");

    render(
      <SimulationProvider>
        <TestComponent />
      </SimulationProvider>,
    );

    expect(screen.getByTestId("user-types").textContent).toBe("");
  });

  it("mirrors isSimulating into the module-level simulation state singleton", async () => {
    render(
      <SimulationProvider>
        <TestComponent />
      </SimulationProvider>,
    );
    expect(getSimulationState().isSimulating).toBe(false);

    fireEvent.click(screen.getByText("Simulate Manager"));
    await waitFor(() => expect(getSimulationState().isSimulating).toBe(true));

    fireEvent.click(screen.getByText("Stop"));
    await waitFor(() => expect(getSimulationState().isSimulating).toBe(false));
  });

  it("throws when useSimulation is used outside a SimulationProvider", () => {
    const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    expect(() => render(<TestComponent />)).toThrow(
      "useSimulation must be used within a SimulationProvider",
    );
    consoleSpy.mockRestore();
  });
});
