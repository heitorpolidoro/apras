import { useMutation, useQueryClient } from "@tanstack/react-query";
import apiClient from "../../../api/client";
import type { Role } from "../../../types/auth";

/**
 * The four role writes and the one membership write (APRAS-48 §6).
 *
 * All five already exist on the backend; this slice adds no endpoint. **Clone**
 * is `POST /roles/` with the source's bundle and an editable pre-filled
 * name, so `assert_can_grant` applies to a clone exactly as to a hand-built
 * role. **Membership** is `PATCH /users/{id}` with the recomputed
 * `role_ids` — the same call the user-side modal makes, so "os dois
 * sentidos" is one code path with two entry points.
 */
export interface RolePayload {
  name: string;
  permissions: string[];
  /** IAM F5 (APRAS-49 §8.1). Optional: an editor that does not opinionate
   *  about landing simply omits it. */
  landing_path?: string | null;
}

const useRoleInvalidation = () => {
  const queryClient = useQueryClient();
  return () => {
    queryClient.invalidateQueries({ queryKey: ["roles"] });
    queryClient.invalidateQueries({ queryKey: ["users"] });
    // The author's own effective set can change with the very role they just
    // edited — an admin who adds `finance:read` to a role they belong to holds
    // it from that moment on. Without this the Navbar and every
    // `ProtectedRoute` keep deciding on the pre-save payload until something
    // else evicts it.
    queryClient.invalidateQueries({ queryKey: ["me", "permissions"] });
  };
};

export const useCreateRole = () => {
  const invalidate = useRoleInvalidation();
  return useMutation({
    mutationFn: async (payload: RolePayload) => {
      const response = await apiClient.post<Role>("/roles/", payload);
      return response.data;
    },
    onSuccess: invalidate,
  });
};

export const useUpdateRole = () => {
  const invalidate = useRoleInvalidation();
  return useMutation({
    mutationFn: async ({
      roleId,
      payload,
    }: {
      roleId: string;
      payload: RolePayload;
    }) => {
      const response = await apiClient.patch<Role>(
        `/roles/${roleId}`,
        payload,
      );
      return response.data;
    },
    onSuccess: invalidate,
  });
};

export const useDeleteRole = () => {
  const invalidate = useRoleInvalidation();
  return useMutation({
    mutationFn: async (roleId: string) => {
      await apiClient.delete(`/roles/${roleId}`);
    },
    onSuccess: invalidate,
  });
};

/**
 * The one membership mutation, used from **both** directions: the role
 * screen's members panel and the user screen's edit modal.
 */
export const useSetUserRoles = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      userId,
      roleIds,
      fullName,
    }: {
      userId: string;
      roleIds: string[];
      /** Only the user-side modal sends it; the role panel never does. */
      fullName?: string;
    }) => {
      const response = await apiClient.patch(`/users/${userId}`, {
        role_ids: roleIds,
        ...(fullName === undefined ? {} : { full_name: fullName }),
      });
      return response.data;
    },
    // Every `["users", …]` filter, and nothing else.
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["users"] }),
  });
};
