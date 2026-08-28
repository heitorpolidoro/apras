import apiClient from "./client";
import type {
  ReservableSpaceCreatePayload,
  ReservableSpaceRead,
  ReservableSpaceUpdatePayload,
  SpaceReservationCreatePayload,
  SpaceReservationListParams,
  SpaceReservationRead,
} from "../types/reservation";

export const getReservableSpaces = async (): Promise<ReservableSpaceRead[]> => {
  const response = await apiClient.get<ReservableSpaceRead[]>("/reservable-spaces/");
  return response.data;
};

export const createReservableSpace = async (
  data: ReservableSpaceCreatePayload
): Promise<ReservableSpaceRead> => {
  const response = await apiClient.post<ReservableSpaceRead>(
    "/reservable-spaces/",
    data
  );
  return response.data;
};

export const updateReservableSpace = async (
  id: string,
  data: ReservableSpaceUpdatePayload
): Promise<ReservableSpaceRead> => {
  const response = await apiClient.patch<ReservableSpaceRead>(
    `/reservable-spaces/${id}`,
    data
  );
  return response.data;
};

export const deactivateReservableSpace = async (id: string): Promise<void> => {
  await apiClient.delete(`/reservable-spaces/${id}`);
};

export const getSpaceReservations = async (
  params?: SpaceReservationListParams
): Promise<SpaceReservationRead[]> => {
  const response = await apiClient.get<SpaceReservationRead[]>(
    "/space-reservations/",
    { params }
  );
  return response.data;
};

export const createSpaceReservation = async (
  data: SpaceReservationCreatePayload
): Promise<SpaceReservationRead> => {
  const response = await apiClient.post<SpaceReservationRead>(
    "/space-reservations/",
    data
  );
  return response.data;
};

export const approveSpaceReservation = async (
  id: string
): Promise<SpaceReservationRead> => {
  const response = await apiClient.post<SpaceReservationRead>(
    `/space-reservations/${id}/approve`
  );
  return response.data;
};

export const rejectSpaceReservation = async (
  id: string
): Promise<SpaceReservationRead> => {
  const response = await apiClient.post<SpaceReservationRead>(
    `/space-reservations/${id}/reject`
  );
  return response.data;
};

export const cancelSpaceReservation = async (
  id: string
): Promise<SpaceReservationRead> => {
  const response = await apiClient.post<SpaceReservationRead>(
    `/space-reservations/${id}/cancel`
  );
  return response.data;
};
