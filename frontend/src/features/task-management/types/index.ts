/**
 * Represents the possible statuses of a task.
 */
export type TaskStatus =
  | "PENDING"
  | "IN_PROGRESS"
  | "BLOCKED"
  | "COMPLETED"
  | "CANCELED";

/**
 * Constants for task statuses.
 */
export const TaskStatus = {
  PENDING: "PENDING" as TaskStatus,
  IN_PROGRESS: "IN_PROGRESS" as TaskStatus,
  BLOCKED: "BLOCKED" as TaskStatus,
  COMPLETED: "COMPLETED" as TaskStatus,
  CANCELED: "CANCELED" as TaskStatus,
};

/**
 * Represents the possible priority levels of a task.
 */
export type TaskPriority = "LOW" | "MEDIUM" | "HIGH" | "URGENT";

/**
 * Constants for task priority levels.
 */
export const TaskPriority = {
  LOW: "LOW" as TaskPriority,
  MEDIUM: "MEDIUM" as TaskPriority,
  HIGH: "HIGH" as TaskPriority,
  URGENT: "URGENT" as TaskPriority,
};

/**
 * Interface for reading category data from the API.
 */
export interface CategoryRead {
  id: string;
  name: string;
  color: string;
  is_active: boolean;
}

/**
 * Base interface for task data.
 */
export interface TaskBase {
  /** The title of the task. */
  title: string;
  /** An optional description of the task. */
  description?: string | null;
  /** The current status of the task. */
  status: TaskStatus;
  /** The priority level of the task. */
  priority: TaskPriority;
  /** The optional deadline for the task. */
  due_date?: Date | string | null;
  /** The UUID of the user assigned to the task. */
  assigned_to_id?: string | null;
  /** The UUID of the category this task belongs to. */
  category_id: string;
  /** The UUID of the user type this task is targeted to. */
  visible_to_id?: string | null;
}

/**
 * Interface for task creation data.
 */
export interface TaskCreate extends Omit<
  TaskBase,
  "status" | "priority" | "due_date" | "assigned_to_id"
> {
  title: string;
  description?: string | null;
  priority?: TaskPriority;
  due_date?: Date | string | null;
  assigned_to_id?: string | null;
  category_id: string;
}

/**
 * Interface for task update data.
 */
export interface TaskUpdate extends Partial<TaskBase> {
  status?: TaskStatus;
  priority?: TaskPriority;
  visible_to_id?: string | null;
}

/**
 * Interface for reading task data from the API.
 */
export interface TaskRead extends TaskBase {
  /** Unique identifier for the task. */
  id: string;
  /** When the task was created. */
  created_at: Date | string;
  /** When the task was last updated. */
  updated_at: Date | string;
  /** The UUID of the user who created the task. */
  created_by_id: string;
  /** The name of the user who created the task. */
  created_by_name?: string | null;
  /** The name of the user assigned to the task. */
  assigned_to_name?: string | null;
  /** The display name of the category. */
  category_name?: string | null;
  /** The hex color of the category. */
  category_color?: string | null;
  /** The name of the target user type. */
  visible_to_name?: string | null;
}

/**
 * Interface for reading task audit history.
 */
export interface TaskHistoryRead {
  /** Unique identifier for the history entry. */
  id: string;
  /** The UUID of the task this entry belongs to. */
  task_id: string;
  /** The UUID of the user who made the change. */
  changed_by_id: string;
  /** The name of the user who made the change. */
  user_name: string;
  /** The name of the field that was changed. */
  field_name: string;
  /** The value before the change. */
  old_value: string | null;
  /** The value after the change. */
  new_value: string | null;
  /** When the change occurred. */
  timestamp: Date | string;
  /** Resolved user info for assigned_to_id old value. */
  resolved_old_value: { name: string; role: string } | null;
  /** Resolved user info for assigned_to_id new value. */
  resolved_new_value: { name: string; role: string } | null;
}

/**
 * Interface for reading a task comment.
 */
export interface TaskCommentRead {
  id: string;
  task_id: string;
  created_by_id: string;
  created_by_name: string;
  content: string;
  created_at: string;
  updated_at: string;
}
