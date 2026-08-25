import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { Lock, MessageSquare, Send } from "lucide-react";
import type { OccurrenceStatus, OccurrenceTimeline } from "../../../types/occurrence";
import { useAddTimelineNote } from "../hooks/useOccurrences";

interface OccurrenceTimelineLogProps {
  occurrenceId: string;
  timeline: OccurrenceTimeline[];
  userRole?: string;
}

export const OccurrenceTimelineLog: React.FC<OccurrenceTimelineLogProps> = ({
  occurrenceId,
  timeline,
  userRole,
}) => {
  const { t } = useTranslation();
  const [noteText, setNoteText] = useState("");
  const [isInternalOnly, setIsInternalOnly] = useState(false);
  const [statusTo, setStatusTo] = useState<OccurrenceStatus | "">("");

  const addNoteMutation = useAddTimelineNote();

  const isManagement = userRole === "ADMINISTRATOR" || userRole === "DIRECTOR";

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!noteText.trim()) return;

    await addNoteMutation.mutateAsync({
      id: occurrenceId,
      data: {
        note: noteText.trim(),
        is_internal_only: isManagement ? isInternalOnly : false,
        status_to: statusTo ? (statusTo as OccurrenceStatus) : null,
      },
    });

    setNoteText("");
    setIsInternalOnly(false);
    setStatusTo("");
  };

  return (
    <div className="space-y-6">
      <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
        <MessageSquare className="w-5 h-5 text-indigo-600" />
        {t("occurrences.timeline.title", "Histórico e Trâmite")}
      </h3>

      <div className="relative border-l-2 border-gray-200 pl-4 space-y-4 ml-2">
        {timeline.map((entry) => (
          <div key={entry.id} className="relative group">
            <div className="absolute -left-6 top-1 w-3 h-3 bg-indigo-600 rounded-full border-2 border-white ring-2 ring-gray-100" />
            <div className="bg-gray-50 border border-gray-100 rounded-lg p-3">
              <div className="flex items-center justify-between text-xs text-gray-500 mb-1">
                <span className="font-medium text-gray-900">
                  {entry.actor_name || t("occurrences.anonymous", "Anônimo")}
                </span>
                <span>{new Date(entry.created_at).toLocaleString()}</span>
              </div>

              {entry.is_internal_only && (
                <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-amber-700 bg-amber-50 border border-amber-200 px-1.5 py-0.5 rounded mb-1">
                  <Lock className="w-3 h-3" />
                  {t("occurrences.timeline.internal_note", "Nota Interna")}
                </span>
              )}

              {entry.status_to && (
                <div className="text-xs font-semibold text-indigo-700 mb-1">
                  {entry.status_from ? `${t(`occurrences.status.${entry.status_from}`)} ➔ ` : ""}
                  {t(`occurrences.status.${entry.status_to}`)}
                </div>
              )}

              <p className="text-sm text-gray-700 whitespace-pre-wrap">{entry.note}</p>
            </div>
          </div>
        ))}
      </div>

      <form onSubmit={handleSubmit} className="bg-white border rounded-lg p-4 space-y-3 shadow-sm">
        <h4 className="text-sm font-medium text-gray-800">
          {t("occurrences.timeline.add_note", "Adicionar observação ou atualização")}
        </h4>
        <textarea
          value={noteText}
          onChange={(e) => setNoteText(e.target.value)}
          placeholder={t("occurrences.timeline.note_placeholder", "Escreva aqui a observação...")}
          rows={3}
          required
          className="w-full border rounded-md p-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
        />

        <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
          <div className="flex items-center gap-4">
            {isManagement && (
              <label className="inline-flex items-center text-xs text-gray-700 gap-1.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={isInternalOnly}
                  onChange={(e) => setIsInternalOnly(e.target.checked)}
                  className="rounded text-indigo-600 focus:ring-indigo-500"
                />
                {t("occurrences.timeline.internal_only_label", "Apenas interno (Administração)")}
              </label>
            )}

            {isManagement && (
              <select
                value={statusTo}
                onChange={(e) => setStatusTo(e.target.value as OccurrenceStatus)}
                className="border text-xs rounded p-1 text-gray-700"
              >
                <option value="">{t("occurrences.timeline.select_status", "Manter status atual")}</option>
                <option value="OPEN">{t("occurrences.status.OPEN", "Aberto")}</option>
                <option value="UNDER_REVIEW">{t("occurrences.status.UNDER_REVIEW", "Em Análise")}</option>
                <option value="IN_PROGRESS">{t("occurrences.status.IN_PROGRESS", "Em Andamento")}</option>
                <option value="RESOLVED">{t("occurrences.status.RESOLVED", "Resolvido")}</option>
                <option value="REJECTED">{t("occurrences.status.REJECTED", "Rejeitado")}</option>
              </select>
            )}
          </div>

          <button
            type="submit"
            disabled={addNoteMutation.isPending || !noteText.trim()}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-white bg-indigo-600 rounded-md hover:bg-indigo-700 disabled:opacity-50"
          >
            <Send className="w-3.5 h-3.5" />
            {t("occurrences.timeline.send", "Enviar")}
          </button>
        </div>
      </form>
    </div>
  );
};
