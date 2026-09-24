import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { readFileSync } from "node:fs";
import path from "node:path";
import type { DerivedTheme, TenantProfile } from "../../api/tenantProfile";
import TenantBrandTheme from "../TenantBrandTheme";
import { Button } from "../ui/button";
import { PDFViewerModal } from "../../features/document-management/components/PDFViewerModal";
import { OccurrenceTable } from "../../features/occurrence-management/components/OccurrenceTable";
import type { AssociationDocument } from "../../types/document";
import type { Occurrence } from "../../types/occurrence";
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

/**
 * APRAS-82's two migrated components, one from each directory it pins.
 *
 * Both are props-only — neither reaches for a query client — so they mount
 * beside `TenantBrandTheme` exactly as the pilot's `Button` does.
 */
const DOCUMENT: AssociationDocument = {
  id: "4c1d2e3f-0a1b-4c2d-8e3f-0a1b2c3d4e5f",
  folder_id: "1a2b3c4d-5e6f-4a1b-8c2d-3e4f5a6b7c8d",
  folder_name: "Atas",
  title: "Ata da assembleia de março",
  description: "Aprovação do orçamento anual",
  file_url: "https://storage.example.com/ata.pdf",
  file_size_bytes: 1048576,
  mime_type: "application/pdf",
  version_number: 2,
  publication_year: 2026,
  publication_month: 3,
  tags: ["ata"],
  uploaded_by_id: "9f8e7d6c-5b4a-4938-8271-605f4e3d2c1b",
  uploader_name: "Síndico",
  created_at: "2026-03-10T12:00:00Z",
  updated_at: "2026-03-10T12:00:00Z",
};

const OCCURRENCE: Occurrence = {
  id: "7b6a5948-3726-4514-8302-f1e0d9c8b7a6",
  protocol_number: "OC-2026-0001",
  lot_summary: "Quadra B, Lote 12",
  reporter_name: "Morador",
  is_anonymous: false,
  is_public: true,
  category: "NOISE",
  title: "Som alto após as 22h",
  description: "Festa na quadra B",
  photo_urls: [],
  status: "IN_PROGRESS",
  priority: "HIGH",
  created_at: "2026-03-10T12:00:00Z",
  updated_at: "2026-03-10T12:00:00Z",
};

/**
 * Every `class` value in `container`, split on whitespace into whole tokens.
 *
 * Whole tokens, never substrings: `bg-accent`, `hover:bg-accent` and
 * `hover:bg-accent/80` are three distinct tokens and none of them matches
 * another. A substring check would let `hover:bg-accent/80` satisfy an
 * assertion about `bg-accent`, which is precisely the §1f distinction these
 * two components are here to keep visible.
 */
const classTokens = (container: HTMLElement): Set<string> => {
  const tokens = new Set<string>();
  for (const element of container.querySelectorAll("[class]")) {
    for (const token of (element.getAttribute("class") ?? "").split(/\s+/)) {
      if (token.length > 0) {
        tokens.add(token);
      }
    }
  }
  return tokens;
};

const brandedPrimary = () =>
  window
    .getComputedStyle(document.documentElement)
    .getPropertyValue("--primary")
    .trim();

describe("the tenant's brand reaches APRAS-82's migrated components", () => {
  it("paints the PDF viewer's download button with the brand fill", async () => {
    profile.data = { ...PROFILE, theme: THEME };
    const { container } = render(
      <>
        <TenantBrandTheme />
        <PDFViewerModal
          isOpen
          document={DOCUMENT}
          onClose={() => {}}
          onDownload={() => {}}
        />
      </>,
    );

    await waitFor(() => expect(brandedPrimary()).toBe(THEME.light.primary));

    const tokens = classTokens(container);

    for (const expected of [
      "bg-primary",
      "hover:bg-primary/90",
      "text-primary-foreground",
      "text-primary",
      "bg-card",
      "bg-muted",
      "bg-foreground/70",
      "hover:bg-accent",
    ]) {
      expect(tokens).toContain(expected);
    }
    // The download button's *fill* migrated (§1f case 3), so this component
    // carries no brand tint and paints no brand characters.
    expect(tokens).not.toContain("bg-accent");
    expect([...tokens].filter((token) => token.includes("primary-text"))).toEqual(
      [],
    );
  });

  it("paints the occurrence table's protocol and details link as brand characters", async () => {
    profile.data = { ...PROFILE, theme: THEME };
    const { container } = render(
      <>
        <TenantBrandTheme />
        <OccurrenceTable
          occurrences={[OCCURRENCE]}
          isLoading={false}
          onSelectOccurrence={() => {}}
        />
      </>,
    );

    await waitFor(() => expect(brandedPrimary()).toBe(THEME.light.primary));

    const tokens = classTokens(container);

    for (const expected of [
      "text-primary-text",
      "hover:text-primary-text",
      "bg-accent",
      "hover:bg-accent",
      "hover:bg-accent/80",
      "bg-card",
      "bg-muted",
      "border-border",
    ]) {
      expect(tokens).toContain(expected);
    }
    // Nothing in this component is an interactive brand *fill*.
    for (const absent of [
      "bg-primary",
      "hover:bg-primary/90",
      "text-primary-foreground",
      "text-primary",
    ]) {
      expect(tokens).not.toContain(absent);
    }
  });
});
