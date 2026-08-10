import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  setSimulationState,
  getSimulationState,
  registerSimulationReset,
  triggerSimulationReset,
} from "../context/simulationState";

describe("simulationState", () => {
  beforeEach(() => {
    setSimulationState({ isSimulating: false });
    registerSimulationReset(null);
  });

  it("defaults to not simulating", () => {
    expect(getSimulationState()).toEqual({ isSimulating: false });
  });

  it("mirrors whatever state is written to it", () => {
    setSimulationState({ isSimulating: true });
    expect(getSimulationState()).toEqual({ isSimulating: true });
  });

  it("does nothing when triggerSimulationReset is called with no handler registered", () => {
    expect(() => triggerSimulationReset()).not.toThrow();
  });

  it("invokes the registered reset handler when triggered", () => {
    const handler = vi.fn();
    registerSimulationReset(handler);
    triggerSimulationReset();
    expect(handler).toHaveBeenCalledOnce();
  });

  it("stops invoking a handler once it has been unregistered", () => {
    const handler = vi.fn();
    registerSimulationReset(handler);
    registerSimulationReset(null);
    triggerSimulationReset();
    expect(handler).not.toHaveBeenCalled();
  });
});
