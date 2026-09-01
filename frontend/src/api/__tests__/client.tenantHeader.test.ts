import { describe, it, expect, beforeEach } from "vitest";
import apiClient from "../client";
import {
  setActingTenantId,
  clearActingTenantId,
} from "../../features/user-administration/context/tenantState";

/**
 * The interceptor is exercised directly, exactly as `client.test.ts` already
 * does: it is the one place that turns the acting-tenant mirror into the
 * `X-Tenant-Id` header the APRAS-42 resolver reads.
 */
const requestInterceptor = () =>
  (
    apiClient.interceptors.request as unknown as {
      handlers: {
        fulfilled: (...args: unknown[]) => unknown;
      }[];
    }
  ).handlers[0];

const runInterceptor = async () =>
  (await requestInterceptor().fulfilled({ headers: {} })) as {
    headers: Record<string, string | undefined>;
  };

const TENANT_A = "11111111-1111-1111-1111-111111111111";

describe("apiClient X-Tenant-Id header", () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
    clearActingTenantId();
  });

  it("attaches X-Tenant-Id from the acting-tenant mirror", async () => {
    sessionStorage.setItem("accessToken", "token");
    setActingTenantId(TENANT_A);

    const config = await runInterceptor();

    expect(config.headers["X-Tenant-Id"]).toBe(TENANT_A);
  });

  it("omits X-Tenant-Id when no acting tenant is set", async () => {
    sessionStorage.setItem("accessToken", "token");

    const config = await runInterceptor();

    expect(config.headers["X-Tenant-Id"]).toBeUndefined();
  });

  it("keeps the Authorization header alongside X-Tenant-Id", async () => {
    localStorage.setItem("accessToken", "remembered-token");
    setActingTenantId(TENANT_A);

    const config = await runInterceptor();

    expect(config.headers.Authorization).toBe("Bearer remembered-token");
    expect(config.headers["X-Tenant-Id"]).toBe(TENANT_A);
  });
});
