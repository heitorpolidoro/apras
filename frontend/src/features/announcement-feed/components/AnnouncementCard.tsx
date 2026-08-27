import React, { useEffect } from "react";
import { useTranslation } from "react-i18next";
import { MessageCircle, CheckCheck, Pencil, Trash2 } from "lucide-react";
import { useAuth, UserRole } from "../../user-administration/context/AuthContext";
import {
  useAnnouncementComments,
  useDeleteAnnouncement,
  useMarkAnnouncementRead,
} from "../hooks/useAnnouncements";
import { MediaCarousel } from "./MediaCarousel";
import { CommentThread } from "./CommentThread";
import type { Announcement } from "../../../types/announcement";

interface AnnouncementCardProps {
  announcement: Announcement;
  onEdit?: (announcement: Announcement) => void;
}

export const AnnouncementCard: React.FC<AnnouncementCardProps> = ({ announcement, onEdit }) => {
  const { t } = useTranslation();
  const { user } = useAuth();
  const markRead = useMarkAnnouncementRead();
  const deleteAnnouncement = useDeleteAnnouncement();
  const { data: comments } = useAnnouncementComments(announcement.id);

  const isPublisher = user?.role === UserRole.ADMINISTRATOR || user?.role === UserRole.DIRECTOR;

  useEffect(() => {
    if (!announcement.is_read) {
      markRead.mutate(announcement.id);
    }
    // Only mark as read once when the card first mounts / announcement changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [announcement.id]);

  const handleDelete = () => {
    deleteAnnouncement.mutate(announcement.id);
  };

  return (
    <article className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 space-y-4">
      <header className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-lg font-bold text-gray-900">{announcement.title}</h3>
          <p className="text-xs text-gray-500">
            {announcement.author_name ?? t("announcements.unknown_author", "Usuário")} ·{" "}
            {new Date(announcement.created_at).toLocaleDateString()}
          </p>
        </div>

        <div className="flex items-center gap-2">
          {announcement.is_read && (
            <span
              title={t("announcements.read", "Lido")}
              className="flex items-center gap-1 text-xs text-emerald-600"
            >
              <CheckCheck className="w-4 h-4" />
            </span>
          )}
          {isPublisher && (
            <>
              <button
                type="button"
                aria-label={t("announcements.edit", "Editar comunicado")}
                onClick={() => onEdit?.(announcement)}
                className="p-1.5 text-gray-400 hover:text-indigo-600 rounded-md hover:bg-gray-100"
              >
                <Pencil className="w-4 h-4" />
              </button>
              <button
                type="button"
                aria-label={t("announcements.delete", "Excluir comunicado")}
                onClick={handleDelete}
                className="p-1.5 text-gray-400 hover:text-red-600 rounded-md hover:bg-gray-100"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </>
          )}
        </div>
      </header>

      <p className="text-sm text-gray-700 whitespace-pre-wrap">{announcement.content}</p>

      {announcement.media.length > 0 && <MediaCarousel media={announcement.media} />}

      <div className="flex items-center gap-1.5 text-xs text-gray-500">
        <MessageCircle className="w-3.5 h-3.5" />
        {t("announcements.comment_count", "{{count}} comentários", {
          count: announcement.comment_count,
        })}
      </div>

      <CommentThread announcementId={announcement.id} comments={comments ?? []} />
    </article>
  );
};
