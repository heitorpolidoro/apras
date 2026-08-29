import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  createAsset,
  deleteAsset,
  getAssetById,
  getAssets,
  getAssetSummary,
  getInventoryMovements,
  recordMovement,
  updateAsset,
} from "../assets";
import apiClient from "../client";

vi.mock("../client", () => ({
  default: { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() },
}));

describe("assets api client", () => {
  beforeEach(() => vi.clearAllMocks());

  it("lists assets with filter params", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: { items: [{ id: "a-1" }], total: 1, skip: 0, limit: 10 },
    });

    const res = await getAssets({ category: "FERRAMENTAS", low_stock_only: true });
    expect(res).toEqual({ items: [{ id: "a-1" }], total: 1, skip: 0, limit: 10 });
    expect(apiClient.get).toHaveBeenCalledWith("/assets", {
      params: { category: "FERRAMENTAS", low_stock_only: true },
    });
  });

  it("fetches asset summary", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: { total_assets: 10, total_consumables: 5, low_stock_count: 2, total_patrimonial_value: 5000 },
    });

    const res = await getAssetSummary();
    expect(res.total_assets).toBe(10);
    expect(apiClient.get).toHaveBeenCalledWith("/assets/summary");
  });

  it("fetches asset by id", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: { id: "a-1", name: "Lawn Mower", movements: [] },
    });

    const res = await getAssetById("a-1");
    expect(res.id).toBe("a-1");
    expect(apiClient.get).toHaveBeenCalledWith("/assets/a-1");
  });

  it("creates a new asset", async () => {
    const payload = {
      name: "Câmera",
      category: "SEGURANCA" as const,
      location: "Portaria",
      is_consumable: false,
    };
    vi.mocked(apiClient.post).mockResolvedValue({ data: { id: "a-2", ...payload } });

    const res = await createAsset(payload);
    expect(res.id).toBe("a-2");
    expect(apiClient.post).toHaveBeenCalledWith("/assets", payload);
  });

  it("updates an asset", async () => {
    vi.mocked(apiClient.put).mockResolvedValue({ data: { id: "a-2", location: "Oficina" } });

    const res = await updateAsset("a-2", { location: "Oficina" });
    expect(res.location).toBe("Oficina");
    expect(apiClient.put).toHaveBeenCalledWith("/assets/a-2", { location: "Oficina" });
  });

  it("deletes an asset", async () => {
    vi.mocked(apiClient.delete).mockResolvedValue({ data: undefined });

    await deleteAsset("a-2");
    expect(apiClient.delete).toHaveBeenCalledWith("/assets/a-2");
  });

  it("records an inventory movement", async () => {
    const payload = {
      movement_type: "ENTRADA" as const,
      quantity: 5,
      reason: "Compra",
    };
    vi.mocked(apiClient.post).mockResolvedValue({ data: { id: "m-1", ...payload } });

    const res = await recordMovement("a-1", payload);
    expect(res.id).toBe("m-1");
    expect(apiClient.post).toHaveBeenCalledWith("/assets/a-1/movements", payload);
  });

  it("lists global inventory movements", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: { items: [], total: 0, skip: 0, limit: 50 },
    });

    const res = await getInventoryMovements({ asset_id: "a-1", skip: 0, limit: 50 });
    expect(res).toEqual({ items: [], total: 0, skip: 0, limit: 50 });
    expect(apiClient.get).toHaveBeenCalledWith("/inventory-movements", {
      params: { asset_id: "a-1", skip: 0, limit: 50 },
    });
  });
});
