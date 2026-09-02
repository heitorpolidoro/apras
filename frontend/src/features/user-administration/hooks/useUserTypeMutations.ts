import { useMutation, useQueryClient } from "@tanstack/react-query";
import apiClient from "../../../api/client";
import type { UserType } from "../../../types/auth";

/**
 * The four group writes and the one membership write (APRAS-48 §6).
 *
 * All five already exist on the backend; this slice adds no endpoint. **Clone**
 * is `POST /user-types/` with the source's bundle and an editable pre-filled
 * name, so `assert_can_grant` applies to a clone exactly as to a hand-built
 * group. **Membership** is `PATCH /users/{id}` with the recomputed
 * `user_type_ids` — the same call the user-side modal makes, so "os dois
 * sentidos" is one code path with two entry points.
 */
export interface GroupPayload {
  name: string;
  permissions: string[];
  allowed_menus: string[];
}

/**
 * The `allowed_menus` a bundle implies — **unioned with what is stored,
 * never replacing it** (§2.3).
 *
 * TRANSITIONAL (IAM F4 -> F5). `deps.assert_menu_access` still gates 12
 * handlers, and §7 deletes the only UI that could write this column. Sending
 * the derived list verbatim would make renaming a pre-existing group silently
 * revoke its backend menu access — the state of every operator-configured
 * group today, since IAM F1 seeds nothing. Additive-only makes revoking a menu
 * key impossible from this UI until F5 deletes the column, which is the safe
 * direction. Deletable outright when the column goes.
 */
export const deriveAllowedMenus = (
  permissions: readonly string[],
  stored: readonly string[] = [],
): string[] => {
  const derived = [
    ...(permissions.some((p) => p.startsWith("tasks:")) ? ["tasks"] : []),
    ...(permissions.some((p) => p.startsWith("categories:"))
      ? ["categories"]
      : []),
  ];
  return [...new Set([...stored, ...derived])].sort();
};

const useGroupInvalidation = () => {
  const queryClient = useQueryClient();
  return () => {
    queryClient.invalidateQueries({ queryKey: ["user-types"] });
    queryClient.invalidateQueries({ queryKey: ["users"] });
    // The author's own effective set can change with the very group they just
    // edited — an admin who adds `finance:read` to a group they belong to holds
    // it from that moment on. Without this the Navbar and every
    // `ProtectedRoute` keep deciding on the pre-save payload until something
    // else evicts it.
    queryClient.invalidateQueries({ queryKey: ["me", "permissions"] });
  };
};

export const useCreateUserType = () => {
  const invalidate = useGroupInvalidation();
  return useMutation({
    mutationFn: async (payload: GroupPayload) => {
      const response = await apiClient.post<UserType>("/user-types/", payload);
      return response.data;
    },
    onSuccess: invalidate,
  });
};

export const useUpdateUserType = () => {
  const invalidate = useGroupInvalidation();
  return useMutation({
    mutationFn: async ({
      groupId,
      payload,
    }: {
      groupId: string;
      payload: GroupPayload;
    }) => {
      const response = await apiClient.patch<UserType>(
        `/user-types/${groupId}`,
        payload,
      );
      return response.data;
    },
    onSuccess: invalidate,
  });
};

export const useDeleteUserType = () => {
  const invalidate = useGroupInvalidation();
  return useMutation({
    mutationFn: async (groupId: string) => {
      await apiClient.delete(`/user-types/${groupId}`);
    },
    onSuccess: invalidate,
  });
};

/**
 * The one membership mutation, used from **both** directions: the group
 * screen's members panel and the user screen's edit modal.
 */
export const useSetUserGroups = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      userId,
      userTypeIds,
      fullName,
    }: {
      userId: string;
      userTypeIds: string[];
      /** Only the user-side modal sends it; the group panel never does. */
      fullName?: string;
    }) => {
      const response = await apiClient.patch(`/users/${userId}`, {
        user_type_ids: userTypeIds,
        ...(fullName === undefined ? {} : { full_name: fullName }),
      });
      return response.data;
    },
    // Every `["users", …]` filter, and nothing else.
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["users"] }),
  });
};
