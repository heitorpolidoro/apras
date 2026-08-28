import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, it, expect, vi, beforeEach } from "vitest";
import React from "react";
import {
  useAddLotVoterEligibility,
  useAssemblies,
  useAssemblyMinutes,
  useCastBallot,
  useCloseAssembly,
  useCloseVote,
  useCreateAssembly,
  useCreateVote,
  useEligibleLots,
  useLotVoterEligibility,
  useMyBallot,
  useRemoveLotVoterEligibility,
  useRetractBallot,
  useSaveAssemblyMinutes,
  useTally,
  useUpdateAssembly,
  useUpdateLotDelinquency,
  useVotes,
} from "../useVoting";
import apiClient from "../../../../api/client";

vi.mock("../../../../api/client", () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}));

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");
  const wrapper = ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: queryClient }, children);
  return { wrapper, invalidateSpy };
};

describe("voting queries", () => {
  beforeEach(() => vi.clearAllMocks());

  it("fetches the assembly list", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: [] });
    const { wrapper } = createWrapper();
    const { result } = renderHook(() => useAssemblies(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(apiClient.get).toHaveBeenCalledWith("/assemblies/");
  });

  it("fetches the vote list", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: [] });
    const { wrapper } = createWrapper();
    const { result } = renderHook(() => useVotes(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(apiClient.get).toHaveBeenCalledWith("/votes/", {
      params: undefined,
    });
  });

  it("passes the list filters through to GET /votes/", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: [] });
    const { wrapper } = createWrapper();
    const { result } = renderHook(
      () => useVotes({ kind: "ENQUETE", assembly_id: undefined }),
      { wrapper },
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(apiClient.get).toHaveBeenCalledWith("/votes/", {
      params: { kind: "ENQUETE", assembly_id: undefined },
    });
  });

  it.each([
    ["/votes/vote-1/my-ballot", () => useMyBallot("vote-1")],
    ["/votes/vote-1/eligible-lots", () => useEligibleLots("vote-1")],
    ["/votes/vote-1/tally", () => useTally("vote-1")],
    ["/lots/lot-1/voter-eligibility", () => useLotVoterEligibility("lot-1")],
  ])("fetches %s", async (url, hook) => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: [] });
    const { wrapper } = createWrapper();
    const { result } = renderHook(hook, { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(apiClient.get).toHaveBeenCalledWith(url);
  });

  it("fetches the minutes as text", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: "<h1>Minuta</h1>" });
    const { wrapper } = createWrapper();
    const { result } = renderHook(() => useAssemblyMinutes("assembly-1"), {
      wrapper,
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(apiClient.get).toHaveBeenCalledWith("/assemblies/assembly-1/minutes", {
      responseType: "text",
    });
    expect(result.current.data).toBe("<h1>Minuta</h1>");
  });

  it("does not fetch until an id is supplied", () => {
    const { wrapper } = createWrapper();
    renderHook(() => useMyBallot(undefined), { wrapper });
    renderHook(() => useTally(undefined), { wrapper });
    renderHook(() => useEligibleLots(undefined), { wrapper });
    renderHook(() => useAssemblyMinutes(undefined), { wrapper });
    renderHook(() => useLotVoterEligibility(undefined), { wrapper });

    expect(apiClient.get).not.toHaveBeenCalled();
  });
});

