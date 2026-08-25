import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createResident,
  deleteResident,
  getLotResidents,
  getResidentDetail,
  linkResidentUser,
  unlinkResidentUser,
  updateResident,
} from "../../../api/residents";
import type {
  ResidentCreatePayload,
  ResidentUpdatePayload,
} from "../../../types/resident";

export const useLotResidents = (
  lotId?: string,
  skip?: number,
  limit?: number
) => {
  return useQuery({
    queryKey: ["lot-residents", lotId, skip, limit],
    queryFn: () =>
      lotId
        ? getLotResidents(lotId, skip, limit)
        : Promise.reject("No lot ID provided"),
    enabled: !!lotId,
  });
};

export const useResidentDetail = (residentId?: string) => {
  return useQuery({
    queryKey: ["resident-detail", residentId],
    queryFn: () =>
      residentId
        ? getResidentDetail(residentId)
        : Promise.reject("No resident ID provided"),
    enabled: !!residentId,
  });
};

export const useCreateResident = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      lotId,
      data,
    }: {
      lotId: string;
      data: ResidentCreatePayload;
    }) => createResident(lotId, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: ["lot-residents", variables.lotId],
      });
      queryClient.invalidateQueries({
        queryKey: ["lot-detail", variables.lotId],
      });
    },
  });
};

export const useUpdateResident = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      residentId,
      lotId,
      data,
    }: {
      residentId: string;
      lotId: string;
      data: ResidentUpdatePayload;
    }) => updateResident(residentId, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: ["lot-residents", variables.lotId],
      });
      queryClient.invalidateQueries({
        queryKey: ["resident-detail", variables.residentId],
      });
    },
  });
};

export const useDeactivateResident = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      residentId,
      lotId,
    }: {
      residentId: string;
      lotId: string;
    }) => deleteResident(residentId),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: ["lot-residents", variables.lotId],
      });
      queryClient.invalidateQueries({
        queryKey: ["lot-detail", variables.lotId],
      });
    },
  });
};

export const useLinkResidentUser = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      residentId,
      userId,
      lotId,
    }: {
      residentId: string;
      userId: string;
      lotId: string;
    }) => linkResidentUser(residentId, userId),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: ["lot-residents", variables.lotId],
      });
      queryClient.invalidateQueries({
        queryKey: ["resident-detail", variables.residentId],
      });
    },
  });
};

export const useUnlinkResidentUser = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      residentId,
      lotId,
    }: {
      residentId: string;
      lotId: string;
    }) => unlinkResidentUser(residentId),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: ["lot-residents", variables.lotId],
      });
      queryClient.invalidateQueries({
        queryKey: ["resident-detail", variables.residentId],
      });
    },
  });
};
