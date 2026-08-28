import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { MessageSquare, X } from "lucide-react";
import { useFeedbackDetail, useRespondToFeedback } from "../hooks/useFeedback";

interface FeedbackDetailsViewProps {
  feedbackId: string;
  canRespond: boolean;
  onClose: () => void;
}

export const FeedbackDetailsView: React.FC<FeedbackDetailsViewProps> = ({
  feedbackId,
  canRespond,
  onClose,
}) => {
  const { t } = useTranslation();
  // Fetches via GET /feedback/{id}, which is the endpoint that flips
  // response_seen_by_reporter for the reporter's own view.
  const { data: feedback, isLoading } = useFeedbackDetail(feedbackId);
  const respondMutation = useRespondToFeedback();

  const [responseText, setResponseText] = useState("");

  if (isLoading || !feedback) {
    return (
      <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4 z-50">
        <div className="bg-white rounded-xl p-8 max-w-2xl w-full text-center">
          <p className="text-gray-500">{t("common.loading", "Carregando...")}</p>
        </div>
      </div>
    );
  }

  const handleRespond = async (e: React.FormEvent) => {
    e.preventDefault();
    await respondMutation.mutateAsync({
      id: feedback.id,
      data: { board_response: responseText.trim() },
    });
    setResponseText("");
  };

  return (
    <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4 z-50 overflow-y-auto">
      <div className="bg-white rounded-xl shadow-xl max-w-2xl w-full my-8 flex flex-col max-h-[90vh]">
        <div className="flex items-center justify-between p-6 border-b">
          <div className="space-y-1">
            <span className="bg-gray-100 text-gray-800 px-2 py-0.5 rounded border border-gray-200 font-medium text-xs">
              {t(`feedback.category_labels.${feedback.category}`, feedback.category)}
            </span>
            <h2 className="text-lg font-bold text-gray-900">
              {feedback.reporter_name || t("feedback.anonymous", "Anônimo")}
            </h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        <div className="p-6 overflow-y-auto space-y-6">
          <div>
            <h3 className="text-sm font-semibold text-gray-700 mb-1">
              {t("feedback.message", "Mensagem")}
            </h3>
            <p className="text-gray-800 bg-gray-50 p-4 rounded-lg text-sm whitespace-pre-wrap">
              {feedback.message}
            </p>
          </div>

          {feedback.board_response && (
            <div className="bg-emerald-50 border border-emerald-200 p-4 rounded-lg">
              <h3 className="text-sm font-semibold text-emerald-900 flex items-center gap-1.5 mb-1">
                <MessageSquare className="w-4 h-4 text-emerald-600" />
                {t("feedback.board_response", "Resposta da Diretoria")}
              </h3>
              <p className="text-sm text-emerald-800 whitespace-pre-wrap">
                {feedback.board_response}
              </p>
            </div>
          )}

          {canRespond && (
            <form onSubmit={handleRespond} className="bg-slate-50 border p-4 rounded-lg space-y-3">
              <h3 className="text-sm font-semibold text-gray-800">
                {t("feedback.respond_title", "Responder")}
              </h3>
              <textarea
                required
                rows={3}
                value={responseText}
                onChange={(e) => setResponseText(e.target.value)}
                placeholder={t("feedback.respond_placeholder", "Escreva a resposta da diretoria...")}
                className="w-full text-xs border rounded p-2 text-gray-800 bg-white"
              />
              <button
                type="submit"
                disabled={respondMutation.isPending || !responseText.trim()}
                className="px-3 py-1.5 text-xs font-medium text-white bg-indigo-600 rounded hover:bg-indigo-700 disabled:opacity-50"
              >
                {t("feedback.send_response", "Enviar Resposta")}
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};
