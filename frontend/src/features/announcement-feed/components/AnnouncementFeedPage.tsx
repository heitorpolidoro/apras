import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { Megaphone, Plus } from "lucide-react";
import { useEffectivePermissionSet } from "../../user-administration/access/useCanAccess";
import { useAnnouncements } from "../hooks/useAnnouncements";
import { AnnouncementCard } from "./AnnouncementCard";
import { AnnouncementFormModal } from "./AnnouncementFormModal";
import type { Announcement } from "../../../types/announcement";

export const AnnouncementFeedPage: React.FC = () => {
  const { t } = useTranslation();
  const { has } = useEffectivePermissionSet();
  const { data, isLoading } = useAnnouncements();

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingAnnouncement, setEditingAnnouncement] = useState<Announcement | null>(null);

  // IAM F5 (APRAS-49 §10.2): `announcements:create` is the legacy
  // {A, D} set exactly, so this is the same predicate as data.
  const isPublisher = has("announcements:create");

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
      <div className="flex items-center justify-between gap-4 bg-card p-6 rounded-xl border border-border shadow-sm">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-accent text-primary rounded-lg">
            <Megaphone className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-foreground">
              {t("announcements.page_title", "Comunicados e Notícias")}
            </h1>
            <p className="text-sm text-muted-foreground">
              {t("announcements.page_subtitle", "Fique por dentro das novidades do condomínio.")}
            </p>
          </div>
        </div>

        {isPublisher && (
          <button
            onClick={openCreateModal}
            className="inline-flex items-center justify-center gap-2 px-4 py-2.5 text-sm font-semibold text-primary-foreground bg-primary hover:bg-primary/90 rounded-lg shadow-sm transition-colors shrink-0"
          >
            <Plus className="w-4 h-4" />
            {t("announcements.new_announcement_btn", "Novo Comunicado")}
          </button>
        )}
      </div>

      {isLoading && (
        <p className="text-sm text-muted-foreground text-center">
          {t("common.loading", "Carregando...")}
        </p>
      )}

      {!isLoading && (data?.items.length ?? 0) === 0 && (
        <p className="text-sm text-muted-foreground text-center bg-card p-6 rounded-xl border border-border">
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
