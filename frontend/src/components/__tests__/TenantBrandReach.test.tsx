import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { readFileSync } from "node:fs";
import path from "node:path";
import type { DerivedTheme, TenantProfile } from "../../api/tenantProfile";
import TenantBrandTheme from "../TenantBrandTheme";
import { Button } from "../ui/button";
import { TENANT_BRAND_STYLE_ID } from "../../lib/brandStylesheet";

/**
 * The brand-reach proof (APRAS-78 §4c).
 *
 * APRAS-68 gave the tenant a stylesheet; APRAS-78 is the first task to move a
 * component onto the tokens that stylesheet overrides. This is the test that
 * says the two halves meet: a **migrated** `components/ui` component rendered
 * beside `TenantBrandTheme` resolves `--primary` to the *tenant's* value, not
 * to `index.css`'s.
 *
 * **Every assertion is against the token, never against a colour literal.**
 * The expected value is read out of the mocked derived theme, and the
 * unbranded value is read out of `src/index.css` itself, so neither can drift
 * out of step with the source it came from. `TENANT_BRAND_STYLE_ID` is
 * imported by name for the same reason: `lib/brandStylesheet.ts` grew a
 * second id in APRAS-74 and a hard-coded string here would have silently
 * started asserting the wrong element.
 */

const BRANDED_PRIMARY = "oklch(0.55 0.06 83.88)";

const THEME: DerivedTheme = {
  light: {
    background: "oklch(0.99 0 0)",
    foreground: "oklch(0.14 0.01 83.88)",
    card: "oklch(1.00 0 0)",
    "card-foreground": "oklch(0.14 0.01 83.88)",
    popover: "oklch(1.00 0 0)",
    "popover-foreground": "oklch(0.14 0.01 83.88)",
    primary: BRANDED_PRIMARY,
    "primary-foreground": "oklch(0.98 0.00 0.00)",
    secondary: "oklch(0.68 0.14 237.32)",
    "secondary-foreground": "oklch(0.15 0.02 237.32)",
    accent: "oklch(0.96 0.01 237.32)",
    "accent-foreground": "oklch(0.20 0.02 237.32)",
    muted: "oklch(0.96 0.01 83.88)",
    "muted-foreground": "oklch(0.53 0.02 83.88)",
    border: "oklch(0.92 0.01 83.88)",
    input: "oklch(0.92 0.01 83.88)",
    ring: "oklch(0.55 0.06 83.88)",
  },
  dark: {
    background: "oklch(0.14 0.01 83.88)",
    foreground: "oklch(0.98 0.01 83.88)",
    card: "oklch(0.16 0.01 83.88)",
    "card-foreground": "oklch(0.98 0.01 83.88)",
    popover: "oklch(0.16 0.01 83.88)",
    "popover-foreground": "oklch(0.98 0.01 83.88)",
    primary: "oklch(0.62 0.06 83.88)",
    "primary-foreground": "oklch(0.15 0.02 83.88)",
    secondary: "oklch(0.68 0.14 237.32)",
    "secondary-foreground": "oklch(0.15 0.02 237.32)",
    accent: "oklch(0.22 0.03 237.32)",
    "accent-foreground": "oklch(0.98 0.01 237.32)",
    muted: "oklch(0.22 0.02 83.88)",
    "muted-foreground": "oklch(0.72 0.02 83.88)",
    border: "oklch(0.25 0.02 83.88)",
    input: "oklch(0.25 0.02 83.88)",
    ring: "oklch(0.62 0.06 83.88)",
  },
};

const PROFILE: TenantProfile = {
  id: "8f1c0f2e-5e5c-4a0f-9c1e-1c2a3b4d5e6f",
  name: "Residencial Altos da Serra VI",
  slug: "residencial-altos-da-serra-vi",
  is_active: true,
  logo_url: null,
  brand_theme: { mode: "simple", primary: "#857046", accent: "#0ea5e9" },
  theme: THEME,
};

const profile = vi.hoisted(() => ({ data: { theme: null } as { theme: DerivedTheme | null } }));

vi.mock("../../hooks/useTenantProfile", () => ({
  useTenantProfile: () => profile,
}));

vi.mock("../../features/user-administration/context/AuthContext", () => ({
  useAuth: () => ({ isAuthenticated: true }),
}));

/** `--primary` as the unbranded app declares it, read from the stylesheet
 *  rather than written down, so this test cannot disagree with `index.css`.
 *
 * Read with `node:fs` from the Vitest root rather than imported with `?raw`:
 * the Tailwind Vite plugin owns `.css` in this project and hands back an
 * empty string for a raw import of it. `import.meta.url` is unusable here
 * for the same reason `src/__tests__/themeContrast.test.ts` records — under
 * jsdom it is the dev server's `http:` URL. */
const unbrandedPrimary = (): string => {
  const indexCss = readFileSync(
    path.join(process.cwd(), "src", "index.css"),
    "utf8",
  );
  const root = indexCss.split(":root {")[1].split("}")[0];
  const declared = /--primary:\s*([^;]+);/.exec(root);
  return (declared?.[1] ?? "").trim();
};

const injected = () => document.getElementById(TENANT_BRAND_STYLE_ID);

const renderApp = (theme: DerivedTheme | null) => {
  profile.data = { ...PROFILE, theme };
  return render(
    <>
      <TenantBrandTheme />
      <Button variant="success">Confirmar</Button>
    </>,
  );
};

describe("the tenant's brand reaches a migrated component", () => {
  it("resolves --primary to the tenant's value, not the stylesheet's", async () => {
    const shipped = unbrandedPrimary();
    // The premise of the proof: the mocked theme must actually differ from
    // what `index.css` ships, or the assertion below would pass either way.
    expect(THEME.light.primary).not.toBe(shipped);

    renderApp(THEME);

    await waitFor(() => expect(injected()).not.toBeNull());
    expect(injected()?.textContent).toContain(`--primary: ${THEME.light.primary};`);
    await waitFor(() =>
      expect(
        window
          .getComputedStyle(document.documentElement)
          .getPropertyValue("--primary")
          .trim(),
      ).toBe(THEME.light.primary),
    );
  });

  it("renders the success button on the primary token, not on a palette class", () => {
    renderApp(THEME);

    const button = screen.getByRole("button", { name: "Confirmar" });

    expect(button.className).toContain("bg-primary");
    expect(button.className).toContain("text-primary-foreground");
    expect(button.className).not.toMatch(/emerald/);
  });

  it("injects nothing at all for a tenant with no branding", async () => {
    renderApp(null);

    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Confirmar" })).toBeTruthy(),
    );
    expect(injected()).toBeNull();
  });
});
