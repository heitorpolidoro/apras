import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import PublicObrasReportPage from "../components/PublicObrasReportPage";
import * as publicProjects from "../../../api/publicProjects";
import { TWO_OBRA_REPORT } from "./fixtures/obraReportFixture";

/**
 * `/c/<slug>/obras` (APRAS-92, APRAS-118).
 *
 * The claims the screen exists for: the fetched document reaches the sandboxed
 * iframe's `srcDoc` untouched, a rejected fetch renders the "unavailable" panel
 * rather than a blank page or a redirect to `/login` (an anonymous visitor has
 * no account to sign into), and the print control opens a selector instead of
 * handing the reader the API host.
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

  afterEach(() => {
    vi.restoreAllMocks();
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

  /**
   * APRAS-118 replaced the test that used to sit here — *offers a direct link
   * so the report's own print CSS applies* — which asserted the print control's
   * `href` **was** `http://api.test/api/v1/public/tenants/<slug>/projects/report`.
   * That is the link this task deletes, so leaving it green would have meant
   * either the link survived or the assertion had stopped meaning anything.
   * These three replace it: the link is gone, the API host appears nowhere on
   * the page, and the control now opens the selector.
   */
  describe("the print control (APRAS-118)", () => {
    beforeEach(() => {
      vi.mocked(publicProjects.fetchPublicProjectsReport).mockResolvedValue(
        TWO_OBRA_REPORT,
      );
    });

    it("is a button, not a link to the API host", async () => {
      const { container } = renderAt("altos-da-serra");

      await waitFor(() => screen.getByRole("button", { name: /impress/i }));
      expect(
        screen.queryByRole("link", { name: /impress/i }),
      ).not.toBeInTheDocument();
      // Not merely "no link named /impress/i": nothing on the page may carry
      // the API origin at all.
      expect(container.innerHTML).not.toContain("http://api.test");
      expect(container.querySelectorAll("a[href]")).toHaveLength(0);
    });

    it("opens a modal listing the obras, without fetching again", async () => {
      const user = userEvent.setup();
      const fetchSpy = vi.spyOn(globalThis, "fetch");
      renderAt("altos-da-serra");

      await user.click(
        await waitFor(() => screen.getByRole("button", { name: /impress/i })),
      );

      const dialog = await screen.findByRole("dialog");
      expect(
        within(dialog).getByRole("button", { name: /Sede Social/ }),
      ).toBeInTheDocument();
      expect(
        within(dialog).getByRole("button", { name: /Portarias/ }),
      ).toBeInTheDocument();
      // No second read of the report: the page already holds the HTML.
      expect(publicProjects.fetchPublicProjectsReport).toHaveBeenCalledTimes(1);
      expect(fetchSpy).not.toHaveBeenCalled();
    });

    it("prints the chosen obra alone, into a top-level blob window", async () => {
      const user = userEvent.setup();
      const createObjectURL = vi
        .spyOn(URL, "createObjectURL")
        .mockReturnValue("blob:one-obra");
      const open = vi.spyOn(window, "open").mockReturnValue({
        document: {},
        print: vi.fn(),
        addEventListener: vi.fn(),
      } as unknown as Window);

      renderAt("altos-da-serra");
      await user.click(
        await waitFor(() => screen.getByRole("button", { name: /impress/i })),
      );
      await user.click(
        within(await screen.findByRole("dialog")).getByRole("button", {
          name: /Portarias/,
        }),
      );

      await waitFor(() => expect(open).toHaveBeenCalled());
      expect(open).toHaveBeenCalledWith("blob:one-obra", "_blank");
      const blob = createObjectURL.mock.calls[0][0] as Blob;
      const printed = await blob.text();
      expect(printed).toContain("Portarias — Ampliação");
      expect(printed).not.toContain("Sede Social — Reforma");
      expect(printed).not.toContain("<script");
    });

    it("keeps the stage detail on screen and drops it from print", async () => {
      const user = userEvent.setup();
      const createObjectURL = vi
        .spyOn(URL, "createObjectURL")
        .mockReturnValue("blob:one-obra");
      vi.spyOn(window, "open").mockReturnValue({
        document: {},
        print: vi.fn(),
        addEventListener: vi.fn(),
      } as unknown as Window);

      renderAt("altos-da-serra");

      // The presence half, on the document the iframe actually receives. The
      // absence below is only worth something because this passes: the backend
      // still emits the section, and `CSS_BODY`'s second `@media print` block
      // expands it on paper, which is what makes dropping it necessary.
      const frame = await waitFor(() =>
        screen.getByTestId("public-obras-report-frame"),
      );
      expect(frame.getAttribute("srcdoc")).toContain('<details class="all"');

      await user.click(screen.getByRole("button", { name: /impress/i }));
      await user.click(
        within(await screen.findByRole("dialog")).getByRole("button", {
          name: /Portarias/,
        }),
      );

      await waitFor(() => expect(createObjectURL).toHaveBeenCalled());
      const printed = await (createObjectURL.mock.calls[0][0] as Blob).text();
      expect(printed).not.toContain('<details class="all"');
      const parsed = new DOMParser().parseFromString(printed, "text/html");
      expect(parsed.querySelectorAll("details.all")).toHaveLength(0);
    });
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
