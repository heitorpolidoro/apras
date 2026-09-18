import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import type { TaskRead } from "../types";
import { TaskStatus } from "../types";
import TaskCard from "./TaskCard";
import { useTaskFiltering, type TaskFilters } from "../hooks/useTaskFiltering";
import { getStatusLabel } from "../utils/taskUtils";
import { useEffectiveIdentity } from "../../user-administration/context/useEffectiveIdentity";
import { useEffectivePermissionSet } from "../../user-administration/access/useCanAccess";
import { canEditSimulatedTask } from "../utils/simulatedPermissions";

interface TaskBoardProps {
  tasks: TaskRead[];
  isLoading: boolean;
  isError: boolean;
  error: Error | null;
  filters: TaskFilters;
  onTaskClick?: (taskId: string) => void;
  /**
   * Called when a card is dropped on a column other than its own. The board
   * itself performs no write: the dashboard owns the mutation and the undo
   * strip, so the same drop is one `PATCH` and one confirmation.
   */
  onTaskMove?: (taskId: string, from: TaskStatus, to: TaskStatus) => void;
}

const TaskBoard: React.FC<TaskBoardProps> = ({
  tasks,
  isLoading,
  isError,
  error,
  filters,
  onTaskClick,
  onTaskMove,
}) => {
  const { t } = useTranslation();
  const [dragged, setDragged] = useState<{
    id: string;
    from: TaskStatus;
  } | null>(null);
  const [dropTarget, setDropTarget] = useState<TaskStatus | null>(null);
  const { roleIds, isSimulating } = useEffectiveIdentity();
  const { has } = useEffectivePermissionSet();
  const filteredTasks = useTaskFiltering(tasks, filters, {
    isSimulating,
    has,
    roleIds,
  });

  if (isLoading) {
    return (
      <p className="text-center text-muted-foreground py-10">
        {t("tasks.list.loading")}
      </p>
    );
  }

  if (isError) {
    return (
      <p className="text-center text-destructive py-10">
        {t("tasks.list.error", { message: error?.message })}
      </p>
    );
  }

  const columns: {
    status: TaskStatus;
    label: string;
    colorClass: string;
    headerColorClass: string;
  }[] = [
    {
      status: TaskStatus.PENDING,
      label: getStatusLabel(TaskStatus.PENDING, t),
      colorClass: "bg-slate-50/50 dark:bg-slate-900/20",
      headerColorClass: "border-t-slate-400",
    },
    {
      status: TaskStatus.IN_PROGRESS,
      label: getStatusLabel(TaskStatus.IN_PROGRESS, t),
      colorClass: "bg-blue-50/50 dark:bg-blue-900/20",
      headerColorClass: "border-t-blue-400",
    },
    {
      status: TaskStatus.BLOCKED,
      label: getStatusLabel(TaskStatus.BLOCKED, t),
      colorClass: "bg-amber-50/50 dark:bg-amber-900/20",
      headerColorClass: "border-t-amber-500",
    },
    {
      status: TaskStatus.COMPLETED,
      label: getStatusLabel(TaskStatus.COMPLETED, t),
      colorClass: "bg-green-50/50 dark:bg-green-900/20",
      headerColorClass: "border-t-green-400",
    },
    {
      status: TaskStatus.CANCELED,
      label: getStatusLabel(TaskStatus.CANCELED, t),
      colorClass: "bg-red-50/50 dark:bg-red-900/20",
      headerColorClass: "border-t-red-400",
    },
  ];

  // If a status filter is active, only show that column (optional, but consistent with TaskList)
  const visibleColumns = filters.status
    ? columns.filter((col) => col.status === filters.status)
    : columns;

  // A status filter leaves a single column on screen, so a card would have
  // exactly one legal destination — its own, a no-op. Rather than offer a
  // dead affordance, dragging is off and the header names the reason.
  const dragEnabled = !filters.status;

  const handleDragStart = (taskId: string, from: TaskStatus) => {
    setDragged({ id: taskId, from });
  };

  const handleDragEnd = () => {
    setDragged(null);
    setDropTarget(null);
  };

  const handleDragOver = (e: React.DragEvent, status: TaskStatus) => {
    if (!dragEnabled || !dragged || dragged.from === status) return;
    // Without preventDefault the browser refuses the drop outright.
    e.preventDefault();
    setDropTarget(status);
  };

  const handleDragLeave = (status: TaskStatus) => {
    setDropTarget((current) => (current === status ? null : current));
  };

  const handleDrop = (e: React.DragEvent, status: TaskStatus) => {
    e.preventDefault();
    const inFlight = dragged;
    handleDragEnd();
    if (!dragEnabled || !inFlight || inFlight.from === status) return;
    onTaskMove?.(inFlight.id, inFlight.from, status);
  };

  return (
    <div className="flex flex-col md:flex-row gap-6 overflow-x-auto pb-6 mt-4 min-h-[600px] items-start">
      {visibleColumns.map((column) => {
        const columnTasks = filteredTasks.filter(
          (task) => task.status === column.status,
        );

        return (
          <div
            key={column.status}
            data-testid={`task-column-${column.status}`}
            data-drop-target={dropTarget === column.status ? "true" : undefined}
            onDragOver={(e) => handleDragOver(e, column.status)}
            onDragLeave={() => handleDragLeave(column.status)}
            onDrop={(e) => handleDrop(e, column.status)}
            className={`flex-1 min-w-[300px] w-full md:max-w-xs rounded-xl border ${
              dropTarget === column.status
                ? "border-primary border-2 ring-4 ring-primary/20"
                : "border-border/50"
            } ${column.colorClass} flex flex-col shadow-sm`}
          >
            <div
              className={`p-4 border-b border-border/50 border-t-4 ${column.headerColorClass} rounded-t-xl flex items-center justify-between bg-card/50`}
            >
              <h3 className="font-bold text-sm uppercase tracking-wider text-foreground/80">
                {column.label}
              </h3>
              <span className="bg-background/80 text-muted-foreground px-2.5 py-0.5 rounded-full text-xs font-bold border border-border/50">
                {columnTasks.length}
              </span>
            </div>
            {!dragEnabled && (
              <p className="px-4 pt-2 text-[11px] italic text-muted-foreground">
                {t("tasks.board.dragDisabledByStatusFilter")}
              </p>
            )}
            <div className="p-3 space-y-4 flex-1 overflow-y-auto max-h-[70vh]">
              {columnTasks.length === 0 ? (
                <div className="h-24 border-2 border-dashed border-border/40 rounded-xl flex items-center justify-center text-muted-foreground text-xs italic bg-background/30">
                  {t("tasks.list.empty")}
                </div>
              ) : (
                columnTasks.map((task) => (
                  <TaskCard
                    key={task.id}
                    task={task}
                    search={filters.search}
                    onClick={() => onTaskClick?.(task.id)}
                    readOnly={
                      isSimulating
                        ? !canEditSimulatedTask(task, has, roleIds)
                        : false
                    }
                    draggable={dragEnabled}
                    isDragging={dragged?.id === task.id}
                    onDragStart={(taskId) =>
                      handleDragStart(taskId, column.status)
                    }
                    onDragEnd={handleDragEnd}
                  />
                ))
              )}
              {dragged?.from === column.status && (
                <div
                  data-testid="task-drag-origin-gap"
                  className="h-20 border-2 border-dashed border-border/60 rounded-xl bg-background/30"
                />
              )}
              {dropTarget === column.status && (
                <p
                  data-testid="task-drop-hint"
                  className="text-center text-[11px] font-medium text-primary"
                >
                  {t("tasks.board.dropHint", { status: column.label })}
                </p>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
};

export default TaskBoard;
