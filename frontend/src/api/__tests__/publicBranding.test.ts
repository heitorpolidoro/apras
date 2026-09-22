import { describe, it, expect, vi, beforeEach } from "vitest";
import apiClient from "../client";
import { fetchPublicBranding } from "../publicBranding";

vi.mock("../client", () => ({
  default: {
    get: vi.fn(),
    interceptors: {
      request: { use: vi.fn(), eject: vi.fn() },
      response: { use: vi.fn(), eject: vi.fn() },
    },
  },
}));

const asMock = (fn: unknown) => fn as unknown as ReturnType<typeof vi.fn>;

describe("fetchPublicBranding", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("calls the route exactly as FastAPI mounts it, with no trailing slash", async () => {
    asMock(apiClient.get).mockResolvedValue({
      data: {
        slug: "altos-da-serra",
        name: "Condomínio Altos da Serra",
        logo_url: null,
        theme: null,
      },
    });

    const branding = await fetchPublicBranding("altos-da-serra");

    expect(apiClient.get).toHaveBeenCalledWith(
      "/public/tenants/altos-da-serra/branding",
    );
    expect(branding.name).toBe("Condomínio Altos da Serra");
  });

  it("percent-encodes a slug that would otherwise break the path", async () => {
    asMock(apiClient.get).mockResolvedValue({ data: {} });

    await fetchPublicBranding("a/b");

    expect(apiClient.get).toHaveBeenCalledWith(
      "/public/tenants/a%2Fb/branding",
    );
  });

  it("propagates the 404 rather than inventing an empty branding", async () => {
    asMock(apiClient.get).mockRejectedValue({ response: { status: 404 } });

    await expect(fetchPublicBranding("nao-existe")).rejects.toMatchObject({
      response: { status: 404 },
    });
  });
});
