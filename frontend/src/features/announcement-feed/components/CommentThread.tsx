import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { Send, Trash2 } from "lucide-react";
import { useAuth, UserRole } from "../../user-administration/context/AuthContext";
import { useAddComment, useDeleteComment } from "../hooks/useAnnouncements";
import type { AnnouncementComment } from "../../../types/announcement";

interface CommentThreadProps {
  announcementId: string;
  comments: AnnouncementComment[];
}

export const CommentThread: React.FC<CommentThreadProps> = ({ announcementId, comments }) => {
  const { t } = useTranslation();
  const { user } = useAuth();
  const [content, setContent] = useState("");
  const addComment = useAddComment();
  const deleteComment = useDeleteComment();

  const isGuest = user?.role === UserRole.GUEST;
  const isPublisher = user?.role === UserRole.ADMINISTRATOR || user?.role === UserRole.DIRECTOR;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!content.trim()) return;
    await addComment.mutateAsync({ id: announcementId, data: { content: content.trim() } });
    setContent("");
  };

  const handleDelete = (commentId: string) => {
    deleteComment.mutate({ commentId, announcementId });
  };

  return (
    <div className="space-y-3 pt-3 border-t border-gray-100">
      <div className="space-y-2">
        {comments.map((comment) => {
          const canDelete = isPublisher || comment.user_id === user?.id;
          return (
            <div
              key={comment.id}
              className="flex items-start justify-between gap-2 text-sm bg-gray-50 rounded-lg px-3 py-2"
            >
              <div>
                <span className="font-semibold text-gray-800">
                  {comment.author_name ?? t("announcements.unknown_author", "Usuário")}
                </span>{" "}
                <span className="text-gray-600">{comment.content}</span>
              </div>
              {canDelete && (
                <button
                  type="button"
                  aria-label={t("announcements.delete_comment", "Excluir comentário")}
                  onClick={() => handleDelete(comment.id)}
                  className="text-gray-400 hover:text-red-600 shrink-0"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
          );
        })}
        {comments.length === 0 && (
          <p className="text-xs text-gray-400">
            {t("announcements.no_comments", "Nenhum comentário ainda.")}
          </p>
        )}
      </div>

      {!isGuest && (
        <form onSubmit={handleSubmit} className="flex items-center gap-2">
          <input
            type="text"
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder={t("announcements.comment_placeholder", "Escreva um comentário...")}
            className="flex-1 text-sm border rounded-full px-4 py-2 text-gray-800 focus:ring-2 focus:ring-indigo-500"
          />
          <button
            type="submit"
            disabled={addComment.isPending || !content.trim()}
            aria-label={t("announcements.send_comment", "Enviar comentário")}
            className="p-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-full disabled:opacity-50"
          >
            <Send className="w-4 h-4" />
          </button>
        </form>
      )}
    </div>
  );
};
