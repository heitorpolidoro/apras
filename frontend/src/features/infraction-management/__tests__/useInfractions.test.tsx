import { renderHook, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  useAddContestation,
  useAddInfractionStage,
  useCloseCycle,
  useCreateInfraction,
  useCycleCloses,
  useInfraction,
  useMyInfractions,
  useNextStep,
  usePromoteOccurrence,
} from "../hooks/useInfractions";
import {
  useCreateInfractionRule,
  useDeactivateInfractionRule,
  useInfractionSettings,
  useUpdateInfractionRule,
  useWriteInfractionPolicy,
  useWriteInfractionSettings,
} from "../hooks/useInfractionRules";
import * as api from "../../../api/infractions";
import { OCCURRENCES_QUERY_KEY } from "../../occurrence-management/hooks/useOccurrences";

vi.mock("../../../api/infractions");

/**
 * The mutations, and the invalidations they own.
 *
 * The one worth asserting is `usePromoteOccurrence`: appending an infraction
 * changes `OccurrenceDetailRead.infraction_ids` on the *other* side of the
 * bridge, so the occurrence's own cache entry is stale until it is
 * invalidated — and nothing else in the app would do it.
 */

const makeWrapper = (queryClient: QueryClient) => {
  const Wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
  return Wrapper;
};

const setup = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  const invalidate = vi.spyOn(queryClient, "invalidateQueries");
  return { queryClient, invalidate, wrapper: makeWrapper(queryClient) };
};

describe("infraction query hooks", () => {
  beforeEach(() => vi.clearAllMocks());

  it("the id-keyed queries stay disabled until they have an id", () => {
    const { wrapper } = setup();

    renderHook(() => useInfraction(null), { wrapper });
    renderHook(() => useNextStep(null), { wrapper });

    expect(api.getInfraction).not.toHaveBeenCalled();
    expect(api.getNextStep).not.toHaveBeenCalled();
  });

  it("fetches the resident list, the cycle list and the settings", async () => {
    vi.mocked(api.getMyInfractions).mockResolvedValue([]);
    vi.mocked(api.getCycleCloses).mockResolvedValue([]);
    vi.mocked(api.getInfractionSettings).mockResolvedValue({
      condo_fee_amount: null,
      updated_at: null,
      updated_by: null,
    });
    const { wrapper } = setup();

    const mine = renderHook(() => useMyInfractions(), { wrapper });
    const cycles = renderHook(() => useCycleCloses(), { wrapper });
    const settings = renderHook(() => useInfractionSettings(), { wrapper });

    await waitFor(() => expect(mine.result.current.isSuccess).toBe(true));
    await waitFor(() => expect(cycles.result.current.isSuccess).toBe(true));
    await waitFor(() => expect(settings.result.current.isSuccess).toBe(true));
  });
});

