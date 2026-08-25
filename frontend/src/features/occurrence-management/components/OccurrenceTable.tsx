import React from "react";
import { useTranslation } from "react-i18next";
import { Eye, Globe, Lock } from "lucide-react";
import type { Occurrence, OccurrencePriority, OccurrenceStatus } from "../../../types/occurrence";

interface OccurrenceTableProps {
  occurrences: Occurrence[];
  onSelectOccurrence: (id: string) => void;
  isLoading?: boolean;
}

export const OccurrenceTable: React.FC<OccurrenceTableProps> = ({
  occurrences,
  onSelectOccurrence,
  isLoading = false,
}) => {
  const { t } = useTranslation();

  const getStatusBadgeClass = (status: OccurrenceStatus) => {
    switch (status) {
      case "OPEN":
        return "bg-amber-50 text-amber-700 border-amber-200";
      case "UNDER_REVIEW":
        return "bg-blue-50 text-blue-700 border-blue-200";
      case "IN_PROGRESS":
        return "bg-indigo-50 text-indigo-700 border-indigo-200";
      case "RESOLVED":
        return "bg-emerald-50 text-emerald-700 border-emerald-200";
      case "REJECTED":
        return "bg-rose-50 text-rose-700 border-rose-200";
      default:
        return "bg-gray-50 text-gray-700 border-gray-200";
    }
  };

  const getPriorityBadgeClass = (priority: OccurrencePriority) => {
    switch (priority) {
      case "URGENT":
        return "bg-rose-100 text-rose-800 font-bold";
      case "HIGH":
        return "bg-orange-100 text-orange-800";
      case "MEDIUM":
        return "bg-sky-100 text-sky-800";
      case "LOW":
        return "bg-gray-100 text-gray-700";
    }
  };

  if (isLoading) {
    return (
      <div className="p-8 text-center text-gray-500 bg-white rounded-xl border">
        {t("common.loading", "Carregando...")}
      </div>
    );
  }

  if (occurrences.length === 0) {
    return (
      <div className="p-12 text-center bg-white rounded-xl border space-y-2">
        <p className="text-gray-500 font-medium">
          {t("occurrences.no_records", "Nenhuma ocorrência encontrada")}
        </p>
        <p className="text-xs text-gray-400">
          {t("occurrences.no_records_hint", "Tente ajustar os filtros ou criar uma nova ocorrência.")}
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
              <th className="px-4 py-3">{t("occurrences.table.protocol", "Protocolo")}</th>
              <th className="px-4 py-3">{t("occurrences.table.category", "Categoria")}</th>
              <th className="px-4 py-3">{t("occurrences.table.title", "Título")}</th>
              <th className="px-4 py-3">{t("occurrences.table.status", "Status")}</th>
              <th className="px-4 py-3">{t("occurrences.table.priority", "Prioridade")}</th>
              <th className="px-4 py-3">{t("occurrences.table.reporter", "Relator")}</th>
              <th className="px-4 py-3">{t("occurrences.table.date", "Data")}</th>
              <th className="px-4 py-3 text-right">{t("occurrences.table.actions", "Ações")}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {occurrences.map((item) => (
              <tr key={item.id} className="hover:bg-gray-50/80 transition-colors">
                <td className="px-4 py-3 font-mono font-bold text-xs text-indigo-600">
                  {item.protocol_number}
                </td>
                <td className="px-4 py-3 text-xs">
                  <span className="bg-gray-100 text-gray-800 px-2 py-0.5 rounded border border-gray-200 font-medium">
                    {t(`occurrences.category_labels.${item.category}`, item.category)}
                  </span>
                </td>
                <td className="px-4 py-3 font-medium text-gray-900">
                  <div className="flex items-center gap-1.5">
                    {item.is_public ? (
                      <Globe className="w-3.5 h-3.5 text-emerald-600 flex-shrink-0" />
                    ) : (
                      <Lock className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />
                    )}
                    <span className="truncate max-w-xs">{item.title}</span>
                  </div>
                </td>
                <td className="px-4 py-3 text-xs">
                  <span
                    className={`px-2 py-0.5 rounded-full border text-[11px] font-semibold ${getStatusBadgeClass(
                      item.status
                    )}`}
                  >
                    {t(`occurrences.status.${item.status}`, item.status)}
                  </span>
                </td>
                <td className="px-4 py-3 text-xs">
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-medium ${getPriorityBadgeClass(
                      item.priority
                    )}`}
                  >
                    {t(`occurrences.priority.${item.priority}`, item.priority)}
                  </span>
                </td>
                <td className="px-4 py-3 text-xs text-gray-700">
                  {item.reporter_name || t("occurrences.anonymous", "Anônimo")}
                </td>
                <td className="px-4 py-3 text-xs text-gray-500 whitespace-nowrap">
                  {new Date(item.created_at).toLocaleDateString()}
                </td>
                <td className="px-4 py-3 text-right">
                  <button
                    onClick={() => onSelectOccurrence(item.id)}
                    className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-indigo-600 hover:text-indigo-800 bg-indigo-50 hover:bg-indigo-100 rounded-md transition-colors"
                  >
                    <Eye className="w-3.5 h-3.5" />
                    {t("occurrences.view_details", "Ver Detalhes")}
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
