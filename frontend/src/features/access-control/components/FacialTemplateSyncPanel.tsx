import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { ScanFace, RefreshCw } from "lucide-react";
import { Button } from "../../../components/ui/button";
import { useFacialTemplate, useSyncFacialTemplate } from "../hooks/useAccessControl";

const SYNC_STATUS_CLASSES: Record<string, string> = {
  SYNCED: "bg-emerald-100 text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-400",
  PENDING: "bg-amber-100 text-amber-700 dark:bg-amber-950/50 dark:text-amber-400",
  FAILED: "bg-red-100 text-red-700 dark:bg-red-950/50 dark:text-red-400",
};

export const FacialTemplateSyncPanel: React.FC = () => {
  const { t } = useTranslation();
  const [residentId, setResidentId] = useState("");
  const [searchedId, setSearchedId] = useState<string | undefined>(undefined);
  const [errorMessage, setErrorMessage] = useState("");

  const { data: template, isFetching } = useFacialTemplate(searchedId);
  const syncMutation = useSyncFacialTemplate();

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setSearchedId(residentId.trim() || undefined);
  };

  const handleSync = async () => {
    if (!searchedId) return;
    setErrorMessage("");
    try {
      await syncMutation.mutateAsync(searchedId);
    } catch (err: any) {
      setErrorMessage(err?.response?.data?.detail || t("accessControl.syncError"));
    }
  };

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900 space-y-4">
      <h2 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
        <ScanFace className="size-5 text-indigo-600 dark:text-indigo-400" />
        {t("accessControl.facialTemplateSync")}
      </h2>

      <form onSubmit={handleSearch} className="flex gap-2">
        <input
          type="text"
          value={residentId}
          onChange={(e) => setResidentId(e.target.value)}
          placeholder={t("accessControl.residentIdPlaceholder")}
          className="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm bg-white dark:border-slate-700 dark:bg-slate-800 text-slate-900 dark:text-white"
        />
        <Button type="submit" variant="outline">
          {t("accessControl.search")}
        </Button>
      </form>

      {errorMessage && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700 dark:border-red-900/50 dark:bg-red-950/50 dark:text-red-400">
          {errorMessage}
        </div>
      )}

      {searchedId && (
        <div className="rounded-xl border border-slate-100 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-800/40 space-y-3">
          {isFetching ? (
            <p className="text-sm text-slate-500 dark:text-slate-400">{t("accessControl.loading")}</p>
          ) : template ? (
            <div className="flex items-center justify-between">
              <span
                className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold ${SYNC_STATUS_CLASSES[template.sync_status]}`}
              >
                {t(`accessControl.syncStatus${template.sync_status}`)}
              </span>
              <span className="text-xs text-slate-500 dark:text-slate-400">
                {template.synced_at ? new Date(template.synced_at).toLocaleString() : ""}
              </span>
            </div>
          ) : (
            <p className="text-sm text-slate-500 dark:text-slate-400">
              {t("accessControl.noTemplateSynced")}
            </p>
          )}

          <Button
            size="sm"
            disabled={syncMutation.isPending}
            onClick={handleSync}
            className="gap-1"
          >
            <RefreshCw className="size-3.5" />
            {syncMutation.isPending ? t("accessControl.syncing") : t("accessControl.syncNow")}
          </Button>
        </div>
      )}
    </div>
  );
};
