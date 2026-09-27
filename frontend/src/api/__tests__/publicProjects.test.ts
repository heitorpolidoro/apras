import { describe, it, expect, vi, beforeEach } from "vitest";
import apiClient from "../client";
import {
  fetchPublicProjectsReport,
  publicReportPath,
  publicReportUrl,
} from "../publicProjects";

vi.mock("../client", () => ({
  default: {
    get: vi.fn(),
    defaults: { baseURL: "http://api.test/api/v1" },
    interceptors: {
      request: { use: vi.fn(), eject: vi.fn() },
      response: { use: vi.fn(), eject: vi.fn() },
    },
  },
}));

const asMock = (fn: unknown) => fn as unknown as ReturnType<typeof vi.fn>;

const DOCUMENT = "<!DOCTYPE html><html><body>Obra</body></html>";

describe("the public obras report client (APRAS-92)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("calls the route exactly as FastAPI mounts it, with no trailing slash", async () => {
    asMock(apiClient.get).mockResolvedValue({ data: DOCUMENT });

    const html = await fetchPublicProjectsReport("altos-da-serra");

    expect(apiClient.get).toHaveBeenCalledWith(
      "/public/tenants/altos-da-serra/projects/report",
      expect.objectContaining({ responseType: "text" }),
    );
    expect(html).toBe(DOCUMENT);
  });

  it("asks Axios not to parse the body, which is HTML and not JSON", async () => {
    asMock(apiClient.get).mockResolvedValue({ data: DOCUMENT });

    await fetchPublicProjectsReport("altos-da-serra");

    const [, config] = asMock(apiClient.get).mock.calls[0];
    const [identity] = config.transformResponse as Array<
      (data: string) => string
    >;
    expect(identity(DOCUMENT)).toBe(DOCUMENT);
  });

  it("percent-encodes a slug that would otherwise break the path", () => {
    expect(publicReportPath("a/b")).toBe(
      "/public/tenants/a%2Fb/projects/report",
    );
  });

  it("builds the print link off the shared client's base URL", () => {
    // Never off `import.meta.env`: this module must not become a second
    // definition of where the API lives.
    expect(publicReportUrl("altos-da-serra")).toBe(
      "http://api.test/api/v1/public/tenants/altos-da-serra/projects/report",
    );
  });

  it("propagates the 404 rather than inventing an empty document", async () => {
    asMock(apiClient.get).mockRejectedValue({ response: { status: 404 } });

    await expect(fetchPublicProjectsReport("nao-existe")).rejects.toMatchObject(
      { response: { status: 404 } },
    );
  });
});
