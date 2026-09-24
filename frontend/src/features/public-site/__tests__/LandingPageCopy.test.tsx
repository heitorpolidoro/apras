import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeAll } from "vitest";
import { MemoryRouter } from "react-router-dom";

// The global setup file (src/test/setup.ts) mocks react-i18next for every
// suite, which makes key-resolution bugs invisible: a key that no resource
// bundle can answer still renders "something". This file deliberately opts
// out of that mock and drives the page through the *real* i18next instance,
// configured exactly as the app configures it (a single `translation`
// namespace holding both locale files).
vi.unmock("react-i18next");

import i18n from "../../../i18n";
import LandingPage from "../pages/LandingPage";

describe("LandingPage copy resolves through the real i18n instance", () => {
  beforeAll(async () => {
    await i18n.changeLanguage("pt");
  });

  const renderLanding = () =>
    render(
      <MemoryRouter>
        <LandingPage />
      </MemoryRouter>,
    );

  it("renders the Portuguese hero copy, not a raw i18n key", () => {
    renderLanding();

    expect(
      screen.getByRole("heading", {
        level: 1,
        name: "Gestão inteligente e transparente para condomínios e associações",
      }),
    ).toBeInTheDocument();
  });

  it("renders the Portuguese capability copy inside landing-capabilities", () => {
    renderLanding();

    expect(
      screen.getByText("Gestão de Tarefas e Manutenção"),
    ).toBeInTheDocument();
    expect(screen.getByText("Documentos e Governança")).toBeInTheDocument();
  });

  it("leaks no unresolved dotted i18n key into the rendered text", () => {
    const { container } = renderLanding();
    const text = container.textContent ?? "";

    // An unresolved i18next lookup renders the key verbatim. None of the
    // landing's key stems may therefore appear in the visible text.
    for (const stem of [
      "hero.",
      "capabilities.",
      "previews.",
      "ctaBand.",
      "footer.",
      "loginButton",
    ]) {
      expect(text).not.toContain(stem);
    }
  });
});
