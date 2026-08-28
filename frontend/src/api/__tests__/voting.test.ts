import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  getAssembly,
  getVote,
  updateAssembly,
} from "../voting";
import apiClient from "../client";

vi.mock("../client", () => ({
  default: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}));

describe("voting api client", () => {
  beforeEach(() => vi.clearAllMocks());

  it("reads a single assembly", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: { id: "a-1" } });
    await expect(getAssembly("a-1")).resolves.toEqual({ id: "a-1" });
    expect(apiClient.get).toHaveBeenCalledWith("/assemblies/a-1");
  });

  it("patches an assembly", async () => {
    vi.mocked(apiClient.patch).mockResolvedValue({ data: { id: "a-1" } });
    await updateAssembly("a-1", { status: "OPEN" });
    expect(apiClient.patch).toHaveBeenCalledWith("/assemblies/a-1", {
      status: "OPEN",
    });
  });

  it("reads a single vote", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: { id: "v-1" } });
    await expect(getVote("v-1")).resolves.toEqual({ id: "v-1" });
    expect(apiClient.get).toHaveBeenCalledWith("/votes/v-1");
  });
});
