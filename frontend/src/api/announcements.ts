import apiClient from "./client";
import type {
  Announcement,
  AnnouncementComment,
  AnnouncementCreatePayload,
  AnnouncementDetail,
  AnnouncementMedia,
  AnnouncementReadReceipt,
  AnnouncementUpdatePayload,
  CommentCreatePayload,
  MarkReadResponse,
  PaginatedAnnouncementsResponse,
} from "../types/announcement";

export const getAnnouncements = async (params?: {
  skip?: number;
  limit?: number;
}): Promise<PaginatedAnnouncementsResponse> => {
  const response = await apiClient.get<PaginatedAnnouncementsResponse>("/announcements", {
    params,
  });
  return response.data;
};

export const getAnnouncementById = async (id: string): Promise<AnnouncementDetail> => {
  const response = await apiClient.get<AnnouncementDetail>(`/announcements/${id}`);
  return response.data;
};

export const createAnnouncement = async (
  data: AnnouncementCreatePayload
): Promise<Announcement> => {
  const response = await apiClient.post<Announcement>("/announcements", data);
  return response.data;
};

export const updateAnnouncement = async (
  id: string,
  data: AnnouncementUpdatePayload
): Promise<Announcement> => {
  const response = await apiClient.put<Announcement>(`/announcements/${id}`, data);
  return response.data;
};

export const deleteAnnouncement = async (id: string): Promise<void> => {
  await apiClient.delete(`/announcements/${id}`);
};

export const uploadAnnouncementMedia = async (
  id: string,
  file: File
): Promise<AnnouncementMedia> => {
  const formData = new FormData();
  formData.append("file", file);
  const response = await apiClient.post<AnnouncementMedia>(
    `/announcements/${id}/media`,
    formData,
    { headers: { "Content-Type": "multipart/form-data" } }
  );
  return response.data;
};

export const deleteAnnouncementMedia = async (id: string, mediaId: string): Promise<void> => {
  await apiClient.delete(`/announcements/${id}/media/${mediaId}`);
};

export const getAnnouncementComments = async (id: string): Promise<AnnouncementComment[]> => {
  const response = await apiClient.get<AnnouncementComment[]>(`/announcements/${id}/comments`);
  return response.data;
};

export const addAnnouncementComment = async (
  id: string,
  data: CommentCreatePayload
): Promise<AnnouncementComment> => {
  const response = await apiClient.post<AnnouncementComment>(
    `/announcements/${id}/comments`,
    data
  );
  return response.data;
};

export const deleteAnnouncementComment = async (commentId: string): Promise<void> => {
  await apiClient.delete(`/announcements/comments/${commentId}`);
};

export const markAnnouncementRead = async (id: string): Promise<MarkReadResponse> => {
  const response = await apiClient.post<MarkReadResponse>(`/announcements/${id}/read`);
  return response.data;
};

export const getAnnouncementReadReceipts = async (
  id: string
): Promise<AnnouncementReadReceipt[]> => {
  const response = await apiClient.get<AnnouncementReadReceipt[]>(
    `/announcements/${id}/read-receipts`
  );
  return response.data;
};
