import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  getProjects,
  getProjectDetail,
  createProject,
  updateProject,
  deleteProject,
  createMilestone,
  updateMilestone,
  deleteMilestone,
  createProjectUpdate,
  deleteProjectUpdate,
} from "../projects";
import apiClient from "../client";

vi.mock("../client", () => ({
  default: { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() },
}));

describe("projects api client", () => {
  beforeEach(() => vi.clearAllMocks());

  it("lists projects forwarding the status and paging params", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: { items: [], total: 0, skip: 0, limit: 20 },
    });

    await expect(
      getProjects({ status: "IN_PROGRESS", skip: 0, limit: 20 }),
    ).resolves.toEqual({ items: [], total: 0, skip: 0, limit: 20 });

    expect(apiClient.get).toHaveBeenCalledWith("/projects", {
      params: { status: "IN_PROGRESS", skip: 0, limit: 20 },
    });
  });

  it("lists projects with no params when none are given", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: { items: [], total: 0, skip: 0, limit: 20 },
    });

    await getProjects();

    expect(apiClient.get).toHaveBeenCalledWith("/projects", {
      params: undefined,
    });
  });

  it("reads a project detail by id", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: { id: "p-1" } });

    await expect(getProjectDetail("p-1")).resolves.toEqual({ id: "p-1" });

    expect(apiClient.get).toHaveBeenCalledWith("/projects/p-1");
  });

  it("creates a project", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: { id: "p-1" } });

    await expect(
      createProject({ title: "Portaria", total_budget: 50000 }),
    ).resolves.toEqual({ id: "p-1" });

    expect(apiClient.post).toHaveBeenCalledWith("/projects", {
      title: "Portaria",
      total_budget: 50000,
    });
  });

  it("updates a project by id", async () => {
    vi.mocked(apiClient.put).mockResolvedValue({ data: { id: "p-1" } });

    await expect(
      updateProject("p-1", { status: "COMPLETED" }),
    ).resolves.toEqual({ id: "p-1" });

    expect(apiClient.put).toHaveBeenCalledWith("/projects/p-1", {
      status: "COMPLETED",
    });
  });

  it("deletes a project by id", async () => {
    vi.mocked(apiClient.delete).mockResolvedValue({ data: undefined });

    await expect(deleteProject("p-1")).resolves.toBeUndefined();

    expect(apiClient.delete).toHaveBeenCalledWith("/projects/p-1");
  });

  it("creates a milestone nested under the project", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: { id: "m-1" } });

    await expect(
      createMilestone("p-1", { title: "Fundação", status: "IN_PROGRESS" }),
    ).resolves.toEqual({ id: "m-1" });

    expect(apiClient.post).toHaveBeenCalledWith("/projects/p-1/milestones", {
      title: "Fundação",
      status: "IN_PROGRESS",
    });
  });

  it("updates a milestone nested under the project", async () => {
    vi.mocked(apiClient.put).mockResolvedValue({ data: { id: "m-1" } });

    await expect(
      updateMilestone("p-1", "m-1", { status: "DONE" }),
    ).resolves.toEqual({ id: "m-1" });

    expect(apiClient.put).toHaveBeenCalledWith(
      "/projects/p-1/milestones/m-1",
      { status: "DONE" },
    );
  });

  it("deletes a milestone nested under the project", async () => {
    vi.mocked(apiClient.delete).mockResolvedValue({ data: undefined });

    await expect(deleteMilestone("p-1", "m-1")).resolves.toBeUndefined();

    expect(apiClient.delete).toHaveBeenCalledWith("/projects/p-1/milestones/m-1");
  });

  it("creates a project update", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: { id: "u-1" } });

    await expect(
      createProjectUpdate("p-1", {
        title: "Semana 1",
        content: "Concretagem concluída",
        cost_impact: 1200,
      }),
    ).resolves.toEqual({ id: "u-1" });

    expect(apiClient.post).toHaveBeenCalledWith("/projects/p-1/updates", {
      title: "Semana 1",
      content: "Concretagem concluída",
      cost_impact: 1200,
    });
  });

  it("deletes a project update", async () => {
    vi.mocked(apiClient.delete).mockResolvedValue({ data: undefined });

    await expect(deleteProjectUpdate("p-1", "u-1")).resolves.toBeUndefined();

    expect(apiClient.delete).toHaveBeenCalledWith("/projects/p-1/updates/u-1");
  });
});
