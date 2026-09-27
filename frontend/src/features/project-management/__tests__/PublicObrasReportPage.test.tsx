import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import PublicObrasReportPage from "../components/PublicObrasReportPage";
import * as publicProjects from "../../../api/publicProjects";

/**
 * `/c/<slug>/obras` (APRAS-92).
 *
 * Two claims, and they are the two the screen exists for: the fetched document
 * reaches the sandboxed iframe's `srcDoc` untouched, and a rejected fetch
 * renders the "unavailable" panel rather than a blank page or a redirect to
 * `/login` — an anonymous visitor has no account to sign into.
 */

vi.mock("../../../api/publicProjects", async () => {
  const actual = await vi.importActual<typeof publicProjects>(
    "../../../api/publicProjects",
  );
  return {
    ...actual,
    fetchPublicProjectsReport: vi.fn(),
    publicReportUrl: (slug: string) =>
      `http://api.test/api/v1/public/tenants/${slug}/projects/report`,
  };
});

const DOCUMENT = "<!DOCTYPE html><html><body><h1>Obra Um</h1></body></html>";

const renderAt = (slug: string) =>
  render(
    <MemoryRouter initialEntries={[`/c/${slug}/obras`]}>
      <Routes>
        <Route path="/c/:slug/obras" element={<PublicObrasReportPage />} />
      </Routes>
    </MemoryRouter>,
  );

describe("PublicObrasReportPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the fetched report into the sandboxed iframe", async () => {
    vi.mocked(publicProjects.fetchPublicProjectsReport).mockResolvedValue(
      DOCUMENT,
    );

    renderAt("altos-da-serra");

    const frame = await waitFor(() =>
      screen.getByTestId("public-obras-report-frame"),
    );
    expect(frame).toHaveAttribute("srcdoc", DOCUMENT);
    // `sandbox=""` is the whole isolation: the report is a full page with its
    // own `<style>`, which must not leak into the application's stylesheet.
    expect(frame).toHaveAttribute("sandbox", "");
    expect(publicProjects.fetchPublicProjectsReport).toHaveBeenCalledWith(
      "altos-da-serra",
    );
  });

  it("offers a direct link so the report's own print CSS applies", async () => {
    vi.mocked(publicProjects.fetchPublicProjectsReport).mockResolvedValue(
      DOCUMENT,
    );

    renderAt("altos-da-serra");

    const link = await waitFor(() =>
      screen.getByRole("link", { name: /impress/i }),
    );
    expect(link).toHaveAttribute(
      "href",
      "http://api.test/api/v1/public/tenants/altos-da-serra/projects/report",
    );
    expect(link).toHaveAttribute("target", "_blank");
  });

  it("renders the unavailable panel when the read fails", async () => {
    vi.mocked(publicProjects.fetchPublicProjectsReport).mockRejectedValue(
      new Error("Request failed with status code 404"),
    );

    renderAt("nao-existe");

    expect(
      await screen.findByText("Relatório indisponível"),
    ).toBeInTheDocument();
    expect(
      screen.queryByTestId("public-obras-report-frame"),
    ).not.toBeInTheDocument();
  });
});
