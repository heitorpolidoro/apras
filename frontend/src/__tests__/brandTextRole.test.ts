/// <reference types="node" />
// @vitest-environment node
//
// The characters / graphical-object guard for bare `text-primary` (APRAS-87).
//
// `--primary` is a *surface* colour: as normal text it measures 3.3091:1 on
// `--background` and never reaches WCAG 2.1 AA on any light surface. APRAS-88
// added `--primary-text` and published, in §1k of
// `docs/frontend/theme-token-mapping.md`, the single question that routes a
// brand class: **does this element paint glyphs of text?** Characters take
// `text-primary-text` at a 4.5:1 floor; a graphical object keeps
// `text-primary` at the 3:1 floor of SC 1.4.11.
//
// This task applied that question to the bare `text-primary` call sites that
// predate the rule. This file is what stops the distinction rotting, in two
// halves:
//
//   (a) a **set equivalence** between the bare `text-primary` occurrences in
//       the tree and `GRAPHICAL_PRIMARY_SITES` below — every occurrence is
//       declared, every declaration is still matched by an occurrence. A
//       character site that regresses to `text-primary` therefore fails here,
//       named by its file, and a new graphical site fails until it is declared;
//   (b) the measurement of both tokens on every surface the character sites
//       sit on, by **importing** `src/lib/contrast.ts` — the repository's one
//       contrast implementation. Nothing here reimplements its arithmetic.
//
// Two deliberate omissions, both load-bearing:
//
//   * **No tree-wide total is asserted.** A sibling of APRAS-77 migrating a
//     `text-indigo-*` icon to `text-primary` creates a new graphical site; it
//     appends one entry and this guard stays green. The floor — that the
//     graphical sites already declared keep their bare token — is what the set
//     equivalence protects, and a sibling can only add to the set, because the
//     sibling grammar matches *palette* classes and never a bare token class.
//   * **Entries carry no line numbers.** A sibling editing an unrelated line of
//     the same file would otherwise shift them and turn a correct tree red.
//
// The node environment is what makes `import.meta.url` a `file:` URL, exactly
// as `src/__tests__/brandTextOpacity.test.ts` needs it to be.
import { readFileSync, readdirSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

import {
  compositeOver,
  contrastRatio,
  oklchToHex,
  parseOklch,
  MINIMUM_CONTRAST_RATIO,
  type Oklch,
} from "../lib/contrast";

/** Every ratio below is published to four decimals; assert to ±0.001. */
const DECIMALS = 3;

const HERE = path.dirname(fileURLToPath(import.meta.url));
const FRONTEND_ROOT = path.resolve(HERE, "..", "..");
const SRC_ROOT = path.join(FRONTEND_ROOT, "src");

// --- the grammar -----------------------------------------------------------

/**
 * A **bare** `text-primary` class, with or without a variant prefix.
 *
 * The boundaries are the whole point: `-` is excluded on both sides, so
 * `text-primary-text`, `text-primary-foreground` and `bg-primary/10` are not
 * matches, while `group-hover:text-primary` and `hover:text-primary` are —
 * `:` is not a word character, so the lookbehind admits the variant.
 *
 * Built fresh on every call because a `g` regex carries `lastIndex`.
 */
export const barePrimaryTextGrammar = (): RegExp =>
  new RegExp(String.raw`(?<![\w-])text-primary(?![\w-])`, "g");

// --- the sweep -------------------------------------------------------------

const isSwept = (name: string): boolean =>
  /\.tsx?$/.test(name) && !/\.test\.tsx?$/.test(name);

/** Every swept source file under `src/`, excluding `__tests__/` directories. */
const sourceFiles = (directory: string = SRC_ROOT): string[] => {
  const found: string[] = [];
  for (const entry of readdirSync(directory, { withFileTypes: true })) {
    const full = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      if (entry.name !== "__tests__") {
        found.push(...sourceFiles(full));
      }
      continue;
    }
    if (isSwept(entry.name)) {
      found.push(full);
    }
  }
  return found;
};

/** How many bare `text-primary` occurrences each swept file carries today. */
const occurrencesByFile = (): Map<string, number> => {
  const counts = new Map<string, number>();
  for (const file of sourceFiles()) {
    const matches = readFileSync(file, "utf8").match(barePrimaryTextGrammar());
    if (matches !== null && matches.length > 0) {
      counts.set(path.relative(SRC_ROOT, file).split(path.sep).join("/"), matches.length);
    }
  }
  return counts;
};

