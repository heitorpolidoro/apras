import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  approveSpaceReservation,
  cancelSpaceReservation,
  createReservableSpace,
  createSpaceReservation,
  deactivateReservableSpace,
  getReservableSpaces,
  getSpaceReservations,
  rejectSpaceReservation,
  updateReservableSpace,
} from "../../../api/reservations";
import type {
  ReservableSpaceCreatePayload,
  ReservableSpaceUpdatePayload,
  SpaceReservationCreatePayload,
} from "../../../types/reservation";

export const RESERVABLE_SPACES_QUERY_KEY = ["reservable-spaces"];
export const SPACE_RESERVATIONS_QUERY_KEY = ["space-reservations"];

export function useReservableSpaces() {
  return useQuery({
    queryKey: RESERVABLE_SPACES_QUERY_KEY,
    queryFn: getReservableSpaces,
  });
}

export function useCreateReservableSpace() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: ReservableSpaceCreatePayload) => createReservableSpace(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: RESERVABLE_SPACES_QUERY_KEY });
    },
  });
}

export function useUpdateReservableSpace() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      data,
    }: {
      id: string;
      data: ReservableSpaceUpdatePayload;
    }) => updateReservableSpace(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: RESERVABLE_SPACES_QUERY_KEY });
    },
  });
}

export function useDeactivateReservableSpace() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deactivateReservableSpace(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: RESERVABLE_SPACES_QUERY_KEY });
    },
  });
}

export function useSpaceReservations(spaceId?: string, mine?: boolean) {
  return useQuery({
    queryKey: [...SPACE_RESERVATIONS_QUERY_KEY, spaceId, mine],
    queryFn: () => getSpaceReservations({ space_id: spaceId, mine }),
  });
}

export function useCreateSpaceReservation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: SpaceReservationCreatePayload) =>
      createSpaceReservation(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: SPACE_RESERVATIONS_QUERY_KEY });
    },
  });
}

export function useApproveReservation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => approveSpaceReservation(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: SPACE_RESERVATIONS_QUERY_KEY });
    },
  });
}

export function useRejectReservation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => rejectSpaceReservation(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: SPACE_RESERVATIONS_QUERY_KEY });
    },
  });
}

export function useCancelReservation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => cancelSpaceReservation(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: SPACE_RESERVATIONS_QUERY_KEY });
    },
  });
}
