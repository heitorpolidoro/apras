import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  getLotResidents,
  createResident,
  getResidentDetail,
  updateResident,
  deleteResident,
  linkResidentUser,
  unlinkResidentUser,
} from "../residents";
import apiClient from "../client";

vi.mock("../client", () => ({
  default: { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() },
}));

const emptyPage = { items: [], total: 0, skip: 0, limit: 20 };

describe("residents api client", () => {
  beforeEach(() => vi.clearAllMocks());

  it("lists the residents of a lot forwarding skip and limit", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: emptyPage });

    await expect(getLotResidents("l-1", 10, 5)).resolves.toEqual(emptyPage);

    expect(apiClient.get).toHaveBeenCalledWith("/lots/l-1/residents", {
      params: { skip: 10, limit: 5 },
    });
  });

  it("lists the residents of a lot with undefined paging when none is given", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: emptyPage });

    await getLotResidents("l-1");

    expect(apiClient.get).toHaveBeenCalledWith("/lots/l-1/residents", {
      params: { skip: undefined, limit: undefined },
    });
  });

  it("creates a resident nested under the lot", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: { id: "r-1" } });

    await expect(
      createResident("l-1", {
        full_name: "João",
        cpf: "12345678900",
        relationship_type: "TITULAR",
      }),
    ).resolves.toEqual({ id: "r-1" });

    expect(apiClient.post).toHaveBeenCalledWith("/lots/l-1/residents", {
      full_name: "João",
      cpf: "12345678900",
      relationship_type: "TITULAR",
    });
  });

  it("reads a resident detail by id", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: { id: "r-1" } });

    await expect(getResidentDetail("r-1")).resolves.toEqual({ id: "r-1" });

    expect(apiClient.get).toHaveBeenCalledWith("/residents/r-1");
  });

  it("updates a resident by id", async () => {
    vi.mocked(apiClient.put).mockResolvedValue({ data: { id: "r-1" } });

    await expect(
      updateResident("r-1", { is_active: false }),
    ).resolves.toEqual({ id: "r-1" });

    expect(apiClient.put).toHaveBeenCalledWith("/residents/r-1", {
      is_active: false,
    });
  });

  it("deletes a resident by id", async () => {
    vi.mocked(apiClient.delete).mockResolvedValue({ data: undefined });

    await expect(deleteResident("r-1")).resolves.toBeUndefined();

    expect(apiClient.delete).toHaveBeenCalledWith("/residents/r-1");
  });

  it("links a user to a resident wrapping the id in a user_id payload", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: { id: "r-1" } });

    await expect(linkResidentUser("r-1", "u-1")).resolves.toEqual({ id: "r-1" });

    expect(apiClient.post).toHaveBeenCalledWith("/residents/r-1/link-user", {
      user_id: "u-1",
    });
  });

  it("unlinks the user of a resident with no request body", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: { id: "r-1" } });

    await expect(unlinkResidentUser("r-1")).resolves.toEqual({ id: "r-1" });

    expect(apiClient.post).toHaveBeenCalledWith("/residents/r-1/unlink-user");
  });
});
