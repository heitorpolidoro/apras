import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import apiClient from "../../../api/client";
import pt from "../../../i18n/locales/pt.json";
import TenantProfilePage from "../pages/TenantProfilePage";
import { useSimulation } from "../context/SimulationContext";
import {
  BRAND_AUTHORED_KEYS,
  type BrandPalette,
  type DerivedTheme,
  type TenantProfile,
} from "../../../api/tenantProfile";

/**
 * The brand-colour section of the condominium profile (APRAS-68).
 *
 * Three things are pinned here and nowhere else: the **mode switch** (two
 * inputs in simple, thirteen plus the derive-dark checkbox in advanced), the
 * **client-side refusal** — a pair below 4.5:1 disables the save, measured
 * with the same function the server uses — and the **server's 422**, which
 * must render even when the client check passed, because the server is the
 * judge and the two can disagree the day the derivation changes.
 */

vi.mock("../../../api/client", () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}));

vi.mock("../context/SimulationContext", () => ({ useSimulation: vi.fn() }));

vi.mock("../../../hooks/useRoles", () => ({ useRoles: vi.fn(() => ({ data: [] })) }));

const t = (key: string): string =>
  key
    .split(".")
    .reduce<unknown>(
      (node, part) => (node as Record<string, unknown>)?.[part],
      pt,
    ) as string;

const mockedGet = vi.mocked(apiClient.get);
const mockedPatch = vi.mocked(apiClient.patch);

/** The mock's "carregar paleta legível" preset: every measured pair clears AA. */
const READABLE: BrandPalette = {
  background: "#fffdf7",
  foreground: "#1d1b16",
  card: "#ffffff",
  "card-foreground": "#1d1b16",
  primary: "#8a2b2b",
  "primary-foreground": "#fff7f5",
  secondary: "#1f6f8b",
  "secondary-foreground": "#ffffff",
  accent: "#e8ddc9",
  "accent-foreground": "#3a3128",
  muted: "#f1ece4",
  "muted-foreground": "#5c5344",
  border: "#e2d9c8",
};

const THEME: DerivedTheme = {
  light: {
    background: "oklch(0.99 0 0)",
    foreground: "oklch(0.14 0.01 83.88)",
    card: "oklch(1.00 0 0)",
    "card-foreground": "oklch(0.14 0.01 83.88)",
    popover: "oklch(1.00 0 0)",
    "popover-foreground": "oklch(0.14 0.01 83.88)",
    primary: "oklch(0.55 0.06 83.88)",
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
    primary: "oklch(0.72 0.06 83.88)",
    "primary-foreground": "oklch(0.15 0.02 83.88)",
    secondary: "oklch(0.68 0.14 237.32)",
    "secondary-foreground": "oklch(0.15 0.02 237.32)",
    accent: "oklch(0.22 0.03 237.32)",
    "accent-foreground": "oklch(0.98 0.01 237.32)",
    muted: "oklch(0.22 0.02 83.88)",
    "muted-foreground": "oklch(0.72 0.02 83.88)",
    border: "oklch(0.25 0.02 83.88)",
    input: "oklch(0.25 0.02 83.88)",
    ring: "oklch(0.72 0.06 83.88)",
  },
};

const PROFILE: TenantProfile = {
  id: "8f1c0f2e-5e5c-4a0f-9c1e-1c2a3b4d5e6f",
  name: "Residencial Altos da Serra VI",
  slug: "residencial-altos-da-serra-vi",
  is_active: true,
  logo_url: null,
  brand_theme: null,
  theme: null,
};

const serve = (profile: Partial<TenantProfile> = {}) => {
  mockedGet.mockImplementation(((url: string) => {
    if (url === "/tenant-profile") {
      return Promise.resolve({ data: { ...PROFILE, ...profile } });
    }
    return Promise.resolve({ data: [] });
  }) as never);
};

const renderPage = () => {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const Wrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
  return render(<TenantProfilePage />, { wrapper: Wrapper });
};

const hexInputs = () =>
  Array.from(
    document.querySelectorAll<HTMLInputElement>("input[data-brand-hex]"),
  );

