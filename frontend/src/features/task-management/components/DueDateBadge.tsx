import React from "react";
import { useTranslation } from "react-i18next";
import { AlertTriangle, CalendarClock, CalendarDays } from "lucide-react";
import { cn } from "../../../lib/utils";
import { dueDateInfo, type DueDateState } from "../utils/taskUtils";

interface DueDateBadgeProps {
  dueDate: Date | string | null | undefined;
  /** The task's status: a COMPLETED/CANCELED task is never overdue. */
  status: string;
  /** Injectable "today", so the five states are testable against a fixed date. */
  now?: Date;
  className?: string;
}

const STATE_CLASS: Record<DueDateState, string> = {
  overdue: "text-destructive font-semibold",
  today: "text-amber-700 dark:text-amber-400 font-semibold",
  tomorrow: "text-amber-700 dark:text-amber-400",
  soon: "text-muted-foreground",
  future: "text-muted-foreground",
};

/**
 * Renders a task's deadline as **text plus an icon** — never colour alone —
 * naming how far away it is: overdue, today, tomorrow, within a week, or the
 * plain absolute date for anything further out.
 */
const DueDateBadge: React.FC<DueDateBadgeProps> = ({
  dueDate,
  status,
  now,
  className,
}) => {
  const { t, i18n } = useTranslation();
  const info = dueDateInfo(dueDate, status, now);
  if (!info) return null;

  const locale = i18n.language === "pt" ? "pt-BR" : "en-US";
  let label: string;
  let Icon = CalendarDays;

  switch (info.state) {
    case "overdue":
      label =
        info.days === 1
          ? t("tasks.dueDate.overdueOne")
          : t("tasks.dueDate.overdueMany", { days: info.days });
      Icon = AlertTriangle;
      break;
    case "today":
      label = t("tasks.dueDate.today");
      Icon = CalendarClock;
      break;
    case "tomorrow":
      label = t("tasks.dueDate.tomorrow");
      Icon = CalendarClock;
      break;
    case "soon":
      label =
        info.days === 1
          ? t("tasks.dueDate.soonOne")
          : t("tasks.dueDate.soonMany", { days: info.days });
      Icon = CalendarClock;
      break;
    default:
      label = new Date(dueDate as Date | string).toLocaleDateString(locale);
  }

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 text-xs whitespace-nowrap",
        STATE_CLASS[info.state],
        className,
      )}
      data-due-state={info.state}
    >
      <Icon className="size-3.5 shrink-0" data-testid="due-date-icon" />
      {label}
    </span>
  );
};

export default DueDateBadge;
