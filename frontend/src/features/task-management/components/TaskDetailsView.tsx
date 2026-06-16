import React from "react";
import { useTranslation } from "react-i18next";
import type { TaskPriority, TaskRead, TaskStatus } from "../types";
import { useUpdateTask } from "../hooks/useTasks";
import { useCategories } from "../hooks/useCategories";
import { useAssignableUsers } from "../../../hooks/useUsers";
import AuditTimeline from "./AuditTimeline";
import TaskComments from "./TaskComments";
import { Button } from "../../../components/ui/button";
import { cn } from "../../../lib/utils";
import { getStatusLabel, getPriorityLabel } from "../utils/taskUtils";

const PRIORITY_OPTIONS: TaskPriority[] = ["LOW", "MEDIUM", "HIGH", "URGENT"];

const inlineSelectClassName = cn(
  "appearance-none px-2 py-0.5 rounded text-xs font-medium",
  "border border-border/40 bg-background text-foreground",
  "cursor-pointer focus:ring-2 focus:ring-ring outline-none",
  "disabled:opacity-50 disabled:cursor-not-allowed",
);

interface TaskDetailsViewProps {
  task: TaskRead;
  onEdit: () => void;
  onClose: () => void;
}

const TaskDetailsView: React.FC<TaskDetailsViewProps> = ({
  task,
  onEdit,
  onClose,
}) => {
  const { t, i18n } = useTranslation();
  const updateTaskMutation = useUpdateTask();
  const { data: assignableUsers } = useAssignableUsers();
  const { data: categories } = useCategories();

  /** Updates the task status when the user selects a new value. */
  const handleStatusChange = (newStatus: TaskStatus) => {
    updateTaskMutation.mutate({ id: task.id, data: { status: newStatus } });
  };

  /** Updates the task priority when the user selects a new value. */
  const handlePriorityChange = (newPriority: TaskPriority) => {
    updateTaskMutation.mutate({ id: task.id, data: { priority: newPriority } });
  };

  /** Updates the assignee, sending null when the empty option is selected. */
  const handleAssignedToChange = (userId: string) => {
    updateTaskMutation.mutate({
      id: task.id,
      data: { assigned_to_id: userId === "" ? null : userId },
    });
  };

  /** Updates the task category when the user selects a new value. */
  const handleCategoryChange = (categoryId: string) => {
    updateTaskMutation.mutate({
      id: task.id,
      data: { category_id: categoryId },
    });
  };

  /** Formats a date value for display using the current locale. */
  const formatDate = (date: Date | string | null | undefined) => {
    if (!date) return t("tasks.details.notSet");
    return new Date(date).toLocaleString(
      i18n.language === "pt" ? "pt-BR" : "en-US",
    );
  };

  const statuses = [
    "PENDING",
    "IN_PROGRESS",
    "BLOCKED",
    "COMPLETED",
    "CANCELED",
  ];
  const displayStatuses = statuses.includes(task.status)
    ? statuses
    : [task.status, ...statuses];

  const activeCategories = categories?.filter((c) => c.is_active) ?? [];
  const currentCategory = categories?.find((c) => c.id === task.category_id);
  const categoryOptions =
    currentCategory && !currentCategory.is_active
      ? [currentCategory, ...activeCategories]
      : activeCategories;

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex flex-col gap-3 pb-4 border-b mb-4">
        <div className="flex items-start justify-between gap-4">
          <h2 className="text-xl font-semibold text-foreground leading-snug">
            {task.title}
          </h2>
          <div className="relative group shrink-0">
            <select
              aria-label="status"
              value={task.status}
              onChange={(e) => handleStatusChange(e.target.value as TaskStatus)}
              disabled={updateTaskMutation.isPending}
              className={cn(
                "appearance-none pl-3 pr-8 py-1 rounded-full text-xs font-bold uppercase tracking-wide border-none cursor-pointer focus:ring-2 focus:ring-ring outline-none",
                task.status === "PENDING" &&
                  "bg-[var(--status-pending-bg)] text-[var(--status-pending-fg)]",
                task.status === "IN_PROGRESS" &&
                  "bg-[var(--status-in-progress-bg)] text-[var(--status-in-progress-fg)]",
                task.status === "BLOCKED" &&
                  "bg-[var(--status-blocked-bg)] text-[var(--status-blocked-fg)]",
                task.status === "COMPLETED" &&
                  "bg-[var(--status-completed-bg)] text-[var(--status-completed-fg)]",
                task.status === "CANCELED" &&
                  "bg-[var(--status-canceled-bg)] text-[var(--status-canceled-fg)]",
              )}
            >
              {displayStatuses.map((status) => (
                <option
                  key={status}
                  value={status}
                  className="bg-background text-foreground"
                >
                  {getStatusLabel(status, t)}
                </option>
              ))}
            </select>
            <div className="absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none opacity-60">
              <svg className="size-3 fill-current" viewBox="0 0 20 20">
                <path d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" />
              </svg>
            </div>
          </div>
        </div>

        {/* Priority select — inline, replacing the static Badge */}
        <div className="flex gap-2 flex-wrap items-center">
          <select
            aria-label="priority"
            value={task.priority}
            onChange={(e) =>
              handlePriorityChange(e.target.value as TaskPriority)
            }
            disabled={updateTaskMutation.isPending}
            className={inlineSelectClassName}
          >
            {PRIORITY_OPTIONS.map((p) => (
              <option key={p} value={p}>
                {getPriorityLabel(p, t)}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Description */}
      <section className="mb-4">
        <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1">
          {t("tasks.details.description")}
        </p>
        <p className="text-sm text-foreground leading-relaxed whitespace-pre-wrap">
          {task.description || t("tasks.details.noDescription")}
        </p>
      </section>

      {/* Metadata grid */}
      <section className="mb-4">
        <div className="grid grid-cols-2 gap-3">
          {/* Assigned To — editable */}
          <div className="flex flex-col">
            <span className="text-xs text-muted-foreground mb-0.5">
              {t("tasks.details.assignedTo")}
            </span>
            <select
              aria-label="assigned_to"
              value={task.assigned_to_id ?? ""}
              onChange={(e) => handleAssignedToChange(e.target.value)}
              disabled={updateTaskMutation.isPending}
              className={inlineSelectClassName}
            >
              <option value="">{t("tasks.details.unassigned")}</option>
              {assignableUsers?.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.full_name || u.email}
                </option>
              ))}
            </select>
          </div>

          {/* Created By — static */}
          <div className="flex flex-col">
            <span className="text-xs text-muted-foreground mb-0.5">
              {t("tasks.details.createdBy")}
            </span>
            <span className="text-sm font-medium text-foreground">
              {task.created_by_name || task.created_by_id}
            </span>
          </div>

          {/* Category — editable, with color dot */}
          <div className="flex flex-col">
            <span className="text-xs text-muted-foreground mb-0.5">
              {t("tasks.details.category")}
            </span>
            <div className="flex items-center gap-1.5">
              <span
                data-testid="category-color-dot"
                className="inline-block size-2.5 rounded-full shrink-0"
                style={{ backgroundColor: task.category_color ?? undefined }}
              />
              <select
                aria-label="category"
                value={task.category_id}
                onChange={(e) => handleCategoryChange(e.target.value)}
                disabled={updateTaskMutation.isPending}
                className={inlineSelectClassName}
              >
                {categoryOptions.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Due Date — static */}
          <div className="flex flex-col">
            <span className="text-xs text-muted-foreground mb-0.5">
              {t("tasks.details.dueDate")}
            </span>
            <span className="text-sm font-medium text-foreground">
              {formatDate(task.due_date)}
            </span>
          </div>

          {/* Created At — static */}
          <div className="flex flex-col">
            <span className="text-xs text-muted-foreground mb-0.5">
              {t("tasks.details.createdAt")}
            </span>
            <span className="text-sm font-medium text-foreground">
              {formatDate(task.created_at)}
            </span>
          </div>

          {/* Updated At — static */}
          <div className="flex flex-col">
            <span className="text-xs text-muted-foreground mb-0.5">
              {t("tasks.details.updatedAt")}
            </span>
            <span className="text-sm font-medium text-foreground">
              {formatDate(task.updated_at)}
            </span>
          </div>
        </div>
      </section>

      {/* Comments */}
      <TaskComments taskId={task.id} />

      {/* Audit timeline */}
      <AuditTimeline taskId={task.id} />

      {/* Footer actions */}
      <div className="flex justify-end gap-3 pt-4 mt-4 border-t">
        <Button variant="outline" onClick={onClose}>
          {t("tasks.details.close")}
        </Button>
        <Button variant="success" onClick={onEdit}>
          {t("tasks.details.edit")}
        </Button>
      </div>
    </div>
  );
};

export default TaskDetailsView;
