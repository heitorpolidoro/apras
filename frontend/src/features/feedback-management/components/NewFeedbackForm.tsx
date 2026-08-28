import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { EyeOff, Send } from "lucide-react";
import type { FeedbackCategory } from "../../../types/feedback";
import { useCreateFeedback } from "../hooks/useFeedback";

export const NewFeedbackForm: React.FC = () => {
  const { t } = useTranslation();
  const createMutation = useCreateFeedback();

  const [category, setCategory] = useState<FeedbackCategory>("SUGGESTION");
  const [message, setMessage] = useState("");
  const [isAnonymous, setIsAnonymous] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    await createMutation.mutateAsync({
      category,
      message: message.trim(),
      is_anonymous: isAnonymous,
    });

    setMessage("");
    setIsAnonymous(false);
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm space-y-4"
    >
      <h2 className="text-lg font-bold text-gray-900">
        {t("feedback.form_title", "Enviar Mensagem")}
      </h2>

      <div>
        <label className="block text-xs font-semibold text-gray-700 mb-1">
          {t("feedback.category", "Categoria")}
        </label>
        <select
          value={category}
          onChange={(e) => setCategory(e.target.value as FeedbackCategory)}
          className="w-full text-sm border rounded-md p-2 text-gray-800 bg-white"
        >
          <option value="CRITICISM">{t("feedback.category_labels.CRITICISM", "Crítica")}</option>
          <option value="SUGGESTION">{t("feedback.category_labels.SUGGESTION", "Sugestão")}</option>
          <option value="COMPLIMENT">{t("feedback.category_labels.COMPLIMENT", "Elogio")}</option>
          <option value="OTHER">{t("feedback.category_labels.OTHER", "Outro")}</option>
        </select>
      </div>

      <div>
        <label className="block text-xs font-semibold text-gray-700 mb-1">
          {t("feedback.message", "Mensagem")}
        </label>
        <textarea
          required
          rows={4}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder={t(
            "feedback.message_placeholder",
            "Escreva sua crítica, sugestão ou elogio..."
          )}
          className="w-full text-sm border rounded-md p-2 text-gray-800 focus:ring-2 focus:ring-indigo-500"
        />
      </div>

      <label className="flex items-center gap-2 p-3 border rounded-lg cursor-pointer bg-gray-50 hover:bg-gray-100">
        <input
          type="checkbox"
          checked={isAnonymous}
          onChange={(e) => setIsAnonymous(e.target.checked)}
          className="rounded text-indigo-600"
        />
        <div className="text-xs">
          <span className="font-semibold text-gray-800 flex items-center gap-1">
            <EyeOff className="w-3.5 h-3.5 text-gray-500" />
            {t("feedback.anonymous_toggle", "Enviar anonimamente")}
          </span>
          <p className="text-gray-500 text-[10px]">
            {t("feedback.anonymous_hint", "Ocultar sua identidade da diretoria.")}
          </p>
        </div>
      </label>

      <button
        type="submit"
        disabled={createMutation.isPending || !message.trim()}
        className="inline-flex items-center justify-center gap-2 px-4 py-2 text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg shadow-sm transition-colors disabled:opacity-50"
      >
        <Send className="w-4 h-4" />
        {t("feedback.submit", "Enviar")}
      </button>
    </form>
  );
};
