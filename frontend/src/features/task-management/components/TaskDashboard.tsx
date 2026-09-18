import React, { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { TaskStatus, TaskPriority } from "../types";

import TaskList from "./TaskList";
import TaskBoard from "./TaskBoard";
import TaskForm from "./TaskForm";
import TaskDetailsView from "./TaskDetailsView";
import { useTasks, useUpdateTaskStatus } from "../hooks/useTasks";
import { useCategories } from "../hooks/useCategories";
import { useAssignableUsers } from "../../../hooks/useUsers";
import { Button } from "../../../components/ui/button";
import { Select } from "../../../components/ui/select";
import { AlertModal } from "../../../components/ui/alert-modal";
import { Plus, LayoutGrid, List, Undo2, X } from "lucide-react";
import { getStatusLabel, isOverdue, matchesSearch } from "../utils/taskUtils";
import TaskFilterBar, { type ServerFilterKey } from "./TaskFilterBar";

const TaskDashboard: React.FC = () => {
  const { t } = useTranslation();
  const [viewMode, setViewMode] = useState<"list" | "board">("board");
  // Two filter objects, not one (APRAS-62). `serverFilters` is the `useTasks`
  // query key; `clientFilters` never reaches it, so typing in the search box
  // re-filters the loaded list instead of refetching on every keystroke.
  const [serverFilters, setServerFilters] = useState<{
    status: TaskStatus | null;
    priority: TaskPriority | null;
    category_id: string | null;
    assigned_to_id: string | null;
  }>({ status: null, priority: null, category_id: null, assigned_to_id: null });
  const [clientFilters, setClientFilters] = useState<{
    search: string;
    overdueOnly: boolean;
  }>({ search: "", overdueOnly: false });
  const [lastMove, setLastMove] = useState<{
    taskId: string;
    title: string;
    from: TaskStatus;
    to: TaskStatus;
  } | null>(null);

  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [isEditing, setIsEditing] = useState(false);

  const { data: tasks, isLoading, isError, error } = useTasks(serverFilters);
  const { data: categories } = useCategories();
  const { data: users } = useAssignableUsers();
  const updateStatus = useUpdateTaskStatus();

  const filters = useMemo(
    () => ({ ...serverFilters, ...clientFilters }),
    [serverFilters, clientFilters],
  );

  const selectedTask = tasks?.find((t) => t.id === selectedTaskId);

  // The summary's two numbers, and the overdue counter. The counter ignores
  // `overdueOnly` itself: otherwise turning it on would make it count its own
  // result and always agree with the summary.
  const loadedTasks = useMemo(() => tasks ?? [], [tasks]);
  const matchingTasks = useMemo(
    () =>
      loadedTasks.filter((task) => {
        if (filters.status && task.status !== filters.status) return false;
        if (filters.priority && task.priority !== filters.priority)
          return false;
        if (
          filters.assigned_to_id &&
          task.assigned_to_id !== filters.assigned_to_id
        )
          return false;
        return matchesSearch(task, filters.search);
      }),
    [loadedTasks, filters],
  );
  const overdueCount = matchingTasks.filter((task) => isOverdue(task)).length;
  const visibleCount = filters.overdueOnly
    ? overdueCount
    : matchingTasks.length;

  // The confirmation strip is transient: it names the move just made and
  // offers to undo it, then gets out of the way.
  useEffect(() => {
    if (!lastMove) return undefined;
    const timer = setTimeout(() => setLastMove(null), 8_000);
    return () => clearTimeout(timer);
  }, [lastMove]);

  const handleTaskMove = (
    taskId: string,
    from: TaskStatus,
    to: TaskStatus,
  ) => {
    const moved = tasks?.find((task) => task.id === taskId);
    updateStatus.mutate({ id: taskId, status: to });
    setLastMove({ taskId, title: moved?.title ?? "", from, to });
  };

  const handleUndoMove = () => {
    if (!lastMove) return;
    // Undo is a second write, never a cache replay: the server stays the
    // single source of truth for the task's status.
    updateStatus.mutate({ id: lastMove.taskId, status: lastMove.from });
    setLastMove(null);
  };

  const handleFilterChange = (
    filterType: ServerFilterKey,
    value: TaskStatus | TaskPriority | string | null,
  ) => {
    setServerFilters((prev) => ({ ...prev, [filterType]: value }));
  };

  const clearFilters = () => {
    setServerFilters({
      status: null,
      priority: null,
      category_id: null,
      assigned_to_id: null,
    });
    setClientFilters({ search: "", overdueOnly: false });
  };

  const handleSearchChange = (search: string) =>
    setClientFilters((prev) => ({ ...prev, search }));

  const handleOverdueToggle = () =>
    setClientFilters((prev) => ({ ...prev, overdueOnly: !prev.overdueOnly }));

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
            value={serverFilters.status ?? ""}
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
            value={serverFilters.priority ?? ""}
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
            value={serverFilters.category_id ?? ""}
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
            value={serverFilters.assigned_to_id ?? ""}
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

      <TaskFilterBar
        search={clientFilters.search}
        onSearchChange={handleSearchChange}
        overdueOnly={clientFilters.overdueOnly}
        onOverdueToggle={handleOverdueToggle}
        overdueCount={overdueCount}
        visibleCount={visibleCount}
        totalCount={loadedTasks.length}
        filters={serverFilters}
        categories={categories}
        users={users}
        onClearFilter={(key) => handleFilterChange(key, null)}
        onClearAll={clearFilters}
      />

      {lastMove && (
        <div
          data-testid="task-move-strip"
          className="flex flex-wrap items-center gap-3 mb-4 rounded-lg border border-border/60 bg-muted/40 px-4 py-2 text-sm"
        >
          <span className="text-muted-foreground">
            {t("tasks.board.moved", {
              title: lastMove.title,
              from: getStatusLabel(lastMove.from, t),
              to: getStatusLabel(lastMove.to, t),
            })}
          </span>
          <Button variant="outline" size="sm" onClick={handleUndoMove}>
            <Undo2 className="size-4" />
            {t("tasks.board.undo")}
          </Button>
          <button
            type="button"
            className="ml-auto rounded-full p-1 text-muted-foreground hover:bg-black/10 dark:hover:bg-white/10"
            aria-label={t("tasks.board.dismissMove")}
            onClick={() => setLastMove(null)}
          >
            <X className="size-4" />
          </button>
        </div>
      )}

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
          onTaskMove={handleTaskMove}
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
