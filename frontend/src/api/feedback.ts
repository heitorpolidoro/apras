import apiClient from "./client";
import type {
  Feedback,
  FeedbackCreatePayload,
  FeedbackFilterParams,
  FeedbackRespondPayload,
  PaginatedFeedbackResponse,
} from "../types/feedback";

export const getFeedbackList = async (
  params?: FeedbackFilterParams
): Promise<PaginatedFeedbackResponse> => {
  const response = await apiClient.get<PaginatedFeedbackResponse>("/feedback", {
    params,
  });
  return response.data;
};

export const createFeedback = async (
  data: FeedbackCreatePayload
): Promise<Feedback> => {
  const response = await apiClient.post<Feedback>("/feedback", data);
  return response.data;
};

export const getFeedbackById = async (id: string): Promise<Feedback> => {
  const response = await apiClient.get<Feedback>(`/feedback/${id}`);
  return response.data;
};

export const respondToFeedback = async (
  id: string,
  data: FeedbackRespondPayload
): Promise<Feedback> => {
  const response = await apiClient.put<Feedback>(`/feedback/${id}/respond`, data);
  return response.data;
};
