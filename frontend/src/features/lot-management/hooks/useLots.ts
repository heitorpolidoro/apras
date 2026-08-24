import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getLots,
  getLotDetail,
  createLot,
  updateLot,
  deleteLot,
  linkUserLot,
  unlinkUserLot,
} from "../../../api/lots";
import type {
  LotCreate,
  LotStatus,
  LotUpdate,
  UserLotLinkCreate,
} from "../../../types/lot";

export const useLots = (params?: {
  block?: string;
  status?: LotStatus;
  skip?: number;
  limit?: number;
}) => {
  return useQuery({
    queryKey: ["lots", params],
    queryFn: () => getLots(params),
  });
};

export const useLotDetail = (id?: string) => {
  return useQuery({
    queryKey: ["lot-detail", id],
    queryFn: () => (id ? getLotDetail(id) : Promise.reject("No lot ID provided")),
    enabled: !!id,
  });
};

export const useCreateLot = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: LotCreate) => createLot(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["lots"] });
    },
  });
};

export const useUpdateLot = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: LotUpdate }) =>
      updateLot(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ["lots"] });
      queryClient.invalidateQueries({ queryKey: ["lot-detail", variables.id] });
    },
  });
};

export const useDeleteLot = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteLot(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["lots"] });
    },
  });
};

export const useLinkUserLot = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UserLotLinkCreate }) =>
      linkUserLot(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ["lots"] });
      queryClient.invalidateQueries({ queryKey: ["lot-detail", variables.id] });
    },
  });
};

export const useUnlinkUserLot = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, userId }: { id: string; userId: string }) =>
      unlinkUserLot(id, userId),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ["lots"] });
      queryClient.invalidateQueries({ queryKey: ["lot-detail", variables.id] });
    },
  });
};
