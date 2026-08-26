import React from "react";
import { useTranslation } from "react-i18next";
import { CheckCircle2, XCircle } from "lucide-react";
import type { FacialAccessEvent } from "../../../types/accessControl";

interface AccessEventFeedProps {
  events: FacialAccessEvent[];
}

export const AccessEventFeed: React.FC<AccessEventFeedProps> = ({ events }) => {
  const { t } = useTranslation();

  if (events.length === 0) {
    return (
      <p className="p-6 text-center text-sm text-slate-500 dark:text-slate-400">
        {t("accessControl.noEvents")}
      </p>
    );
  }

  return (
    <ul className="divide-y divide-slate-100 dark:divide-slate-800/80">
      {events.map((event) => (
        <li key={event.id} className="flex items-center justify-between py-3">
          <div className="flex items-center gap-3">
            {event.access_granted ? (
              <CheckCircle2 className="size-5 text-emerald-500" />
            ) : (
              <XCircle className="size-5 text-red-500" />
            )}
            <div>
              <div className="text-sm font-semibold text-slate-900 dark:text-white">
                {event.resident_id
                  ? event.resident_id
                  : t("accessControl.unrecognized")}
              </div>
              <div className="text-xs text-slate-500 dark:text-slate-400">
                {new Date(event.event_time).toLocaleString()}
                {event.confidence_score != null &&
                  ` · ${t("accessControl.confidence")}: ${(event.confidence_score * 100).toFixed(0)}%`}
              </div>
            </div>
          </div>
          <span
            className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold ${
              event.access_granted
                ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-400"
                : "bg-red-100 text-red-700 dark:bg-red-950/50 dark:text-red-400"
            }`}
          >
            {event.access_granted
              ? t("accessControl.accessGranted")
              : t("accessControl.accessDenied")}
          </span>
        </li>
      ))}
    </ul>
  );
};
