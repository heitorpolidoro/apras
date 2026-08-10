import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { TaskStatus, TaskPriority } from "../types";

import TaskList from "./TaskList";
import TaskBoard from "./TaskBoard";
import TaskForm from "./TaskForm";
import TaskDetailsView from "./TaskDetailsView";
import { useTasks } from "../hooks/useTasks";
import { useCategories } from "../hooks/useCategories";
import { useAssignableUsers } from "../../../hooks/useUsers";
import { Button } from "../../../components/ui/button";
import { Select } from "../../../components/ui/select";
import { AlertModal } from "../../../components/ui/alert-modal";
import { Plus, LayoutGrid, List } from "lucide-react";
import { getStatusLabel } from "../utils/taskUtils";

const TaskDashboard: React.FC = () => {
  const { t } = useTranslation();
  const [viewMode, setViewMode] = useState<"list" | "board">("board");
  const [filters, setFilters] = useState<{
    status: TaskStatus | null;
    priority: TaskPriority | null;
    category_id: string | null;
    assigned_to_id: string | null;
  }>({ status: null, priority: null, category_id: null, assigned_to_id: null });

  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [isEditing, setIsEditing] = useState(false);

  const { data: tasks, isLoading, isError, error } = useTasks(filters);
  const { data: categories } = useCategories();
  const { data: users } = useAssignableUsers();

  const selectedTask = tasks?.find((t) => t.id === selectedTaskId);

  const handleFilterChange = (
    filterType: "status" | "priority" | "category_id" | "assigned_to_id",
    value: TaskStatus | TaskPriority | string | null,
  ) => {
    setFilters((prev) => ({ ...prev, [filterType]: value }));
  };

  const clearFilters = () =>
    setFilters({
      status: null,
      priority: null,
      category_id: null,
      assigned_to_id: null,
    });

  const handleTaskClick = (taskId: string) => {
    setSelectedTaskId(taskId);
    setIsEditing(false);
    setIsCreating(false);
  };

  const handleCreateNewTask = () => {
    setIsCreating(true);
    setSelectedTaskId(null);
    setIsEditing(false);
  };

  const handleEditTask = () => setIsEditing(true);

  const handleCloseOverlay = () => {
    setSelectedTaskId(null);
    setIsCreating(false);
    setIsEditing(false);
  };

  const handleOverlayKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" || e.key === " ") handleCloseOverlay();
  };

  const showModal = isCreating || !!selectedTask;

  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-foreground">
          {t("tasks.dashboard.title")}
        </h1>
        <Button onClick={handleCreateNewTask}>
          <Plus className="size-4" />
          {t("tasks.dashboard.newTask")}
        </Button>
      </div>

      {/* Error Message */}
      <AlertModal
        open={isError}
        onClose={() => {}}
        variant="destructive"
        title="Erro de conexão"
        message={t("tasks.dashboard.connectionError")}
      />

      {/* Filters & View Toggle */}
      <div className="flex flex-wrap items-center justify-between gap-4 mb-6 p-4 rounded-lg border bg-muted/30">
        <div className="flex flex-wrap gap-3">
          <Select
            value={filters.status ?? ""}
            onChange={(e) =>
              handleFilterChange(
                "status",
                (e.target.value as TaskStatus) || null,
              )
            }
            className="w-40"
          >
            <option value="">{t("tasks.dashboard.allStatuses")}</option>
            {Object.values(TaskStatus).map((s) => (
              <option key={s} value={s}>
                {getStatusLabel(s, t)}
              </option>
            ))}
          </Select>

          <Select
            value={filters.priority ?? ""}
            onChange={(e) =>
              handleFilterChange(
                "priority",
                (e.target.value as TaskPriority) || null,
              )
            }
            className="w-40"
          >
            <option value="">{t("tasks.dashboard.allPriorities")}</option>
            {Object.values(TaskPriority).map((p) => (
              <option key={p} value={p}>
                {t(`tasks.priority.${p}`)}
              </option>
            ))}
          </Select>

          <Select
            value={filters.category_id ?? ""}
            onChange={(e) =>
              handleFilterChange("category_id", e.target.value || null)
            }
            className="w-40"
          >
            <option value="">{t("tasks.dashboard.allCategories")}</option>
            {categories?.map((cat) => (
              <option key={cat.id} value={cat.id}>
                {cat.name}
              </option>
            ))}
          </Select>

          <Select
            value={filters.assigned_to_id ?? ""}
            onChange={(e) =>
              handleFilterChange("assigned_to_id", e.target.value || null)
            }
            className="w-48"
          >
            <option value="">{t("tasks.dashboard.allAssignees")}</option>
            {users?.map((user) => (
              <option key={user.id} value={user.id}>
                {user.full_name}
              </option>
            ))}
          </Select>

          {(filters.status ||
            filters.priority ||
            filters.category_id ||
            filters.assigned_to_id) && (
            <Button variant="ghost" size="sm" onClick={clearFilters}>
              {t("tasks.dashboard.clearFilters")}
            </Button>
          )}
        </div>

        <div className="flex items-center border rounded-lg p-1 bg-background">
          <Button
            variant={viewMode === "board" ? "secondary" : "ghost"}
            size="sm"
            className="px-3"
            onClick={() => setViewMode("board")}
            title={t("tasks.dashboard.viewBoard")}
          >
            <LayoutGrid className="size-4 mr-2" />
            {t("tasks.dashboard.viewBoard")}
          </Button>
          <Button
            variant={viewMode === "list" ? "secondary" : "ghost"}
            size="sm"
            className="px-3"
            onClick={() => setViewMode("list")}
            title={t("tasks.dashboard.viewList")}
          >
            <List className="size-4 mr-2" />
            {t("tasks.dashboard.viewList")}
          </Button>
        </div>
      </div>

      {/* Task view */}
      {viewMode === "list" ? (
        <TaskList
          tasks={tasks || []}
          isLoading={isLoading}
          isError={isError}
          error={error}
          filters={filters}
          onTaskClick={handleTaskClick}
        />
      ) : (
        <TaskBoard
          tasks={tasks || []}
          isLoading={isLoading}
          isError={isError}
          error={error}
          filters={filters}
          onTaskClick={handleTaskClick}
        />
      )}

      {/* Modal overlay */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <button
            className="absolute inset-0 bg-black/50 backdrop-blur-sm cursor-default"
            onClick={handleCloseOverlay}
            onKeyDown={handleOverlayKeyDown}
            aria-label={t("tasks.dashboard.closeModal")}
          />
          <dialog
            className="w-full max-w-lg max-h-[90vh] overflow-y-auto rounded-xl bg-card shadow-2xl z-10 block border-none p-0"
            open
            aria-modal="true"
          >
            {isCreating && (
              <TaskForm
                onCancel={handleCloseOverlay}
                onSuccess={handleCloseOverlay}
              />
            )}
            {selectedTask && !isEditing && (
              <TaskDetailsView
                task={selectedTask}
                onClose={handleCloseOverlay}
                onEdit={handleEditTask}
              />
            )}
            {selectedTask && isEditing && (
              <TaskForm
                task={selectedTask}
                onCancel={() => setIsEditing(false)}
                onSuccess={handleCloseOverlay}
              />
            )}
          </dialog>
        </div>
      )}
    </div>
  );
};

export default TaskDashboard;
