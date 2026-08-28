import { renderHook, waitFor, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, it, expect, vi, beforeEach } from "vitest";
import React from "react";
import {
  useReservableSpaces,
  useCreateReservableSpace,
  useUpdateReservableSpace,
  useDeactivateReservableSpace,
  useSpaceReservations,
  useCreateSpaceReservation,
  useApproveReservation,
  useRejectReservation,
  useCancelReservation,
  RESERVABLE_SPACES_QUERY_KEY,
  SPACE_RESERVATIONS_QUERY_KEY,
} from "../useReservations";
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

describe("useReservableSpaces", () => {
  beforeEach(() => vi.clearAllMocks());

  it("fetches spaces from GET /reservable-spaces/", async () => {
    const mockData = [{ id: "space-1", name: "Salão", requires_approval: false, is_active: true, created_at: "2026-01-01" }];
    vi.mocked(apiClient.get).mockResolvedValue({ data: mockData });

    const { wrapper } = createWrapper();
    const { result } = renderHook(() => useReservableSpaces(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(apiClient.get).toHaveBeenCalledWith("/reservable-spaces/");
    expect(result.current.data).toEqual(mockData);
  });
});

describe("useCreateReservableSpace", () => {
  beforeEach(() => vi.clearAllMocks());

  it("calls POST /reservable-spaces/ and invalidates spaces query", async () => {
    const created = { id: "space-2", name: "Quadra", requires_approval: false, is_active: true, created_at: "2026-01-01" };
    vi.mocked(apiClient.post).mockResolvedValue({ data: created });

    const { wrapper, invalidateSpy } = createWrapper();
    const { result } = renderHook(() => useCreateReservableSpace(), { wrapper });

    act(() => {
      result.current.mutate({ name: "Quadra" });
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(apiClient.post).toHaveBeenCalledWith("/reservable-spaces/", { name: "Quadra" });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: RESERVABLE_SPACES_QUERY_KEY });
  });
});

describe("useUpdateReservableSpace", () => {
  beforeEach(() => vi.clearAllMocks());

  it("calls PATCH /reservable-spaces/{id} and invalidates spaces query", async () => {
    const updated = { id: "space-1", name: "Renamed", requires_approval: false, is_active: true, created_at: "2026-01-01" };
    vi.mocked(apiClient.patch).mockResolvedValue({ data: updated });

    const { wrapper, invalidateSpy } = createWrapper();
    const { result } = renderHook(() => useUpdateReservableSpace(), { wrapper });

    act(() => {
      result.current.mutate({ id: "space-1", data: { name: "Renamed" } });
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(apiClient.patch).toHaveBeenCalledWith("/reservable-spaces/space-1", { name: "Renamed" });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: RESERVABLE_SPACES_QUERY_KEY });
  });
});

describe("useDeactivateReservableSpace", () => {
  beforeEach(() => vi.clearAllMocks());

  it("calls DELETE /reservable-spaces/{id} and invalidates spaces query", async () => {
    vi.mocked(apiClient.delete).mockResolvedValue({});

    const { wrapper, invalidateSpy } = createWrapper();
    const { result } = renderHook(() => useDeactivateReservableSpace(), { wrapper });

    act(() => {
      result.current.mutate("space-1");
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(apiClient.delete).toHaveBeenCalledWith("/reservable-spaces/space-1");
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: RESERVABLE_SPACES_QUERY_KEY });
  });
});

describe("useSpaceReservations", () => {
  beforeEach(() => vi.clearAllMocks());

  it("fetches reservations with space_id and mine params", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: [] });

    const { wrapper } = createWrapper();
    const { result } = renderHook(() => useSpaceReservations("space-1", true), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(apiClient.get).toHaveBeenCalledWith("/space-reservations/", {
      params: { space_id: "space-1", mine: true },
    });
  });
});

describe("useCreateSpaceReservation", () => {
  beforeEach(() => vi.clearAllMocks());

  it("calls POST /space-reservations/ and invalidates reservations query", async () => {
    const created = { id: "res-1", space_id: "space-1", start_time: "x", end_time: "y", status: "CONFIRMED", created_at: "x" };
    vi.mocked(apiClient.post).mockResolvedValue({ data: created });

    const { wrapper, invalidateSpy } = createWrapper();
    const { result } = renderHook(() => useCreateSpaceReservation(), { wrapper });

    act(() => {
      result.current.mutate({ space_id: "space-1", start_time: "x", end_time: "y" });
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(apiClient.post).toHaveBeenCalledWith("/space-reservations/", {
      space_id: "space-1",
      start_time: "x",
      end_time: "y",
    });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: SPACE_RESERVATIONS_QUERY_KEY });
  });

  it("propagates a 409 conflict error", async () => {
    vi.mocked(apiClient.post).mockRejectedValue({
      response: { status: 409, data: { detail: "Conflict" } },
    });

    const { wrapper } = createWrapper();
    const { result } = renderHook(() => useCreateSpaceReservation(), { wrapper });

    act(() => {
      result.current.mutate({ space_id: "space-1", start_time: "x", end_time: "y" });
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

describe("useApproveReservation", () => {
  beforeEach(() => vi.clearAllMocks());

  it("calls POST /space-reservations/{id}/approve and invalidates query", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: {} });

    const { wrapper, invalidateSpy } = createWrapper();
    const { result } = renderHook(() => useApproveReservation(), { wrapper });

    act(() => {
      result.current.mutate("res-1");
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(apiClient.post).toHaveBeenCalledWith("/space-reservations/res-1/approve");
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: SPACE_RESERVATIONS_QUERY_KEY });
  });
});

describe("useRejectReservation", () => {
  beforeEach(() => vi.clearAllMocks());

  it("calls POST /space-reservations/{id}/reject and invalidates query", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: {} });

    const { wrapper, invalidateSpy } = createWrapper();
    const { result } = renderHook(() => useRejectReservation(), { wrapper });

    act(() => {
      result.current.mutate("res-1");
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(apiClient.post).toHaveBeenCalledWith("/space-reservations/res-1/reject");
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: SPACE_RESERVATIONS_QUERY_KEY });
  });
});

describe("useCancelReservation", () => {
  beforeEach(() => vi.clearAllMocks());

  it("calls POST /space-reservations/{id}/cancel and invalidates query", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: {} });

    const { wrapper, invalidateSpy } = createWrapper();
    const { result } = renderHook(() => useCancelReservation(), { wrapper });

    act(() => {
      result.current.mutate("res-1");
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(apiClient.post).toHaveBeenCalledWith("/space-reservations/res-1/cancel");
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: SPACE_RESERVATIONS_QUERY_KEY });
  });
});
