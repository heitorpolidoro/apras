import { describe, it, expect, beforeEach, vi } from "vitest";
import {
  getActingTenantId,
  setActingTenantId,
  clearActingTenantId,
  subscribeActingTenantId,
  resolveActingTenantId,
} from "../context/tenantState";
import { UserRole, type TenantMembership } from "../../../types/auth";

const TENANT_A = "11111111-1111-1111-1111-111111111111";
const TENANT_B = "22222222-2222-2222-2222-222222222222";
const TENANT_C = "33333333-3333-3333-3333-333333333333";

const membership = (
  overrides: Partial<TenantMembership> & { tenant_id: string },
): TenantMembership => ({
  name: "Tenant",
  is_active: true,
  is_tenant_admin: false,
  ...overrides,
});

describe("tenantState", () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
    clearActingTenantId();
  });

  describe("persistence", () => {
    it("persists the selection in localStorage when the token is in localStorage", () => {
      localStorage.setItem("accessToken", "remembered-token");

      setActingTenantId(TENANT_A);

      expect(localStorage.getItem("actingTenantId")).toBe(TENANT_A);
      expect(sessionStorage.getItem("actingTenantId")).toBeNull();
      expect(getActingTenantId()).toBe(TENANT_A);
    });

    it("persists the selection in sessionStorage when the token is in sessionStorage", () => {
      sessionStorage.setItem("accessToken", "session-token");

      setActingTenantId(TENANT_B);

      expect(sessionStorage.getItem("actingTenantId")).toBe(TENANT_B);
      expect(localStorage.getItem("actingTenantId")).toBeNull();
      expect(getActingTenantId()).toBe(TENANT_B);
    });

    it("restores the selection from storage on a fresh module read (page reload)", async () => {
      localStorage.setItem("actingTenantId", TENANT_C);

      // A page reload is a brand-new module instance whose mirror has never
      // been written: it must read storage lazily so the very first request
      // already carries the right X-Tenant-Id.
      vi.resetModules();
      const fresh = await import("../context/tenantState");

      expect(fresh.getActingTenantId()).toBe(TENANT_C);
      vi.resetModules();
    });

    it("clearActingTenantId empties the mirror and both storages", () => {
      localStorage.setItem("accessToken", "remembered-token");
      setActingTenantId(TENANT_A);
      sessionStorage.setItem("actingTenantId", TENANT_B);

      clearActingTenantId();

      expect(getActingTenantId()).toBeNull();
      expect(localStorage.getItem("actingTenantId")).toBeNull();
      expect(sessionStorage.getItem("actingTenantId")).toBeNull();
    });

    it("notifies subscribers after the mirror and storage are already updated", () => {
      const seen: (string | null)[] = [];
      const unsubscribe = subscribeActingTenantId(() => {
        seen.push(getActingTenantId());
      });

      setActingTenantId(TENANT_A);
      clearActingTenantId();
      unsubscribe();
      setActingTenantId(TENANT_B);

      expect(seen).toEqual([TENANT_A, null]);
    });

    it("exposes stable module-level identities for useSyncExternalStore", async () => {
      const first = await import("../context/tenantState");
      const second = await import("../context/tenantState");

      expect(first.subscribeActingTenantId).toBe(second.subscribeActingTenantId);
      expect(first.getActingTenantId).toBe(second.getActingTenantId);
      // The snapshot must be the cached primitive itself, never a fresh
      // wrapper, or React loops on snapshot inequality.
      expect(getActingTenantId()).toBe(getActingTenantId());
    });
  });

  describe("resolveActingTenantId", () => {
    it("keeps a stored id that is an active membership", () => {
      const memberships = [
        membership({ tenant_id: TENANT_A }),
        membership({ tenant_id: TENANT_B }),
      ];

      expect(
        resolveActingTenantId(memberships, UserRole.RESIDENT, TENANT_B),
      ).toBe(TENANT_B);
    });

    it("falls back to the first active membership for a multi-membership user", () => {
      const memberships = [
        membership({ tenant_id: TENANT_A }),
        membership({ tenant_id: TENANT_B }),
      ];

      expect(resolveActingTenantId(memberships, UserRole.RESIDENT, null)).toBe(
        TENANT_A,
      );
    });

    it("skips an inactive membership and a stored id pointing at one", () => {
      const memberships = [
        membership({ tenant_id: TENANT_A, is_active: false }),
        membership({ tenant_id: TENANT_B }),
      ];

      expect(
        resolveActingTenantId(memberships, UserRole.RESIDENT, TENANT_A),
      ).toBe(TENANT_B);
      expect(resolveActingTenantId(memberships, UserRole.RESIDENT, null)).toBe(
        TENANT_B,
      );
    });

    it("keeps a stored non-membership id for an ADMINISTRATOR", () => {
      // An administrator may legitimately act in a tenant they are not a
      // member of; the backend validates the header and TenantContext
      // reconciles it if it turns out to be stale.
      const memberships = [membership({ tenant_id: TENANT_A })];

      expect(
        resolveActingTenantId(memberships, UserRole.ADMINISTRATOR, TENANT_C),
      ).toBe(TENANT_C);
      expect(
        resolveActingTenantId(memberships, UserRole.RESIDENT, TENANT_C),
      ).toBe(TENANT_A);
    });

    it("returns null for a user with no memberships", () => {
      expect(resolveActingTenantId([], UserRole.RESIDENT, null)).toBeNull();
      expect(resolveActingTenantId([], UserRole.RESIDENT, TENANT_A)).toBeNull();
    });
  });
});
