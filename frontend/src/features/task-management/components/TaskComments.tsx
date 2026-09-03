import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { useComments, useCreateComment, useUpdateComment,  } from "../hooks/useTasks";
import { useAuth } from "../../user-administration/context/AuthContext";
import type { TaskCommentRead } from "../types";
import { Button } from "../../../components/ui/button";
import { Textarea } from "../../../components/ui/textarea";

interface TaskCommentsProps {
  taskId: string;
}

interface CommentItemProps {
  comment: TaskCommentRead;
  currentUserId: string;
  taskId: string;
}

const CommentItem: React.FC<CommentItemProps> = ({
  comment,
  currentUserId,
  taskId,
}) => {
  const { t, i18n } = useTranslation();
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(comment.content);
  const updateComment = useUpdateComment(taskId);

  const isOwner = comment.created_by_id === currentUserId;

  const formatDate = (date: string) =>
    new Date(date).toLocaleString(i18n.language === "pt" ? "pt-BR" : "en-US");

  const handleSave = () => {
    if (!draft.trim() || draft === comment.content) {
      setEditing(false);
      return;
    }
    updateComment.mutate(
      { commentId: comment.id, content: draft.trim() },
      { onSuccess: () => setEditing(false) },
    );
  };

  const handleCancel = () => {
    setDraft(comment.content);
    setEditing(false);
  };

  return (
    <div className="flex flex-col gap-1 py-3 border-b last:border-b-0">
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-semibold text-foreground">
          {comment.created_by_name}
        </span>
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground">
            {formatDate(comment.created_at)}
            {comment.updated_at !== comment.created_at && (
              <span className="italic"> ({t("tasks.comments.edited")})</span>
            )}
          </span>
          {isOwner && !editing && (
            <button
              onClick={() => setEditing(true)}
              className="text-xs text-muted-foreground hover:text-foreground underline"
            >
              {t("tasks.comments.edit")}
            </button>
          )}
        </div>
      </div>

      {editing ? (
        <div className="flex flex-col gap-2 mt-1">
          <Textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            rows={2}
            disabled={updateComment.isPending}
            className="text-sm"
          />
          <div className="flex gap-2 justify-end">
            <Button
              variant="outline"
              size="sm"
              onClick={handleCancel}
              disabled={updateComment.isPending}
            >
              {t("tasks.comments.cancel")}
            </Button>
            <Button
              size="sm"
              onClick={handleSave}
              disabled={!draft.trim() || updateComment.isPending}
            >
              {t("tasks.comments.save")}
            </Button>
          </div>
        </div>
      ) : (
        <p className="text-sm text-foreground whitespace-pre-wrap">
          {comment.content}
        </p>
      )}
    </div>
  );
};

const TaskComments: React.FC<TaskCommentsProps> = ({ taskId }) => {
  const { t } = useTranslation();
  const { user } = useAuth();
  const { data: comments, isLoading } = useComments(taskId);
  const createComment = useCreateComment(taskId);
  const [newComment, setNewComment] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newComment.trim()) return;
    createComment.mutate(newComment.trim(), {
      onSuccess: () => setNewComment(""),
    });
  };

  return (
    <section className="mt-4">
      <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
        {t("tasks.comments.title")}
      </p>

      {isLoading ? (
        <p className="text-xs text-muted-foreground">
          {t("tasks.comments.loading")}
        </p>
      ) : comments && comments.length > 0 ? (
        <div className="mb-3">
          {comments.map((comment) => (
            <CommentItem
              key={comment.id}
              comment={comment}
              currentUserId={user?.id ?? ""}
              taskId={taskId}
            />
          ))}
        </div>
      ) : (
        <p className="text-xs text-muted-foreground mb-3">
          {t("tasks.comments.empty")}
        </p>
      )}

      <form onSubmit={handleSubmit} className="flex flex-col gap-2">
        <Textarea
          value={newComment}
          onChange={(e) => setNewComment(e.target.value)}
          placeholder={t("tasks.comments.placeholder")}
          rows={2}
          disabled={createComment.isPending}
          className="text-sm"
        />
        <div className="flex justify-end">
          <Button
            type="submit"
            size="sm"
            disabled={!newComment.trim() || createComment.isPending}
          >
            {createComment.isPending
              ? t("tasks.comments.sending")
              : t("tasks.comments.send")}
          </Button>
        </div>
      </form>
    </section>
  );
};

export default TaskComments;
