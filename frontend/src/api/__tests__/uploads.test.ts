import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  uploadPhoto,
  getPendingPhotos,
  approvePhoto,
  rejectPhoto,
  deletePhoto,
  getPhotoMetadata,
} from "../uploads";
import apiClient from "../client";

vi.mock("../client", () => ({
  default: { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() },
}));

const lastPostBody = () =>
  vi.mocked(apiClient.post).mock.calls[0][1] as FormData;

describe("uploads api client", () => {
  beforeEach(() => vi.clearAllMocks());

  describe("uploadPhoto", () => {
    it("sends the file, entity_type and entity_id as multipart form data", async () => {
      vi.mocked(apiClient.post).mockResolvedValue({ data: { id: "ph-1" } });
      const file = new File(["img"], "residente.jpg", { type: "image/jpeg" });

      await expect(uploadPhoto(file, "RESIDENT", "r-1")).resolves.toEqual({
        id: "ph-1",
      });

      const [path, body, config] = vi.mocked(apiClient.post).mock.calls[0];
      expect(path).toBe("/uploads/photo");
      expect(body).toBeInstanceOf(FormData);
      expect(((body as FormData).get("file") as File).name).toBe("residente.jpg");
      expect((body as FormData).get("entity_type")).toBe("RESIDENT");
      expect((body as FormData).get("entity_id")).toBe("r-1");
      expect(config).toEqual({
        headers: { "Content-Type": "multipart/form-data" },
      });
    });

    it("names a raw Blob 'webcam_capture.jpg' and omits entity_id when not given", async () => {
      vi.mocked(apiClient.post).mockResolvedValue({ data: { id: "ph-1" } });
      const blob = new Blob(["img"], { type: "image/jpeg" });

      await uploadPhoto(blob, "VISITOR");

      const body = lastPostBody();
      expect((body.get("file") as File).name).toBe("webcam_capture.jpg");
      expect(body.get("entity_type")).toBe("VISITOR");
      expect(body.get("entity_id")).toBeNull();
    });
  });

  it("lists pending photos forwarding page and limit", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: { items: [], total: 0 },
    });

    await expect(getPendingPhotos(2, 50)).resolves.toEqual({
      items: [],
      total: 0,
    });

    expect(apiClient.get).toHaveBeenCalledWith("/uploads/photos/pending", {
      params: { page: 2, limit: 50 },
    });
  });

  it("defaults pending photos to page 1 with a limit of 20", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: { items: [], total: 0 },
    });

    await getPendingPhotos();

    expect(apiClient.get).toHaveBeenCalledWith("/uploads/photos/pending", {
      params: { page: 1, limit: 20 },
    });
  });

  it("approves a photo with no request body", async () => {
    vi.mocked(apiClient.put).mockResolvedValue({ data: { id: "ph-1" } });

    await expect(approvePhoto("ph-1")).resolves.toEqual({ id: "ph-1" });

    expect(apiClient.put).toHaveBeenCalledWith("/uploads/photos/ph-1/approve");
  });

  it("rejects a photo sending the rejection_reason", async () => {
    vi.mocked(apiClient.put).mockResolvedValue({ data: { id: "ph-1" } });

    await expect(rejectPhoto("ph-1", "Foto ilegível")).resolves.toEqual({
      id: "ph-1",
    });

    expect(apiClient.put).toHaveBeenCalledWith("/uploads/photos/ph-1/reject", {
      rejection_reason: "Foto ilegível",
    });
  });

  it("deletes a photo by id", async () => {
    vi.mocked(apiClient.delete).mockResolvedValue({ data: undefined });

    await expect(deletePhoto("ph-1")).resolves.toBeUndefined();

    expect(apiClient.delete).toHaveBeenCalledWith("/uploads/photos/ph-1");
  });

  it("reads the metadata of a photo", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: { id: "ph-1" } });

    await expect(getPhotoMetadata("ph-1")).resolves.toEqual({ id: "ph-1" });

    expect(apiClient.get).toHaveBeenCalledWith("/uploads/photos/ph-1");
  });
});
