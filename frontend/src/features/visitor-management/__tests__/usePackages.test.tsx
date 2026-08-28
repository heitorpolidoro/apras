import { renderHook, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import * as packagesApi from "../../../api/packages";
import {
  useCreatePackage,
  useMarkPackagePickedUp,
  usePackageQueue,
  usePackagesForLot,
} from "../hooks/usePackages";

vi.mock("../../../api/packages");

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

describe("usePackages hooks", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("usePackageQueue fetches the awaiting-pickup queue", async () => {
    vi.mocked(packagesApi.getPackageQueue).mockResolvedValue({
      items: [{ id: "p1", status: "AWAITING_PICKUP" }] as any,
      total: 1,
      skip: 0,
      limit: 100,
    });

    const { result } = renderHook(() => usePackageQueue(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.items[0].id).toBe("p1");
  });

  it("usePackagesForLot is disabled without a lotId", () => {
    const { result } = renderHook(() => usePackagesForLot(undefined), {
      wrapper: createWrapper(),
    });

    expect(result.current.fetchStatus).toBe("idle");
    expect(packagesApi.getPackagesForLot).not.toHaveBeenCalled();
  });

  it("usePackagesForLot fetches packages for a given lot", async () => {
    vi.mocked(packagesApi.getPackagesForLot).mockResolvedValue({
      items: [{ id: "p2", lot_id: "lot-1" }] as any,
      total: 1,
      skip: 0,
      limit: 100,
    });

    const { result } = renderHook(() => usePackagesForLot("lot-1"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.items[0].id).toBe("p2");
    expect(packagesApi.getPackagesForLot).toHaveBeenCalledWith(
      "lot-1",
      undefined,
      undefined,
      undefined
    );
  });

  it("useCreatePackage calls createPackage API and invalidates queries", async () => {
    vi.mocked(packagesApi.createPackage).mockResolvedValue({ id: "p3" } as any);

    const { result } = renderHook(() => useCreatePackage(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({ lot_id: "lot-1", description: "Caixa" });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(packagesApi.createPackage).toHaveBeenCalledWith({
      lot_id: "lot-1",
      description: "Caixa",
    });
  });

  it("useMarkPackagePickedUp calls markPackagePickedUp API", async () => {
    vi.mocked(packagesApi.markPackagePickedUp).mockResolvedValue({
      id: "p1",
      status: "PICKED_UP",
    } as any);

    const { result } = renderHook(() => useMarkPackagePickedUp(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({ id: "p1", data: { picked_up_by_notes: "Retirado" } });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(packagesApi.markPackagePickedUp).toHaveBeenCalledWith("p1", {
      picked_up_by_notes: "Retirado",
    });
  });
});
