import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  deleteTenantLogo,
  getTenantProfile,
  patchTenantProfile,
  putTenantLogo,
  type TenantProfile,
  type TenantProfileUpdate,
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

/**
 * `enabled` exists for one caller: `TenantBrandTheme` (APRAS-68).
 *
 * The injector is mounted for the whole app, including the login screen,
 * where there is no token and this `GET` could only 401. Passing
 * `{ enabled: isAuthenticated }` keeps it from firing there. Every other
 * caller omits it and gets today's behaviour, because `enabled` defaults to
 * `true`.
 */
export const useTenantProfile = ({ enabled = true }: { enabled?: boolean } = {}) =>
  useQuery({ queryKey: TENANT_PROFILE_KEY, queryFn: getTenantProfile, enabled });

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

/**
 * The one write behind the name **and** the slug (APRAS-66).
 *
 * One mutation rather than two, because it is one `PATCH`: the server treats
 * an absent field as "leave it alone", which is exactly how a rename is kept
 * from touching the slug (D-C.2). The caller decides what to include.
 */
export const useUpdateTenantProfile = () =>
  useProfileMutation((update: TenantProfileUpdate) =>
    patchTenantProfile(update),
  );

export const useSetTenantLogo = () =>
  useProfileMutation((logo: File) => putTenantLogo(logo));

export const useClearTenantLogo = () =>
  useProfileMutation(() => deleteTenantLogo());
