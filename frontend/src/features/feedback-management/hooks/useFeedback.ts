import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createFeedback,
  getFeedbackById,
  getFeedbackList,
  respondToFeedback,
} from "../../../api/feedback";
import type {
  FeedbackCreatePayload,
  FeedbackFilterParams,
  FeedbackRespondPayload,
} from "../../../types/feedback";

export const FEEDBACK_QUERY_KEY = ["feedback"];

export function useFeedbackList(params?: FeedbackFilterParams) {
  return useQuery({
    queryKey: [...FEEDBACK_QUERY_KEY, params],
    queryFn: () => getFeedbackList(params),
  });
}

/**
 * Fetches a single feedback item via `GET /feedback/{id}`, distinct from
 * `useFeedbackList`. This is required so that opening an item in the
 * reporter's own history actually calls the detail endpoint, which is the
 * only place `response_seen_by_reporter` flips to `true` server-side.
 * Rendering `board_response` inline from the list payload would never
 * trigger that flip.
 */
export function useFeedbackDetail(id: string | null) {
  return useQuery({
    queryKey: [...FEEDBACK_QUERY_KEY, "detail", id],
    queryFn: () => (id ? getFeedbackById(id) : Promise.reject("No ID provided")),
    enabled: Boolean(id),
  });
}

export function useCreateFeedback() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: FeedbackCreatePayload) => createFeedback(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: FEEDBACK_QUERY_KEY });
    },
  });
}

export function useRespondToFeedback() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      data,
    }: {
      id: string;
      data: FeedbackRespondPayload;
    }) => respondToFeedback(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: FEEDBACK_QUERY_KEY });
      queryClient.invalidateQueries({
        queryKey: [...FEEDBACK_QUERY_KEY, "detail", variables.id],
      });
    },
  });
}
