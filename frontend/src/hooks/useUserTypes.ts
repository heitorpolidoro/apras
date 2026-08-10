import { useQuery } from "@tanstack/react-query";
import apiClient from "../api/client";
import type { UserType } from "../types/auth";

export const useUserTypes = () => {
  return useQuery({
    queryKey: ["user-types"],
    queryFn: async () => {
      const response = await apiClient.get<UserType[]>("/user-types/");
      return response.data;
    },
  });
};
