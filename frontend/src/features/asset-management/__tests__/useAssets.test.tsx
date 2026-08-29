import React from "react";
import { renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import * as assetsApi from "../../../api/assets";
import {
  useAsset,
  useAssets,
  useAssetSummary,
  useCreateAsset,
  useDeleteAsset,
  useInventoryMovements,
  useRecordMovement,
  useUpdateAsset,
} from "../hooks/useAssets";
import type {
  Asset,
  AssetDetail,
  AssetSummary,
  InventoryMovement,
  PaginatedAssets,
  PaginatedInventoryMovements,
} from "../../../types/asset";
import { AssetCategory, AssetCondition, MovementType } from "../../../types/asset";

vi.mock("../../../api/assets");

const wrapper = ({ children }: { children: React.ReactNode }) => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

const mockAsset: Asset = {
  id: "asset-1",
  name: "Cortador de Grama",
  category: AssetCategory.FERRAMENTAS,
  serial_number: "SN-100",
  asset_tag: "PAT-100",
  location: "Oficina",
  acquisition_date: "2026-01-01",
  acquisition_value: 2000,
  condition: AssetCondition.BOM,
  is_consumable: false,
  current_quantity: 1,
  min_quantity: null,
  unit_of_measure: "un",
  notes: null,
  is_low_stock: false,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

const mockAssetDetail: AssetDetail = {
  ...mockAsset,
  movements: [],
};

const mockPaginatedAssets: PaginatedAssets = {
  items: [mockAsset],
  total: 1,
  skip: 0,
  limit: 10,
};

const mockSummary: AssetSummary = {
  total_assets: 1,
  total_consumables: 0,
  low_stock_count: 0,
  total_patrimonial_value: 2000,
};

const mockMovement: InventoryMovement = {
  id: "mov-1",
  asset_id: "asset-1",
  movement_type: MovementType.ENTRADA,
  quantity: 1,
  previous_quantity: 0,
  new_quantity: 1,
  performed_by_id: "user-1",
  reason: "Cadastro inicial",
  document_number: null,
  created_at: "2026-01-01T00:00:00Z",
};

const mockPaginatedMovements: PaginatedInventoryMovements = {
  items: [mockMovement],
  total: 1,
  skip: 0,
  limit: 10,
};

describe("useAssets hooks", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(assetsApi.getAssets).mockResolvedValue(mockPaginatedAssets);
    vi.mocked(assetsApi.getAssetSummary).mockResolvedValue(mockSummary);
    vi.mocked(assetsApi.getAssetById).mockResolvedValue(mockAssetDetail);
    vi.mocked(assetsApi.createAsset).mockResolvedValue(mockAsset);
    vi.mocked(assetsApi.updateAsset).mockResolvedValue(mockAsset);
    vi.mocked(assetsApi.deleteAsset).mockResolvedValue(undefined);
    vi.mocked(assetsApi.recordMovement).mockResolvedValue(mockMovement);
    vi.mocked(assetsApi.getInventoryMovements).mockResolvedValue(mockPaginatedMovements);
  });

  it("useAssets fetches paginated assets", async () => {
    const { result } = renderHook(() => useAssets({ category: AssetCategory.FERRAMENTAS }), {
      wrapper,
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(mockPaginatedAssets);
    expect(assetsApi.getAssets).toHaveBeenCalledWith({ category: AssetCategory.FERRAMENTAS });
  });

  it("useAssetSummary fetches summary metrics", async () => {
    const { result } = renderHook(() => useAssetSummary(), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(mockSummary);
  });

  it("useAsset fetches asset detail by id", async () => {
    const { result } = renderHook(() => useAsset("asset-1"), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.name).toBe("Cortador de Grama");
  });

  it("useCreateAsset creates an asset", async () => {
    const { result } = renderHook(() => useCreateAsset(), { wrapper });
    await result.current.mutateAsync({
      name: "Cortador de Grama",
      category: AssetCategory.FERRAMENTAS,
      location: "Oficina",
      is_consumable: false,
    });
    expect(assetsApi.createAsset).toHaveBeenCalled();
  });

  it("useUpdateAsset updates an asset", async () => {
    const { result } = renderHook(() => useUpdateAsset(), { wrapper });
    await result.current.mutateAsync({
      id: "asset-1",
      data: { location: "Depósito 2" },
    });
    expect(assetsApi.updateAsset).toHaveBeenCalledWith("asset-1", {
      location: "Depósito 2",
    });
  });

  it("useDeleteAsset deletes an asset", async () => {
    const { result } = renderHook(() => useDeleteAsset(), { wrapper });
    await result.current.mutateAsync("asset-1");
    expect(assetsApi.deleteAsset).toHaveBeenCalledWith("asset-1");
  });

  it("useRecordMovement records a movement", async () => {
    const { result } = renderHook(() => useRecordMovement(), { wrapper });
    await result.current.mutateAsync({
      assetId: "asset-1",
      data: {
        movement_type: MovementType.ENTRADA,
        quantity: 5,
        reason: "Compra",
      },
    });
    expect(assetsApi.recordMovement).toHaveBeenCalledWith("asset-1", {
      movement_type: MovementType.ENTRADA,
      quantity: 5,
      reason: "Compra",
    });
  });

  it("useInventoryMovements lists movements", async () => {
    const { result } = renderHook(() => useInventoryMovements({ asset_id: "asset-1" }), {
      wrapper,
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(mockPaginatedMovements);
  });
});