// --- the declaration -------------------------------------------------------

/** One element that paints no glyphs and therefore keeps `text-primary`. */
export interface GraphicalPrimarySite {
  /** Path under `frontend/src/`. Never a line number — see the header. */
  file: string;
  /** What the element is, precisely enough to find it by reading the file. */
  element: string;
  /** Why §1k classifies it as a graphical object. */
  why: string;
}

/** §1k's answer for a self-closing icon component: it renders no characters. */
const ICON_ONLY = "a self-closing icon component with no children — renders no glyphs";
/** §1k's answer for a wrapper whose only children are icons. */
const ICON_WRAPPER = "its only child is an icon component — renders no glyphs";
/** §1k's answer for a form control. */
const FORM_CONTROL = "a native form control — the class tints the box, not any text";

/**
 * Every bare `text-primary` occurrence in the tree, declared as graphical.
 *
 * One entry per occurrence. A file appears as many times as it carries
 * occurrences; the guard below compares the per-file counts in both
 * directions, so an undeclared occurrence and an unmatched declaration both
 * fail, and neither side may assert a total.
 */
export const GRAPHICAL_PRIMARY_SITES: readonly GraphicalPrimarySite[] = [
  {
    file: "components/ui/alert-modal.tsx",
    element: "the `info` variant `iconClass`, applied to the `<Info />` component",
    why: ICON_ONLY,
  },
  {
    file: "features/dashboard/components/GeneralDashboardPage.tsx",
    element: "the `<Building />` in the acting-tenant chip",
    why: ICON_ONLY,
  },
  {
    file: "features/document-management/components/DocumentCenterPage.tsx",
    element: "the `<FileText />` in the page-header `bg-accent` tile",
    why: ICON_ONLY,
  },
  {
    file: "features/document-management/components/DocumentCenterPage.tsx",
    element: "the `<FolderPlus />` icon inside the new-folder button",
    why: ICON_ONLY,
  },
  {
    file: "features/document-management/components/DocumentGridTable.tsx",
    element: "the `<FileText />` icon in the document-name cell",
    why: ICON_ONLY,
  },
  {
    file: "features/document-management/components/DocumentGridTable.tsx",
    element: "the preview `<button>` (`hover:text-primary`)",
    why: ICON_WRAPPER,
  },
  {
    file: "features/document-management/components/DocumentGridTable.tsx",
    element: "the new-version `<button>` (`hover:text-primary`)",
    why: ICON_WRAPPER,
  },
  {
    file: "features/document-management/components/DocumentUploadModal.tsx",
    element: "the `<FileUp />` in the upload modal header",
    why: ICON_ONLY,
  },
  {
    file: "features/document-management/components/FolderFormModal.tsx",
    element: "the `<FolderPlus />` modal-title icon",
    why: ICON_ONLY,
  },
  {
    file: "features/document-management/components/FolderFormModal.tsx",
    element: "the allowed-role `<input type=\"checkbox\">`",
    why: FORM_CONTROL,
  },
  {
    file: "features/document-management/components/FolderTreeSidebar.tsx",
    element: "the `<FolderOpen />` of a selected or open tree node",
    why: ICON_ONLY,
  },
  {
    file: "features/document-management/components/FolderTreeSidebar.tsx",
    element: "the new-subfolder `<button>` (`hover:text-primary`)",
    why: ICON_WRAPPER,
  },
  {
    file: "features/document-management/components/FolderTreeSidebar.tsx",
    element: "the edit-folder `<button>` (`hover:text-primary`)",
    why: ICON_WRAPPER,
  },
  {
    file: "features/document-management/components/FolderTreeSidebar.tsx",
    element: "the `<FolderIcon />` of the all-documents row",
    why: ICON_ONLY,
  },
  {
    file: "features/document-management/components/PDFViewerModal.tsx",
    element: "the `<FileText />` in the PDF viewer header",
    why: ICON_ONLY,
  },
  {
    file: "features/lot-management/components/LinkUserAccountModal.tsx",
    element: "the account-choice `<input type=\"radio\">`",
    why: FORM_CONTROL,
  },
  {
    file: "features/lot-management/components/ResidentTable.tsx",
    element: "the `<LinkIcon />` inside the link-user action `<Button>`",
    why: ICON_ONLY,
  },
  {
    file: "features/occurrence-management/components/NewOccurrenceModal.tsx",
    element: "the `<Plus />` modal-title icon",
    why: ICON_ONLY,
  },
  {
    file: "features/occurrence-management/components/NewOccurrenceModal.tsx",
    element: "the anonymity `<input type=\"checkbox\">`",
    why: FORM_CONTROL,
  },
  {
    file: "features/occurrence-management/components/NewOccurrenceModal.tsx",
    element: "the `<Eye />` in the anonymity label, shown when not anonymous",
    why: ICON_ONLY,
  },
  {
    file: "features/occurrence-management/components/NewOccurrenceModal.tsx",
    element: "the public-visibility `<input type=\"checkbox\">`",
    why: FORM_CONTROL,
  },
  {
    file: "features/occurrence-management/components/OccurrenceBookPage.tsx",
    element: "the page-header icon tile wrapping `<BookOpen />`",
    why: ICON_WRAPPER,
  },
  {
    file: "features/occurrence-management/components/OccurrenceBookPage.tsx",
    element: "the `<Filter />` icon in the filter bar",
    why: ICON_ONLY,
  },
  {
    file: "features/occurrence-management/components/OccurrenceDetailsView.tsx",
    element: "the `<AlertCircle />` in the management-controls `<h3>`",
    why: ICON_ONLY,
  },
  {
    file: "features/occurrence-management/components/OccurrenceTimelineLog.tsx",
    element: "the `<MessageSquare />` in the timeline `<h3>`",
    why: ICON_ONLY,
  },
  {
    file: "features/occurrence-management/components/OccurrenceTimelineLog.tsx",
    element: "the internal-only `<input type=\"checkbox\">`",
    why: FORM_CONTROL,
  },
  {
    file: "features/public-site/pages/LandingPage.tsx",
    element: "the `<ClipboardList />` of the tasks capability card",
    why: ICON_ONLY,
  },
  {
    file: "features/public-site/pages/LandingPage.tsx",
    element: "the `<ShieldCheck />` of the access capability card",
    why: ICON_ONLY,
  },
  {
    file: "features/public-site/pages/LandingPage.tsx",
    element: "the `<AlertCircle />` of the infractions capability card",
    why: ICON_ONLY,
  },
  {
    file: "features/public-site/pages/LandingPage.tsx",
    element: "the `<HardHat />` of the finance capability card",
    why: ICON_ONLY,
  },
  {
    file: "features/public-site/pages/LandingPage.tsx",
    element: "the `<Wallet />` of the purchases capability card",
    why: ICON_ONLY,
  },
  {
    file: "features/public-site/pages/LandingPage.tsx",
    element: "the `<FileText />` of the documents capability card",
    why: ICON_ONLY,
  },
  {
    file: "features/purchase-management/components/PurchaseRequestsPage.tsx",
    element: "the per-card `<Icon />` of a summary card",
    why: ICON_ONLY,
  },
  {
    file: "features/user-administration/components/PermissionMatrix.tsx",
    element: "the per-permission `<input type=\"checkbox\">`",
    why: FORM_CONTROL,
  },
  {
    file: "features/user-administration/components/Sidebar.tsx",
    element: "the nav item's `<IconComponent />`, active branch",
    why: ICON_ONLY,
  },
  {
    file: "features/user-administration/components/Sidebar.tsx",
    element: "the Início item's `<Home />`, active branch",
    why: ICON_ONLY,
  },
  {
    file: "features/user-administration/pages/AdminUserDashboard.tsx",
    element: "the user-type `<input type=\"checkbox\">` in the edit form",
    why: FORM_CONTROL,
  },
  {
    file: "features/visitor-management/components/AuthorizationFormModal.tsx",
    element: "the `<ShieldCheck />` modal-title icon",
    why: ICON_ONLY,
  },
  {
    file: "features/visitor-management/components/AuthorizationQrModal.tsx",
    element: "the `<QrCode />` modal-title icon",
    why: ICON_ONLY,
  },
  {
    file: "features/visitor-management/components/GatekeeperDashboard.tsx",
    element: "the `<Building2 />` in the page `<h1>` title",
    why: ICON_ONLY,
  },
  {
    file: "features/visitor-management/components/GatekeeperDashboard.tsx",
    element: "the `<Users />` in the Active Visitors Counter",
    why: ICON_ONLY,
  },
  {
    file: "features/visitor-management/components/GatekeeperDashboard.tsx",
    element: "the `<Search />` in the `gatekeeper.searchVisitor` `<h2>`",
    why: ICON_ONLY,
  },
  {
    file: "features/visitor-management/components/GatekeeperDashboard.tsx",
    element: "the `<History />` in the `accessLogs.title` `<h2>`",
    why: ICON_ONLY,
  },
  {
    file: "features/visitor-management/components/GatekeeperDashboard.tsx",
    element: "the `<PackageIcon />` in the `packages.title` (\"Encomendas\") `<h2>`",
    why: ICON_ONLY,
  },
  {
    file: "features/visitor-management/components/GatekeeperDashboard.tsx",
    element: "the `<PackageIcon />` in the `packages.awaitingPickup` `<h2>`",
    why: ICON_ONLY,
  },
  {
    file: "features/visitor-management/components/QrScannerModal.tsx",
    element: "the `<ScanLine />` modal-title icon",
    why: ICON_ONLY,
  },
  {
    file: "features/visitor-management/components/VisitorAuthPage.tsx",
    element: "the `<ShieldCheck />` page-header icon",
    why: ICON_ONLY,
  },
  // APRAS-81 migrated `project-management` and `asset-management` to the
  // tokens; its ten `text-indigo-*` icon sites become graphical sites here,
  // which is the append this file's header anticipates from a sibling.
  {
    file: "features/project-management/components/ConstructionTrackerPage.tsx",
    element: "the `<HardHat />` page-header icon",
    why: ICON_ONLY,
  },
  {
    file: "features/project-management/components/ConstructionTrackerPage.tsx",
    element: "the `<RefreshCw />` spinner of the project-detail loader",
    why: ICON_ONLY,
  },
  {
    file: "features/project-management/components/ConstructionTrackerPage.tsx",
    element: "the `<RefreshCw />` spinner of the project-grid loader",
    why: ICON_ONLY,
  },
  {
    file: "features/project-management/components/MilestoneTimeline.tsx",
    element: "the `<ListOrdered />` card-header icon",
    why: ICON_ONLY,
  },
  {
    file: "features/project-management/components/MilestoneTimeline.tsx",
    element: "the edit-milestone `<button>` (`hover:text-primary`)",
    why: ICON_WRAPPER,
  },
  {
    file: "features/project-management/components/ProjectUpdateFeed.tsx",
    element: "the `<Camera />` card-header icon",
    why: ICON_ONLY,
  },
  {
    file: "features/project-management/components/ProjectSummaryCard.tsx",
    element: "the edit-project `<button>` over the cover photo (`hover:text-primary`)",
    why: ICON_WRAPPER,
  },
  {
    file: "features/asset-management/components/AssetMovementHistoryModal.tsx",
    element: "the `<Clock />` modal-title icon",
    why: ICON_ONLY,
  },
  {
    file: "features/asset-management/components/AssetSummaryCards.tsx",
    element: "the consumables tile holding the `<Archive />`",
    why: ICON_WRAPPER,
  },
  {
    file: "features/asset-management/components/AssetTable.tsx",
    element: "the movement-history `<Button>` (`hover:text-primary`)",
    why: ICON_WRAPPER,
  },
  // APRAS-83's ten new graphical sites — nine `text-indigo-*` icons and one
  // `text-emerald-600` control glyph, all migrated to the brand token by §1k's
  // question. A pure append, exactly as this file's header anticipates: a
  // sibling of APRAS-77 can only add to the set.
  {
    file: "features/finance/components/CashBalanceCard.tsx",
    element: "the `<Wallet />` inside the balance tile's `bg-accent` square",
    why: ICON_ONLY,
  },
  {
    file: "features/finance/components/CategoryTransactionDrilldown.tsx",
    element: "the view-invoice `<button>` whose only child is `<FileText />`",
    why: ICON_WRAPPER,
  },
  {
    file: "features/finance/components/FinanceDashboardPage.tsx",
    element: "the `<Wallet />` in the page-header card title",
    why: ICON_ONLY,
  },
  {
    file: "features/finance/components/InvoicePreviewModal.tsx",
    element: "the `<FileText />` in the invoice-preview modal header",
    why: ICON_ONLY,
  },
  {
    file: "features/purchase-management/components/QuoteComparisonTable.tsx",
    element: "the `<Award />` inside the choose-quote ghost `<Button>`",
    why: ICON_ONLY,
  },
  {
    file: "features/access-control/components/AccessControlPage.tsx",
    element: "the `<ScanFace />` in the page-header `<h1>`",
    why: ICON_ONLY,
  },
  {
    file: "features/access-control/components/FacialTemplateSyncPanel.tsx",
    element: "the `<ScanFace />` in the sync-panel `<h2>`",
    why: ICON_ONLY,
  },
  {
    file: "features/access-control/components/GateMonitorPage.tsx",
    element: "the `<Radio />` in the page-header `<h1>`",
    why: ICON_ONLY,
  },
  {
    file: "features/access-control/components/GateMonitorPage.tsx",
    element: "the per-device `<Icon />` in a gate chip",
    why: ICON_ONLY,
  },
  {
    file: "features/access-control/components/RegisterDeviceModal.tsx",
    element: "the `<ScanFace />` in the register-device modal header",
    why: ICON_ONLY,
  },
  // APRAS-84's nine new graphical sites — eight `text-indigo-*` icons, tiles
  // and form controls plus one `hover:` variant, all routed to the brand
  // token by §1k's question. A pure append, exactly as this file's header
  // anticipates: a sibling of APRAS-77 can only add to the set. Its two
  // *character* sites — `PhotoUploadModal`'s "Ajustar Recorte" button and
  // `FeedbackInboxTable`'s "Ver Detalhes" button, the latter an icon and a
  // label painted from one `currentColor` — take `text-primary-text` instead
  // and so are correctly absent here.
  {
    file: "features/feedback-management/components/FeedbackChannelPage.tsx",
    element: "the page-header icon tile wrapping `<MessageCircle />`",
    why: ICON_WRAPPER,
  },
  {
    file: "features/feedback-management/components/FeedbackChannelPage.tsx",
    element: "the `<Filter />` icon in the filter-bar heading",
    why: ICON_ONLY,
  },
  {
    file: "features/feedback-management/components/FeedbackHistoryList.tsx",
    element: "the trailing `<Eye />` of a history row (the only `text-indigo-500`)",
    why: ICON_ONLY,
  },
  {
    file: "features/feedback-management/components/NewFeedbackForm.tsx",
    element: "the send-anonymously `<input type=\"checkbox\">`",
    why: FORM_CONTROL,
  },
  {
    file: "features/announcement-feed/components/AnnouncementCard.tsx",
    element: "the edit-announcement `<button>` (`hover:text-primary`)",
    why: ICON_WRAPPER,
  },
  {
    file: "features/announcement-feed/components/AnnouncementFeedPage.tsx",
    element: "the page-header icon tile wrapping `<Megaphone />`",
    why: ICON_WRAPPER,
  },
  {
    file: "features/announcement-feed/components/AnnouncementFormModal.tsx",
    element: "the `<Plus />` modal-title icon",
    why: ICON_ONLY,
  },
  {
    file: "features/announcement-feed/components/AnnouncementFormModal.tsx",
    element: "the `<Paperclip />` inside the attach-media `<label>`",
    why: ICON_ONLY,
  },
  {
    file: "features/package-management/components/PackageStatusPage.tsx",
    element: "the page-header icon tile wrapping `<PackageIcon />`",
    why: ICON_WRAPPER,
  },
];

