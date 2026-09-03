import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { useTaskHistory } from "../hooks/useTasks";
import type { TaskHistoryRead } from "../types";

interface AuditTimelineProps {
  taskId: string;
}

const AuditTimeline: React.FC<AuditTimelineProps> = ({ taskId }) => {
  const { t, i18n } = useTranslation();
  const { data: history, isLoading, error } = useTaskHistory(taskId);
  const [isOpen, setIsOpen] = useState(false);

  const formatDate = (date: Date | string) =>
    new Date(date).toLocaleString(i18n.language === "pt" ? "pt-BR" : "en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });

  const formatFieldName = (name: string) => name?.replaceAll("_", " ") || "";

  const formatValue = (value: string | null) => {
    if (value === null || value === "null") return t("tasks.audit.none");
    if (value === "") return t("tasks.audit.emptyValue");
    return value;
  };

  const formatAssignedValue = (entry: TaskHistoryRead, which: "old" | "new") => {
    const resolved = which === "old" ? entry.resolved_old_value : entry.resolved_new_value;
    if (resolved) {
      // IAM F5 (APRAS-49 §8.2): the backend resolves an assignee to
      // `{name, roles}` — the role *names* in the acting tenant — instead of
      // a single enum value with an i18n label. The names are already
      // human-readable ("Diretor (papel)"), so there is nothing left to
      // translate and no `legacyRoles.*` lookup.
      const roleLabel = resolved.roles.join(", ");
      return roleLabel ? `${resolved.name} (${roleLabel})` : resolved.name;
    }
    const rawValue = which === "old" ? entry.old_value : entry.new_value;
    return formatValue(rawValue);
  };

  if (isLoading) {
    return (
      <p className="text-sm text-muted-foreground py-2">
        {t("tasks.audit.loading")}
      </p>
    );
  }

  if (error) {
    return (
      <p className="text-sm text-destructive py-2">{t("tasks.audit.error")}</p>
    );
  }

  const count = history?.length ?? 0;

  return (
    <div className="pt-3 border-t mt-2">
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wider text-muted-foreground mb-3 hover:text-foreground transition-colors"
        aria-expanded={isOpen}
      >
        <span aria-hidden="true">{isOpen ? "▼" : "▶"}</span>
        <span>{t("tasks.audit.title")}</span>
        {!isOpen && count > 0 && (
          <span className="normal-case font-normal text-muted-foreground/70">
            ({count})
          </span>
        )}
      </button>

      {isOpen && (
        <>
          {!history || count === 0 ? (
            <p className="text-sm text-muted-foreground italic">
              {t("tasks.audit.empty")}
            </p>
          ) : (
            <div className="relative pl-5">
              <div className="absolute left-0 top-0 bottom-0 w-px bg-border" />
              {(history as TaskHistoryRead[]).map((entry) => (
                <div key={entry.id} className="relative mb-4 last:mb-0">
                  <div className="absolute -left-5 top-1 size-2.5 rounded-full bg-primary border-2 border-background translate-x-[-50%]" />
                  <div className="flex justify-between items-center mb-1">
                    <span className="text-sm font-medium text-foreground">
                      {entry.user_name}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      {formatDate(entry.timestamp)}
                    </span>
                  </div>
                  <div className="rounded-md bg-muted/40 border px-3 py-2 text-sm">
                    <span className="font-medium text-foreground capitalize block mb-1">
                      {formatFieldName(entry.field_name)}
                    </span>
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-muted-foreground line-through">
                        {entry.field_name === "assigned_to_id"
                          ? formatAssignedValue(entry, "old")
                          : formatValue(entry.old_value)}
                      </span>
                      <span className="text-muted-foreground">→</span>
                      <span className="text-emerald-600 font-medium">
                        {entry.field_name === "assigned_to_id"
                          ? formatAssignedValue(entry, "new")
                          : formatValue(entry.new_value)}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default AuditTimeline;
