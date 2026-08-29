import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  getAnnouncements,
  getAnnouncementById,
  createAnnouncement,
  updateAnnouncement,
  deleteAnnouncement,
  uploadAnnouncementMedia,
  deleteAnnouncementMedia,
  getAnnouncementComments,
  addAnnouncementComment,
  deleteAnnouncementComment,
  markAnnouncementRead,
  getAnnouncementReadReceipts,
} from "../announcements";
import apiClient from "../client";

vi.mock("../client", () => ({
  default: { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() },
}));

describe("announcements api client", () => {
  beforeEach(() => vi.clearAllMocks());

  it("lists announcements forwarding the paging params", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: { items: [], total: 0, skip: 10, limit: 10 },
    });

    await expect(getAnnouncements({ skip: 10, limit: 10 })).resolves.toEqual({
      items: [],
      total: 0,
      skip: 10,
      limit: 10,
    });

    expect(apiClient.get).toHaveBeenCalledWith("/announcements", {
      params: { skip: 10, limit: 10 },
    });
  });

  it("lists announcements with no params when none are given", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: { items: [], total: 0, skip: 0, limit: 20 },
    });

    await getAnnouncements();

    expect(apiClient.get).toHaveBeenCalledWith("/announcements", {
      params: undefined,
    });
  });

  it("reads a single announcement by id", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: { id: "a-1" } });

    await expect(getAnnouncementById("a-1")).resolves.toEqual({ id: "a-1" });

    expect(apiClient.get).toHaveBeenCalledWith("/announcements/a-1");
  });

  it("creates an announcement", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: { id: "a-1" } });

    await expect(
      createAnnouncement({ title: "Aviso", content: "Corpo" }),
    ).resolves.toEqual({ id: "a-1" });

    expect(apiClient.post).toHaveBeenCalledWith("/announcements", {
      title: "Aviso",
      content: "Corpo",
    });
  });

  it("updates an announcement by id", async () => {
    vi.mocked(apiClient.put).mockResolvedValue({ data: { id: "a-1" } });

    await expect(
      updateAnnouncement("a-1", { title: "Novo título" }),
    ).resolves.toEqual({ id: "a-1" });

    expect(apiClient.put).toHaveBeenCalledWith("/announcements/a-1", {
      title: "Novo título",
    });
  });

  it("deletes an announcement by id", async () => {
    vi.mocked(apiClient.delete).mockResolvedValue({ data: undefined });

    await expect(deleteAnnouncement("a-1")).resolves.toBeUndefined();

    expect(apiClient.delete).toHaveBeenCalledWith("/announcements/a-1");
  });

  it("uploads media as multipart form data under the 'file' field", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: { id: "m-1" } });
    const file = new File(["img"], "foto.png", { type: "image/png" });

    await expect(uploadAnnouncementMedia("a-1", file)).resolves.toEqual({
      id: "m-1",
    });

    const [path, body, config] = vi.mocked(apiClient.post).mock.calls[0];
    expect(path).toBe("/announcements/a-1/media");
    expect(body).toBeInstanceOf(FormData);
    expect((body as FormData).get("file")).toBe(file);
    expect(config).toEqual({
      headers: { "Content-Type": "multipart/form-data" },
    });
  });

  it("deletes a media item of an announcement", async () => {
    vi.mocked(apiClient.delete).mockResolvedValue({ data: undefined });

    await expect(
      deleteAnnouncementMedia("a-1", "m-1"),
    ).resolves.toBeUndefined();

    expect(apiClient.delete).toHaveBeenCalledWith("/announcements/a-1/media/m-1");
  });

  it("lists the comments of an announcement", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: [{ id: "cm-1" }] });

    await expect(getAnnouncementComments("a-1")).resolves.toEqual([
      { id: "cm-1" },
    ]);

    expect(apiClient.get).toHaveBeenCalledWith("/announcements/a-1/comments");
  });

  it("adds a comment to an announcement", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: { id: "cm-1" } });

    await expect(
      addAnnouncementComment("a-1", { content: "Comentário" }),
    ).resolves.toEqual({ id: "cm-1" });

    expect(apiClient.post).toHaveBeenCalledWith("/announcements/a-1/comments", {
      content: "Comentário",
    });
  });

  it("deletes a comment by its own id, not nested under the announcement", async () => {
    vi.mocked(apiClient.delete).mockResolvedValue({ data: undefined });

    await expect(
      deleteAnnouncementComment("cm-1"),
    ).resolves.toBeUndefined();

    expect(apiClient.delete).toHaveBeenCalledWith("/announcements/comments/cm-1");
  });

  it("marks an announcement as read with no request body", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: { read: true } });

    await expect(markAnnouncementRead("a-1")).resolves.toEqual({ read: true });

    expect(apiClient.post).toHaveBeenCalledWith("/announcements/a-1/read");
  });

  it("lists the read receipts of an announcement", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: [{ user_id: "u-1" }] });

    await expect(getAnnouncementReadReceipts("a-1")).resolves.toEqual([
      { user_id: "u-1" },
    ]);

    expect(apiClient.get).toHaveBeenCalledWith("/announcements/a-1/read-receipts");
  });
});