/** The declared entries, counted per file, for the equivalence below. */
const declaredByFile = (): Map<string, number> => {
  const counts = new Map<string, number>();
  for (const site of GRAPHICAL_PRIMARY_SITES) {
    counts.set(site.file, (counts.get(site.file) ?? 0) + 1);
  }
  return counts;
};

// --- the surfaces ----------------------------------------------------------

/**
 * Tailwind authors its palette with a **percentage** lightness, a form
 * `parseOklch`'s grammar rejects. Normalising the literal is not a second
 * implementation of its arithmetic — it only rewrites `96%` as `0.96`.
 */
const normalise = (value: string): string =>
  value.replace(/([\d.]+)%/, (_match, digits: string) =>
    String(Number(digits) / 100),
  );

/** The `:root` block of `src/index.css` — never `.dark`, which is unapplied. */
const ROOT = (() => {
  const css = readFileSync(path.join(SRC_ROOT, "index.css"), "utf8");
  const start = css.indexOf(":root {");
  const end = css.indexOf("\n}", start);
  return css.slice(start, end);
})();

const token = (name: string): Oklch => {
  const match = new RegExp(
    String.raw`(?<![\w-])--${name}:\s*(oklch\([^)]*\))`,
  ).exec(ROOT);
  if (match === null) {
    throw new Error(`--${name} is not declared in :root`);
  }
  const colour = parseOklch(normalise(match[1]));
  if (colour === null) {
    throw new Error(`--${name} is not a parseable oklch() value`);
  }
  return colour;
};