describe("infraction mutation hooks", () => {
  beforeEach(() => vi.clearAllMocks());

  it("promoting invalidates the occurrence's own cache entry too", async () => {
    vi.mocked(api.promoteOccurrence).mockResolvedValue({} as never);
    const { wrapper, invalidate } = setup();

    const { result } = renderHook(() => usePromoteOccurrence(), { wrapper });
    result.current.mutate({
      occurrenceId: "occ-1",
      data: { rule_id: "r-1", responsible_resident_id: "res-1" },
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    // Asserted against the **consuming feature's exported key**, not against a
    // string this file also types: the round-2 version asserted
    // `["occurrence", "occ-1"]`, which is what the implementation happened to
    // contain and what no query is registered under, so it passed while the
    // link it names stayed stale for the 5-minute `staleTime`.
    expect(invalidate).toHaveBeenCalledWith({
      queryKey: [...OCCURRENCES_QUERY_KEY, "detail", "occ-1"],
    });
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["infractions"] });
  });

  it("closing a cycle invalidates the cycle list as well as the process", async () => {
    vi.mocked(api.closeCycle).mockResolvedValue({} as never);
    const { wrapper, invalidate } = setup();

    const { result } = renderHook(() => useCloseCycle(), { wrapper });
    result.current.mutate({
      rule_id: "r-1",
      responsible_resident_id: "res-1",
      justification: "j",
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(invalidate).toHaveBeenCalledWith({
      queryKey: ["infraction-cycles"],
    });
  });

  it("the create mutation calls its endpoint", async () => {
    vi.mocked(api.createInfraction).mockResolvedValue({} as never);
    const { wrapper } = setup();
    const { result } = renderHook(() => useCreateInfraction(), { wrapper });

    result.current.mutate({
      rule_id: "r-1",
      lot_id: "l-1",
      responsible_resident_id: "res-1",
      occurred_on: "2026-09-01",
      description: "d",
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(api.createInfraction).toHaveBeenCalled();
  });

  it("the stage mutation calls its endpoint", async () => {
    vi.mocked(api.addInfractionStage).mockResolvedValue({} as never);
    const { wrapper } = setup();
    const { result } = renderHook(() => useAddInfractionStage(), { wrapper });

    result.current.mutate({ id: "i-1", data: { note: "n" } });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(api.addInfractionStage).toHaveBeenCalledWith("i-1", { note: "n" });
  });

  it("the contestation mutation calls its endpoint", async () => {
    vi.mocked(api.addContestation).mockResolvedValue({} as never);
    const { wrapper } = setup();
    const { result } = renderHook(() => useAddContestation(), { wrapper });

    result.current.mutate({ id: "i-1", data: { body: "b" } });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(api.addContestation).toHaveBeenCalledWith("i-1", { body: "b" });
  });
});

describe("infraction rule mutation hooks", () => {
  beforeEach(() => vi.clearAllMocks());

  it("creating a rule invalidates the catalogue", async () => {
    vi.mocked(api.createInfractionRule).mockResolvedValue({} as never);
    const { wrapper, invalidate } = setup();
    const { result } = renderHook(() => useCreateInfractionRule(), { wrapper });

    result.current.mutate({
      article: "a",
      origin: "ESTATUTO",
      description: "d",
      recidivism_window_days: 30,
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(invalidate).toHaveBeenCalledWith({
      queryKey: ["infraction-rules"],
    });
  });

  it("updating a rule invalidates the catalogue", async () => {
    vi.mocked(api.updateInfractionRule).mockResolvedValue({} as never);
    const { wrapper, invalidate } = setup();
    const { result } = renderHook(() => useUpdateInfractionRule(), { wrapper });

    result.current.mutate({ id: "r-1", data: { description: "x" } });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(api.updateInfractionRule).toHaveBeenCalledWith("r-1", {
      description: "x",
    });
    expect(invalidate).toHaveBeenCalled();
  });

  it("deactivating a rule invalidates the catalogue", async () => {
    vi.mocked(api.deactivateInfractionRule).mockResolvedValue(undefined);
    const { wrapper, invalidate } = setup();
    const { result } = renderHook(() => useDeactivateInfractionRule(), {
      wrapper,
    });

    result.current.mutate("r-1");

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(api.deactivateInfractionRule).toHaveBeenCalledWith("r-1");
    expect(invalidate).toHaveBeenCalled();
  });

  it("writing the ladder invalidates the catalogue", async () => {
    vi.mocked(api.writeInfractionPolicy).mockResolvedValue({} as never);
    const { wrapper, invalidate } = setup();
    const { result } = renderHook(() => useWriteInfractionPolicy(), { wrapper });

    result.current.mutate({
      id: "r-1",
      steps: [{ step_order: 1, action: "AVISO" }],
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(api.writeInfractionPolicy).toHaveBeenCalledWith("r-1", [
      { step_order: 1, action: "AVISO" },
    ]);
    expect(invalidate).toHaveBeenCalled();
  });

  it("writing the fee invalidates the settings singleton, not the catalogue", async () => {
    vi.mocked(api.writeInfractionSettings).mockResolvedValue({} as never);
    const { wrapper, invalidate } = setup();
    const { result } = renderHook(() => useWriteInfractionSettings(), {
      wrapper,
    });

    result.current.mutate(850);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(api.writeInfractionSettings).toHaveBeenCalledWith(850);
    expect(invalidate).toHaveBeenCalledWith({
      queryKey: ["infraction-settings"],
    });
  });
});
