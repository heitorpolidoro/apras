import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createDevice,
  getAccessEvents,
  getFacialTemplate,
  listDevices,
  regenerateDeviceKey,
  syncFacialTemplate,
  updateDeviceStatus,
} from "../../../api/accessControl";
import type {
  AccessDeviceCreate,
  AccessDeviceStatusUpdate,
} from "../../../types/accessControl";

export const useDevices = () => {
  return useQuery({
    queryKey: ["access-devices"],
    queryFn: () => listDevices(),
  });
};

export const useCreateDevice = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: AccessDeviceCreate) => createDevice(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["access-devices"] });
    },
  });
};

export const useUpdateDeviceStatus = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      deviceId,
      data,
    }: {
      deviceId: string;
      data: AccessDeviceStatusUpdate;
    }) => updateDeviceStatus(deviceId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["access-devices"] });
    },
  });
};

export const useRegenerateDeviceKey = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (deviceId: string) => regenerateDeviceKey(deviceId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["access-devices"] });
    },
  });
};

export const useFacialTemplate = (residentId?: string) => {
  return useQuery({
    queryKey: ["facial-template", residentId],
    queryFn: () =>
      residentId
        ? getFacialTemplate(residentId)
        : Promise.reject(new Error("No resident ID provided")),
    enabled: !!residentId,
  });
};

export const useSyncFacialTemplate = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (residentId: string) => syncFacialTemplate(residentId),
    onSuccess: (_, residentId) => {
      queryClient.invalidateQueries({
        queryKey: ["facial-template", residentId],
      });
    },
  });
};

export const useAccessEvents = (
  params?: {
    device_id?: string;
    resident_id?: string;
    skip?: number;
    limit?: number;
  },
  refetchInterval?: number,
) => {
  return useQuery({
    queryKey: ["access-events", params],
    queryFn: () => getAccessEvents(params),
    refetchInterval,
  });
};
