import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import apiClient from "../../../api/client";
import type {
  TaskCommentRead,
  TaskRead,
  TaskStatus,
  TaskPriority,
  TaskCreate,
  TaskUpdate,
} from "../types";

/**
 * Options for fetching tasks, including various filters.
 */
interface FetchTasksOptions {
  /** Filter by task status. */
  status?: TaskStatus | null;
  /** Filter by task priority. */
  priority?: TaskPriority | null;
  /** Filter by the UUID of the assigned user. */
  assigned_to_id?: string | null;
  /** Filter by the UUID of the category. */
  category_id?: string | null;
}

/**
 * Fetches tasks from the API based on provided options.
 *
 * @param options - Filters for status, priority, and assignee.
 * @returns A promise with the list of tasks.
 */
const fetchTasks = async (options: FetchTasksOptions): Promise<TaskRead[]> => {
  const response = await apiClient.get("/tasks/", {
    params: {
      status: options.status,
      priority: options.priority,
      assigned_to_id: options.assigned_to_id,
      category_id: options.category_id,
    },
  });
  return response.data;
};

/**
 * Fetches a single task by its ID.
 *
 * @param id - The UUID of the task to fetch.
 * @returns A promise with the task data.
 */
const fetchTask = async (id: string): Promise<TaskRead> => {
  const response = await apiClient.get(`/tasks/${id}`);
  return response.data;
};

/**
 * Hook to retrieve and manage tasks with filtering.
 *
 * @param options - Filters for the task list.
 * @returns React Query result with task data.
 */
export const useTasks = (options: FetchTasksOptions) => {
  return useQuery<TaskRead[], Error>({
    queryKey: ["tasks", options],
    queryFn: () => fetchTasks(options),
    retry: 1, // Fail faster to show the connection error message
  });
};

/**
 * Hook to retrieve a single task by its ID.
 *
 * @param id - The UUID of the task.
 * @returns React Query result with task data.
 */
export const useTask = (id: string) => {
  return useQuery<TaskRead, Error>({
    queryKey: ["tasks", id],
    queryFn: () => fetchTask(id),
    enabled: !!id,
  });
};

/**
 * Hook to create a new task.
 *
 * @returns React Query mutation result.
 */
export const useCreateTask = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (newTask: TaskCreate) => apiClient.post("/tasks/", newTask),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tasks"] });
    },
  });
};

/**
 * Hook to update an existing task.
 *
 * @returns React Query mutation result.
 */
export const useUpdateTask = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: TaskUpdate }) =>
      apiClient.patch(`/tasks/${id}`, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ["tasks"] });
      queryClient.invalidateQueries({ queryKey: ["tasks", id] });
    },
  });
};

/**
 * Hook to move a task to another status, optimistically.
 *
 * This is the board drag-and-drop's only write (APRAS-62): the cached
 * `["tasks", …]` lists are updated in `onMutate`, rolled back in `onError`
 * and reconciled with the server in `onSettled`. *Undo* is a second call of
 * this same mutation with the previous status — never a cache replay — so a
 * failed undo is refused and reported by the server like any other write.
 *
 * @returns React Query mutation result.
 */
export const useUpdateTaskStatus = () => {
  const queryClient = useQueryClient();
  return useMutation<
    unknown,
    Error,
    { id: string; status: TaskStatus },
    { previous: [readonly unknown[], unknown][] }
  >({
    mutationFn: ({ id, status }) => apiClient.patch(`/tasks/${id}`, { status }),
    onMutate: async ({ id, status }) => {
      await queryClient.cancelQueries({ queryKey: ["tasks"] });
      const previous = queryClient.getQueriesData({ queryKey: ["tasks"] });
      queryClient.setQueriesData<TaskRead[]>({ queryKey: ["tasks"] }, (old) =>
        Array.isArray(old)
          ? old.map((task) => (task.id === id ? { ...task, status } : task))
          : old,
      );
      return { previous };
    },
    onError: (_error, _variables, context) => {
      context?.previous.forEach(([key, data]) => {
        queryClient.setQueryData(key, data);
      });
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["tasks"] });
    },
  });
};

/**
 * Fetches the audit history for a specific task.
 *
 * @param taskId - The UUID of the task.
 * @returns A promise with the task history records.
 */
const fetchTaskHistory = async (taskId: string) => {
  const response = await apiClient.get(`/tasks/${taskId}/history`);
  return response.data;
};

/**
 * Hook to retrieve the audit history of a task.
 *
 * @param taskId - The UUID of the task.
 * @returns React Query result with history data.
 */
export const useTaskHistory = (taskId: string) => {
  return useQuery({
    queryKey: ["tasks", taskId, "history"],
    queryFn: () => fetchTaskHistory(taskId),
    enabled: !!taskId,
  });
};

/**
 * Hook to delete a task.
 *
 * @returns React Query mutation result.
 */
export const useDeleteTask = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => apiClient.delete(`/tasks/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tasks"] });
    },
  });
};

/**
 * Hook to get a function that invalidates the tasks query.
 *
 * @returns A function to invalidate tasks.
 */
export const useInvalidateTasks = () => {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: ["tasks"] });
};

// ── Comments ──────────────────────────────────────────────────────────────

export const useComments = (taskId: string) => {
  return useQuery<TaskCommentRead[]>({
    queryKey: ["tasks", taskId, "comments"],
    queryFn: async () => {
      const response = await apiClient.get(`/tasks/${taskId}/comments`);
      return response.data;
    },
    enabled: !!taskId,
  });
};

export const useCreateComment = (taskId: string) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (content: string) =>
      apiClient.post<TaskCommentRead>(`/tasks/${taskId}/comments`, { content }),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["tasks", taskId, "comments"],
      });
    },
  });
};

export const useUpdateComment = (taskId: string) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      commentId,
      content,
    }: {
      commentId: string;
      content: string;
    }) =>
      apiClient.patch<TaskCommentRead>(
        `/tasks/${taskId}/comments/${commentId}`,
        { content },
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["tasks", taskId, "comments"],
      });
    },
  });
};
