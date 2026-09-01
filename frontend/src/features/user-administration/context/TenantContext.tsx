/**
 * The tenant provider (APRAS-38 §4.5). The context object and its consumer
 * hooks live in `useTenant.ts`, so this module exports only a component.
 */
import React, {
  useCallback,
  useEffect,
  useMemo,
  useSyncExternalStore,
} from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import apiClient from "../../../api/client";
import type { Tenant } from "../../../types/auth";
import { useAuth } from "./AuthContext";
import { TenantContext, type TenantContextValue } from "./useTenant";
import {
  getActingTenantId,
  setActingTenantId,
  subscribeActingTenantId,
} from "./tenantState";

export const TenantProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const { user, isAuthenticated } = useAuth();
  const queryClient = useQueryClient();

  /**
   * The acting tenant is **not** React state and is **not** synchronised by an
   * effect: it is read straight off the `tenantState` mirror. React re-reads
   * `getSnapshot` during every render of this provider, so the context value
   * *is* the mirror in every commit — including the commit in which
   * `AuthContext` sets `user` and clears `isLoading`, because `fetchUser`
   * writes the mirror before `setUser`. That is what stops the capability gate
   * of `ProtectedRoute` from ever judging a stale `null` and redirecting a
   * tenant_admin off `/admin/users` on a load with no stored selection. A
   * `useState` + `useEffect(…, [user])` re-sync has exactly that one-commit
   * lag. The `subscribe` arm covers the writes that do not originate from a
   * React render: the switcher gesture and `clearActingTenantId()` in
   * `logout`.
   */
  const actingTenantId = useSyncExternalStore(
    subscribeActingTenantId,
    getActingTenantId,
    getActingTenantId,
  );

  const { data, isLoading } = useQuery({
    queryKey: ["tenants"],
    // No trailing slash: the route is mounted at "" and a slash costs a 307.
    // `.data` is unwrapped here so the cache holds the array, not the
    // AxiosResponse envelope.
    queryFn: async () => (await apiClient.get<Tenant[]>("/tenants")).data,
    enabled: isAuthenticated,
  });

  /**
   * `_resolve_from_header` answers 403 "Tenant is inactive" for everyone
   * including administrators, so an inactive tenant is never selectable.
   */
  const tenants = useMemo(
    () => (data ?? []).filter((tenant) => tenant.is_active),
    [data],
  );

  const setActingTenant = useCallback(
    (id: string) => {
      // 1. Mirror + storage first, so any refetch triggered below already
      //    carries the new header, and every `useTenant()` consumer re-renders
      //    off the same single source of truth.
      setActingTenantId(id);
      // 2. Evict — not invalidate — every cached tenant-scoped payload, so no
      //    row of the previous tenant is readable at any point after the
      //    switch. Invalidation would leave the stale rows readable while the
      //    refetch is in flight.
      //
      //    `["tenants"]` is deliberately kept: it is a global-route payload
      //    unaffected by the switch, and a bare `clear()` would empty the
      //    switcher's own option list mid-gesture, dropping it below the
      //    2-option render threshold and resetting its value.
      //
      //    Two calls, because they cover different halves of the cache:
      //    `resetQueries` returns the *observed* queries to their dataless
      //    initial state and refetches them under the new header (a bare
      //    `removeQueries` on an observed query leaves its observer holding
      //    the removed entry and never refetching), while `removeQueries`
      //    drops the *unobserved* entries outright, so a component mounting
      //    later cannot read a previous tenant's payload from cache.
      const scopedOnly = (query: { queryKey: readonly unknown[] }) =>
        query.queryKey[0] !== "tenants";
      void queryClient.resetQueries({ predicate: scopedOnly });
      queryClient.removeQueries({ predicate: scopedOnly, type: "inactive" });
    },
    [queryClient],
  );

  /**
   * Reconciliation. The `null` arm promotes a zero-membership ADMINISTRATOR
   * (offered every tenant, a member of none) out of the "no header at all"
   * rung of the ladder; the mismatch arm recovers from a stored id pointing at
   * a tenant that was deactivated or whose membership was revoked. A plain
   * member with zero memberships has an empty option list, so neither arm
   * fires and the backend's own fallback keeps serving them. This is the only
   * place a selection changes without a user gesture, and it can only run
   * after `/tenants` has answered — i.e. after `/auth/me` — so it never races
   * the `useActingTenantReady` gate.
   */
  useEffect(() => {
    if (tenants.length === 0) return;
    const isKnown = tenants.some((tenant) => tenant.id === actingTenantId);
    if (!isKnown) {
      setActingTenant(tenants[0].id);
    }
  }, [tenants, actingTenantId, setActingTenant]);

  const value = useMemo<TenantContextValue>(
    () => ({
      tenants,
      actingTenantId,
      actingTenant:
        tenants.find((tenant) => tenant.id === actingTenantId) ?? null,
      // Derived from /auth/me, so it is per membership and re-evaluates on
      // every switch for free.
      isActingTenantAdmin:
        user?.tenants?.some(
          (membership) =>
            membership.tenant_id === actingTenantId &&
            membership.is_tenant_admin,
        ) ?? false,
      isLoading,
      setActingTenant,
    }),
    [tenants, actingTenantId, user, isLoading, setActingTenant],
  );

  return (
    <TenantContext.Provider value={value}>{children}</TenantContext.Provider>
  );
};
