import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { Eye, EyeOff, Globe, Lock, Plus, X } from "lucide-react";
import type { OccurrenceCategory } from "../../../types/occurrence";
import { useCreateOccurrence } from "../hooks/useOccurrences";

interface NewOccurrenceModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const NewOccurrenceModal: React.FC<NewOccurrenceModalProps> = ({
  isOpen,
  onClose,
}) => {
  const { t } = useTranslation();
  const createMutation = useCreateOccurrence();

  const [category, setCategory] = useState<OccurrenceCategory>("MAINTENANCE");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [isAnonymous, setIsAnonymous] = useState(false);
  const [isPublic, setIsPublic] = useState(false);
  const [photoUrlsInput, setPhotoUrlsInput] = useState("");

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const photoUrls = photoUrlsInput
      .split(",")
      .map((url) => url.trim())
      .filter((url) => url.length > 0);

    await createMutation.mutateAsync({
      category,
      title: title.trim(),
      description: description.trim(),
      is_anonymous: isAnonymous,
      is_public: isPublic,
      photo_urls: photoUrls.length > 0 ? photoUrls : null,
    });

    // Reset and close
    setTitle("");
    setDescription("");
    setIsAnonymous(false);
    setIsPublic(false);
    setPhotoUrlsInput("");
    onClose();
  };

  return (
    <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4 z-50 overflow-y-auto">
      <div className="bg-white rounded-xl shadow-xl max-w-lg w-full p-6 space-y-6">
        <div className="flex items-center justify-between border-b pb-4">
          <h2 className="text-lg font-bold text-gray-900 flex items-center gap-2">
            <Plus className="w-5 h-5 text-indigo-600" />
            {t("occurrences.new_occurrence", "Nova Ocorrência / Reclamação")}
          </h2>
          <button
            onClick={onClose}
            className="p-1 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">
              {t("occurrences.category", "Categoria")}
            </label>
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value as OccurrenceCategory)}
              className="w-full text-sm border rounded-md p-2 text-gray-800 bg-white"
            >
              <option value="NOISE">{t("occurrences.category_labels.NOISE", "Barulho / Perturbação")}</option>
              <option value="MAINTENANCE">{t("occurrences.category_labels.MAINTENANCE", "Manutenção / Infraestrutura")}</option>
              <option value="SECURITY">{t("occurrences.category_labels.SECURITY", "Segurança")}</option>
              <option value="PARKING">{t("occurrences.category_labels.PARKING", "Estacionamento / Vagas")}</option>
              <option value="RULES_VIOLATION">{t("occurrences.category_labels.RULES_VIOLATION", "Infração ao Regulamento")}</option>
              <option value="OTHER">{t("occurrences.category_labels.OTHER", "Outros")}</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">
              {t("occurrences.title", "Título da Ocorrência")}
            </label>
            <input
              type="text"
              required
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder={t("occurrences.title_placeholder", "Ex: Barulho de som após 22h na quadra B")}
              className="w-full text-sm border rounded-md p-2 text-gray-800 focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">
              {t("occurrences.description", "Descrição Detalhada")}
            </label>
            <textarea
              required
              rows={4}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder={t("occurrences.description_placeholder", "Descreva detalhadamente o ocorrido...")}
              className="w-full text-sm border rounded-md p-2 text-gray-800 focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">
              {t("occurrences.photo_urls", "Links de Fotos / Evidências (separados por vírgula)")}
            </label>
            <input
              type="text"
              value={photoUrlsInput}
              onChange={(e) => setPhotoUrlsInput(e.target.value)}
              placeholder="https://example.com/photo1.jpg, https://example.com/photo2.jpg"
              className="w-full text-sm border rounded-md p-2 text-gray-800 focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
            <label className="flex items-center gap-2 p-3 border rounded-lg cursor-pointer bg-gray-50 hover:bg-gray-100">
              <input
                type="checkbox"
                checked={isAnonymous}
                onChange={(e) => setIsAnonymous(e.target.checked)}
                className="rounded text-indigo-600"
              />
              <div className="text-xs">
                <span className="font-semibold text-gray-800 flex items-center gap-1">
                  {isAnonymous ? <EyeOff className="w-3.5 h-3.5 text-gray-500" /> : <Eye className="w-3.5 h-3.5 text-indigo-600" />}
                  {t("occurrences.anonymous_toggle", "Anonimato")}
                </span>
                <p className="text-gray-500 text-[10px]">
                  {t("occurrences.anonymous_hint", "Ocultar seu nome para outros moradores.")}
                </p>
              </div>
            </label>

            <label className="flex items-center gap-2 p-3 border rounded-lg cursor-pointer bg-gray-50 hover:bg-gray-100">
              <input
                type="checkbox"
                checked={isPublic}
                onChange={(e) => setIsPublic(e.target.checked)}
                className="rounded text-indigo-600"
              />
              <div className="text-xs">
                <span className="font-semibold text-gray-800 flex items-center gap-1">
                  {isPublic ? <Globe className="w-3.5 h-3.5 text-emerald-600" /> : <Lock className="w-3.5 h-3.5 text-gray-500" />}
                  {t("occurrences.public_toggle", "Visibilidade Pública")}
                </span>
                <p className="text-gray-500 text-[10px]">
                  {t("occurrences.public_hint", "Permitir que outros moradores vejam esta ocorrência.")}
                </p>
              </div>
            </label>
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-md"
            >
              {t("common.cancel", "Cancelar")}
            </button>
            <button
              type="submit"
              disabled={createMutation.isPending || !title.trim() || !description.trim()}
              className="px-4 py-2 text-xs font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-md disabled:opacity-50"
            >
              {t("occurrences.submit", "Registrar Ocorrência")}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
