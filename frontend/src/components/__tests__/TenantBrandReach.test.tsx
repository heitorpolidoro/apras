import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { readFileSync } from "node:fs";
import path from "node:path";
import type { DerivedTheme, TenantProfile } from "../../api/tenantProfile";
import TenantBrandTheme from "../TenantBrandTheme";
import { Button } from "../ui/button";
import { PDFViewerModal } from "../../features/document-management/components/PDFViewerModal";
import { OccurrenceTable } from "../../features/occurrence-management/components/OccurrenceTable";
import { MilestoneTimeline } from "../../features/project-management/components/MilestoneTimeline";
import { AssetSummaryCards } from "../../features/asset-management/components/AssetSummaryCards";
import type { AssociationDocument } from "../../types/document";
import type { Occurrence } from "../../types/occurrence";
import type { ProjectMilestone } from "../../types/project";
import type { AssetSummary } from "../../types/asset";
import { CashBalanceCard } from "../../features/finance/components/CashBalanceCard";
import { SelectQuoteModal } from "../../features/purchase-management/components/SelectQuoteModal";
import { DeviceTable } from "../../features/access-control/components/DeviceTable";
import type { CashBalance } from "../../types/finance";
import type { PurchaseQuote } from "../../types/purchase";
import type { AccessDevice } from "../../types/accessControl";
import { TENANT_BRAND_STYLE_ID } from "../../lib/brandStylesheet";
import { AvatarWithFallback } from "../../features/media-management/components/AvatarWithFallback";
import { AvatarCropEditor } from "../../features/media-management/components/AvatarCropEditor";
import { FeedbackInboxTable } from "../../features/feedback-management/components/FeedbackInboxTable";
import { MediaCarousel } from "../../features/announcement-feed/components/MediaCarousel";
import { PackageStatusPage } from "../../features/package-management/components/PackageStatusPage";
import type { Feedback } from "../../types/feedback";
import type { AnnouncementMedia } from "../../types/announcement";
import type { Package } from "../../types/package";

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

/**
 * `PackageStatusPage` is the one component here that reaches for data rather
 * than taking it as props, and its two hooks live in two different modules —
 * the list in `package-management`, the mutation in `visitor-management` — so
 * each needs its own `vi.mock`. Everything else on this page is props-only.
 */
const PACKAGE: Package = vi.hoisted(() => ({
  id: "b2c3d4e5-6f70-4812-9345-67890abcdef1",
  lot_id: "c3d4e5f6-7081-4923-a456-7890abcdef12",
  lot_summary: null,
  received_by_id: null,
  received_by_name: "Portaria",
  description: "Caixa da farmácia",
  carrier: "Correios",
  received_at: "2026-02-10T09:30:00Z",
  status: "AWAITING_PICKUP",
  picked_up_at: null,
  picked_up_by_id: null,
  picked_up_by_name: null,
  picked_up_by_notes: null,
}));

vi.mock("../../features/package-management/hooks/usePackages", () => ({
  useMyPackages: () => ({
    lotsWithPackages: [
      {
        lot: { id: "c3d4e5f6-7081-4923-a456-7890abcdef12", block: "B", lot_number: "12" },
        packages: [PACKAGE],
        isLoading: false,
      },
    ],
    isLoading: false,
  }),
}));

