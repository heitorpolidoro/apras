import { describe, it, expect, vi, beforeEach } from "vitest";
import apiClient from "../client";
import {
  setSimulationState,
  getSimulationState,
} from "../../features/user-administration/context/simulationState";

describe("apiClient", () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
    vi.clearAllMocks();
    setSimulationState({ isSimulating: false });
  });

  it("adds Authorization header if token exists in localStorage", async () => {
    const token = "test-token";
    localStorage.setItem("accessToken", token);

    // O axios-mock-adapter seria o ideal aqui, mas podemos testar o interceptor diretamente
    // acessando a lista de interceptores do axios ou simulando uma requisição.

    const requestInterceptor = (
      apiClient.interceptors.request as unknown as {
        handlers: {
          fulfilled: (...args: unknown[]) => unknown;
          rejected: (...args: unknown[]) => unknown;
        }[];
      }
    ).handlers[0];

    const config = { headers: {} };
    const updatedConfig = (await requestInterceptor.fulfilled(config)) as any;

    expect(updatedConfig.headers.Authorization).toBe(`Bearer ${token}`);
  });

  it("adds Authorization header if token exists in sessionStorage", async () => {
    const token = "session-test-token";
    sessionStorage.setItem("accessToken", token);

    const requestInterceptor = (
      apiClient.interceptors.request as unknown as {
        handlers: {
          fulfilled: (...args: unknown[]) => unknown;
          rejected: (...args: unknown[]) => unknown;
        }[];
      }
    ).handlers[0];

    const config = { headers: {} };
    const updatedConfig = (await requestInterceptor.fulfilled(config)) as any;

    expect(updatedConfig.headers.Authorization).toBe(`Bearer ${token}`);
  });

  it("does not add Authorization header if token is missing", async () => {
    const requestInterceptor = (
      apiClient.interceptors.request as unknown as {
        handlers: {
          fulfilled: (...args: unknown[]) => unknown;
          rejected: (...args: unknown[]) => unknown;
        }[];
      }
    ).handlers[0];

    const config = { headers: {} };
    const updatedConfig = (await requestInterceptor.fulfilled(config)) as any;

    expect(updatedConfig.headers.Authorization).toBeUndefined();
  });

  it("rejects the promise if request interceptor fails", async () => {
    const requestInterceptor = (
      apiClient.interceptors.request as unknown as {
        handlers: {
          fulfilled: (...args: unknown[]) => unknown;
          rejected: (...args: unknown[]) => unknown;
        }[];
      }
    ).handlers[0];
    const error = new Error("Request failed");

    await expect(requestInterceptor.rejected(error)).rejects.toThrow(
      "Request failed",
    );
  });

  it("adds bypass token header when VITE_BYPASS_TOKEN is set", async () => {
    vi.stubEnv("VITE_BYPASS_TOKEN", "my-bypass-token");
    vi.resetModules();

    const { default: freshClient } = await import("../client");
    const interceptor = (
      freshClient.interceptors.request as unknown as {
        handlers: { fulfilled: (...args: unknown[]) => unknown }[];
      }
    ).handlers[0];

    const config = { headers: {} as Record<string, string> };
    const result = (await interceptor.fulfilled(config)) as { headers: Record<string, string> };

    expect(result.headers["x-vercel-protection-bypass"]).toBe("my-bypass-token");

    vi.unstubAllEnvs();
    vi.resetModules();
  });

  describe("simulation mutation guard", () => {
    const getRequestInterceptor = () =>
      (
        apiClient.interceptors.request as unknown as {
          handlers: {
            fulfilled: (...args: unknown[]) => unknown;
            rejected: (...args: unknown[]) => unknown;
          }[];
        }
      ).handlers[0];

    it.each(["post", "put", "patch", "delete"])(
      "rejects %s requests while simulating, with a parseApiError-shaped error",
      async (method) => {
        setSimulationState({ isSimulating: true });
        const requestInterceptor = getRequestInterceptor();
        const config = { method, headers: {} };

        await expect(
          requestInterceptor.fulfilled(config),
        ).rejects.toMatchObject({
          response: { data: { detail: expect.any(String) } },
        });
      },
    );

    it("does not block GET requests while simulating", async () => {
      setSimulationState({ isSimulating: true });
      const requestInterceptor = getRequestInterceptor();
      const config = { method: "get", headers: {} };

      const result = await requestInterceptor.fulfilled(config);
      expect(result).toBe(config);
    });

    it("does not block mutating requests when not simulating", async () => {
      setSimulationState({ isSimulating: false });
      const requestInterceptor = getRequestInterceptor();
      const config = { method: "post", headers: {} };

      const result = await requestInterceptor.fulfilled(config);
      expect(result).toBe(config);
    });

    it("is case-insensitive about the HTTP method", async () => {
      setSimulationState({ isSimulating: true });
      const requestInterceptor = getRequestInterceptor();
      const config = { method: "POST", headers: {} };

      await expect(requestInterceptor.fulfilled(config)).rejects.toBeTruthy();
    });

    it("reads the current simulation state via getSimulationState", () => {
      setSimulationState({ isSimulating: true });
      expect(getSimulationState().isSimulating).toBe(true);
      setSimulationState({ isSimulating: false });
      expect(getSimulationState().isSimulating).toBe(false);
    });
  });
});
