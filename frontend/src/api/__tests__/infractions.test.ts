import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  addContestation,
  addInfractionStage,
  closeCycle,
  createInfraction,
  createInfractionRule,
  deactivateInfractionRule,
  getCycleCloses,
  getInfraction,
  getInfractionRule,
  getInfractionRules,
  getInfractionSettings,
  getInfractions,
  getMyInfractions,
  getNextStep,
  promoteOccurrence,
  updateInfractionRule,
  writeInfractionPolicy,
  writeInfractionSettings,
} from "../infractions";
import apiClient from "../client";

vi.mock("../client", () => ({
  default: { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() },
}));

/**
 * The 18 routes, called once each.
 *
 * The point of this module is the *URL and verb* of every call: the module's
 * route ordering is a correctness requirement on the server (`/my-lots` and
 * `/cycles` must not be matched as a `{infraction_id}`), and a client that
 * spelled one of them differently would never reach the handler the parity
 * matrix measured.
 */
describe("infractions api client", () => {
  beforeEach(() => vi.clearAllMocks());

  it("reads and writes the rule catalogue", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: [] });
    await expect(getInfractionRules()).resolves.toEqual([]);
    expect(apiClient.get).toHaveBeenCalledWith("/infraction-rules");

    vi.mocked(apiClient.get).mockResolvedValue({ data: { id: "r-1" } });
    await expect(getInfractionRule("r-1")).resolves.toEqual({ id: "r-1" });
    expect(apiClient.get).toHaveBeenLastCalledWith("/infraction-rules/r-1");

    vi.mocked(apiClient.post).mockResolvedValue({ data: { id: "r-2" } });
    await createInfractionRule({
      article: "art. 1",
      origin: "ESTATUTO",
      description: "d",
      recidivism_window_days: 30,
    });
    expect(apiClient.post).toHaveBeenCalledWith("/infraction-rules", {
      article: "art. 1",
      origin: "ESTATUTO",
      description: "d",
      recidivism_window_days: 30,
    });

    vi.mocked(apiClient.put).mockResolvedValue({ data: { id: "r-1" } });
    await updateInfractionRule("r-1", { description: "x" });
    expect(apiClient.put).toHaveBeenCalledWith("/infraction-rules/r-1", {
      description: "x",
    });

    vi.mocked(apiClient.delete).mockResolvedValue({ data: undefined });
    await deactivateInfractionRule("r-1");
    expect(apiClient.delete).toHaveBeenCalledWith("/infraction-rules/r-1");

    await writeInfractionPolicy("r-1", [{ step_order: 1, action: "AVISO" }]);
    expect(apiClient.put).toHaveBeenLastCalledWith(
      "/infraction-rules/r-1/policy",
      { steps: [{ step_order: 1, action: "AVISO" }] },
    );
  });

  it("reads and writes the settings singleton", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: { condo_fee_amount: null, updated_at: null, updated_by: null },
    });
    await expect(getInfractionSettings()).resolves.toEqual({
      condo_fee_amount: null,
      updated_at: null,
      updated_by: null,
    });
    expect(apiClient.get).toHaveBeenCalledWith("/infraction-settings");

    vi.mocked(apiClient.put).mockResolvedValue({ data: {} });
    await writeInfractionSettings(null);
    expect(apiClient.put).toHaveBeenCalledWith("/infraction-settings", {
      condo_fee_amount: null,
    });
  });

  it("reads the process, its list and its suggestion", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: [] });

    await getInfractions({ stage: "NONE", skip: 0, limit: 50 });
    expect(apiClient.get).toHaveBeenCalledWith("/infractions", {
      params: { stage: "NONE", skip: 0, limit: 50 },
    });

    // No query string at all is a valid call: every parameter is optional.
    await getInfractions();
    expect(apiClient.get).toHaveBeenLastCalledWith("/infractions", {
      params: {},
    });

    await getMyInfractions();
    expect(apiClient.get).toHaveBeenLastCalledWith("/infractions/my-lots");

    await getInfraction("i-1");
    expect(apiClient.get).toHaveBeenLastCalledWith("/infractions/i-1");

    await getNextStep("i-1");
    expect(apiClient.get).toHaveBeenLastCalledWith("/infractions/i-1/next-step");

    await getCycleCloses();
    expect(apiClient.get).toHaveBeenLastCalledWith("/infractions/cycles");
  });

  it("writes the process", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: { id: "i-1" } });

    await createInfraction({
      rule_id: "r-1",
      lot_id: "l-1",
      responsible_resident_id: "res-1",
      occurred_on: "2026-09-01",
      description: "d",
    });
    expect(apiClient.post).toHaveBeenCalledWith(
      "/infractions",
      expect.objectContaining({ rule_id: "r-1" }),
    );

    await promoteOccurrence("occ-1", {
      rule_id: "r-1",
      responsible_resident_id: "res-1",
    });
    expect(apiClient.post).toHaveBeenLastCalledWith(
      "/infractions/from-occurrence/occ-1",
      { rule_id: "r-1", responsible_resident_id: "res-1" },
    );

    // `action` absent means "apply the suggestion" -- the server distinguishes
    // it from an explicit action, so the client must not default it.
    await addInfractionStage("i-1", { note: "n" });
    expect(apiClient.post).toHaveBeenLastCalledWith("/infractions/i-1/stages", {
      note: "n",
    });

    await addContestation("i-1", { body: "b" });
    expect(apiClient.post).toHaveBeenLastCalledWith(
      "/infractions/i-1/contestation",
      { body: "b" },
    );

    await closeCycle({
      rule_id: "r-1",
      responsible_resident_id: "res-1",
      justification: "j",
    });
    expect(apiClient.post).toHaveBeenLastCalledWith(
      "/infractions/cycles/close",
      { rule_id: "r-1", responsible_resident_id: "res-1", justification: "j" },
    );
  });
});
