import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { Megaphone, Plus } from "lucide-react";
import { useAuth, UserRole } from "../../user-administration/context/AuthContext";
import { useAnnouncements } from "../hooks/useAnnouncements";
import { AnnouncementCard } from "./AnnouncementCard";
import { AnnouncementFormModal } from "./AnnouncementFormModal";
import type { Announcement } from "../../../types/announcement";

export const AnnouncementFeedPage: React.FC = () => {
  const { t } = useTranslation();
  const { user } = useAuth();
  const { data, isLoading } = useAnnouncements();

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingAnnouncement, setEditingAnnouncement] = useState<Announcement | null>(null);

  const isPublisher = user?.role === UserRole.ADMINISTRATOR || user?.role === UserRole.DIRECTOR;

  const openCreateModal = () => {
    setEditingAnnouncement(null);
    setIsModalOpen(true);
  };

  const openEditModal = (announcement: Announcement) => {
    setEditingAnnouncement(announcement);
    setIsModalOpen(true);
  };

  return (
    <div className="container mx-auto px-4 py-8 max-w-2xl space-y-6">
      <div className="flex items-center justify-between gap-4 bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-indigo-50 text-indigo-600 rounded-lg">
            <Megaphone className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              {t("announcements.page_title", "Comunicados e Notícias")}
            </h1>
            <p className="text-sm text-gray-500">
              {t("announcements.page_subtitle", "Fique por dentro das novidades do condomínio.")}
            </p>
          </div>
        </div>

        {isPublisher && (
          <button
            onClick={openCreateModal}
            className="inline-flex items-center justify-center gap-2 px-4 py-2.5 text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg shadow-sm transition-colors shrink-0"
          >
            <Plus className="w-4 h-4" />
            {t("announcements.new_announcement_btn", "Novo Comunicado")}
          </button>
        )}
      </div>

      {isLoading && (
        <p className="text-sm text-gray-500 text-center">
          {t("common.loading", "Carregando...")}
        </p>
      )}

      {!isLoading && (data?.items.length ?? 0) === 0 && (
        <p className="text-sm text-gray-400 text-center bg-white p-6 rounded-xl border border-gray-200">
          {t("announcements.empty_feed", "Nenhum comunicado publicado até o momento.")}
        </p>
      )}

      <div className="space-y-5">
        {data?.items.map((announcement) => (
          <AnnouncementCard
            key={announcement.id}
            announcement={announcement}
            onEdit={openEditModal}
          />
        ))}
      </div>

      <AnnouncementFormModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        announcement={editingAnnouncement}
      />
    </div>
  );
};
