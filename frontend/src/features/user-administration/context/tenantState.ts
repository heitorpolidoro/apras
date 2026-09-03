/**
 * Module-level mirror of the acting tenant, plus its storage and the pure
 * pre-selection ladder (APRAS-38 §4.2).
 *
 * Two consumers cannot read React context and therefore read this module
 * instead: the Axios request interceptor (`api/client.ts`), which must attach
 * `X-Tenant-Id` synchronously on every request, and `AuthContext.fetchUser`,
 * which resolves the acting tenant from `/auth/me` *before* `setUser`. This
 * follows the `simulationState.ts` pattern verbatim, with one addition — a
 * subscription list, so `TenantContext` can expose the mirror through
 * `useSyncExternalStore` and the context value can *be* the mirror in every
 * commit rather than a `useState` copy that lags it by one commit.
 */
import type { TenantMembership } from "../../../types/auth";

const STORAGE_KEY = "actingTenantId";
const TOKEN_KEY = "accessToken";

/**
 * `undefined` means "never read yet" — the sentinel that makes the first
 * `getActingTenantId()` after a page reload restore the stored selection.
 * `null` is a real value: "no acting tenant".
 */
let mirror: string | null | undefined;

const listeners = new Set<() => void>();

/**
 * Storage precedence matches the one `api/client.ts` already uses for
 * `accessToken`: session first, then local.
 */
const readStored = (): string | null =>
  sessionStorage.getItem(STORAGE_KEY) ?? localStorage.getItem(STORAGE_KEY);

/**
 * The storage that currently holds the JWT — the selection must live exactly
 * as long as the token it was chosen under. With no token at all the choice is
 * ephemeral, so `sessionStorage` is the safe default.
 */
const storageForToken = (): Storage => {
  if (sessionStorage.getItem(TOKEN_KEY)) return sessionStorage;
  if (localStorage.getItem(TOKEN_KEY)) return localStorage;
  return sessionStorage;
};

const notify = (): void => {
  listeners.forEach((listener) => {
    listener();
  });
};

/**
 * The acting tenant id, or `null` when none is selected.
 *
 * A module-level constant with a cached primitive return value, both of which
 * `useSyncExternalStore` requires: an unstable identity re-subscribes on every
 * render, and a freshly allocated snapshot loops on snapshot inequality.
 */
export const getActingTenantId = (): string | null => {
  mirror ??= readStored();
  return mirror;
};

/**
 * Updates the mirror and the storage holding the token, then notifies
 * subscribers — in that order, so a listener calling `getActingTenantId()`
 * synchronously observes the new value.
 */
export const setActingTenantId = (id: string | null): void => {
  if (id === null) {
    clearActingTenantId();
    return;
  }
  mirror = id;
  const target = storageForToken();
  const other = target === sessionStorage ? localStorage : sessionStorage;
  target.setItem(STORAGE_KEY, id);
  other.removeItem(STORAGE_KEY);
  notify();
};

/** Clears the mirror and both storages. Called by `AuthContext.logout`. */
export const clearActingTenantId = (): void => {
  mirror = null;
  localStorage.removeItem(STORAGE_KEY);
  sessionStorage.removeItem(STORAGE_KEY);
  notify();
};

/**
 * Registers a listener notified on every mirror write; returns its
 * unsubscribe. The store half of the `useSyncExternalStore` in
 * `TenantContext`.
 */
export const subscribeActingTenantId = (listener: () => void): (() => void) => {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
};

/**
 * The pure pre-selection ladder (§2.2), exported for direct unit testing.
 *
 * 1. a stored id that is one of the caller's **active** memberships → keep it;
 * 2. a stored id when the caller is an `ADMINISTRATOR` → keep it (an
 *    administrator may legitimately act in a tenant they are not a member of;
 *    the backend validates it and `TenantContext` reconciles a stale one);
 * 3. otherwise the first active membership — `/auth/me` orders them by tenant
 *    name server-side, so "first" is deterministic;
 * 4. otherwise `null`: no header at all, and the zero-membership user keeps
 *    the backend's own default-tenant fallback.
 */
export const resolveActingTenantId = (
  memberships: TenantMembership[],
  isSuperuser: boolean | undefined,
  stored: string | null,
): string | null => {
  const active = memberships.filter((m) => m.is_active);
  if (stored !== null) {
    if (active.some((m) => m.tenant_id === stored)) return stored;
    // IAM F5 (APRAS-49 §10.4): the one consumer of `UserMeRead.is_superuser`.
    // It runs before an acting tenant exists, so it cannot ask
    // `/permissions/me`, and the flag is the exact successor of the
    // `role === ADMINISTRATOR` test it replaces.
    if (isSuperuser) return stored;
  }
  return active[0]?.tenant_id ?? null;
};
