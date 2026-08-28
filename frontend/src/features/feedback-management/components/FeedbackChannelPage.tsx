import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { Filter, MessageCircle } from "lucide-react";
import type { FeedbackCategory, FeedbackStatus } from "../../../types/feedback";
import { UserRole } from "../../../types/auth";
import { useEffectiveIdentity } from "../../user-administration/context/useEffectiveIdentity";
import { useFeedbackList } from "../hooks/useFeedback";
import { NewFeedbackForm } from "./NewFeedbackForm";
import { FeedbackHistoryList } from "./FeedbackHistoryList";
import { FeedbackInboxTable } from "./FeedbackInboxTable";
import { FeedbackDetailsView } from "./FeedbackDetailsView";

export const FeedbackChannelPage: React.FC = () => {
  const { t } = useTranslation();
  const { role } = useEffectiveIdentity();
  const isManagement = role === UserRole.ADMINISTRATOR || role === UserRole.DIRECTOR;

  const [categoryFilter, setCategoryFilter] = useState<FeedbackCategory | "">("");
  const [statusFilter, setStatusFilter] = useState<FeedbackStatus | "">("");
  const [selectedFeedbackId, setSelectedFeedbackId] = useState<string | null>(null);

  const { data, isLoading } = useFeedbackList({
    category: categoryFilter ? (categoryFilter as FeedbackCategory) : undefined,
    status: statusFilter ? (statusFilter as FeedbackStatus) : undefined,
  });

  const items = data?.items || [];

  return (
    <div className="container mx-auto px-4 py-8 max-w-5xl space-y-6">
      <div className="flex items-center gap-3 bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
        <div className="p-3 bg-indigo-50 text-indigo-600 rounded-lg">
          <MessageCircle className="w-6 h-6" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            {t("feedback.page_title", "Fale Conosco")}
          </h1>
          <p className="text-sm text-gray-500">
            {t(
              "feedback.page_subtitle",
              "Envie críticas, sugestões e elogios diretamente para a diretoria."
            )}
          </p>
        </div>
      </div>

      {isManagement ? (
        <>
          <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm space-y-3">
            <div className="flex items-center gap-2 text-sm font-semibold text-gray-700">
              <Filter className="w-4 h-4 text-indigo-600" />
              {t("feedback.filters.title", "Filtros")}
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <select
                value={categoryFilter}
                onChange={(e) => setCategoryFilter(e.target.value as FeedbackCategory | "")}
                className="w-full px-3 py-2 text-sm border rounded-lg text-gray-800 bg-gray-50 focus:bg-white"
              >
                <option value="">{t("feedback.filters.all_categories", "Todas as Categorias")}</option>
                <option value="CRITICISM">{t("feedback.category_labels.CRITICISM", "Crítica")}</option>
                <option value="SUGGESTION">{t("feedback.category_labels.SUGGESTION", "Sugestão")}</option>
                <option value="COMPLIMENT">{t("feedback.category_labels.COMPLIMENT", "Elogio")}</option>
                <option value="OTHER">{t("feedback.category_labels.OTHER", "Outro")}</option>
              </select>

              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value as FeedbackStatus | "")}
                className="w-full px-3 py-2 text-sm border rounded-lg text-gray-800 bg-gray-50 focus:bg-white"
              >
                <option value="">{t("feedback.filters.all_statuses", "Todos os Status")}</option>
                <option value="PENDING">{t("feedback.status.PENDING", "Pendente")}</option>
                <option value="ANSWERED">{t("feedback.status.ANSWERED", "Respondido")}</option>
              </select>
            </div>
          </div>

          <FeedbackInboxTable
            items={items}
            isLoading={isLoading}
            onSelectFeedback={(id) => setSelectedFeedbackId(id)}
          />
        </>
      ) : (
        <>
          <NewFeedbackForm />

          <div>
            <h2 className="text-lg font-bold text-gray-900 mb-3">
              {t("feedback.history_title", "Meu Histórico")}
            </h2>
            <FeedbackHistoryList
              items={items}
              isLoading={isLoading}
              onSelectFeedback={(id) => setSelectedFeedbackId(id)}
            />
          </div>
        </>
      )}

      {selectedFeedbackId && (
        <FeedbackDetailsView
          feedbackId={selectedFeedbackId}
          canRespond={isManagement}
          onClose={() => setSelectedFeedbackId(null)}
        />
      )}
    </div>
  );
};
