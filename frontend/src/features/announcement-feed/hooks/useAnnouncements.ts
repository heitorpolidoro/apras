import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  addAnnouncementComment,
  createAnnouncement,
  deleteAnnouncement,
  deleteAnnouncementComment,
  deleteAnnouncementMedia,
  getAnnouncementById,
  getAnnouncementComments,
  getAnnouncementReadReceipts,
  getAnnouncements,
  markAnnouncementRead,
  updateAnnouncement,
  uploadAnnouncementMedia,
} from "../../../api/announcements";
import type {
  AnnouncementCreatePayload,
  AnnouncementUpdatePayload,
  CommentCreatePayload,
} from "../../../types/announcement";

export const ANNOUNCEMENTS_QUERY_KEY = ["announcements"];

export function useAnnouncements(params?: { skip?: number; limit?: number }) {
  return useQuery({
    queryKey: [...ANNOUNCEMENTS_QUERY_KEY, params],
    queryFn: () => getAnnouncements(params),
  });
}

export function useAnnouncementDetail(id: string | null) {
  return useQuery({
    queryKey: [...ANNOUNCEMENTS_QUERY_KEY, "detail", id],
    queryFn: () => (id ? getAnnouncementById(id) : Promise.reject("No ID provided")),
    enabled: Boolean(id),
  });
}

export function useCreateAnnouncement() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: AnnouncementCreatePayload) => createAnnouncement(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ANNOUNCEMENTS_QUERY_KEY });
    },
  });
}

export function useUpdateAnnouncement() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: AnnouncementUpdatePayload }) =>
      updateAnnouncement(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ANNOUNCEMENTS_QUERY_KEY });
      queryClient.invalidateQueries({
        queryKey: [...ANNOUNCEMENTS_QUERY_KEY, "detail", variables.id],
      });
    },
  });
}

export function useDeleteAnnouncement() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteAnnouncement(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ANNOUNCEMENTS_QUERY_KEY });
    },
  });
}

export function useUploadAnnouncementMedia() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, file }: { id: string; file: File }) => uploadAnnouncementMedia(id, file),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ANNOUNCEMENTS_QUERY_KEY });
      queryClient.invalidateQueries({
        queryKey: [...ANNOUNCEMENTS_QUERY_KEY, "detail", variables.id],
      });
    },
  });
}

export function useDeleteAnnouncementMedia() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, mediaId }: { id: string; mediaId: string }) =>
      deleteAnnouncementMedia(id, mediaId),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ANNOUNCEMENTS_QUERY_KEY });
      queryClient.invalidateQueries({
        queryKey: [...ANNOUNCEMENTS_QUERY_KEY, "detail", variables.id],
      });
    },
  });
}

export function useAnnouncementComments(id: string | null) {
  return useQuery({
    queryKey: [...ANNOUNCEMENTS_QUERY_KEY, "comments", id],
    queryFn: () => (id ? getAnnouncementComments(id) : Promise.reject("No ID provided")),
    enabled: Boolean(id),
  });
}

export function useAddComment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: CommentCreatePayload }) =>
      addAnnouncementComment(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: [...ANNOUNCEMENTS_QUERY_KEY, "comments", variables.id],
      });
      queryClient.invalidateQueries({
        queryKey: [...ANNOUNCEMENTS_QUERY_KEY, "detail", variables.id],
      });
      queryClient.invalidateQueries({ queryKey: ANNOUNCEMENTS_QUERY_KEY });
    },
  });
}

export function useDeleteComment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ commentId }: { commentId: string; announcementId: string }) =>
      deleteAnnouncementComment(commentId),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: [...ANNOUNCEMENTS_QUERY_KEY, "comments", variables.announcementId],
      });
      queryClient.invalidateQueries({
        queryKey: [...ANNOUNCEMENTS_QUERY_KEY, "detail", variables.announcementId],
      });
      queryClient.invalidateQueries({ queryKey: ANNOUNCEMENTS_QUERY_KEY });
    },
  });
}

export function useMarkAnnouncementRead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => markAnnouncementRead(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ANNOUNCEMENTS_QUERY_KEY });
      queryClient.invalidateQueries({
        queryKey: [...ANNOUNCEMENTS_QUERY_KEY, "detail", id],
      });
    },
  });
}

export function useAnnouncementReadReceipts(id: string | null) {
  return useQuery({
    queryKey: [...ANNOUNCEMENTS_QUERY_KEY, "read-receipts", id],
    queryFn: () => (id ? getAnnouncementReadReceipts(id) : Promise.reject("No ID provided")),
    enabled: Boolean(id),
  });
}
