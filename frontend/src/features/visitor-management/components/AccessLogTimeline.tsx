import React from "react";
import { useTranslation } from "react-i18next";
import { LogIn, LogOut, Clock, FileText } from "lucide-react";
import type { AccessLog } from "../../../types/visitor";

interface AccessLogTimelineProps {
  logs: AccessLog[];
  onCheckOut?: (log: AccessLog) => void;
  canCheckOut?: boolean;
}

export const AccessLogTimeline: React.FC<AccessLogTimelineProps> = ({
  logs,
  onCheckOut,
  canCheckOut = false,
}) => {
  const { t } = useTranslation();

  const calculateDuration = (entry: string, exit?: string | null) => {
    if (!exit) return null;
    const entryDt = new Date(entry).getTime();
    const exitDt = new Date(exit).getTime();
    const diffMs = exitDt - entryDt;
    if (diffMs <= 0) return "0m";

    const mins = Math.floor(diffMs / 60000);
    const hrs = Math.floor(mins / 60);
    const remMins = mins % 60;

    if (hrs > 0) {
      return `${hrs}h ${remMins}m`;
    }
    return `${mins}m`;
  };

  return (
    <div className="space-y-3">
      {logs.length === 0 ? (
        <div className="rounded-xl border border-slate-200 bg-white p-8 text-center shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <Clock className="mx-auto size-8 text-slate-400 mb-2" />
          <p className="text-sm font-medium text-slate-600 dark:text-slate-300">
            {t("accessLogs.empty")}
          </p>
        </div>
      ) : (
        <div className="relative border-l-2 border-slate-200 dark:border-slate-800 ml-4 space-y-6 py-2">
          {logs.map((log) => {
            const isCurrentlyOnSite = !log.exit_time;
            const visitorName = log.visitor?.full_name || "Visitor";
            const duration = calculateDuration(log.entry_time, log.exit_time);

            return (
              <div key={log.id} className="relative pl-6">
                {/* Timeline Dot Icon */}
                <div
                  className={`absolute -left-[17px] top-0 flex size-8 items-center justify-center rounded-full border-2 border-white bg-slate-100 shadow-sm dark:border-slate-900 ${
                    isCurrentlyOnSite
                      ? "bg-emerald-100 text-emerald-600 dark:bg-emerald-950 dark:text-emerald-400"
                      : "bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400"
                  }`}
                >
                  {isCurrentlyOnSite ? (
                    <LogIn className="size-4" />
                  ) : (
                    <LogOut className="size-4" />
                  )}
                </div>

                {/* Card */}
                <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
                  <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-slate-900 dark:text-white text-base">
                          {visitorName}
                        </span>
                        {isCurrentlyOnSite ? (
                          <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-semibold text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-400">
                            On-Site
                          </span>
                        ) : (
                          <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-400">
                            Left {duration ? `(${duration})` : ""}
                          </span>
                        )}
                      </div>

                      {log.visitor?.company_name && (
                        <div className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                          {log.visitor.company_name} {log.visitor.vehicle_plate ? `• ${log.visitor.vehicle_plate}` : ""}
                        </div>
                      )}
                    </div>

                    {isCurrentlyOnSite && canCheckOut && onCheckOut && (
                      <button
                        onClick={() => onCheckOut(log)}
                        className="rounded-lg bg-amber-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-amber-700 transition-colors self-start sm:self-auto"
                      >
                        {t("gatekeeper.checkOut")}
                      </button>
                    )}
                  </div>

                  {/* Times */}
                  <div className="mt-3 flex flex-wrap gap-4 text-xs text-slate-500 dark:text-slate-400 border-t border-slate-100 pt-3 dark:border-slate-800/80">
                    <div>
                      <span className="font-semibold text-slate-700 dark:text-slate-300">
                        {t("accessLogs.entryTime")}:
                      </span>{" "}
                      {new Date(log.entry_time).toLocaleString()}
                    </div>
                    {log.exit_time && (
                      <div>
                        <span className="font-semibold text-slate-700 dark:text-slate-300">
                          {t("accessLogs.exitTime")}:
                        </span>{" "}
                        {new Date(log.exit_time).toLocaleString()}
                      </div>
                    )}
                    {log.entry_notes && (
                      <div className="flex items-center gap-1">
                        <FileText className="size-3 text-slate-400" />
                        <span>{log.entry_notes}</span>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
