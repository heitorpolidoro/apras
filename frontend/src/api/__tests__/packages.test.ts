import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  createPackage,
  getPackagesForLot,
  getPackageQueue,
  getPackage,
  markPackagePickedUp,
  getMyPackageLots,
} from "../packages";
import apiClient from "../client";

vi.mock("../client", () => ({
  default: { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() },
}));

const emptyPage = { items: [], total: 0, skip: 0, limit: 20 };

describe("packages api client", () => {
  beforeEach(() => vi.clearAllMocks());

  it("creates a package", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: { id: "pk-1" } });

    await expect(
      createPackage({
        lot_id: "l-1",
        description: "Caixa média",
        carrier: "Correios",
      }),
    ).resolves.toEqual({ id: "pk-1" });

    expect(apiClient.post).toHaveBeenCalledWith("/packages", {
      lot_id: "l-1",
      description: "Caixa média",
      carrier: "Correios",
    });
  });

  it("lists the packages of a lot forwarding lot_id, status and paging", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: emptyPage });

    await expect(
      getPackagesForLot("l-1", "AWAITING_PICKUP", 0, 20),
    ).resolves.toEqual(emptyPage);

    expect(apiClient.get).toHaveBeenCalledWith("/packages", {
      params: {
        lot_id: "l-1",
        status: "AWAITING_PICKUP",
        skip: 0,
        limit: 20,
      },
    });
  });

  it("lists the packages of a lot with only lot_id when no filters are given", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: emptyPage });

    await getPackagesForLot("l-1");

    expect(apiClient.get).toHaveBeenCalledWith("/packages", {
      params: {
        lot_id: "l-1",
        status: undefined,
        skip: undefined,
        limit: undefined,
      },
    });
  });

  it("reads the gatekeeper queue", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: emptyPage });

    await expect(getPackageQueue(0, 50)).resolves.toEqual(emptyPage);

    expect(apiClient.get).toHaveBeenCalledWith("/packages/queue", {
      params: { skip: 0, limit: 50 },
    });
  });

  it("reads a single package by id", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: { id: "pk-1" } });

    await expect(getPackage("pk-1")).resolves.toEqual({ id: "pk-1" });

    expect(apiClient.get).toHaveBeenCalledWith("/packages/pk-1");
  });

  it("marks a package as picked up", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: { id: "pk-1" } });

    await expect(
      markPackagePickedUp("pk-1", { picked_up_by_notes: "Retirado pelo porteiro" }),
    ).resolves.toEqual({ id: "pk-1" });

    expect(apiClient.post).toHaveBeenCalledWith("/packages/pk-1/pickup", {
      picked_up_by_notes: "Retirado pelo porteiro",
    });
  });

  it("lists the lots the current user can receive packages for", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: [{ id: "l-1" }] });

    await expect(getMyPackageLots()).resolves.toEqual([{ id: "l-1" }]);

    expect(apiClient.get).toHaveBeenCalledWith("/packages/my-lots");
  });
});