const PRIMARY = token("primary");
const PRIMARY_TEXT = token("primary-text");
const BACKGROUND = token("background");
const CARD = token("card");
const MUTED = token("muted");
const ACCENT = token("accent");

/**
 * `bg-muted/30` over `--background`: the auth-page shell.
 *
 * `compositeOver` is imported, never re-implemented: it is APRAS-90's single
 * home for the compositing order, so a later revision of that order reaches
 * these ratios instead of leaving them stale behind a private copy.
 */
const MUTED_30_ON_BACKGROUND = compositeOver(MUTED, BACKGROUND, 0.3);

/**
 * Every surface a character site of this task sits on, traced from the JSX
 * rather than assumed, with the `#rrggbb` the compositor paints for it.
 */
const SURFACES = [
  ["--background", BACKGROUND, "#fcfcfc", 3.3091, 5.0622],
  ["--card", CARD, "#ffffff", 3.4054, 5.2096],
  ["--muted / --accent / --secondary", MUTED, "#ecf4ef", 3.0427, 4.6547],
  [
    "bg-primary/10 over --background",
    compositeOver(PRIMARY, BACKGROUND, 0.1),
    "#e3f3ed",
    2.9691,
    4.5421,
  ],
  [
    "bg-primary/10 over --card",
    compositeOver(PRIMARY, CARD, 0.1),
    "#e6f5f0",
    3.0298,
    4.635,
  ],
  [
    "bg-muted/30 over --background",
    MUTED_30_ON_BACKGROUND,
    "#f7faf8",
    3.2408,
    4.9576,
  ],
  [
    "bg-primary/5 over bg-muted/30 over --background",
    compositeOver(PRIMARY, MUTED_30_ON_BACKGROUND, 0.05),
    "#ebf5f1",
    3.059,
    4.6796,
  ],
  [
    "bg-accent/40 over --card",
    compositeOver(ACCENT, CARD, 0.4),
    "#f7fbf9",
    3.263,
    4.9917,
  ],
] as const;

