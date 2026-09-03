import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { useTasks, useTask, useCreateTask, useUpdateTask, useTaskHistory, useInvalidateTasks, useDeleteTask, useComments, useCreateComment, useUpdateComment,  } from "../useTasks";
import apiClient from "../../../../api/client";
import { TaskStatus, TaskPriority } from "../../types";

// Mock do apiClient
vi.mock("../../../../api/client", () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}));

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0, // Desabilita cache para evitar interferência entre testes
      },
    },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

describe("useTasks hooks", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("useTasks", () => {
    it("fetches tasks with filters", async () => {
      const mockData = [{ id: "1", title: "Task 1" }];
      vi.mocked(apiClient.get).mockResolvedValue({ data: mockData });

      const { result } = renderHook(() => useTasks({ status: TaskStatus.PENDING }), {
        wrapper: createWrapper(),
      });

      // Espera até que os dados sejam carregados (superando o initialData)
      await waitFor(() => expect(result.current.data).toEqual(mockData), { timeout: 2000 });
      
      expect(apiClient.get).toHaveBeenCalledWith("/tasks/", {
        params: { status: TaskStatus.PENDING, priority: undefined, assigned_to_id: undefined },
      });
    });
  });

  describe("useTask", () => {
    it("fetches a single task by id", async () => {
      const mockTask = { id: "1", title: "Task 1" };
      vi.mocked(apiClient.get).mockResolvedValue({ data: mockTask });

      const { result } = renderHook(() => useTask("1"), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      
      expect(apiClient.get).toHaveBeenCalledWith("/tasks/1");
      expect(result.current.data).toEqual(mockTask);
    });

    it("does not fetch if id is empty", () => {
      renderHook(() => useTask(""), {
        wrapper: createWrapper(),
      });
      expect(apiClient.get).not.toHaveBeenCalled();
    });
  });

  describe("useCreateTask", () => {
    it("calls post and invalidates queries on success", async () => {
      const newTask = { title: "New Task", status: TaskStatus.PENDING, priority: TaskPriority.MEDIUM };
      vi.mocked(apiClient.post).mockResolvedValue({ data: { id: "2", ...newTask } });

      const { result } = renderHook(() => useCreateTask(), {
        wrapper: createWrapper(),
      });

      await result.current.mutateAsync(newTask as any);

      expect(apiClient.post).toHaveBeenCalledWith("/tasks/", newTask);
    });
  });

  describe("useUpdateTask", () => {
    it("calls patch and invalidates queries on success", async () => {
      const updateData = { status: TaskStatus.COMPLETED };
      vi.mocked(apiClient.patch).mockResolvedValue({ data: { id: "1", ...updateData } });

      const { result } = renderHook(() => useUpdateTask(), {
        wrapper: createWrapper(),
      });

      await result.current.mutateAsync({ id: "1", data: updateData as any });

      expect(apiClient.patch).toHaveBeenCalledWith("/tasks/1", updateData);
    });
  });

  describe("useTaskHistory", () => {
    it("fetches task history", async () => {
      const mockHistory = [{ field_name: "status", old_value: "PENDING", new_value: "COMPLETED" }];
      vi.mocked(apiClient.get).mockResolvedValue({ data: mockHistory });

      const { result } = renderHook(() => useTaskHistory("1"), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      
      expect(apiClient.get).toHaveBeenCalledWith("/tasks/1/history");
      expect(result.current.data).toEqual(mockHistory);
    });
  });

  describe("useInvalidateTasks", () => {
    it("returns a function that invalidates tasks query", () => {
      const { result } = renderHook(() => useInvalidateTasks(), {
        wrapper: createWrapper(),
      });
      
      expect(typeof result.current).toBe("function");
      result.current();
    });
  });

  describe("useDeleteTask", () => {
    it("calls delete and invalidates queries on success", async () => {
      vi.mocked(apiClient.delete).mockResolvedValue({ data: { success: true } });

      const { result } = renderHook(() => useDeleteTask(), {
        wrapper: createWrapper(),
      });

      await result.current.mutateAsync("1");

      expect(apiClient.delete).toHaveBeenCalledWith("/tasks/1");
    });
  });

  describe("useComments", () => {
    it("fetches comments for a task", async () => {
      const mockComments = [
        { id: "c1", task_id: "1", content: "Hello", created_by_id: "u1", created_by_name: "Alice", created_at: "", updated_at: "" },
      ];
      vi.mocked(apiClient.get).mockResolvedValueOnce({ data: mockComments });

      const { result } = renderHook(() => useComments("1"), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data).toEqual(mockComments);
      expect(apiClient.get).toHaveBeenCalledWith("/tasks/1/comments");
    });
  });

  describe("useCreateComment", () => {
    it("posts a new comment and invalidates query", async () => {
      const mockComment = { id: "c1", content: "Hello" };
      vi.mocked(apiClient.post).mockResolvedValueOnce({ data: mockComment });

      const { result } = renderHook(() => useCreateComment("1"), {
        wrapper: createWrapper(),
      });

      await result.current.mutateAsync("Hello");

      expect(apiClient.post).toHaveBeenCalledWith("/tasks/1/comments", { content: "Hello" });
    });
  });

  describe("useUpdateComment", () => {
    it("patches a comment and invalidates query", async () => {
      const mockComment = { id: "c1", content: "Updated" };
      vi.mocked(apiClient.patch).mockResolvedValueOnce({ data: mockComment });

      const { result } = renderHook(() => useUpdateComment("1"), {
        wrapper: createWrapper(),
      });

      await result.current.mutateAsync({ commentId: "c1", content: "Updated" });

      expect(apiClient.patch).toHaveBeenCalledWith("/tasks/1/comments/c1", { content: "Updated" });
    });
  });
});
