import apiClient from "./client";
import type {
  Occurrence,
  OccurrenceCreatePayload,
  OccurrenceDetail,
  OccurrenceFilterParams,
  OccurrenceStatusUpdatePayload,
  OccurrenceTimeline,
  PaginatedOccurrencesResponse,
  TimelineNoteCreatePayload,
} from "../types/occurrence";

export const getOccurrences = async (
  params?: OccurrenceFilterParams
): Promise<PaginatedOccurrencesResponse> => {
  const response = await apiClient.get<PaginatedOccurrencesResponse>("/occurrences", {
    params,
  });
  return response.data;
};

export const createOccurrence = async (
  data: OccurrenceCreatePayload
): Promise<Occurrence> => {
  const response = await apiClient.post<Occurrence>("/occurrences", data);
  return response.data;
};

export const getOccurrenceById = async (id: string): Promise<OccurrenceDetail> => {
  const response = await apiClient.get<OccurrenceDetail>(`/occurrences/${id}`);
  return response.data;
};

export const updateOccurrenceStatus = async (
  id: string,
  data: OccurrenceStatusUpdatePayload
): Promise<Occurrence> => {
  const response = await apiClient.put<Occurrence>(`/occurrences/${id}/status`, data);
  return response.data;
};

export const addTimelineNote = async (
  id: string,
  data: TimelineNoteCreatePayload
): Promise<OccurrenceTimeline> => {
  const response = await apiClient.post<OccurrenceTimeline>(
    `/occurrences/${id}/timeline`,
    data
  );
  return response.data;
};
