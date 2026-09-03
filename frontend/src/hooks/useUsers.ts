import { useQuery } from "@tanstack/react-query";
import apiClient from "../api/client";
import type { User } from "../types/auth";

export const useUsers = () => {
  return useQuery({
    queryKey: ["users", "ALL"],
    queryFn: async () => {
      const response = await apiClient.get<User[]>("/users/");
      return response.data;
    },
  });
};

export const useAssignableUsers = () => {
  const query = useUsers();
  return {
    ...query,
    data: query.data?.filter(
      (u) =>
        u.roles &&
        u.roles.length > 0,
    ),
  };
};
