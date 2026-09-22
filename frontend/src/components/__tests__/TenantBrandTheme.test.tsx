import { render, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import apiClient from "../../api/client";
import type { DerivedTheme, TenantProfile } from "../../api/tenantProfile";
import TenantBrandTheme from "../TenantBrandTheme";
import {
  TENANT_BRAND_STYLE_ID,
  themeStylesheet,
} from "../../lib/brandStylesheet";
import * as AuthHook from "../../features/user-administration/context/AuthContext";

/**
 * The injector (APRAS-68 Frontend).
 *
 * The no-branding case is the one that has to be proven rather than assumed:
 * `theme: null` must leave the document **untouched**, not carry an empty
 * `<style>`. An empty element would still be a rule set with a higher
 * document order than `index.css`, and the day someone adds a fallback value
 * to it the unbranded rendering stops being today's byte for byte.
 */

vi.mock("../../api/client", () => ({
  default: { get: vi.fn(), post: vi.fn(), put: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}));

const mockedGet = vi.mocked(apiClient.get);

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

const serve = (profile: Partial<TenantProfile>) => {
  mockedGet.mockImplementation(((url: string) => {
    if (url === "/tenant-profile") {
      return Promise.resolve({ data: { ...PROFILE, ...profile } });
    }
    return Promise.resolve({ data: [] });
  }) as never);
};

const authenticate = (isAuthenticated: boolean) => {
  vi.spyOn(AuthHook, "useAuth").mockReturnValue({
    isAuthenticated,
  } as unknown as ReturnType<typeof AuthHook.useAuth>);
};

const renderInjector = () => {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const Wrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
  return render(<TenantBrandTheme />, { wrapper: Wrapper });
};

const injected = () => document.getElementById(TENANT_BRAND_STYLE_ID);

beforeEach(() => {
  vi.clearAllMocks();
  mockedGet.mockReset();
  document.getElementById(TENANT_BRAND_STYLE_ID)?.remove();
  authenticate(true);
});

describe("TenantBrandTheme", () => {
  it("injects nothing at all for a tenant with no branding", async () => {
    serve({ brand_theme: null, theme: null });

    renderInjector();

    await waitFor(() => expect(mockedGet).toHaveBeenCalled());
    // Given a tick for any effect to have run, the document is still exactly
    // what `index.css` alone produces.
    await waitFor(() => expect(injected()).toBeNull());
    expect(document.head.querySelectorAll("style").length).toBe(0);
  });

  it("does not read the profile at all while unauthenticated", async () => {
    authenticate(false);
    serve({});

    renderInjector();

    await waitFor(() => expect(injected()).toBeNull());
    expect(mockedGet).not.toHaveBeenCalled();
  });

  it("appends one style element as the last child of head", async () => {
    serve({});

    renderInjector();

    await waitFor(() => expect(injected()).not.toBeNull());
    expect(document.head.lastElementChild).toBe(injected());
    expect(document.querySelectorAll(`#${TENANT_BRAND_STYLE_ID}`).length).toBe(1);
  });

  it("writes a :root rule and a dark rule carrying primary and secondary", async () => {
    serve({});

    renderInjector();

    await waitFor(() => expect(injected()).not.toBeNull());
    const css = injected()?.textContent ?? "";

    expect(css).toContain(":root:root");
    expect(css).toContain(".dark");
    expect(css).toContain("--primary: oklch(0.55 0.06 83.88)");
    expect(css).toContain("--secondary: oklch(0.68 0.14 237.32)");
    // The dark scheme's own primary, which differs from the light one.
    expect(css).toContain("--primary: oklch(0.62 0.06 83.88)");
  });

  it("removes the element when the tenant clears its branding", async () => {
    serve({});
    const { rerender } = renderInjector();
    await waitFor(() => expect(injected()).not.toBeNull());

    serve({ brand_theme: null, theme: null });
    mockedGet.mockClear();
    // A tenant switch resets `["tenantProfile"]`, so the next render reads a
    // profile with no branding; here the same is produced by unmounting.
    rerender(<></>);

    await waitFor(() => expect(injected()).toBeNull());
  });
});

describe("themeStylesheet", () => {
  it("emits every variable of both schemes with the leading double dash", () => {
    const css = themeStylesheet(THEME);

    for (const key of Object.keys(THEME.light)) {
      expect(css).toContain(`--${key}: ${THEME.light[key]};`);
    }
    for (const key of Object.keys(THEME.dark)) {
      expect(css).toContain(`--${key}: ${THEME.dark[key]};`);
    }
  });

  it("never emits a semantic token the tenant does not own", () => {
    const css = themeStylesheet(THEME);

    expect(css).not.toContain("--destructive");
    expect(css).not.toContain("--radius");
    expect(css).not.toContain("--status-");
    expect(css).not.toContain("--priority-");
  });

  it("writes the dark rule at a specificity that beats the :root override", () => {
    // `:root:root` is (0,2,0); a bare `.dark` is (0,1,0), so a literal
    // `.dark{…}` here would be **overridden by our own light rule** and dark
    // mode would silently render the light palette. The dark selector
    // therefore carries the same doubled `:root` plus the class.
    const css = themeStylesheet(THEME);

    expect(css).toContain(":root:root.dark");
  });
});
