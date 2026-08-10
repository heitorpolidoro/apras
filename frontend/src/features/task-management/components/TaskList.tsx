import React from "react";
import { useTranslation } from "react-i18next";
import { Lock } from "lucide-react";
import type { TaskRead } from "../types";
import { Badge } from "../../../components/ui/badge";
import { useTaskFiltering, type TaskFilters } from "../hooks/useTaskFiltering";
import {
  getStatusLabel,
  getPriorityLabel,
  statusVariant,
  priorityVariant,
} from "../utils/taskUtils";
import { useEffectiveIdentity } from "../../user-administration/context/useEffectiveIdentity";
import { canEditSimulatedTask } from "../utils/simulatedPermissions";

interface TaskListProps {
  tasks: TaskRead[];
  isLoading: boolean;
  isError: boolean;
  error: Error | null;
  filters: TaskFilters;
  onTaskClick?: (taskId: string) => void;
}

const TaskList: React.FC<TaskListProps> = ({
  tasks,
  isLoading,
  isError,
  error,
  filters,
  onTaskClick,
}) => {
  const { t, i18n } = useTranslation();
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

  if (tasks.length === 0) {
    return (
      <p className="text-center text-muted-foreground py-10">
        {t("tasks.list.empty")}
      </p>
    );
  }

  if (filteredTasks.length === 0) {
    return (
      <p className="text-center text-muted-foreground py-10">
        {t("tasks.list.emptyFiltered")}
      </p>
    );
  }

  return (
    <div className="mt-4 overflow-x-auto rounded-xl border border-border/40 bg-card shadow-sm">
      <table className="w-full text-left border-collapse">
        <thead className="bg-muted/50 border-b border-border/40">
          <tr>
            <th className="px-6 py-4 text-xs font-bold uppercase tracking-wider text-muted-foreground">
              {t("tasks.list.headerTitle")}
            </th>
            <th className="px-6 py-4 text-xs font-bold uppercase tracking-wider text-muted-foreground">
              {t("tasks.list.headerCategory")}
            </th>
            <th className="px-6 py-4 text-xs font-bold uppercase tracking-wider text-muted-foreground">
              {t("tasks.list.headerStatus")}
            </th>
            <th className="px-6 py-4 text-xs font-bold uppercase tracking-wider text-muted-foreground">
              {t("tasks.list.headerPriority")}
            </th>
            <th className="px-6 py-4 text-xs font-bold uppercase tracking-wider text-muted-foreground">
              {t("tasks.list.headerAssignee")}
            </th>
            <th className="px-6 py-4 text-xs font-bold uppercase tracking-wider text-muted-foreground">
              {t("tasks.list.headerDueDate")}
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border/40">
          {filteredTasks.map((task) => (
            <tr
              key={task.id}
              onClick={() => onTaskClick?.(task.id)}
              className="group hover:bg-muted/30 transition-colors cursor-pointer"
            >
              <td className="px-6 py-4">
                <div className="flex flex-col">
                  <span className="font-semibold text-foreground group-hover:text-primary transition-colors flex items-center gap-1.5">
                    {task.title}
                    {isSimulating &&
                      role &&
                      !canEditSimulatedTask(task, role, userTypeIds) && (
                        <span
                          data-testid="task-readonly-indicator"
                          title={t("simulation.readOnlyTask")}
                          aria-label={t("simulation.readOnlyTask")}
                          className="text-muted-foreground shrink-0 inline-flex"
                        >
                          <Lock className="size-3" />
                        </span>
                      )}
                  </span>
                  {task.description && (
                    <span className="text-xs text-muted-foreground line-clamp-1 mt-0.5">
                      {task.description}
                    </span>
                  )}
                </div>
              </td>
              <td className="px-6 py-4">
                {task.category_name ? (
                  <div className="flex items-center gap-1.5">
                    <span
                      className="size-2 rounded-full shrink-0"
                      style={{ backgroundColor: task.category_color ?? "#808080" }}
                    />
                    <span className="text-sm text-foreground">
                      {task.category_name}
                    </span>
                  </div>
                ) : (
                  <span className="text-xs text-muted-foreground italic">
                    {t("tasks.list.noCategory")}
                  </span>
                )}
              </td>
              <td className="px-6 py-4">
                <Badge variant={statusVariant(task.status)}>
                  {getStatusLabel(task.status, t)}
                </Badge>
              </td>
              <td className="px-6 py-4">
                <Badge variant={priorityVariant(task.priority)}>
                  {getPriorityLabel(task.priority, t)}
                </Badge>
              </td>
              <td className="px-6 py-4">
                {task.assigned_to_name ? (
                  <span className="text-sm text-foreground">
                    {task.assigned_to_name}
                  </span>
                ) : (
                  <span className="text-xs text-muted-foreground italic">
                    {t("tasks.list.unassigned")}
                  </span>
                )}
              </td>
              <td className="px-6 py-4">
                {task.due_date ? (
                  <span className="text-sm text-muted-foreground whitespace-nowrap">
                    {new Date(task.due_date).toLocaleDateString(
                      i18n.language === "pt" ? "pt-BR" : "en-US",
                    )}
                  </span>
                ) : (
                  <span className="text-xs text-muted-foreground italic">
                    -
                  </span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default TaskList;
