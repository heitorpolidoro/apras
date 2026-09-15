import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  deleteTenantLogo,
  getTenantProfile,
  patchTenantProfile,
  putTenantLogo,
  type TenantProfile,
} from "../api/tenantProfile";

/**
 * The condominium profile (APRAS-61).
 *
 * **Cache-key discipline.** `["tenantProfile"]` deliberately does not start
 * with `"tenants"`, so `setActingTenant`'s `resetQueries` predicate
 * (`queryKey[0] !== "tenants"`, APRAS-38/39) **resets** it on a tenant
 * switch — which is correct: this is acting-tenant data, read through
 * `X-Tenant-Id` with no tenant id anywhere in the path. `["subscription"]` is
 * keyed the same way and for the same reason; the superuser hooks in
 * `usePlans.ts` key on `["tenants", id, …]` for the opposite one.
 */
export const TENANT_PROFILE_KEY = ["tenantProfile"] as const;

export const useTenantProfile = () =>
  useQuery({ queryKey: TENANT_PROFILE_KEY, queryFn: getTenantProfile });

/** The response body *is* the new state, so it is written straight in. */
const useProfileMutation = <TVariables>(
  mutationFn: (variables: TVariables) => Promise<TenantProfile>,
) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn,
    // The response body *is* the new profile, so it is written straight in
    // and **not** invalidated: an invalidation would issue a second `GET`
    // whose answer can only be the same row, and would make the screen flash
    // the previous logo while it is in flight. No optimistic update to roll
    // back either — nothing is written before the server answers.
    onSuccess: (data) => queryClient.setQueryData(TENANT_PROFILE_KEY, data),
  });
};

export const useRenameTenant = () =>
  useProfileMutation((name: string) => patchTenantProfile(name));

export const useSetTenantLogo = () =>
  useProfileMutation((logo: File) => putTenantLogo(logo));

export const useClearTenantLogo = () =>
  useProfileMutation(() => deleteTenantLogo());
