import React, { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { AlertTriangle, Search, X } from "lucide-react";
import type { CategoryRead, TaskPriority, TaskStatus } from "../types";
import type { User } from "../../../types/auth";
import { Input } from "../../../components/ui/input";
import { Button } from "../../../components/ui/button";
import { getStatusLabel } from "../utils/taskUtils";

/** The server-side filters the bar describes; the dashboard owns them. */
export interface ServerFilterState {
  status: TaskStatus | null;
  priority: TaskPriority | null;
  category_id: string | null;
  assigned_to_id: string | null;
}

export type ServerFilterKey = keyof ServerFilterState;

interface TaskFilterBarProps {
  /** The committed search text (the dashboard's `clientFilters.search`). */
  search: string;
  onSearchChange: (value: string) => void;
  overdueOnly: boolean;
  onOverdueToggle: () => void;
  /** How many of the visible tasks are past due. */
  overdueCount: number;
  visibleCount: number;
  totalCount: number;
  filters: ServerFilterState;
  categories?: CategoryRead[];
  users?: User[];
  onClearFilter: (key: ServerFilterKey) => void;
  onClearAll: () => void;
}

/** How long the search input waits before the board re-filters. */
const SEARCH_DEBOUNCE_MS = 200;

interface Chip {
  key: string;
  label: string;
  className: string;
  icon?: React.ReactNode;
}

/**
 * The task board's top bar: a free-text search, one removable chip per active
 * filter, an overdue counter that filters the board, and a summary saying how
 * many tasks the filters leave visible out of the total.
 *
 * The search is **client-side** and never reaches `useTasks`'s query key, so
 * typing re-filters the already-loaded list instead of refetching.
 */
const TaskFilterBar: React.FC<TaskFilterBarProps> = ({
  search,
  onSearchChange,
  overdueOnly,
  onOverdueToggle,
  overdueCount,
  visibleCount,
  totalCount,
  filters,
  categories,
  users,
  onClearFilter,
  onClearAll,
}) => {
  const { t } = useTranslation();
  const [text, setText] = useState(search);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(
    () => () => {
      if (timer.current) clearTimeout(timer.current);
    },
    [],
  );

  const handleType = (value: string) => {
    setText(value);
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(
      () => onSearchChange(value),
      SEARCH_DEBOUNCE_MS,
    );
  };

  /**
   * Removes exactly one filter and leaves every other one alone. The search
   * clears with no debounce: a chip removal is a decision, not typing.
   */
  const handleRemoveChip = (key: string) => {
    if (key === "search") {
      if (timer.current) clearTimeout(timer.current);
      setText("");
      onSearchChange("");
      return;
    }
    if (key === "overdueOnly") {
      onOverdueToggle();
      return;
    }
    onClearFilter(key as ServerFilterKey);
  };

  const handleClearAll = () => {
    if (timer.current) clearTimeout(timer.current);
    setText("");
    onClearAll();
  };

  const chips: Chip[] = [];

  if (search.trim()) {
    chips.push({
      key: "search",
      label: t("tasks.dashboard.chipSearch", { value: search }),
      className: "bg-muted text-foreground",
      icon: <Search className="size-3" />,
    });
  }
  if (overdueOnly) {
    chips.push({
      key: "overdueOnly",
      label: t("tasks.dashboard.chipOverdue"),
      className: "bg-destructive/10 text-destructive",
      icon: <AlertTriangle className="size-3" />,
    });
  }
  if (filters.status) {
    chips.push({
      key: "status",
      label: t("tasks.dashboard.chipStatus", {
        value: getStatusLabel(filters.status, t),
      }),
      className: "bg-muted text-foreground",
    });
  }
  if (filters.priority) {
    chips.push({
      key: "priority",
      label: t("tasks.dashboard.chipPriority", {
        value: t(`tasks.priority.${filters.priority}`),
      }),
      className: "bg-amber-100 text-amber-800 dark:bg-amber-500/20 dark:text-amber-300",
    });
  }
  if (filters.category_id) {
    const category = categories?.find((c) => c.id === filters.category_id);
    chips.push({
      key: "category_id",
      label: t("tasks.dashboard.chipCategory", {
        value: category?.name ?? filters.category_id,
      }),
      className: "bg-muted text-foreground",
    });
  }
  if (filters.assigned_to_id) {
    const user = users?.find((u) => u.id === filters.assigned_to_id);
    chips.push({
      key: "assigned_to_id",
      label: t("tasks.dashboard.chipAssignee", {
        value: user?.full_name || user?.email || filters.assigned_to_id,
      }),
      className: "bg-sky-100 text-sky-800 dark:bg-sky-500/20 dark:text-sky-300",
    });
  }

  return (
    <div className="flex flex-col gap-3 mb-4" data-testid="task-filter-bar">
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[240px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
          <Input
            id="task-search"
            type="search"
            className="pl-9"
            aria-label={t("tasks.dashboard.searchLabel")}
            placeholder={t("tasks.dashboard.searchPlaceholder")}
            value={text}
            onChange={(e) => handleType(e.target.value)}
          />
        </div>

        {overdueCount > 0 && (
          <Button
            type="button"
            variant={overdueOnly ? "secondary" : "outline"}
            size="sm"
            aria-pressed={overdueOnly}
            onClick={onOverdueToggle}
          >
            <AlertTriangle className="size-4 text-destructive" />
            {t("tasks.dashboard.overdueCount", { count: overdueCount })}
          </Button>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs font-medium text-muted-foreground">
          {t("tasks.dashboard.summary", {
            visible: visibleCount,
            total: totalCount,
          })}
        </span>
        {chips.map((chip) => (
          <span
            key={chip.key}
            className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs ${chip.className}`}
          >
            {chip.icon}
            {chip.label}
            <button
              type="button"
              className="rounded-full p-0.5 hover:bg-black/10 dark:hover:bg-white/10"
              aria-label={`${t("tasks.dashboard.removeFilter")}: ${chip.label}`}
              onClick={() => handleRemoveChip(chip.key)}
            >
              <X className="size-3" />
            </button>
          </span>
        ))}
        {chips.length > 0 && (
          <Button variant="ghost" size="sm" onClick={handleClearAll}>
            {t("tasks.dashboard.clearFilters")}
          </Button>
        )}
      </div>
    </div>
  );
};

export default TaskFilterBar;
