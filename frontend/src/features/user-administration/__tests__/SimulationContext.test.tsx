import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, beforeEach, vi } from "vitest";
import { SimulationProvider, useSimulation } from "../context/SimulationContext";
import { getSimulationState } from "../context/simulationState";

/**
 * IAM F5 (APRAS-49 §10.3) deleted `simulatedRole`: there is no enum left to
 * simulate, and a simulation is now exactly a **set of roles**.
 * `isSimulating` therefore became "at least one role is selected" rather than
 * "a role value has been picked" — the same statement in the model that
 * exists, and the reason the `simulation.role` storage key is gone with it.
 */

const TestComponent = () => {
  const { simulatedRoleIds, isSimulating, setSimulatedRoleIds, stopSimulation } =
    useSimulation();

  return (
    <div>
      <div data-testid="roles">{simulatedRoleIds.join(",")}</div>
      <div data-testid="is-simulating">{String(isSimulating)}</div>
      <button onClick={() => setSimulatedRoleIds(["type-1", "type-2"])}>
        Set Roles
      </button>
      <button onClick={() => setSimulatedRoleIds([])}>Clear Roles</button>
      <button onClick={stopSimulation}>Stop</button>
    </div>
  );
};

const renderProvider = () =>
  render(
    <SimulationProvider>
      <TestComponent />
    </SimulationProvider>,
  );

describe("SimulationContext", () => {
  beforeEach(() => {
    sessionStorage.clear();
  });

  it("starts with no simulated roles and isSimulating false", () => {
    renderProvider();

    expect(screen.getByTestId("roles").textContent).toBe("");
    expect(screen.getByTestId("is-simulating").textContent).toBe("false");
  });

  it("activates simulation once at least one role is selected", async () => {
    renderProvider();

    fireEvent.click(screen.getByText("Set Roles"));

    await waitFor(() =>
      expect(screen.getByTestId("roles").textContent).toBe("type-1,type-2"),
    );
    expect(screen.getByTestId("is-simulating").textContent).toBe("true");
  });

  it("deactivates simulation when the selection is emptied", async () => {
    renderProvider();

    fireEvent.click(screen.getByText("Set Roles"));
    await waitFor(() =>
      expect(screen.getByTestId("is-simulating").textContent).toBe("true"),
    );

    fireEvent.click(screen.getByText("Clear Roles"));
    await waitFor(() =>
      expect(screen.getByTestId("is-simulating").textContent).toBe("false"),
    );
  });

  it("stopSimulation clears the selection", async () => {
    renderProvider();

    fireEvent.click(screen.getByText("Set Roles"));
    await waitFor(() =>
      expect(screen.getByTestId("is-simulating").textContent).toBe("true"),
    );

    fireEvent.click(screen.getByText("Stop"));

    await waitFor(() =>
      expect(screen.getByTestId("is-simulating").textContent).toBe("false"),
    );
    expect(screen.getByTestId("roles").textContent).toBe("");
  });

  it("persists the selection to sessionStorage, and only that key", async () => {
    renderProvider();

    fireEvent.click(screen.getByText("Set Roles"));

    await waitFor(() =>
      expect(sessionStorage.getItem("simulation.roleIds")).toBe(
        JSON.stringify(["type-1", "type-2"]),
      ),
    );
    expect(sessionStorage.getItem("simulation.role")).toBeNull();
  });

  it("restores a previously persisted simulation on mount", () => {
    sessionStorage.setItem("simulation.roleIds", JSON.stringify(["type-9"]));

    renderProvider();

    expect(screen.getByTestId("roles").textContent).toBe("type-9");
    expect(screen.getByTestId("is-simulating").textContent).toBe("true");
  });

  it("treats a malformed persisted selection as not simulating", () => {
    sessionStorage.setItem("simulation.roleIds", "NOT JSON");

    renderProvider();

    expect(screen.getByTestId("roles").textContent).toBe("");
    expect(screen.getByTestId("is-simulating").textContent).toBe("false");
  });

  it("ignores non-string entries in a persisted selection", () => {
    sessionStorage.setItem("simulation.roleIds", JSON.stringify(["ok", 7, null]));

    renderProvider();

    expect(screen.getByTestId("roles").textContent).toBe("ok");
  });

  it("ignores a persisted value that is valid JSON but not an array", () => {
    // `JSON.parse` succeeds here, so the `catch` never fires: the shape check
    // is what stops `"a string".filter` from throwing.
    sessionStorage.setItem("simulation.roleIds", JSON.stringify({ a: 1 }));

    renderProvider();

    expect(screen.getByTestId("roles").textContent).toBe("");
    expect(screen.getByTestId("is-simulating").textContent).toBe("false");
  });

  it("refuses to be used outside a SimulationProvider", () => {
    // The guard the provider exists to make unnecessary: a component that
    // forgets the provider must fail loudly at the hook, not silently read
    // `undefined.isSimulating` somewhere far away.
    const Orphan = () => {
      useSimulation();
      return null;
    };
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});

    expect(() => render(<Orphan />)).toThrow(
      "useSimulation must be used within a SimulationProvider",
    );

    spy.mockRestore();
  });

  it("mirrors the flag for the Axios interceptor, which has no React context", async () => {
    renderProvider();

    expect(getSimulationState().isSimulating).toBe(false);

    fireEvent.click(screen.getByText("Set Roles"));
    await waitFor(() => expect(getSimulationState().isSimulating).toBe(true));

    fireEvent.click(screen.getByText("Stop"));
    await waitFor(() => expect(getSimulationState().isSimulating).toBe(false));
  });
});
