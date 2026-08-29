import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  getDocumentFolders,
  createDocumentFolder,
  updateDocumentFolder,
  deleteDocumentFolder,
  getDocuments,
  createDocument,
  createDocumentVersion,
  downloadDocument,
  deleteDocument,
} from "../documents";
import apiClient from "../client";

vi.mock("../client", () => ({
  default: { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() },
}));

describe("documents api client", () => {
  beforeEach(() => vi.clearAllMocks());

  describe("folders", () => {
    it("lists the folder tree", async () => {
      vi.mocked(apiClient.get).mockResolvedValue({ data: [{ id: "f-1" }] });

      await expect(getDocumentFolders()).resolves.toEqual([{ id: "f-1" }]);

      expect(apiClient.get).toHaveBeenCalledWith("/documents/folders");
    });

    it("creates a folder", async () => {
      vi.mocked(apiClient.post).mockResolvedValue({ data: { id: "f-1" } });

      await expect(
        createDocumentFolder({
          name: "Atas",
          parent_id: null,
          allowed_roles: ["ADMINISTRADOR"],
        }),
      ).resolves.toEqual({ id: "f-1" });

      expect(apiClient.post).toHaveBeenCalledWith("/documents/folders", {
        name: "Atas",
        parent_id: null,
        allowed_roles: ["ADMINISTRADOR"],
      });
    });

    it("updates a folder by id", async () => {
      vi.mocked(apiClient.put).mockResolvedValue({ data: { id: "f-1" } });

      await expect(
        updateDocumentFolder("f-1", { name: "Atas 2026" }),
      ).resolves.toEqual({ id: "f-1" });

      expect(apiClient.put).toHaveBeenCalledWith("/documents/folders/f-1", {
        name: "Atas 2026",
      });
    });

    it("deletes a folder by id", async () => {
      vi.mocked(apiClient.delete).mockResolvedValue({ data: undefined });

      await expect(deleteDocumentFolder("f-1")).resolves.toBeUndefined();

      expect(apiClient.delete).toHaveBeenCalledWith("/documents/folders/f-1");
    });
  });

  describe("documents", () => {
    it("lists documents forwarding every filter param", async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        data: { items: [], total: 0, skip: 0, limit: 20 },
      });

      await expect(
        getDocuments({
          folder_id: "f-1",
          tag: "ata",
          year: 2026,
          month: 3,
          search: "assembleia",
          skip: 0,
          limit: 20,
        }),
      ).resolves.toEqual({ items: [], total: 0, skip: 0, limit: 20 });

      expect(apiClient.get).toHaveBeenCalledWith("/documents", {
        params: {
          folder_id: "f-1",
          tag: "ata",
          year: 2026,
          month: 3,
          search: "assembleia",
          skip: 0,
          limit: 20,
        },
      });
    });

    it("lists documents with no params when none are given", async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        data: { items: [], total: 0, skip: 0, limit: 20 },
      });

      await getDocuments();

      expect(apiClient.get).toHaveBeenCalledWith("/documents", {
        params: undefined,
      });
    });

    it("creates a document", async () => {
      vi.mocked(apiClient.post).mockResolvedValue({ data: { id: "d-1" } });

      await expect(
        createDocument({
          folder_id: "f-1",
          title: "Ata de março",
          file_url: "https://blob/ata.pdf",
          file_size_bytes: 2048,
          mime_type: "application/pdf",
        }),
      ).resolves.toEqual({ id: "d-1" });

      expect(apiClient.post).toHaveBeenCalledWith("/documents", {
        folder_id: "f-1",
        title: "Ata de março",
        file_url: "https://blob/ata.pdf",
        file_size_bytes: 2048,
        mime_type: "application/pdf",
      });
    });

    it("creates a new version of a document", async () => {
      vi.mocked(apiClient.post).mockResolvedValue({ data: { id: "d-1" } });

      await expect(
        createDocumentVersion("d-1", {
          file_url: "https://blob/ata-v2.pdf",
          file_size_bytes: 4096,
        }),
      ).resolves.toEqual({ id: "d-1" });

      expect(apiClient.post).toHaveBeenCalledWith("/documents/d-1/versions", {
        file_url: "https://blob/ata-v2.pdf",
        file_size_bytes: 4096,
      });
    });

    it("requests a download url with POST and no body", async () => {
      vi.mocked(apiClient.post).mockResolvedValue({
        data: { file_url: "https://blob/ata.pdf" },
      });

      await expect(downloadDocument("d-1")).resolves.toEqual({
        file_url: "https://blob/ata.pdf",
      });

      expect(apiClient.post).toHaveBeenCalledWith("/documents/d-1/download");
    });

    it("deletes a document by id", async () => {
      vi.mocked(apiClient.delete).mockResolvedValue({ data: undefined });

      await expect(deleteDocument("d-1")).resolves.toBeUndefined();

      expect(apiClient.delete).toHaveBeenCalledWith("/documents/d-1");
    });
  });
});
