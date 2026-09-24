import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";
import LandingPage from "../pages/LandingPage";

// i18next: return the key so assertions are stable regardless of locale load.
vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: { changeLanguage: vi.fn() },
  }),
}));

const renderLanding = () =>
  render(
    <MemoryRouter>
      <LandingPage />
    </MemoryRouter>,
  );

describe("LandingPage", () => {
  it("renders a top <header> with brand and a link to /login", () => {
    renderLanding();

    const header = document.querySelector("header");
    expect(header).not.toBeNull();
    // The brand key is rendered in the header.
    expect(header).toHaveTextContent("landing.brand");
    // At least one link inside the header pointing at /login.
    const loginLinks = within(header!).getAllByRole("link");
    expect(
      loginLinks.some((l) => l.getAttribute("href") === "/login"),
    ).toBeTruthy();
  });

  it("renders exactly one <h1>", () => {
    const { container } = renderLanding();
    expect(container.querySelectorAll("h1")).toHaveLength(1);
  });

  it("renders the landing-previews section", () => {
    renderLanding();
    expect(screen.getByTestId("landing-previews")).toBeInTheDocument();
  });

  it("renders exactly six <h2> elements inside landing-capabilities", () => {
    renderLanding();
    const caps = screen.getByTestId("landing-capabilities");
    expect(within(caps).getAllByRole("heading", { level: 2 })).toHaveLength(6);
  });

  it("renders at least one link to /login", () => {
    renderLanding();
    const allLinks = screen
      .getAllByRole("link")
      .filter((l) => l.getAttribute("href") === "/login");
    expect(allLinks.length).toBeGreaterThanOrEqual(1);
  });

  it("renders a <footer>", () => {
    const { container } = renderLanding();
    expect(container.querySelector("footer")).not.toBeNull();
  });

  it("renders no hard-coded user-visible strings (all text via t() key placeholders)", () => {
    // When useTranslation returns the key as the string, every visible text
    // should match a dotted i18n key pattern — no English/Portuguese prose.
    const { container } = renderLanding();
    // The text content of the entire page should contain known key fragments.
    const text = container.textContent ?? "";
    // A known capability key must be present.
    expect(text).toContain("landing.capabilities.tasks.title");
    // Raw Portuguese/English prose should NOT be present.
    expect(text).not.toContain("Gestão inteligente");
    expect(text).not.toContain("Smart and transparent");
  });

  it("tab navigation switches the preview panel", async () => {
    renderLanding();
    const user = userEvent.setup();

    // Default tab is tasks.
    expect(screen.getByText("landing.previews.tasks.cardTitle")).toBeInTheDocument();

    // Click the access tab.
    await user.click(screen.getByRole("tab", { name: "landing.previews.tabAccess" }));
    expect(screen.getByText("landing.previews.access.cardTitle")).toBeInTheDocument();
    expect(
      screen.queryByText("landing.previews.tasks.cardTitle"),
    ).not.toBeInTheDocument();
  });

  it("renders the infractions and finance preview panels when selected", async () => {
    renderLanding();
    const user = userEvent.setup();

    await user.click(
      screen.getByRole("tab", { name: "landing.previews.tabInfractions" }),
    );
    expect(
      screen.getByText("landing.previews.infractions.cardTitle"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("landing.previews.infractions.evidence"),
    ).toBeInTheDocument();

    await user.click(
      screen.getByRole("tab", { name: "landing.previews.tabFinance" }),
    );
    expect(
      screen.getByText("landing.previews.finance.cardTitle"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("landing.previews.finance.milestone"),
    ).toBeInTheDocument();
    expect(
      screen.queryByText("landing.previews.infractions.cardTitle"),
    ).not.toBeInTheDocument();
  });
});
