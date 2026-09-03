import { createContext, useContext } from "react";
import type { Tenant } from "../../../types/auth";
import { useAuth } from "./AuthContext";

/**
 * The tenant context object and its consumer hooks.
 *
 * Split from `TenantContext.tsx` so that file exports only the
 * `TenantProvider` component: `react-refresh/only-export-components` flags a
 * module that mixes a component with plain function exports, and this task is
 * held to adding no new lint problem. It also matches the layout the sibling
 * hooks already use (`useEffectiveIdentity.ts`).
 */
export interface TenantContextValue {
  /** Dropdown options: the active tenants the caller may act in. */
  tenants: Tenant[];
  /** The acting tenant id — the exact value the Axios interceptor will send. */
  actingTenantId: string | null;
  /** The acting tenant's option row, when it is one of the options. */
  actingTenant: Tenant | null;
  /** Whether the caller holds `is_tenant_admin` **in the acting tenant**. */
  isActingTenantAdmin: boolean;
  /** Whether the option list is still being fetched. */
  isLoading: boolean;
  /** Switches tenant: writes the mirror, then evicts every scoped payload. */
  setActingTenant: (id: string) => void;
}

/**
 * The value `useTenant()` returns with no provider mounted. Fail-closed by
 * construction: no provider ⇒ no options, no acting tenant and no capability.
 */
const ZERO_VALUE: TenantContextValue = {
  tenants: [],
  actingTenantId: null,
  actingTenant: null,
  isActingTenantAdmin: false,
  isLoading: false,
  setActingTenant: () => {
    /* no provider: nothing to switch */
  },
};

export const TenantContext = createContext<TenantContextValue | undefined>(
  undefined,
);

/**
 * The acting tenant, its options and the tenant_admin capability.
 *
 * Unlike `useAuth`, this **does not throw** without a provider: it returns a
 * fail-closed zero value. Two reasons. It is safe — no provider means no
 * capability, so no admin UI is offered. And it keeps every component that is
 * rendered bare in a `MemoryRouter` (as many existing tests do) working
 * without a `TenantProvider` wrapper.
 */
export const useTenant = (): TenantContextValue =>
  useContext(TenantContext) ?? ZERO_VALUE;

/**
 * True once the acting tenant for the current identity is decided.
 *
 * `AuthContext` resolves it from `/auth/me` *before* `setUser`, so
 * `!isLoading` means either "boot finished, tenant decided" or "no token,
 * nothing to decide". Gates every tenant-scoped query that can subscribe
 * above an auth guard — today exactly one, `useRoles`, which
 * `Navbar` and `ProtectedRoute` both call above their own guards.
 */
export const useActingTenantReady = (): boolean => !useAuth().isLoading;
