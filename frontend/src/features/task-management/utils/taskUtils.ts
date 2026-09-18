import type { TFunction } from "i18next";
import type { BadgeProps } from "../../../components/ui/badge";
import type { TaskRead } from "../types";

export type BadgeVariant = BadgeProps["variant"];

export function getStatusLabel(status: string, t: TFunction): string {
  const map: Record<string, string> = {
    PENDING: t("tasks.details.statusPending"),
    IN_PROGRESS: t("tasks.details.statusInProgress"),
    BLOCKED: t("tasks.details.statusBlocked"),
    COMPLETED: t("tasks.details.statusCompleted"),
    CANCELED: t("tasks.details.statusCanceled"),
  };
  return map[status] || status;
}

export function statusVariant(status: string): BadgeVariant {
  const map: Record<string, BadgeVariant> = {
    PENDING: "pending",
    IN_PROGRESS: "in_progress",
    BLOCKED: "blocked",
    COMPLETED: "completed",
    CANCELED: "canceled",
  };
  return map[status] ?? "default";
}

export function getPriorityLabel(priority: string, t: TFunction): string {
  const map: Record<string, string> = {
    LOW: t("tasks.priority.LOW"),
    MEDIUM: t("tasks.priority.MEDIUM"),
    HIGH: t("tasks.priority.HIGH"),
    URGENT: t("tasks.priority.URGENT"),
  };
  return map[priority] || priority;
}

export function priorityVariant(priority: string): BadgeVariant {
  const map: Record<string, BadgeVariant> = {
    LOW: "low",
    MEDIUM: "medium",
    HIGH: "high",
    URGENT: "urgent",
  };
  return map[priority] ?? "default";
}

/**
 * Lower-cases a value and strips its diacritics, so `manutencao` matches
 * `Manutenção`. A null/undefined value normalises to an empty string.
 */
export function normalizeText(value: string | null | undefined): string {
  return (value ?? "")
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .toLowerCase();
}

/**
 * Whether a task matches a free-text search over its title or description.
 * A blank (or whitespace-only) search matches every task.
 */
export function matchesSearch(
  task: Pick<TaskRead, "title" | "description">,
  search: string | null | undefined,
): boolean {
  const needle = normalizeText(search).trim();
  if (!needle) return true;
  return (
    normalizeText(task.title).includes(needle) ||
    normalizeText(task.description).includes(needle)
  );
}

/** The five due-date classes a task's deadline can fall into. */
export type DueDateState =
  | "overdue"
  | "today"
  | "tomorrow"
  | "soon"
  | "future";

export interface DueDateInfo {
  state: DueDateState;
  /** Whole-day distance between the due date and "today", always positive. */
  days: number;
}

/** Midnight of the given date, so distances are whole calendar days. */
function startOfDay(value: Date): Date {
  return new Date(value.getFullYear(), value.getMonth(), value.getDate());
}

/**
 * Classifies a due date against `now` into one of five states, with the
 * whole-day distance between the two.
 *
 * A `COMPLETED` or `CANCELED` task is **never** overdue: its deadline no
 * longer demands anything, so it reads as a plain absolute date (`future`).
 */
export function dueDateInfo(
  dueDate: Date | string | null | undefined,
  status: string,
  now: Date = new Date(),
): DueDateInfo | null {
  if (!dueDate) return null;
  const due = startOfDay(new Date(dueDate));
  if (Number.isNaN(due.getTime())) return null;

  const days = Math.round(
    (due.getTime() - startOfDay(now).getTime()) / 86_400_000,
  );
  const isClosed = status === "COMPLETED" || status === "CANCELED";

  if (days < 0) {
    return { state: isClosed ? "future" : "overdue", days: -days };
  }
  if (days === 0) return { state: "today", days };
  if (days === 1) return { state: "tomorrow", days };
  if (days <= 7) return { state: "soon", days };
  return { state: "future", days };
}

/** Whether a task is past its deadline and still open. */
export function isOverdue(
  task: Pick<TaskRead, "due_date" | "status">,
  now: Date = new Date(),
): boolean {
  return dueDateInfo(task.due_date, task.status, now)?.state === "overdue";
}
