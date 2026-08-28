import React from "react";
import { useTranslation } from "react-i18next";
import { Bell, Eye } from "lucide-react";
import type { Feedback } from "../../../types/feedback";

interface FeedbackHistoryListProps {
  items: Feedback[];
  isLoading?: boolean;
  onSelectFeedback: (id: string) => void;
}

export const FeedbackHistoryList: React.FC<FeedbackHistoryListProps> = ({
  items,
  isLoading = false,
  onSelectFeedback,
}) => {
  const { t } = useTranslation();

  if (isLoading) {
    return (
      <div className="p-8 text-center text-gray-500 bg-white rounded-xl border">
        {t("common.loading", "Carregando...")}
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="p-12 text-center bg-white rounded-xl border space-y-2">
        <p className="text-gray-500 font-medium">
          {t("feedback.no_records_history", "Nenhuma mensagem enviada ainda")}
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden shadow-sm divide-y divide-gray-100">
      {items.map((item) => {
        const isUnread = item.status === "ANSWERED" && !item.response_seen_by_reporter;
        return (
          <button
            key={item.id}
            onClick={() => onSelectFeedback(item.id)}
            className="w-full text-left px-4 py-3 hover:bg-gray-50/80 transition-colors flex items-center justify-between gap-3"
          >
            <div className="flex items-center gap-2 min-w-0">
              {isUnread && (
                <span
                  aria-label={t("feedback.unread_indicator", "Nova resposta")}
                  className="inline-flex items-center gap-1 text-[10px] font-bold text-white bg-rose-500 px-1.5 py-0.5 rounded-full"
                >
                  <Bell className="w-3 h-3" />
                  {t("feedback.unread_badge", "Novo")}
                </span>
              )}
              <span className="bg-gray-100 text-gray-800 px-2 py-0.5 rounded border border-gray-200 font-medium text-[11px]">
                {t(`feedback.category_labels.${item.category}`, item.category)}
              </span>
              <span className="truncate text-sm text-gray-800">{item.message}</span>
            </div>
            <div className="flex items-center gap-2 flex-shrink-0">
              <span
                className={`px-2 py-0.5 rounded-full border text-[11px] font-semibold ${
                  item.status === "ANSWERED"
                    ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                    : "bg-amber-50 text-amber-700 border-amber-200"
                }`}
              >
                {t(`feedback.status.${item.status}`, item.status)}
              </span>
              <Eye className="w-3.5 h-3.5 text-indigo-500" />
            </div>
          </button>
        );
      })}
    </div>
  );
};
