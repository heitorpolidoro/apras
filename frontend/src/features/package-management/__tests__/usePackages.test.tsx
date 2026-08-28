import { renderHook, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import * as packagesApi from "../../../api/packages";
import { useMyLots, useMyPackages } from "../hooks/usePackages";

vi.mock("../../../api/packages");

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

describe("package-management usePackages hooks", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("useMyLots fetches the caller's own linked lots", async () => {
    vi.mocked(packagesApi.getMyPackageLots).mockResolvedValue([
      { id: "lot-1", block: "A", lot_number: "101" },
    ]);

    const { result } = renderHook(() => useMyLots(), { wrapper: createWrapper() });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.[0].id).toBe("lot-1");
  });

  it("useMyPackages resolves lots and their packages together", async () => {
    vi.mocked(packagesApi.getMyPackageLots).mockResolvedValue([
      { id: "lot-1", block: "A", lot_number: "101" },
    ]);
    vi.mocked(packagesApi.getPackagesForLot).mockResolvedValue({
      items: [{ id: "pkg-1", lot_id: "lot-1" }] as any,
      total: 1,
      skip: 0,
      limit: 100,
    });

    const { result } = renderHook(() => useMyPackages(), { wrapper: createWrapper() });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.lotsWithPackages).toHaveLength(1);
    expect(result.current.lotsWithPackages[0].lot.id).toBe("lot-1");
    expect(result.current.lotsWithPackages[0].packages[0].id).toBe("pkg-1");
  });

  it("useMyPackages returns an empty list when the resident has no linked lots", async () => {
    vi.mocked(packagesApi.getMyPackageLots).mockResolvedValue([]);

    const { result } = renderHook(() => useMyPackages(), { wrapper: createWrapper() });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.lotsWithPackages).toEqual([]);
    expect(packagesApi.getPackagesForLot).not.toHaveBeenCalled();
  });
});
