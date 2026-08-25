import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { BookOpen, Filter, Plus, Search } from "lucide-react";
import type { OccurrenceCategory, OccurrenceStatus } from "../../../types/occurrence";
import { useEffectiveIdentity } from "../../user-administration/context/useEffectiveIdentity";
import { useOccurrences } from "../hooks/useOccurrences";
import { NewOccurrenceModal } from "./NewOccurrenceModal";
import { OccurrenceDetailsView } from "./OccurrenceDetailsView";
import { OccurrenceTable } from "./OccurrenceTable";

export const OccurrenceBookPage: React.FC = () => {
  const { t } = useTranslation();
  const { role } = useEffectiveIdentity();

  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState<OccurrenceCategory | "">("");
  const [statusFilter, setStatusFilter] = useState<OccurrenceStatus | "">("");
  const [isPublicFilter, setIsPublicFilter] = useState<boolean | "">("");

  const [isNewModalOpen, setIsNewModalOpen] = useState(false);
  const [selectedOccurrenceId, setSelectedOccurrenceId] = useState<string | null>(null);

  const { data, isLoading } = useOccurrences({
    search: search.trim() || undefined,
    category: categoryFilter ? (categoryFilter as OccurrenceCategory) : undefined,
    status: statusFilter ? (statusFilter as OccurrenceStatus) : undefined,
    is_public: typeof isPublicFilter === "boolean" ? isPublicFilter : undefined,
  });

  return (
    <div className="container mx-auto px-4 py-8 max-w-7xl space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-indigo-50 text-indigo-600 rounded-lg">
            <BookOpen className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              {t("occurrences.page_title", "Livro de Ocorrências e Reclamações")}
            </h1>
            <p className="text-sm text-gray-500">
              {t(
                "occurrences.page_subtitle",
                "Registre, acompanhe e resolva chamados e incidentes da associação."
              )}
            </p>
          </div>
        </div>

        <button
          onClick={() => setIsNewModalOpen(true)}
          className="inline-flex items-center justify-center gap-2 px-4 py-2.5 text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg shadow-sm transition-colors"
        >
          <Plus className="w-4 h-4" />
          {t("occurrences.new_occurrence_btn", "Nova Ocorrência")}
        </button>
      </div>

      {/* Filters Bar */}
      <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm space-y-3">
        <div className="flex items-center gap-2 text-sm font-semibold text-gray-700">
          <Filter className="w-4 h-4 text-indigo-600" />
          {t("occurrences.filters.title", "Filtros de Busca")}
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {/* Text/Protocol Search */}
          <div className="relative">
            <Search className="w-4 h-4 text-gray-400 absolute left-3 top-3" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder={t("occurrences.filters.search_placeholder", "Buscar protocolo ou título...")}
              className="w-full pl-9 pr-3 py-2 text-sm border rounded-lg text-gray-800 bg-gray-50 focus:bg-white focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          {/* Category Filter */}
          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value as OccurrenceCategory | "")}
            className="w-full px-3 py-2 text-sm border rounded-lg text-gray-800 bg-gray-50 focus:bg-white"
          >
            <option value="">{t("occurrences.filters.all_categories", "Todas as Categorias")}</option>
            <option value="NOISE">{t("occurrences.category_labels.NOISE", "Barulho / Perturbação")}</option>
            <option value="MAINTENANCE">{t("occurrences.category_labels.MAINTENANCE", "Manutenção / Infraestrutura")}</option>
            <option value="SECURITY">{t("occurrences.category_labels.SECURITY", "Segurança")}</option>
            <option value="PARKING">{t("occurrences.category_labels.PARKING", "Estacionamento / Vagas")}</option>
            <option value="RULES_VIOLATION">{t("occurrences.category_labels.RULES_VIOLATION", "Infração ao Regulamento")}</option>
            <option value="OTHER">{t("occurrences.category_labels.OTHER", "Outros")}</option>
          </select>

          {/* Status Filter */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as OccurrenceStatus | "")}
            className="w-full px-3 py-2 text-sm border rounded-lg text-gray-800 bg-gray-50 focus:bg-white"
          >
            <option value="">{t("occurrences.filters.all_statuses", "Todos os Status")}</option>
            <option value="OPEN">{t("occurrences.status.OPEN", "Aberto")}</option>
            <option value="UNDER_REVIEW">{t("occurrences.status.UNDER_REVIEW", "Em Análise")}</option>
            <option value="IN_PROGRESS">{t("occurrences.status.IN_PROGRESS", "Em Andamento")}</option>
            <option value="RESOLVED">{t("occurrences.status.RESOLVED", "Resolvido")}</option>
            <option value="REJECTED">{t("occurrences.status.REJECTED", "Rejeitado")}</option>
          </select>

          {/* Public/Private Filter */}
          <select
            value={typeof isPublicFilter === "boolean" ? String(isPublicFilter) : ""}
            onChange={(e) => {
              const val = e.target.value;
              setIsPublicFilter(val === "" ? "" : val === "true");
            }}
            className="w-full px-3 py-2 text-sm border rounded-lg text-gray-800 bg-gray-50 focus:bg-white"
          >
            <option value="">{t("occurrences.filters.all_visibility", "Todas as Visibilidades")}</option>
            <option value="true">{t("occurrences.public", "Apenas Públicas")}</option>
            <option value="false">{t("occurrences.private", "Apenas Privadas")}</option>
          </select>
        </div>
      </div>

      {/* Main Table */}
      <OccurrenceTable
        occurrences={data?.items || []}
        isLoading={isLoading}
        onSelectOccurrence={(id) => setSelectedOccurrenceId(id)}
      />

      {/* New Occurrence Modal */}
      <NewOccurrenceModal
        isOpen={isNewModalOpen}
        onClose={() => setIsNewModalOpen(false)}
      />

      {/* Occurrence Details View Modal */}
      {selectedOccurrenceId && (
        <OccurrenceDetailsView
          occurrenceId={selectedOccurrenceId}
          userRole={role}
          onClose={() => setSelectedOccurrenceId(null)}
        />
      )}
    </div>
  );
};
