import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { AlertCircle, CheckCircle2, Clock, Globe, Lock, MapPin, User as UserIcon, X } from "lucide-react";
import type { OccurrencePriority, OccurrenceStatus } from "../../../types/occurrence";
import { useOccurrenceDetail, useUpdateOccurrenceStatus } from "../hooks/useOccurrences";
import { OccurrenceTimelineLog } from "./OccurrenceTimelineLog";

interface OccurrenceDetailsViewProps {
  occurrenceId: string;
  userRole?: string;
  onClose: () => void;
}

export const OccurrenceDetailsView: React.FC<OccurrenceDetailsViewProps> = ({
  occurrenceId,
  userRole,
  onClose,
}) => {
  const { t } = useTranslation();
  const { data: occurrence, isLoading } = useOccurrenceDetail(occurrenceId);
  const updateStatusMutation = useUpdateOccurrenceStatus();

  const [editStatus, setEditStatus] = useState<OccurrenceStatus | "">("");
  const [editPriority, setEditPriority] = useState<OccurrencePriority | "">("");
  const [resolutionNotes, setResolutionNotes] = useState("");

  const isManagement = userRole === "ADMINISTRATOR" || userRole === "DIRECTOR";

  if (isLoading || !occurrence) {
    return (
      <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4 z-50">
        <div className="bg-white rounded-xl p-8 max-w-2xl w-full text-center">
          <p className="text-gray-500">{t("common.loading", "Carregando...")}</p>
        </div>
      </div>
    );
  }

  const handleStatusUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    await updateStatusMutation.mutateAsync({
      id: occurrence.id,
      data: {
        status: editStatus ? (editStatus as OccurrenceStatus) : occurrence.status,
        priority: editPriority ? (editPriority as OccurrencePriority) : occurrence.priority,
        resolution_notes: resolutionNotes ? resolutionNotes : undefined,
      },
    });
    setResolutionNotes("");
  };

  return (
    <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4 z-50 overflow-y-auto">
      <div className="bg-white rounded-xl shadow-xl max-w-4xl w-full my-8 flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="font-mono text-sm font-bold text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded border border-indigo-200">
                {occurrence.protocol_number}
              </span>
              {occurrence.is_public ? (
                <span className="inline-flex items-center gap-1 text-xs text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded">
                  <Globe className="w-3 h-3" />
                  {t("occurrences.public", "Pública")}
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 text-xs text-gray-600 bg-gray-100 border border-gray-200 px-2 py-0.5 rounded">
                  <Lock className="w-3 h-3" />
                  {t("occurrences.private", "Privada")}
                </span>
              )}
            </div>
            <h2 className="text-xl font-bold text-gray-900">{occurrence.title}</h2>
          </div>

          <button
            onClick={onClose}
            className="p-1 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto space-y-6">
          {/* Metadata Grid */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 bg-gray-50 rounded-lg p-4 text-sm">
            <div className="flex items-center gap-2">
              <UserIcon className="w-4 h-4 text-gray-400" />
              <div>
                <p className="text-xs text-gray-500">{t("occurrences.reporter", "Relator")}</p>
                <p className="font-medium text-gray-800">
                  {occurrence.reporter_name || t("occurrences.anonymous", "Anônimo")}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <MapPin className="w-4 h-4 text-gray-400" />
              <div>
                <p className="text-xs text-gray-500">{t("occurrences.lot", "Lote Referência")}</p>
                <p className="font-medium text-gray-800">{occurrence.lot_summary || "-"}</p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4 text-gray-400" />
              <div>
                <p className="text-xs text-gray-500">{t("occurrences.created_at", "Data de Registro")}</p>
                <p className="font-medium text-gray-800">
                  {new Date(occurrence.created_at).toLocaleString()}
                </p>
              </div>
            </div>
          </div>

          {/* Description */}
          <div>
            <h3 className="text-sm font-semibold text-gray-700 mb-1">
              {t("occurrences.description", "Descrição do ocorrido")}
            </h3>
            <p className="text-gray-800 bg-gray-50 p-4 rounded-lg text-sm whitespace-pre-wrap">
              {occurrence.description}
            </p>
          </div>

          {/* Photos */}
          {occurrence.photo_urls && occurrence.photo_urls.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-gray-700 mb-2">
                {t("occurrences.photos", "Fotos / Evidências")}
              </h3>
              <div className="flex flex-wrap gap-2">
                {occurrence.photo_urls.map((url, idx) => (
                  <a
                    key={idx}
                    href={url}
                    target="_blank"
                    rel="noreferrer"
                    className="block text-xs text-indigo-600 bg-indigo-50 px-3 py-1.5 rounded border border-indigo-200 hover:underline"
                  >
                    Evidência #{idx + 1}
                  </a>
                ))}
              </div>
            </div>
          )}

          {/* Resolution Notes */}
          {occurrence.resolution_notes && (
            <div className="bg-emerald-50 border border-emerald-200 p-4 rounded-lg">
              <h3 className="text-sm font-semibold text-emerald-900 flex items-center gap-1.5 mb-1">
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                {t("occurrences.resolution_notes", "Parecer de Resolução")}
              </h3>
              <p className="text-sm text-emerald-800">{occurrence.resolution_notes}</p>
            </div>
          )}

          {/* Management Update Controls */}
          {isManagement && (
            <form onSubmit={handleStatusUpdate} className="bg-slate-50 border p-4 rounded-lg space-y-3">
              <h3 className="text-sm font-semibold text-gray-800 flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-indigo-600" />
                {t("occurrences.manage_ticket", "Gestão do Chamado (Administração)")}
              </h3>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">
                    {t("occurrences.change_status", "Alterar Status")}
                  </label>
                  <select
                    value={editStatus || occurrence.status}
                    onChange={(e) => setEditStatus(e.target.value as OccurrenceStatus)}
                    className="w-full text-xs border rounded p-2 text-gray-800 bg-white"
                  >
                    <option value="OPEN">{t("occurrences.status.OPEN", "Aberto")}</option>
                    <option value="UNDER_REVIEW">{t("occurrences.status.UNDER_REVIEW", "Em Análise")}</option>
                    <option value="IN_PROGRESS">{t("occurrences.status.IN_PROGRESS", "Em Andamento")}</option>
                    <option value="RESOLVED">{t("occurrences.status.RESOLVED", "Resolvido")}</option>
                    <option value="REJECTED">{t("occurrences.status.REJECTED", "Rejeitado")}</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">
                    {t("occurrences.change_priority", "Alterar Prioridade")}
                  </label>
                  <select
                    value={editPriority || occurrence.priority}
                    onChange={(e) => setEditPriority(e.target.value as OccurrencePriority)}
                    className="w-full text-xs border rounded p-2 text-gray-800 bg-white"
                  >
                    <option value="LOW">{t("occurrences.priority.LOW", "Baixa")}</option>
                    <option value="MEDIUM">{t("occurrences.priority.MEDIUM", "Média")}</option>
                    <option value="HIGH">{t("occurrences.priority.HIGH", "Alta")}</option>
                    <option value="URGENT">{t("occurrences.priority.URGENT", "Urgente")}</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  {t("occurrences.resolution_notes_input", "Parecer de Resolução / Justificativa")}
                </label>
                <textarea
                  value={resolutionNotes}
                  onChange={(e) => setResolutionNotes(e.target.value)}
                  placeholder={t("occurrences.resolution_placeholder", "Descreva o parecer de conclusão...")}
                  rows={2}
                  className="w-full text-xs border rounded p-2 text-gray-800 bg-white"
                />
              </div>

              <button
                type="submit"
                disabled={updateStatusMutation.isPending}
                className="px-3 py-1.5 text-xs font-medium text-white bg-indigo-600 rounded hover:bg-indigo-700"
              >
                {t("common.save", "Salvar Alterações")}
              </button>
            </form>
          )}

          {/* Timeline Log */}
          <OccurrenceTimelineLog
            occurrenceId={occurrence.id}
            timeline={occurrence.timeline || []}
            userRole={userRole}
          />
        </div>
      </div>
    </div>
  );
};
