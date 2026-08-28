import { renderHook, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import * as visitorsApi from "../../../api/visitors";
import {
  useAccessLogs,
  useAuthorization,
  useCheckIn,
  useCheckOut,
  useCreateAuthorization,
  useCreateVisitor,
  useLotAuthorizations,
  useRevokeAuthorization,
  useVisitors,
} from "../hooks/useVisitors";

vi.mock("../../../api/visitors");

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

describe("useVisitors hooks", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("useVisitors fetches visitor list", async () => {
    vi.mocked(visitorsApi.searchVisitors).mockResolvedValue({
      items: [{ id: "v1", full_name: "Carlos Test" }] as any,
      total: 1,
      skip: 0,
      limit: 100,
    });

    const { result } = renderHook(() => useVisitors("Carlos"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.items[0].full_name).toBe("Carlos Test");
  });

  it("useCreateVisitor calls createVisitor API", async () => {
    vi.mocked(visitorsApi.createVisitor).mockResolvedValue({
      id: "v2",
      full_name: "Ana Test",
    } as any);

    const { result } = renderHook(() => useCreateVisitor(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({ full_name: "Ana Test" });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(visitorsApi.createVisitor).toHaveBeenCalledWith({ full_name: "Ana Test" });
  });

  it("useLotAuthorizations fetches lot authorizations", async () => {
    vi.mocked(visitorsApi.getLotAuthorizations).mockResolvedValue({
      items: [{ id: "a1", status: "ACTIVE" }] as any,
      total: 1,
      skip: 0,
      limit: 100,
    });

    const { result } = renderHook(() => useLotAuthorizations("lot-1"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.items[0].id).toBe("a1");
  });

  it("useCreateAuthorization calls createLotAuthorization API", async () => {
    vi.mocked(visitorsApi.createLotAuthorization).mockResolvedValue({
      id: "a2",
      status: "ACTIVE",
    } as any);

    const { result } = renderHook(() => useCreateAuthorization(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({
      lotId: "lot-1",
      data: { visitor_id: "v1", auth_type: "SINGLE" },
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(visitorsApi.createLotAuthorization).toHaveBeenCalledWith("lot-1", {
      visitor_id: "v1",
      auth_type: "SINGLE",
    });
  });

  it("useRevokeAuthorization calls revokeAuthorization API", async () => {
    vi.mocked(visitorsApi.revokeAuthorization).mockResolvedValue({
      id: "a1",
      status: "REVOKED",
    } as any);

    const { result } = renderHook(() => useRevokeAuthorization(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({ authId: "a1", lotId: "lot-1" });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(visitorsApi.revokeAuthorization).toHaveBeenCalledWith("a1", undefined);
  });

  it("useCheckIn and useCheckOut execute API calls", async () => {
    vi.mocked(visitorsApi.checkInVisitor).mockResolvedValue({ id: "log-1" } as any);
    vi.mocked(visitorsApi.checkOutVisitor).mockResolvedValue({ id: "log-1" } as any);

    const { result: checkInResult } = renderHook(() => useCheckIn(), {
      wrapper: createWrapper(),
    });
    checkInResult.current.mutate({ visitor_id: "v1", lot_id: "lot-1" });
    await waitFor(() => expect(checkInResult.current.isSuccess).toBe(true));

    const { result: checkOutResult } = renderHook(() => useCheckOut(), {
      wrapper: createWrapper(),
    });
    checkOutResult.current.mutate({ access_log_id: "log-1" });
    await waitFor(() => expect(checkOutResult.current.isSuccess).toBe(true));
  });

  it("useAuthorization fetches a single authorization by id", async () => {
    vi.mocked(visitorsApi.getAuthorization).mockResolvedValue({
      id: "auth-1",
      lot_id: "lot-1",
      status: "ACTIVE",
    } as any);

    const { result } = renderHook(() => useAuthorization("auth-1"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(visitorsApi.getAuthorization).toHaveBeenCalledWith("auth-1");
    expect(result.current.data?.lot_id).toBe("lot-1");
  });

  it("useAuthorization does not fetch when id is undefined", () => {
    const { result } = renderHook(() => useAuthorization(undefined), {
      wrapper: createWrapper(),
    });

    expect(result.current.fetchStatus).toBe("idle");
    expect(visitorsApi.getAuthorization).not.toHaveBeenCalled();
  });

  it("useAccessLogs fetches access logs timeline", async () => {
    vi.mocked(visitorsApi.getAccessLogs).mockResolvedValue({
      items: [{ id: "log-1" }] as any,
      total: 1,
      skip: 0,
      limit: 100,
    });

    const { result } = renderHook(() => useAccessLogs({ lot_id: "lot-1" }), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.items[0].id).toBe("log-1");
  });
});