vi.mock("../../features/visitor-management/hooks/usePackages", () => ({
  useMarkPackagePickedUp: () => ({ mutateAsync: async () => {}, isPending: false }),
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

/**
 * APRAS-81's two migrated components, one from each directory it pins.
 *
 * Both are props-only — neither reaches for a query client — so they mount
 * beside `TenantBrandTheme` exactly as the pilot's `Button` does.
 */
const MILESTONE: ProjectMilestone = {
  id: "2f3e4d5c-6b7a-4859-9081-a2b3c4d5e6f7",
  project_id: "1a2b3c4d-5e6f-4a1b-8c2d-3e4f5a6b7c8d",
  title: "Fundação concluída",
  description: "Sapatas e baldrames executados",
  status: "DONE",
  due_date: "2026-03-01",
  completion_date: "2026-02-27",
  display_order: 1,
  created_at: "2026-02-27T12:00:00Z",
  updated_at: "2026-02-27T12:00:00Z",
};

const SUMMARY: AssetSummary = {
  total_assets: 42,
  total_consumables: 17,
  low_stock_count: 3,
  total_patrimonial_value: 125000,
};

describe("the tenant's brand reaches APRAS-81's migrated components", () => {
  it("paints the milestone timeline's add control with the brand fill", async () => {
    profile.data = { ...PROFILE, theme: THEME };
    const { container } = render(
      <>
        <TenantBrandTheme />
        <MilestoneTimeline
          milestones={[MILESTONE]}
          onAddMilestone={() => {}}
          onEditMilestone={() => {}}
          onDeleteMilestone={() => {}}
          canManage
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
      "hover:text-primary",
      "bg-card",
      "bg-muted",
      "border-border",
      "border-border/80",
      "text-muted-foreground",
      "text-foreground",
      "hover:text-destructive",
    ]) {
      expect(tokens).toContain(expected);
    }
    // §1k: every brand class here is on an element that paints no glyphs, so
    // the component carries the graphical token and no character token.
    expect([...tokens].filter((token) => token.includes("primary-text"))).toEqual(
      [],
    );
  });

  it("paints the asset summary tile on the brand tint, with no brand fill", async () => {
    profile.data = { ...PROFILE, theme: THEME };
    const { container } = render(
      <>
        <TenantBrandTheme />
        <AssetSummaryCards summary={SUMMARY} />
      </>,
    );

    await waitFor(() => expect(brandedPrimary()).toBe(THEME.light.primary));

    const tokens = classTokens(container);

    for (const expected of [
      "bg-accent",
      "text-primary",
      "bg-card",
      "border-border",
      "text-muted-foreground",
      "text-foreground",
    ]) {
      expect(tokens).toContain(expected);
    }
    // Its single brand call site is a *tile*, so there is no brand fill and
    // no brand character here — asserting `bg-primary` would be asserting a
    // class this component does not produce.
    for (const absent of [
      "bg-primary",
      "hover:bg-primary/90",
      "text-primary-foreground",
      "text-primary-text",
    ]) {
      expect(tokens).not.toContain(absent);
    }
  });
});

/**
 * APRAS-83's three migrated components, one from each directory it pins.
 *
 * All three are props-only — none reaches for a query client — so they mount
 * beside `TenantBrandTheme` exactly as the pilot's `Button` does. Each is
 * asserted over the whitespace-split class tokens of the **full** rendered
 * markup, which includes the tokens contributed by any `components/ui/`
 * primitive it renders, not only the tokens written in its own source.
 */
const BALANCE: CashBalance = {
  as_of_date: "2026-09-30",
  total_income: 128400.5,
  total_expense: 91230.75,
  balance: 37169.75,
};

const QUOTE: PurchaseQuote = {
  id: "5c6d7e8f-9a0b-4c1d-8e2f-3a4b5c6d7e8f",
  purchase_request_id: "1a2b3c4d-5e6f-4a1b-8c2d-3e4f5a6b7c8d",
  supplier_name: "Elevadores Atlas Schindler",
  supplier_contact: "contato@atlas.example",
  items: [
    {
      id: "7e8f9a0b-1c2d-4e3f-8a4b-5c6d7e8f9a0b",
      request_item_id: null,
      model: "Modelo 3300",
      unit_price: 45000,
      description: "Modernização de cabine",
      quantity: 1,
      position: 1,
      line_total: 45000,
    },
  ],
  quoted_item_count: 1,
  is_complete: true,
  notes: null,
  extra_fields: [],
  attachment_url: null,
  attachment_filename: null,
  total_price: 45000,
  created_by_id: "9a0b1c2d-3e4f-4a5b-8c6d-7e8f9a0b1c2d",
  created_by_name: "Síndico",
  is_selected: false,
  is_lowest_price: true,
  created_at: "2026-09-20T12:00:00Z",
  updated_at: "2026-09-20T12:00:00Z",
};

const DEVICE: AccessDevice = {
  id: "3e4f5a6b-7c8d-4e9f-8a0b-1c2d3e4f5a6b",
  name: "Portão social",
  location: "Torre A, térreo",
  status: "ONLINE",
  last_seen_at: "2026-09-25T11:00:00Z",
  created_by_id: "9a0b1c2d-3e4f-4a5b-8c6d-7e8f9a0b1c2d",
  created_at: "2026-09-01T12:00:00Z",
  updated_at: "2026-09-25T11:00:00Z",
};

describe("the tenant's brand reaches APRAS-83's migrated components", () => {
  it("paints the cash-balance tiles on the brand tint, with no brand fill", async () => {
    profile.data = { ...PROFILE, theme: THEME };
    const { container } = render(
      <>
        <TenantBrandTheme />
        <CashBalanceCard balance={BALANCE} isLoading={false} />
      </>,
    );

    await waitFor(() => expect(brandedPrimary()).toBe(THEME.light.primary));

    const tokens = classTokens(container);

    // `CashBalanceCard` renders no `components/ui/` primitive, so this set is
    // entirely its own.
    for (const expected of [
      "bg-card",
      "border-border",
      "bg-accent",
      "text-primary",
      "text-muted-foreground",
      "text-foreground",
    ]) {
      expect(tokens).toContain(expected);
    }
    // Its single brand call site is the `<Wallet/>` inside a *tile*, so there
    // is no brand fill and no brand character here.
    for (const absent of [
      "text-primary-text",
      "bg-primary",
      "text-primary-foreground",
      "text-destructive",
      "bg-muted",
    ]) {
      expect(tokens).not.toContain(absent);
    }
  });

  it("paints the select-quote modal's submit button with the brand fill", async () => {
    profile.data = { ...PROFILE, theme: THEME };
    const { container } = render(
      <>
        <TenantBrandTheme />
        <SelectQuoteModal
          isOpen
          quote={QUOTE}
          onClose={() => {}}
          onSubmit={async () => {}}
        />
      </>,
    );

    await waitFor(() => expect(brandedPrimary()).toBe(THEME.light.primary));

    const tokens = classTokens(container);

    // From its own markup.
    for (const expected of [
      "bg-card",
      "border-border",
      "bg-muted",
      "text-foreground",
      "text-muted-foreground",
    ]) {
      expect(tokens).toContain(expected);
    }
    // Contributed by the already-migrated `ui/button` `default` variant, which
    // the variantless submit button takes. The modal's own source writes
    // neither token, which is exactly why the assertion is over the full
    // rendered markup and not over the file.
    for (const expected of ["bg-primary", "text-primary-foreground"]) {
      expect(tokens).toContain(expected);
    }
    for (const absent of [
      "text-primary",
      "text-primary-text",
      "bg-accent",
      "text-destructive",
    ]) {
      expect(tokens).not.toContain(absent);
    }
  });

  it("paints the revealed device key as brand characters", async () => {
    profile.data = { ...PROFILE, theme: THEME };
    const { container } = render(
      <>
        <TenantBrandTheme />
        <DeviceTable
          devices={[DEVICE]}
          onRegenerateKey={async () => "3f9a-77c1-b204-e8d5"}
        />
      </>,
    );

    await waitFor(() => expect(brandedPrimary()).toBe(THEME.light.primary));
    // The key chip only renders once a regeneration has resolved.
    await userEvent.click(
      screen.getByRole("button", { name: /Regenerar Chave/i }),
    );
    await waitFor(() =>
      expect(classTokens(container)).toContain("text-primary-text"),
    );

    const tokens = classTokens(container);

    for (const expected of [
      "text-primary-text",
      "bg-accent",
      "border-border",
      "text-foreground",
      "text-muted-foreground",
    ]) {
      expect(tokens).toContain(expected);
    }
    // `ui/button` at the `outline` variant contributes `border-input`,
    // `bg-background`, `hover:bg-accent` and `hover:text-accent-foreground`,
    // and no token on either list here.
    for (const expected of [
      "border-input",
      "bg-background",
      "hover:bg-accent",
      "hover:text-accent-foreground",
    ]) {
      expect(tokens).toContain(expected);
    }
    // §1k: the key chip paints glyphs, so it takes the character token and the
    // graphical one appears nowhere in this component.
    for (const absent of [
      "text-primary",
      "bg-primary",
      "bg-card",
      "bg-muted",
      "text-primary-foreground",
      "text-destructive",
    ]) {
      expect(tokens).not.toContain(absent);
    }
  });
});

const FEEDBACK: Feedback = {
  id: "d4e5f607-8192-4a34-b567-890abcdef123",
  reporter_user_id: null,
  reporter_name: "Ana Souza",
  is_anonymous: false,
  category: "SUGGESTION",
  message: "Sugiro instalar bicicletário coberto.",
  status: "PENDING",
  board_response: null,
  responded_by_id: null,
  responded_by_name: null,
  responded_at: null,
  response_seen_by_reporter: false,
  created_at: "2026-02-09T12:00:00Z",
};

/** The first is deliberately **not** an `IMAGE`, so the PDF link renders; two
 *  items is what makes both nav buttons and both dots render. */
const MEDIA: AnnouncementMedia[] = [
  {
    id: "e5f60718-2930-4b45-c678-90abcdef1234",
    announcement_id: "f6071829-3041-4c56-d789-0abcdef12345",
    media_type: "PDF",
    url: "https://example.invalid/ata.pdf",
    mime_type: "application/pdf",
    file_size_bytes: 22_144,
    order_index: 0,
    created_at: "2026-02-08T08:00:00Z",
  },
  {
    id: "07182930-4152-4d67-e890-abcdef123456",
    announcement_id: "f6071829-3041-4c56-d789-0abcdef12345",
    media_type: "IMAGE",
    url: "https://example.invalid/foto.jpg",
    mime_type: "image/jpeg",
    file_size_bytes: 91_002,
    order_index: 1,
    created_at: "2026-02-08T08:05:00Z",
  },
];

describe("the tenant's brand reaches APRAS-84's migrated components", () => {
  it("paints the avatar fallback on the neutral fill, with no brand token at all", async () => {
    profile.data = { ...PROFILE, theme: THEME };
    const { container } = render(
      <>
        <TenantBrandTheme />
        <AvatarWithFallback name="Ana Souza" status="PENDING_APPROVAL" />
      </>,
    );

    await waitFor(() => expect(brandedPrimary()).toBe(THEME.light.primary));

    const tokens = classTokens(container);

    // Renders no `components/ui/` primitive, so this set is entirely its own.
    // `text-slate-700`, `bg-amber-500/90` and `text-white` are the three kept
    // classes: the avatar fill's foreground is out of budget, and the badge is
    // status set 10, whose amber carries no token and whose label therefore has
    // no surface to be named against.
    for (const expected of [
      "bg-muted",
      "border-input",
      "text-slate-700",
      "bg-amber-500/90",
      "text-white",
    ]) {
      expect(tokens).toContain(expected);
    }
    for (const absent of [
      "bg-card",
      "bg-primary",
      "text-primary",
      "text-primary-text",
      "text-primary-foreground",
      "text-muted-foreground",
      "text-foreground",
      "bg-accent",
      "text-destructive",
    ]) {
      expect(tokens).not.toContain(absent);
    }
  });

  it("paints the inbox table's details control as brand characters", async () => {
    profile.data = { ...PROFILE, theme: THEME };
    const { container } = render(
      <>
        <TenantBrandTheme />
        <FeedbackInboxTable
          items={[FEEDBACK]}
          isLoading={false}
          onSelectFeedback={() => {}}
        />
      </>,
    );

    await waitFor(() => expect(brandedPrimary()).toBe(THEME.light.primary));

    const tokens = classTokens(container);

    // §1k's "mixed element wins for text": the control paints an `<Eye/>` and
    // the label "Ver Detalhes" from one `currentColor`, so it takes the
    // character token. Splitting is strict, so `hover:bg-accent` and
    // `hover:bg-accent/80` are two distinct tokens and neither matches
    // `bg-accent`.
    for (const expected of [
      "bg-card",
      "border-border",
      "bg-muted",
      "text-muted-foreground",
      "text-foreground",
      "text-primary-text",
      "hover:text-primary-text",
      "bg-accent",
      "hover:bg-accent",
      "hover:bg-accent/80",
    ]) {
      expect(tokens).toContain(expected);
    }
    for (const absent of [
      "text-primary",
      "bg-primary",
      "text-primary-foreground",
      "text-destructive",
      "border-input",
      "bg-background",
    ]) {
      expect(tokens).not.toContain(absent);
    }
  });

  it("paints the carousel's floating controls on the card family", async () => {
    profile.data = { ...PROFILE, theme: THEME };
    const { container } = render(
      <>
        <TenantBrandTheme />
        <MediaCarousel media={MEDIA} />
      </>,
    );

    await waitFor(() => expect(brandedPrimary()).toBe(THEME.light.primary));

    const tokens = classTokens(container);

    // The three floating white surfaces are controls and an indicator painted
    // *on top of* media, not scrims, so §1h code 1 does not reach them and the
    // §1b row governs: `bg-card/80`, `hover:bg-card` and `bg-card/70`, each an
    // opacity modifier carried over verbatim. The active dot is the one brand
    // fill, and the `<FileText/>` the one destructive glyph.
    for (const expected of [
      "bg-muted",
      "bg-card",
      "bg-card/80",
      "bg-card/70",
      "hover:bg-card",
      "hover:bg-accent",
      "text-destructive",
      "bg-primary",
    ]) {
      expect(tokens).toContain(expected);
    }
    for (const absent of [
      "text-primary",
      "text-primary-text",
      "text-primary-foreground",
      "border-border",
      "bg-accent",
      "text-muted-foreground",
      "text-foreground",
    ]) {
      expect(tokens).not.toContain(absent);
    }
  });

  it("paints the zoom slider's track with the brand and its thumb with the foreground", async () => {
    profile.data = { ...PROFILE, theme: THEME };
    const { container } = render(
      <>
        <TenantBrandTheme />
        <AvatarCropEditor
          imageSrc="https://example.invalid/foto.jpg"
          onCropComplete={() => {}}
          onCancel={() => {}}
        />
      </>,
    );

    await waitFor(() => expect(brandedPrimary()).toBe(THEME.light.primary));

    const tokens = classTokens(container);

    // §7's amendment, pinned here. Takes props only and renders no
    // `components/ui/` primitive, so this set is entirely its own.
    for (const expected of [
      "bg-muted",
      "border-border",
      "text-slate-700",
      "bg-foreground",
      "border-primary",
      "text-muted-foreground",
      "bg-primary",
      "accent-primary-foreground",
      "bg-card",
      "border-input",
      "hover:bg-accent",
      "text-primary-foreground",
      "hover:bg-primary/90",
    ]) {
      expect(tokens).toContain(expected);
    }
    // `accent-primary` is excluded by whitespace-split token equality, which
    // does not treat it as matching `accent-primary-foreground`. That is the
    // distinction the operator's decision turns on: the earlier draft pinned
    // `accent-primary` here and would have put the thumb at 1.0000 on its own
    // track.
    for (const absent of [
      "accent-primary",
      "accent-indigo-600",
      "bg-slate-300",
      "text-primary",
      "text-primary-text",
      "text-destructive",
      "bg-accent",
      "bg-background",
      "text-foreground",
    ]) {
      expect(tokens).not.toContain(absent);
    }
    // The track and the thumb are the same element — the `<input type="range">`
    // — and not two different ones that happen to carry one token each.
    const slider = container.querySelector('input[type="range"]');
    const sliderTokens = (slider?.getAttribute("class") ?? "").split(/\s+/);

    expect(sliderTokens).toContain("bg-primary");
    expect(sliderTokens).toContain("accent-primary-foreground");
    expect(sliderTokens).not.toContain("accent-primary");
    expect(sliderTokens).not.toContain("bg-muted");
  });

  it("paints the package page's pickup button with the brand fill", async () => {
    profile.data = { ...PROFILE, theme: THEME };
    const { container } = render(
      <>
        <TenantBrandTheme />
        <PackageStatusPage />
      </>,
    );

    await waitFor(() => expect(brandedPrimary()).toBe(THEME.light.primary));

    const tokens = classTokens(container);

    // The only site in this child that renders a `components/ui` primitive.
    // Its `<Button>` carries no `variant`, so `buttonVariants` already emits
    // `bg-primary text-primary-foreground hover:bg-primary/90` while the
    // component's own `className` overrides it with the same three tokens after
    // migration; `cn`'s `twMerge` collapses each duplicate to one. §1i forbids
    // *deleting* the now-redundant override — that is a markup change — so it
    // stays, and the rendered result is unchanged either way.
    for (const expected of [
      "bg-card",
      "border-border",
      "bg-accent",
      "bg-muted",
      "border-input",
      "text-primary",
      "text-foreground",
      "text-muted-foreground",
      "text-gray-700",
      "bg-primary",
      "text-primary-foreground",
      "hover:bg-primary/90",
    ]) {
      expect(tokens).toContain(expected);
    }
    for (const absent of [
      "text-primary-text",
      "text-destructive",
      "bg-background",
      "hover:bg-accent",
    ]) {
      expect(tokens).not.toContain(absent);
    }
  });
});