describe("voting mutations", () => {
  beforeEach(() => vi.clearAllMocks());

  it("creates an assembly and invalidates the list", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: { id: "a-1" } });
    const { wrapper, invalidateSpy } = createWrapper();
    const { result } = renderHook(() => useCreateAssembly(), { wrapper });

    result.current.mutate({
      title: "AGO",
      type: "AGO",
      held_on: "2026-03-01",
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(apiClient.post).toHaveBeenCalledWith("/assemblies/", {
      title: "AGO",
      type: "AGO",
      held_on: "2026-03-01",
    });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["assemblies"] });
  });

  it("closes an assembly and invalidates assemblies and votes", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: { id: "a-1" } });
    const { wrapper, invalidateSpy } = createWrapper();
    const { result } = renderHook(() => useCloseAssembly(), { wrapper });

    result.current.mutate("a-1");

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(apiClient.post).toHaveBeenCalledWith("/assemblies/a-1/close");
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["assemblies"] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["votes"] });
  });

  it("opens a draft assembly and invalidates assemblies and votes", async () => {
    vi.mocked(apiClient.patch).mockResolvedValue({
      data: { id: "a-1", status: "OPEN" },
    });
    const { wrapper, invalidateSpy } = createWrapper();
    const { result } = renderHook(() => useUpdateAssembly(), { wrapper });

    result.current.mutate({ id: "a-1", data: { status: "OPEN" } });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(apiClient.patch).toHaveBeenCalledWith("/assemblies/a-1", {
      status: "OPEN",
    });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["assemblies"] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["votes"] });
  });

  it("saves the minutes", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: { id: "doc-1" } });
    const { wrapper } = createWrapper();
    const { result } = renderHook(() => useSaveAssemblyMinutes(), { wrapper });

    result.current.mutate("a-1");

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(apiClient.post).toHaveBeenCalledWith("/assemblies/a-1/minutes/save");
  });

  it("creates a vote and invalidates the vote list", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: { id: "v-1" } });
    const { wrapper, invalidateSpy } = createWrapper();
    const { result } = renderHook(() => useCreateVote(), { wrapper });

    result.current.mutate({
      kind: "ENQUETE",
      title: "Cor",
      vote_type: "SINGLE_CHOICE",
      closes_at: "2026-12-01T00:00:00Z",
      options: [{ label: "Bege" }, { label: "Cinza" }],
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(apiClient.post).toHaveBeenCalledWith(
      "/votes/",
      expect.objectContaining({ kind: "ENQUETE" }),
    );
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["votes"] });
  });

  it("closes a vote and invalidates votes and tallies", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: { id: "v-1" } });
    const { wrapper, invalidateSpy } = createWrapper();
    const { result } = renderHook(() => useCloseVote(), { wrapper });

    result.current.mutate("v-1");

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(apiClient.post).toHaveBeenCalledWith("/votes/v-1/close");
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["tally"] });
  });

  it("casts a ballot and invalidates my-ballot and tally", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: { id: "b-1" } });
    const { wrapper, invalidateSpy } = createWrapper();
    const { result } = renderHook(() => useCastBallot(), { wrapper });

    result.current.mutate({
      voteId: "v-1",
      data: { lot_id: "lot-1", selected_option_ids: ["opt-1"] },
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(apiClient.post).toHaveBeenCalledWith("/votes/v-1/ballots", {
      lot_id: "lot-1",
      selected_option_ids: ["opt-1"],
    });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["my-ballot"] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["tally"] });
  });

  it("retracts a ballot", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: { id: "b-2" } });
    const { wrapper, invalidateSpy } = createWrapper();
    const { result } = renderHook(() => useRetractBallot(), { wrapper });

    result.current.mutate({ voteId: "v-1", data: { lot_id: null } });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(apiClient.post).toHaveBeenCalledWith("/votes/v-1/ballots/retract", {
      lot_id: null,
    });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["my-ballot"] });
  });

  it("adds and removes an extra eligible voter", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: { id: "e-1" } });
    vi.mocked(apiClient.delete).mockResolvedValue({ data: null });
    const { wrapper, invalidateSpy } = createWrapper();

    const add = renderHook(() => useAddLotVoterEligibility(), { wrapper });
    add.result.current.mutate({ lotId: "lot-1", userId: "user-9" });
    await waitFor(() => expect(add.result.current.isSuccess).toBe(true));
    expect(apiClient.post).toHaveBeenCalledWith(
      "/lots/lot-1/voter-eligibility",
      { user_id: "user-9" },
    );

    const remove = renderHook(() => useRemoveLotVoterEligibility(), { wrapper });
    remove.result.current.mutate({ lotId: "lot-1", userId: "user-9" });
    await waitFor(() => expect(remove.result.current.isSuccess).toBe(true));
    expect(apiClient.delete).toHaveBeenCalledWith(
      "/lots/lot-1/voter-eligibility/user-9",
    );
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ["lot-voter-eligibility"],
    });
  });
});

describe("delinquency mutation", () => {
  beforeEach(() => vi.clearAllMocks());

  it("patches the lot delinquency flag and invalidates the lot list", async () => {
    vi.mocked(apiClient.patch).mockResolvedValue({ data: { id: "lot-1" } });
    const { wrapper, invalidateSpy } = createWrapper();
    const { result } = renderHook(() => useUpdateLotDelinquency(), { wrapper });

    result.current.mutate({ lotId: "lot-1", isDelinquent: true });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(apiClient.patch).toHaveBeenCalledWith("/lots/lot-1/delinquency", {
      is_delinquent: true,
    });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["lots"] });
  });
});
