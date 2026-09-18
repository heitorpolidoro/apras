import React from "react";
import { useTranslation } from "react-i18next";
import { GripVertical, Lock } from "lucide-react";
import type { TaskRead } from "../types";
import { Badge } from "../../../components/ui/badge";
import { cn } from "../../../lib/utils";
import { getStatusLabel, getPriorityLabel, statusVariant, priorityVariant } from "../utils/taskUtils";
import HighlightedText from "./HighlightedText";
import DueDateBadge from "./DueDateBadge";

interface TaskCardProps {
  task: TaskRead;
  onClick?: () => void;
  /** When true, shows a lock indicator: the task is not editable in the current simulated view. */
  readOnly?: boolean;
  /** Free text whose matches are highlighted in the title and description. */
  search?: string | null;
  /**
   * Whether this card can be dragged to another column. Dragging is
   * **mouse-only** (APRAS-62): there is no keyboard grab, no drag handle and
   * no arrow-key traversal — the keyboard path to a status change stays the
   * task form's status `<select>`. A read-only card never drags.
   */
  draggable?: boolean;
  onDragStart?: (taskId: string) => void;
  onDragEnd?: () => void;
  /** True while this card is the one being dragged. */
  isDragging?: boolean;
}

const TaskCard: React.FC<TaskCardProps> = ({
  task,
  onClick,
  readOnly = false,
  search,
  draggable = false,
  onDragStart,
  onDragEnd,
  isDragging = false,
}) => {
  const { t } = useTranslation();
  const isDraggable = draggable && !readOnly;

  const handleDragStart = (e: React.DragEvent) => {
    // Firefox refuses to start a drag whose dataTransfer carries no payload.
    e.dataTransfer?.setData("text/plain", task.id);
    if (e.dataTransfer) e.dataTransfer.effectAllowed = "move";
    onDragStart?.(task.id);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if ((e.key === "Enter" || e.key === " ") && onClick) {
      e.preventDefault();
      onClick();
    }
  };

  return (
    <button
      className={cn(
        "relative w-full text-left rounded-xl border border-border/40 bg-card text-card-foreground shadow-sm p-5 transition-all duration-200 cursor-pointer",
        "hover:shadow-md hover:border-primary/30 hover:-translate-y-0.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        isDraggable && "cursor-grab active:cursor-grabbing",
        isDragging && "opacity-50 rotate-1 shadow-xl",
      )}
      onClick={onClick}
      onKeyDown={handleKeyDown}
      draggable={isDraggable}
      onDragStart={isDraggable ? handleDragStart : undefined}
      onDragEnd={isDraggable ? onDragEnd : undefined}
    >
      {readOnly && (
        <span
          data-testid="task-readonly-indicator"
          title={t("simulation.readOnlyTask")}
          aria-label={t("simulation.readOnlyTask")}
          className="absolute top-3 right-3 text-muted-foreground"
        >
          <Lock className="size-3.5" />
        </span>
      )}
      <h3 className="font-semibold text-base mb-1 pr-5 text-foreground leading-snug flex items-start gap-1.5">
        {isDraggable && (
          <span
            aria-hidden="true"
            data-testid="task-card-grip"
            className="text-muted-foreground/50 shrink-0 mt-0.5"
          >
            <GripVertical className="size-4" />
          </span>
        )}
        <HighlightedText text={task.title} search={search} />
      </h3>
      {task.category_name && (
        <span className="inline-flex items-center gap-1 text-xs text-muted-foreground mb-1">
          <span
            className="size-2 rounded-full shrink-0"
            style={{ backgroundColor: task.category_color ?? "#808080" }}
          />
          {task.category_name}
        </span>
      )}
      <div className="flex items-center gap-2 mb-3">
        <p className="text-sm text-muted-foreground line-clamp-2 leading-relaxed flex-1">
          {task.description ? (
            <HighlightedText text={task.description} search={search} />
          ) : (
            t("tasks.card.noDescription")
          )}
        </p>
        {task.assigned_to_name && (
          <div
            className="size-7 rounded-full bg-primary/10 text-primary flex items-center justify-center text-[10px] font-bold border border-primary/20 shrink-0"
            title={task.assigned_to_name}
          >
            {task.assigned_to_name
              .split(" ")
              .map((n) => n[0])
              .join("")
              .substring(0, 2)
              .toUpperCase()}
          </div>
        )}
      </div>
      <div className="flex items-center justify-between">
        <div className="flex gap-2 flex-wrap">
          <Badge variant={statusVariant(task.status)}>
            {getStatusLabel(task.status, t)}
          </Badge>
          <Badge variant={priorityVariant(task.priority)}>
            {getPriorityLabel(task.priority, t)}
          </Badge>
        </div>
        <DueDateBadge dueDate={task.due_date} status={task.status} />
      </div>
    </button>
  );
};


export default TaskCard;
