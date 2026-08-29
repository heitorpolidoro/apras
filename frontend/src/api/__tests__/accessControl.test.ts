import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  createDevice,
  listDevices,
  updateDeviceStatus,
  regenerateDeviceKey,
  syncFacialTemplate,
  getFacialTemplate,
  getAccessEvents,
} from "../accessControl";
import apiClient from "../client";

vi.mock("../client", () => ({
  default: { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() },
}));

describe("accessControl api client", () => {
  beforeEach(() => vi.clearAllMocks());

  it("creates a device", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({
      data: { id: "d-1", api_key: "secret" },
    });

    await expect(
      createDevice({ name: "Portão Social", location: "Entrada" }),
    ).resolves.toEqual({ id: "d-1", api_key: "secret" });

    expect(apiClient.post).toHaveBeenCalledWith("/access-control/devices", {
      name: "Portão Social",
      location: "Entrada",
    });
  });

  it("lists devices", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: { items: [], total: 0 },
    });

    await expect(listDevices()).resolves.toEqual({ items: [], total: 0 });

    expect(apiClient.get).toHaveBeenCalledWith("/access-control/devices");
  });

  it("updates the status of a device", async () => {
    vi.mocked(apiClient.put).mockResolvedValue({ data: { id: "d-1" } });

    await expect(
      updateDeviceStatus("d-1", { status: "MAINTENANCE" }),
    ).resolves.toEqual({ id: "d-1" });

    expect(apiClient.put).toHaveBeenCalledWith(
      "/access-control/devices/d-1/status",
      { status: "MAINTENANCE" },
    );
  });

  it("regenerates the key of a device with no request body", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({
      data: { id: "d-1", api_key: "new-secret" },
    });

    await expect(regenerateDeviceKey("d-1")).resolves.toEqual({
      id: "d-1",
      api_key: "new-secret",
    });

    expect(apiClient.post).toHaveBeenCalledWith(
      "/access-control/devices/d-1/regenerate-key",
    );
  });

  it("syncs the facial template of a resident with no request body", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({
      data: { id: "ft-1", sync_status: "PENDING" },
    });

    await expect(syncFacialTemplate("r-1")).resolves.toEqual({
      id: "ft-1",
      sync_status: "PENDING",
    });

    expect(apiClient.post).toHaveBeenCalledWith(
      "/access-control/residents/r-1/facial-template/sync",
    );
  });

  it("reads the facial template of a resident", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: { id: "ft-1" } });

    await expect(getFacialTemplate("r-1")).resolves.toEqual({ id: "ft-1" });

    expect(apiClient.get).toHaveBeenCalledWith(
      "/access-control/residents/r-1/facial-template",
    );
  });

  it("returns null when the resident has no facial template", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: null });

    await expect(getFacialTemplate("r-1")).resolves.toBeNull();
  });

  it("lists access events forwarding the snake_case filter params", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: { items: [], total: 0 },
    });

    await expect(
      getAccessEvents({
        device_id: "d-1",
        resident_id: "r-1",
        skip: 0,
        limit: 100,
      }),
    ).resolves.toEqual({ items: [], total: 0 });

    expect(apiClient.get).toHaveBeenCalledWith("/access-control/events", {
      params: { device_id: "d-1", resident_id: "r-1", skip: 0, limit: 100 },
    });
  });

  it("lists access events with no params when none are given", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: { items: [], total: 0 },
    });

    await getAccessEvents();

    expect(apiClient.get).toHaveBeenCalledWith("/access-control/events", {
      params: undefined,
    });
  });
});