const ratio = (foreground: Oklch, background: Oklch): number =>
  Number(contrastRatio(foreground, background).toFixed(4));

// --- the guard -------------------------------------------------------------

describe("the graphical `text-primary` inventory", () => {
  it("declares every bare `text-primary` occurrence in the tree", () => {
    const undeclared: string[] = [];
    const declared = declaredByFile();
    for (const [file, count] of occurrencesByFile()) {
      const allowed = declared.get(file) ?? 0;
      if (count > allowed) {
        undeclared.push(
          `${file}: ${count} occurrence(s), ${allowed} declared — a character ` +
            "site regressed, or a new graphical site needs an entry",
        );
      }
    }
    expect(undeclared).toEqual([]);
  });

  it("keeps every declared site alive, so the list cannot go stale", () => {
    const found = occurrencesByFile();
    const stale: string[] = [];
    for (const [file, count] of declaredByFile()) {
      const alive = found.get(file) ?? 0;
      if (count > alive) {
        stale.push(
          `${file}: ${count} declared, ${alive} occurrence(s) — remove the ` +
            "entries whose sites are gone",
        );
      }
    }
    expect(stale).toEqual([]);
  });

  it("names each entry by file and element, never by line number", () => {
    for (const site of GRAPHICAL_PRIMARY_SITES) {
      expect(site.file).toMatch(/^[\w./-]+\.tsx?$/);
      expect(site.file).not.toMatch(/:\d+/);
      expect(site.element.length).toBeGreaterThan(0);
      expect(site.why.length).toBeGreaterThan(0);
    }
  });

  it("still declares the graphical sites APRAS-87 classified", () => {
    const files = new Set(GRAPHICAL_PRIMARY_SITES.map((site) => site.file));
    for (const file of [
      "components/ui/alert-modal.tsx",
      "features/visitor-management/components/GatekeeperDashboard.tsx",
      "features/visitor-management/components/VisitorAuthPage.tsx",
      "features/visitor-management/components/QrScannerModal.tsx",
      "features/visitor-management/components/AuthorizationQrModal.tsx",
      "features/visitor-management/components/AuthorizationFormModal.tsx",
      "features/lot-management/components/ResidentTable.tsx",
      "features/lot-management/components/LinkUserAccountModal.tsx",
      "features/user-administration/components/Sidebar.tsx",
      "features/user-administration/components/PermissionMatrix.tsx",
      "features/user-administration/pages/AdminUserDashboard.tsx",
      "features/dashboard/components/GeneralDashboardPage.tsx",
      "features/purchase-management/components/PurchaseRequestsPage.tsx",
    ]) {
      expect(files).toContain(file);
    }
  });
});

