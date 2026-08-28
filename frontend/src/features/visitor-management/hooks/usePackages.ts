import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createPackage,
  getPackageQueue,
  getPackagesForLot,
  markPackagePickedUp,
} from "../../../api/packages";
import type { PackageCreate, PackagePickup, PackageStatus } from "../../../types/package";

export const usePackageQueue = (skip?: number, limit?: number) => {
  return useQuery({
    queryKey: ["package-queue", skip, limit],
    queryFn: () => getPackageQueue(skip, limit),
  });
};

export const usePackagesForLot = (
  lotId?: string,
  status?: PackageStatus,
  skip?: number,
  limit?: number
) => {
  return useQuery({
    queryKey: ["packages", lotId, status, skip, limit],
    queryFn: () =>
      lotId ? getPackagesForLot(lotId, status, skip, limit) : Promise.reject("No lot ID provided"),
    enabled: !!lotId,
  });
};

export const useCreatePackage = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: PackageCreate) => createPackage(data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ["package-queue"] });
      queryClient.invalidateQueries({ queryKey: ["packages", variables.lot_id] });
    },
  });
};

export const useMarkPackagePickedUp = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: PackagePickup }) =>
      markPackagePickedUp(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["package-queue"] });
      queryClient.invalidateQueries({ queryKey: ["packages"] });
    },
  });
};