const brandSection = async () =>
  (await screen.findByRole("region", {
    name: t("tenantProfile.brand.title"),
  })) as HTMLElement;

const switchTo = async (mode: "modeSimple" | "modeAdvanced") => {
  const user = userEvent.setup();
  await user.click(
    within(await brandSection()).getByRole("button", {
      name: t(`tenantProfile.brand.${mode}`),
    }),
  );
  return user;
};

const typeHex = async (
  user: ReturnType<typeof userEvent.setup>,
  key: string,
  value: string,
) => {
  const field = document.querySelector<HTMLInputElement>(
    `input[data-brand-hex="${key}"]`,
  ) as HTMLInputElement;
  await user.clear(field);
  await user.type(field, value);
};

beforeEach(() => {
  vi.clearAllMocks();
  mockedGet.mockReset();
  mockedPatch.mockReset();
  vi.mocked(useSimulation).mockReturnValue({
    simulatedRoleIds: [],
    isSimulating: false,
    setSimulatedRoleIds: vi.fn(),
    stopSimulation: vi.fn(),
  });
});

describe("the brand-colour section", () => {
  it("renders under the existing profile screen", async () => {
    serve();

    renderPage();

    expect(
      await screen.findByText(t("tenantProfile.brand.title")),
    ).toBeInTheDocument();
  });

  it("offers two colour inputs in simple mode", async () => {
    serve();
    renderPage();
    await brandSection();

    expect(hexInputs()).toHaveLength(2);
    expect(
      screen.queryByLabelText(t("tenantProfile.brand.deriveDark")),
    ).not.toBeInTheDocument();
  });

  it("offers the thirteen authored inputs and the derive-dark checkbox in advanced mode", async () => {
    serve();
    renderPage();
    await switchTo("modeAdvanced");

    expect(hexInputs()).toHaveLength(BRAND_AUTHORED_KEYS.length);
    expect(hexInputs()).toHaveLength(13);
    expect(
      screen.getByLabelText(t("tenantProfile.brand.deriveDark")),
    ).toBeChecked();
  });

  it("asks for a second palette once the derive-dark checkbox is cleared", async () => {
    serve();
    renderPage();
    const user = await switchTo("modeAdvanced");

    await user.click(screen.getByLabelText(t("tenantProfile.brand.deriveDark")));

    expect(hexInputs()).toHaveLength(26);
  });

  it("pre-fills the advanced inputs from the derived light scheme", async () => {
    // Nobody starts from a blank palette: switching modes carries over what
    // the server already derived, converted back to hex for the fields.
    serve({
      brand_theme: { mode: "simple", primary: "#857046", accent: "#0ea5e9" },
      theme: THEME,
    });
    renderPage();
    await switchTo("modeAdvanced");

    for (const field of hexInputs()) {
      expect(field.value).toMatch(/^#[0-9a-f]{6}$/);
    }
  });
});

describe("the live contrast panel", () => {
  it("disables the save and names the failing pair while a pair is below 4.5:1", async () => {
    serve();
    renderPage();
    const user = await switchTo("modeAdvanced");

    // Black text on a near-black background: the mock's "paleta ilegível".
    await typeHex(user, "background", "#121212");
    await typeHex(user, "foreground", "#1a1a1a");

    const section = await brandSection();
    await waitFor(() =>
      expect(
        within(section).getByRole("button", {
          name: t("tenantProfile.brand.save"),
        }),
      ).toBeDisabled(),
    );
    // The pair's own name *and* its measured ratio, in the refusal panel.
    // `foreground/background` is a substring of `muted-foreground/background`,
    // so the assertion reads the panel rather than matching a lone node.
    const refusal = within(section).getByRole("alert");
    expect(refusal.textContent).toMatch(/(^|[^-])foreground\/background — \d+\.\d\d:1/);
  });

  it("keeps the save enabled for a palette every pair of which clears AA", async () => {
    serve();
    renderPage();
    const user = await switchTo("modeAdvanced");

    for (const key of BRAND_AUTHORED_KEYS) {
      await typeHex(user, key, READABLE[key]);
    }

    const section = await brandSection();
    await waitFor(() =>
      expect(
        within(section).getByRole("button", {
          name: t("tenantProfile.brand.save"),
        }),
      ).toBeEnabled(),
    );
  });
});

describe("the writes", () => {
  it("sends the two colours as typed, leaving the server to lowercase them", async () => {
    serve();
    mockedPatch.mockResolvedValue({
      data: {
        ...PROFILE,
        brand_theme: { mode: "simple", primary: "#ffe680", accent: "#0ea5e9" },
        theme: THEME,
      },
    } as never);
    renderPage();
    const section = await brandSection();
    const user = userEvent.setup();

    await typeHex(user, "primary", "#FFE680");
    await typeHex(user, "accent", "#0EA5E9");
    await user.click(
      within(section).getByRole("button", { name: t("tenantProfile.brand.save") }),
    );

    await waitFor(() => expect(mockedPatch).toHaveBeenCalledTimes(1));
    expect(mockedPatch.mock.calls[0][0]).toBe("/tenant-profile");
    expect(mockedPatch.mock.calls[0][1]).toEqual({
      brand_theme: { mode: "simple", primary: "#FFE680", accent: "#0EA5E9" },
    });
  });

  it("sends brand_theme: null for 'voltar ao padrão'", async () => {
    serve({
      brand_theme: { mode: "simple", primary: "#857046", accent: "#0ea5e9" },
      theme: THEME,
    });
    mockedPatch.mockResolvedValue({ data: { ...PROFILE } } as never);
    renderPage();
    const section = await brandSection();
    const user = userEvent.setup();

    await user.click(
      within(section).getByRole("button", { name: t("tenantProfile.brand.reset") }),
    );

    await waitFor(() => expect(mockedPatch).toHaveBeenCalledTimes(1));
    expect(mockedPatch.mock.calls[0][1]).toEqual({ brand_theme: null });
  });

  it("renders the API's 422 failures even though the client check passed", async () => {
    // The two measurements can disagree — a client older than the server, a
    // derivation that moved. The server is the judge, and its body is shown
    // verbatim rather than replaced by a generic message.
    serve();
    mockedPatch.mockRejectedValue({
      response: {
        status: 422,
        data: {
          detail: "Estas cores não podem ser salvas: 1 combinação(ões) abaixo de 4.5:1.",
          failures: [
            {
              pair: "muted-foreground/card",
              ratio: 3.91,
              minimum: 4.5,
              scheme: "light",
            },
          ],
        },
      },
    });
    renderPage();
    const section = await brandSection();
    const user = userEvent.setup();

    await typeHex(user, "primary", "#7c3aed");
    await user.click(
      within(section).getByRole("button", { name: t("tenantProfile.brand.save") }),
    );

    expect(
      await within(section).findByText(/muted-foreground\/card/),
    ).toBeInTheDocument();
    expect(
      within(section).getByText(/muted-foreground\/card/).textContent,
    ).toContain("3.91");
  });

  it("refuses a malformed hex before sending anything", async () => {
    serve();
    renderPage();
    const section = await brandSection();
    const user = userEvent.setup();

    await typeHex(user, "primary", "#GGG");

    expect(
      within(section).getByRole("button", { name: t("tenantProfile.brand.save") }),
    ).toBeDisabled();
    expect(mockedPatch).not.toHaveBeenCalled();
  });
});

describe("a condominium that already authored a palette", () => {
  const ADVANCED = {
    mode: "advanced" as const,
    light: READABLE,
    dark: null,
  };

  it("opens in advanced mode with the stored light palette in the fields", async () => {
    serve({ brand_theme: ADVANCED, theme: THEME });

    renderPage();
    await brandSection();

    expect(hexInputs()).toHaveLength(13);
    expect(
      document.querySelector<HTMLInputElement>('input[data-brand-hex="primary"]')
        ?.value,
    ).toBe(READABLE.primary);
    expect(
      screen.getByLabelText(t("tenantProfile.brand.deriveDark")),
    ).toBeChecked();
  });

  it("opens with both palettes when a second one was stored", async () => {
    serve({
      brand_theme: { ...ADVANCED, dark: READABLE },
      theme: THEME,
    });

    renderPage();
    await brandSection();

    expect(hexInputs()).toHaveLength(26);
    expect(
      screen.getByLabelText(t("tenantProfile.brand.deriveDark")),
    ).not.toBeChecked();
  });

  it("sends the authored dark palette when the checkbox is cleared", async () => {
    serve({ brand_theme: ADVANCED, theme: THEME });
    mockedPatch.mockResolvedValue({
      data: { ...PROFILE, brand_theme: ADVANCED, theme: THEME },
    } as never);
    renderPage();
    const section = await brandSection();
    const user = userEvent.setup();

    await user.click(screen.getByLabelText(t("tenantProfile.brand.deriveDark")));
    for (const key of BRAND_AUTHORED_KEYS) {
      await typeHex(user, `dark-${key}`, READABLE[key]);
    }
    await typeHex(user, "dark-primary", "#123456");
    await user.click(
      within(section).getByRole("button", { name: t("tenantProfile.brand.save") }),
    );

    await waitFor(() => expect(mockedPatch).toHaveBeenCalledTimes(1));
    const body = mockedPatch.mock.calls[0][1] as {
      brand_theme: { dark: Record<string, string> | null };
    };
    expect(body.brand_theme.dark).not.toBeNull();
    expect(body.brand_theme.dark?.primary).toBe("#123456");
  });

  it("carries a colour picked with the native control into the request", async () => {
    serve({});
    mockedPatch.mockResolvedValue({ data: { ...PROFILE } } as never);
    renderPage();
    const section = await brandSection();
    const user = userEvent.setup();

    const picker = section.querySelector<HTMLInputElement>(
      'input[type="color"]',
    ) as HTMLInputElement;
    // jsdom has no colour-picker UI, so the change is fired the way the
    // browser fires it once one closes.
    await user.click(picker);
    fireEvent.change(picker, { target: { value: "#10b981" } });

    await waitFor(() =>
      expect(
        document.querySelector<HTMLInputElement>('input[data-brand-hex="primary"]')
          ?.value,
      ).toBe("#10b981"),
    );
  });

  it("says nothing was saved when the reset itself fails", async () => {
    serve({ brand_theme: ADVANCED, theme: THEME });
    mockedPatch.mockRejectedValue({ response: { status: 500 } });
    renderPage();
    const section = await brandSection();
    const user = userEvent.setup();

    await user.click(
      within(section).getByRole("button", { name: t("tenantProfile.brand.reset") }),
    );

    await waitFor(() => expect(mockedPatch).toHaveBeenCalledTimes(1));
    expect(
      within(section).queryByText(t("tenantProfile.brand.resetDone")),
    ).not.toBeInTheDocument();
  });

  it("announces the save and drops the draft once the server answers", async () => {
    serve({ brand_theme: ADVANCED, theme: THEME });
    mockedPatch.mockResolvedValue({
      data: { ...PROFILE, brand_theme: ADVANCED, theme: THEME },
    } as never);
    renderPage();
    const section = await brandSection();
    const user = userEvent.setup();

    await user.click(
      within(section).getByRole("button", { name: t("tenantProfile.brand.save") }),
    );

    expect(
      await within(section).findByText(t("tenantProfile.brand.saved")),
    ).toBeInTheDocument();
  });

  it("lists every measured pair of both schemes with its ratio", async () => {
    serve({ brand_theme: ADVANCED, theme: THEME });

    renderPage();
    const section = await brandSection();

    expect(
      within(section).getByText(t("tenantProfile.brand.pairsLight")),
    ).toBeInTheDocument();
    expect(
      within(section).getByText(t("tenantProfile.brand.pairsDark")),
    ).toBeInTheDocument();
    // Eight pairs per scheme, each rendered once.
    expect(section.querySelectorAll("li")).toHaveLength(16);
  });

  it("shows the emitted variables of the light scheme and no semantic token", async () => {
    serve({ brand_theme: ADVANCED, theme: THEME });

    renderPage();
    const section = await brandSection();

    const emitted = section.querySelector("pre")?.textContent ?? "";
    expect(emitted).toContain("--primary: oklch(0.55 0.06 83.88);");
    expect(emitted).toContain("--ring: oklch(0.55 0.06 83.88);");
    expect(emitted).not.toContain("--destructive");
    expect(emitted).not.toContain("--radius");
  });
});

describe("a theme the server sent that this client cannot read whole", () => {
  /** A scheme with a key missing and a key this client cannot parse — what a
   *  server older or newer than this bundle can legitimately answer. The
   *  screen must degrade to the default for the field and stay quiet about
   *  the pair, never invent a colour or a ratio. */
  const PARTIAL: DerivedTheme = {
    light: Object.fromEntries(
      Object.entries({
        ...THEME.light,
        primary: "not-an-oklch-string",
        secondary: "oklch(0.30 0.02 83.88)",
      }).filter(([key]) => key !== "muted"),
    ),
    dark: Object.fromEntries(
      Object.entries(THEME.dark).filter(([key]) => key !== "muted-foreground"),
    ),
  };

  it("falls back to the default hex for a value it cannot parse", async () => {
    serve({
      brand_theme: { mode: "simple", primary: "#857046", accent: "#0ea5e9" },
      theme: PARTIAL,
    });
    renderPage();
    await switchTo("modeAdvanced");

    for (const field of hexInputs()) {
      expect(field.value).toMatch(/^#[0-9a-f]{6}$/);
    }
  });

  it("measures only the pairs it could read, and flags the failing one", async () => {
    serve({
      brand_theme: { mode: "simple", primary: "#857046", accent: "#0ea5e9" },
      theme: PARTIAL,
    });

    renderPage();
    const section = await brandSection();

    // Light: `primary-foreground/primary` is unreadable and `muted` is
    // absent, so 6 of 8 remain. Dark: the three `muted-foreground` pairs are
    // gone, so 5 of 8 remain.
    expect(section.querySelectorAll("li")).toHaveLength(11);
    // `--secondary` at 0.30 is too dark for its near-black foreground.
    expect(section.textContent).toMatch(
      /secondary-foreground\/secondary — \d+\.\d\d:1, abaixo/,
    );
  });

  it("falls back to the generic failure list when the save fails with a 500", async () => {
    serve({
      brand_theme: { mode: "simple", primary: "#857046", accent: "#0ea5e9" },
      theme: THEME,
    });
    mockedPatch.mockRejectedValue({ response: { status: 500 } });
    renderPage();
    const section = await brandSection();
    const user = userEvent.setup();

    await user.click(
      within(section).getByRole("button", { name: t("tenantProfile.brand.save") }),
    );

    await waitFor(() => expect(mockedPatch).toHaveBeenCalledTimes(1));
    expect(
      within(section).queryByText(t("tenantProfile.brand.refusalTitle")),
    ).not.toBeInTheDocument();
    expect(
      within(section).queryByText(t("tenantProfile.brand.saved")),
    ).not.toBeInTheDocument();
  });

  it("ignores a 422 whose body carries no failures list", async () => {
    serve({
      brand_theme: { mode: "simple", primary: "#857046", accent: "#0ea5e9" },
      theme: THEME,
    });
    mockedPatch.mockRejectedValue({
      response: { status: 422, data: { detail: "'#GGG' não é uma cor válida." } },
    });
    renderPage();
    const section = await brandSection();
    const user = userEvent.setup();

    await user.click(
      within(section).getByRole("button", { name: t("tenantProfile.brand.save") }),
    );

    await waitFor(() => expect(mockedPatch).toHaveBeenCalledTimes(1));
    expect(
      within(section).queryByText(t("tenantProfile.brand.refusalTitle")),
    ).not.toBeInTheDocument();
  });
});

describe("a condominium with no colours", () => {
  it("says so rather than showing an empty measured-pairs panel", async () => {
    serve({ brand_theme: null, theme: null });

    renderPage();

    expect(
      await screen.findByText(t("tenantProfile.brand.noneBody")),
    ).toBeInTheDocument();
  });

  it("offers no 'voltar ao padrão' action, there being nothing to undo", async () => {
    serve({ brand_theme: null, theme: null });
    renderPage();
    const section = await brandSection();

    expect(
      within(section).queryByRole("button", {
        name: t("tenantProfile.brand.reset"),
      }),
    ).not.toBeInTheDocument();
  });
});