describe("the character sites carry the brand *text* token", () => {
  /** The files §2a of the spec moves to `text-primary-text`. */
  const CHARACTER_FILES = [
    "components/ui/alert-modal.tsx",
    "components/ui/badge.tsx",
    "components/ui/button.tsx",
    "features/lot-management/components/LotDetailsView.tsx",
    "features/user-administration/components/Navbar.tsx",
    "features/user-administration/components/Sidebar.tsx",
    "features/user-administration/components/LoginForm.tsx",
    "features/user-administration/pages/ForgotPasswordPage.tsx",
    "features/user-administration/pages/LoginPage.tsx",
    "features/user-administration/pages/SignupPage.tsx",
    "features/user-administration/pages/ResetPasswordPage.tsx",
    "features/user-administration/pages/BrandedEntryPage.tsx",
    "features/user-administration/pages/AcceptInvitationPage.tsx",
    "features/task-management/components/TaskCard.tsx",
    "features/task-management/components/TaskBoard.tsx",
    "features/task-management/components/TaskList.tsx",
    "features/task-management/components/AssigneePicker.tsx",
    "features/dashboard/components/GeneralDashboardPage.tsx",
  ];

  it.each(CHARACTER_FILES)("%s carries text-primary-text", (file) => {
    const source = readFileSync(path.join(SRC_ROOT, file), "utf8");
    expect(source).toMatch(/(?<![\w-])text-primary-text(?![\w-])/);
  });

  it("preserves the variant prefix where the original carried one", () => {
    for (const file of [
      "features/task-management/components/TaskList.tsx",
      "features/dashboard/components/GeneralDashboardPage.tsx",
    ]) {
      const source = readFileSync(path.join(SRC_ROOT, file), "utf8");
      expect(source).toContain("group-hover:text-primary-text");
    }
  });

  it("leaves both active-tab branches free of the bare token", () => {
    const source = readFileSync(
      path.join(SRC_ROOT, "features/lot-management/components/LotDetailsView.tsx"),
      "utf8",
    );
    const branches = source.match(/"border-primary text-primary-text"/g);
    expect(branches).toHaveLength(2);
    expect(source.match(barePrimaryTextGrammar())).toBeNull();
  });
});

describe("both tokens, measured on every surface the character sites sit on", () => {
  it.each(SURFACES)(
    "%s paints %#",
    (_name, surface, hex, onPrimary, onPrimaryText) => {
      // The surface is the colour the compositor holds, not an assumption.
      expect(oklchToHex(surface)).toBe(hex);
      expect(ratio(PRIMARY, surface)).toBeCloseTo(onPrimary, DECIMALS);
      expect(ratio(PRIMARY_TEXT, surface)).toBeCloseTo(
        onPrimaryText,
        DECIMALS,
      );
    },
  );

  it("clears AA with --primary-text, and fails it with --primary, everywhere", () => {
    for (const [name, surface] of SURFACES) {
      expect(
        ratio(PRIMARY_TEXT, surface),
        `--primary-text on ${name}`,
      ).toBeGreaterThanOrEqual(MINIMUM_CONTRAST_RATIO);
      expect(
        ratio(PRIMARY, surface),
        `--primary on ${name}`,
      ).toBeLessThan(MINIMUM_CONTRAST_RATIO);
    }
  });
});
