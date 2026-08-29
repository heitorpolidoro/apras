import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  getLots,
  createLot,
  getLotDetail,
  updateLot,
  deleteLot,
  linkUserLot,
  unlinkUserLot,
} from "../lots";
import apiClient from "../client";

vi.mock("../client", () => ({
  default: { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() },
}));

const emptyPage = { items: [], total: 0, skip: 0, limit: 20 };

describe("lots api client", () => {
  beforeEach(() => vi.clearAllMocks());

  it("lists lots on the trailing-slash path forwarding the filter params", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: emptyPage });

    await expect(
      getLots({ block: "A", status: "OCCUPIED", skip: 0, limit: 50 }),
    ).resolves.toEqual(emptyPage);

    expect(apiClient.get).toHaveBeenCalledWith("/lots/", {
      params: { block: "A", status: "OCCUPIED", skip: 0, limit: 50 },
    });
  });

  it("lists lots with no params when none are given", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: emptyPage });

    await getLots();

    expect(apiClient.get).toHaveBeenCalledWith("/lots/", { params: undefined });
  });

  it("creates a lot on the trailing-slash path", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: { id: "l-1" } });

    await expect(
      createLot({ block: "A", lot_number: "12", status: "VACANT" }),
    ).resolves.toEqual({ id: "l-1" });

    expect(apiClient.post).toHaveBeenCalledWith("/lots/", {
      block: "A",
      lot_number: "12",
      status: "VACANT",
    });
  });

  it("reads a lot detail by id", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: { id: "l-1" } });

    await expect(getLotDetail("l-1")).resolves.toEqual({ id: "l-1" });

    expect(apiClient.get).toHaveBeenCalledWith("/lots/l-1");
  });

  it("updates a lot by id", async () => {
    vi.mocked(apiClient.put).mockResolvedValue({ data: { id: "l-1" } });

    await expect(
      updateLot("l-1", { status: "UNDER_CONSTRUCTION" }),
    ).resolves.toEqual({ id: "l-1" });

    expect(apiClient.put).toHaveBeenCalledWith("/lots/l-1", {
      status: "UNDER_CONSTRUCTION",
    });
  });

  it("deletes a lot by id", async () => {
    vi.mocked(apiClient.delete).mockResolvedValue({ data: undefined });

    await expect(deleteLot("l-1")).resolves.toBeUndefined();

    expect(apiClient.delete).toHaveBeenCalledWith("/lots/l-1");
  });

  it("links a user to a lot", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: { id: "link-1" } });

    await expect(
      linkUserLot("l-1", {
        user_id: "u-1",
        association_type: "PROPRIETARIO",
        is_primary: true,
      }),
    ).resolves.toEqual({ id: "link-1" });

    expect(apiClient.post).toHaveBeenCalledWith("/lots/l-1/users", {
      user_id: "u-1",
      association_type: "PROPRIETARIO",
      is_primary: true,
    });
  });

  it("unlinks a user from a lot", async () => {
    vi.mocked(apiClient.delete).mockResolvedValue({ data: undefined });

    await expect(unlinkUserLot("l-1", "u-1")).resolves.toBeUndefined();

    expect(apiClient.delete).toHaveBeenCalledWith("/lots/l-1/users/u-1");
  });
});
