import React from "react";
import { useTranslation } from "react-i18next";
import type { TaskRead } from "../types";
import { TaskStatus } from "../types";
import TaskCard from "./TaskCard";
import { useTaskFiltering, type TaskFilters } from "../hooks/useTaskFiltering";
import { getStatusLabel } from "../utils/taskUtils";
import { useEffectiveIdentity } from "../../user-administration/context/useEffectiveIdentity";
import { canEditSimulatedTask } from "../utils/simulatedPermissions";

interface TaskBoardProps {
  tasks: TaskRead[];
  isLoading: boolean;
  isError: boolean;
  error: Error | null;
  filters: TaskFilters;
  onTaskClick?: (taskId: string) => void;
}

const TaskBoard: React.FC<TaskBoardProps> = ({
  tasks,
  isLoading,
  isError,
  error,
  filters,
  onTaskClick,
}) => {
  const { t } = useTranslation();
  const { role, userTypeIds, isSimulating } = useEffectiveIdentity();
  const filteredTasks = useTaskFiltering(tasks, filters, {
    isSimulating,
    role,
    userTypeIds,
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

  return (
    <div className="flex flex-col md:flex-row gap-6 overflow-x-auto pb-6 mt-4 min-h-[600px] items-start">
      {visibleColumns.map((column) => {
        const columnTasks = filteredTasks.filter(
          (task) => task.status === column.status,
        );

        return (
          <div
            key={column.status}
            className={`flex-1 min-w-[300px] w-full md:max-w-xs rounded-xl border border-border/50 ${column.colorClass} flex flex-col shadow-sm`}
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
                    onClick={() => onTaskClick?.(task.id)}
                    readOnly={
                      isSimulating && !!role
                        ? !canEditSimulatedTask(task, role, userTypeIds)
                        : false
                    }
                  />
                ))
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
};

export default TaskBoard;
