import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  addTimelineNote,
  createOccurrence,
  getOccurrenceById,
  getOccurrences,
  updateOccurrenceStatus,
} from "../../../api/occurrences";
import type {
  OccurrenceCreatePayload,
  OccurrenceFilterParams,
  OccurrenceStatusUpdatePayload,
  TimelineNoteCreatePayload,
} from "../../../types/occurrence";

export const OCCURRENCES_QUERY_KEY = ["occurrences"];

export function useOccurrences(params?: OccurrenceFilterParams) {
  return useQuery({
    queryKey: [...OCCURRENCES_QUERY_KEY, params],
    queryFn: () => getOccurrences(params),
  });
}

export function useOccurrenceDetail(id: string | null) {
  return useQuery({
    queryKey: [...OCCURRENCES_QUERY_KEY, "detail", id],
    queryFn: () => (id ? getOccurrenceById(id) : Promise.reject("No ID provided")),
    enabled: Boolean(id),
  });
}

export function useCreateOccurrence() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: OccurrenceCreatePayload) => createOccurrence(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: OCCURRENCES_QUERY_KEY });
    },
  });
}

export function useUpdateOccurrenceStatus() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      data,
    }: {
      id: string;
      data: OccurrenceStatusUpdatePayload;
    }) => updateOccurrenceStatus(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: OCCURRENCES_QUERY_KEY });
      queryClient.invalidateQueries({
        queryKey: [...OCCURRENCES_QUERY_KEY, "detail", variables.id],
      });
    },
  });
}

export function useAddTimelineNote() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      data,
    }: {
      id: string;
      data: TimelineNoteCreatePayload;
    }) => addTimelineNote(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: OCCURRENCES_QUERY_KEY });
      queryClient.invalidateQueries({
        queryKey: [...OCCURRENCES_QUERY_KEY, "detail", variables.id],
      });
    },
  });
}
