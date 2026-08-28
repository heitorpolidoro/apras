import React from "react";
import { useTranslation } from "react-i18next";
import { Eye } from "lucide-react";
import type { Feedback, FeedbackStatus } from "../../../types/feedback";

interface FeedbackInboxTableProps {
  items: Feedback[];
  isLoading?: boolean;
  onSelectFeedback: (id: string) => void;
}

const getStatusBadgeClass = (status: FeedbackStatus) => {
  switch (status) {
    case "PENDING":
      return "bg-amber-50 text-amber-700 border-amber-200";
    case "ANSWERED":
      return "bg-emerald-50 text-emerald-700 border-emerald-200";
    default:
      return "bg-gray-50 text-gray-700 border-gray-200";
  }
};

export const FeedbackInboxTable: React.FC<FeedbackInboxTableProps> = ({
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
          {t("feedback.no_records_inbox", "Nenhuma mensagem recebida ainda")}
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden shadow-sm">
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm text-gray-600">
          <thead className="bg-gray-50 text-xs font-semibold uppercase text-gray-500 border-b">
            <tr>
              <th className="px-4 py-3">{t("feedback.table.category", "Categoria")}</th>
              <th className="px-4 py-3">{t("feedback.table.message", "Mensagem")}</th>
              <th className="px-4 py-3">{t("feedback.table.status", "Status")}</th>
              <th className="px-4 py-3">{t("feedback.table.reporter", "Remetente")}</th>
              <th className="px-4 py-3">{t("feedback.table.date", "Data")}</th>
              <th className="px-4 py-3 text-right">{t("feedback.table.actions", "Ações")}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {items.map((item) => (
              <tr key={item.id} className="hover:bg-gray-50/80 transition-colors">
                <td className="px-4 py-3 text-xs">
                  <span className="bg-gray-100 text-gray-800 px-2 py-0.5 rounded border border-gray-200 font-medium">
                    {t(`feedback.category_labels.${item.category}`, item.category)}
                  </span>
                </td>
                <td className="px-4 py-3 font-medium text-gray-900">
                  <span className="truncate max-w-xs block">{item.message}</span>
                </td>
                <td className="px-4 py-3 text-xs">
                  <span
                    className={`px-2 py-0.5 rounded-full border text-[11px] font-semibold ${getStatusBadgeClass(
                      item.status
                    )}`}
                  >
                    {t(`feedback.status.${item.status}`, item.status)}
                  </span>
                </td>
                <td className="px-4 py-3 text-xs text-gray-700">
                  {item.reporter_name || t("feedback.anonymous", "Anônimo")}
                </td>
                <td className="px-4 py-3 text-xs text-gray-500 whitespace-nowrap">
                  {new Date(item.created_at).toLocaleDateString()}
                </td>
                <td className="px-4 py-3 text-right">
                  <button
                    onClick={() => onSelectFeedback(item.id)}
                    className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-indigo-600 hover:text-indigo-800 bg-indigo-50 hover:bg-indigo-100 rounded-md transition-colors"
                  >
                    <Eye className="w-3.5 h-3.5" />
                    {t("feedback.view_details", "Ver Detalhes")}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
