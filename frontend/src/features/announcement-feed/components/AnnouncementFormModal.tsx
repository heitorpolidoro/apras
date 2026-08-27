import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { Paperclip, Plus, X } from "lucide-react";
import {
  useCreateAnnouncement,
  useUpdateAnnouncement,
  useUploadAnnouncementMedia,
} from "../hooks/useAnnouncements";
import type { Announcement } from "../../../types/announcement";

interface AnnouncementFormModalProps {
  isOpen: boolean;
  onClose: () => void;
  announcement?: Announcement | null;
}

/**
 * Renders the create/edit form. Mounted fresh (via a `key` on the parent)
 * whenever the target announcement changes, so initial field values are
 * derived directly from props without needing an effect-based reset.
 */
const AnnouncementFormModalContent: React.FC<
  Omit<AnnouncementFormModalProps, "isOpen"> & { announcement?: Announcement | null }
> = ({ onClose, announcement }) => {
  const { t } = useTranslation();
  const createMutation = useCreateAnnouncement();
  const updateMutation = useUpdateAnnouncement();
  const uploadMediaMutation = useUploadAnnouncementMedia();

  const [title, setTitle] = useState(announcement?.title ?? "");
  const [content, setContent] = useState(announcement?.content ?? "");
  const [file, setFile] = useState<File | null>(null);

  const isEditing = Boolean(announcement);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    let announcementId = announcement?.id;

    if (isEditing && announcementId) {
      await updateMutation.mutateAsync({
        id: announcementId,
        data: { title: title.trim(), content: content.trim() },
      });
    } else {
      const created = await createMutation.mutateAsync({
        title: title.trim(),
        content: content.trim(),
      });
      announcementId = created.id;
    }

    if (file && announcementId) {
      await uploadMediaMutation.mutateAsync({ id: announcementId, file });
    }

    setTitle("");
    setContent("");
    setFile(null);
    onClose();
  };

  const isPending =
    createMutation.isPending || updateMutation.isPending || uploadMediaMutation.isPending;

  return (
    <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4 z-50 overflow-y-auto">
      <div className="bg-white rounded-xl shadow-xl max-w-lg w-full p-6 space-y-6">
        <div className="flex items-center justify-between border-b pb-4">
          <h2 className="text-lg font-bold text-gray-900 flex items-center gap-2">
            <Plus className="w-5 h-5 text-indigo-600" />
            {isEditing
              ? t("announcements.edit_title", "Editar Comunicado")
              : t("announcements.new_title", "Novo Comunicado")}
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
              {t("announcements.title_label", "Título")}
            </label>
            <input
              type="text"
              required
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder={t("announcements.title_placeholder", "Ex: Assembleia Geral Ordinária")}
              className="w-full text-sm border rounded-md p-2 text-gray-800 focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">
              {t("announcements.content_label", "Conteúdo")}
            </label>
            <textarea
              required
              rows={5}
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder={t("announcements.content_placeholder", "Escreva o comunicado...")}
              className="w-full text-sm border rounded-md p-2 text-gray-800 focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          <div>
            <label className="flex items-center gap-2 p-3 border rounded-lg cursor-pointer bg-gray-50 hover:bg-gray-100 text-xs font-semibold text-gray-700">
              <Paperclip className="w-4 h-4 text-indigo-600" />
              {file ? file.name : t("announcements.attach_media", "Anexar imagem ou PDF")}
              <input
                type="file"
                accept="image/jpeg,image/png,image/webp,application/pdf"
                className="hidden"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              />
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
              disabled={isPending || !title.trim() || !content.trim()}
              className="px-4 py-2 text-xs font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-md disabled:opacity-50"
            >
              {isEditing
                ? t("announcements.save", "Salvar Alterações")
                : t("announcements.publish", "Publicar Comunicado")}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export const AnnouncementFormModal: React.FC<AnnouncementFormModalProps> = ({
  isOpen,
  onClose,
  announcement,
}) => {
  if (!isOpen) return null;

  return (
    <AnnouncementFormModalContent
      key={announcement?.id ?? "new"}
      onClose={onClose}
      announcement={announcement}
    />
  );
};
