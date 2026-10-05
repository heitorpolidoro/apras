import { render, screen, fireEvent, within, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { MemoryRouter } from "react-router-dom";
import Navbar from "../components/Navbar";
import { SidebarProvider } from "../context/SidebarContext";
import * as AuthHook from "../context/AuthContext";
import { useTenantProfile } from "../../../hooks/useTenantProfile";
import { tenantLogoUrl } from "../../../api/publicBranding";
import type { TenantProfile } from "../../../api/tenantProfile";
import type { User } from "../../../types/auth";
import { classTokens } from "../../../test/classTokens";

// APRAS-110. `TenantHeaderLogo` is asserted through the real `Navbar`, because
// every criterion below is scoped to `screen.getByRole("banner")` — the
// `<header>` `Navbar` renders. Rendering the component bare would need a
// hand-built `<header>` and would stop proving that `Navbar` mounts it at all.
//
// Navbar's other data hooks are mocked for the same reason the sibling Navbar
// files mock them: this tree carries no `QueryClientProvider`.
vi.mock("../context/SimulationContext", () => ({
  useSimulation: vi.fn(() => ({
    simulatedRole: null,
    simulatedRoleIds: [],
    isSimulating: false,
    setSimulatedRole: vi.fn(),
    setSimulatedRoleIds: vi.fn(),
    stopSimulation: vi.fn(),
  })),
}));

vi.mock("../../../hooks/useRoles", () => ({
  useRoles: vi.fn(() => ({ data: [] })),
}));

vi.mock("../../../hooks/usePermissionQueries", () => ({
  useMyPermissions: vi.fn(() => ({
    data: { permissions: [] },
    isPending: false,
    isError: false,
  })),
  usePermissionCatalogue: vi.fn(() => ({ data: [], isPending: false })),
}));

vi.mock("../../../hooks/useTenantProfile", () => ({
  useTenantProfile: vi.fn(() => ({
    data: undefined,
    isPending: true,
    isError: false,
  })),
}));

/** The profile fixture the expected results name, by slug. */
const profile = (slug: string, name: string): TenantProfile => ({
  id: `tenant-${slug}`,
  name,
  slug,
  is_active: true,
  // Storage truth, deliberately *not* the display URL: a regression to
  // rendering `logo_url` verbatim fails the `src` assertions below.
  logo_url: `/static/uploads/${slug}.png`,
  brand_theme: null,
  theme: null,
});

const VILA_NOVA = profile("vila-nova", "Residencial Vila Nova");
const PARQUE_AZUL = profile("parque-azul", "Residencial Parque Azul");

type ProfileAnswer = {
  data: TenantProfile | undefined;
  isPending?: boolean;
  isError?: boolean;
};

const answerProfile = (answer: ProfileAnswer) => {
  vi.mocked(useTenantProfile).mockReturnValue({
    isPending: false,
    isError: false,
    ...answer,
  } as unknown as ReturnType<typeof useTenantProfile>);
};

const withLogo = (p: TenantProfile) => answerProfile({ data: p });
const withoutLogo = () =>
  answerProfile({ data: { ...VILA_NOVA, logo_url: null } });

const USER = {
  id: "1",
  email: "resident@example.com",
  full_name: "Resident User",
  is_superuser: false,
  roles: [],
  is_active: true,
} as unknown as User;

/**
 * The tree under test. `dark` wraps it in a `.dark` **ancestor**: the project
 * declares `@custom-variant dark (&:is(.dark *))`, so the class has to sit
 * above the component, and no code in `src` ever applies it.
 */
const navbarTree = (dark: boolean) => {
  const chrome = (
    <MemoryRouter initialEntries={["/dashboard"]}>
      <SidebarProvider>
        <Navbar />
      </SidebarProvider>
    </MemoryRouter>
  );
  return dark ? <div className="dark">{chrome}</div> : chrome;
};

const renderNavbar = ({ dark = false }: { dark?: boolean } = {}) =>
  render(navbarTree(dark));

const banner = () => within(screen.getByRole("banner"));

beforeEach(() => {
  localStorage.clear();
  vi.spyOn(AuthHook, "useAuth").mockReturnValue({
    isAuthenticated: true,
    isLoading: false,
    user: USER,
    login: vi.fn() as never,
    logout: vi.fn(),
  });
  answerProfile({ data: undefined, isPending: true });
});

afterEach(() => {
  vi.useRealTimers();
});

describe("TenantHeaderLogo — state 1, the configured logo", () => {
  it("renders the acting condominium's logo from the public logo route", () => {
    withLogo(VILA_NOVA);
    renderNavbar();

    const img = banner().getByRole("img");
    expect(img).toHaveAttribute("src", tenantLogoUrl("vila-nova"));
    expect(img).toHaveAttribute("alt", "Residencial Vila Nova");
  });

  it("names the link after the condominium and keeps one link in the banner", () => {
    withLogo(VILA_NOVA);
    renderNavbar();

    const link = screen.getByRole("link", { name: "Residencial Vila Nova" });
    expect(link).toHaveAttribute("href", "/");

    // Scoped on purpose: `Navbar` renders `Sidebar` as a sibling, so an
    // unscoped `getAllByRole("link")` would count the Sidebar's links.
    const links = banner().getAllByRole("link");
    expect(links).toHaveLength(1);
    expect(links[0]).toBe(link);
  });

  it("gives the image exactly the four layout tokens and nothing else", () => {
    withLogo(VILA_NOVA);
    renderNavbar();

    expect(classTokens(banner().getByRole("img")).sort()).toEqual([
      "h-7",
      "max-w-32",
      "object-contain",
      "w-auto",
    ]);
  });

  it("leaves the image's tokens untouched in the dark scheme", () => {
    withLogo(VILA_NOVA);
    renderNavbar({ dark: true });

    expect(classTokens(banner().getByRole("img")).sort()).toEqual([
      "h-7",
      "max-w-32",
      "object-contain",
      "w-auto",
    ]);
  });
});

describe("TenantHeaderLogo — states 2, 3 and 4, the fallback mark", () => {
  it("shows the fallback and keeps the appName name when no logo is configured", () => {
    withoutLogo();
    renderNavbar();

    expect(banner().queryByRole("img")).toBeNull();
    expect(screen.getByTestId("tenant-header-fallback")).toBeInTheDocument();
    // Scoped to the banner: `Sidebar` is a sibling and carries its own
    // appName-named link, so the unscoped query matches two elements.
    expect(banner().getByRole("link", { name: "APRAS" })).toBe(
      screen.getByTestId("tenant-header-fallback"),
    );
  });

  it("shows the fallback with no spinner and no skeleton while the profile is pending", () => {
    answerProfile({ data: undefined, isPending: true });
    renderNavbar();

    expect(banner().queryByRole("img")).toBeNull();
    expect(screen.getByTestId("tenant-header-fallback")).toBeInTheDocument();
    expect(screen.queryByRole("status")).toBeNull();
    expect(screen.queryByRole("progressbar")).toBeNull();
  });

  it("shows the fallback when the profile read failed", () => {
    answerProfile({ data: undefined, isError: true });
    renderNavbar();

    expect(banner().queryByRole("img")).toBeNull();
    expect(screen.getByTestId("tenant-header-fallback")).toBeInTheDocument();
  });
});

describe("TenantHeaderLogo — state 5, the latch", () => {
  it("suppresses the image and shows the fallback once the bytes fail", () => {
    withLogo(VILA_NOVA);
    renderNavbar();

    fireEvent.error(banner().getByRole("img"));

    expect(banner().queryByRole("img")).toBeNull();
    expect(screen.getByTestId("tenant-header-fallback")).toBeInTheDocument();
  });

  it("recovers by itself once, 60 s after the failure, and then stops", () => {
    vi.useFakeTimers();
    withLogo(VILA_NOVA);
    renderNavbar();

    fireEvent.error(banner().getByRole("img"));
    expect(banner().queryByRole("img")).toBeNull();

    // Each advance is wrapped in `act`: `fireEvent` wraps its own dispatch but
    // `advanceTimersByTime` does not, and under React 19 the timer's
    // `setState` is scheduled rather than flushed.
    act(() => {
      vi.advanceTimersByTime(59_000);
    });
    expect(banner().queryByRole("img")).toBeNull();

    act(() => {
      vi.advanceTimersByTime(2_000);
    });
    const retried = banner().getByRole("img");
    expect(retried).toHaveAttribute("src", tenantLogoUrl("vila-nova"));
    expect(screen.queryByTestId("tenant-header-fallback")).toBeNull();

    fireEvent.error(retried);
    act(() => {
      vi.advanceTimersByTime(120_000);
    });
    expect(banner().queryByRole("img")).toBeNull();
    expect(screen.getByTestId("tenant-header-fallback")).toBeInTheDocument();
  });

  it("replaces the element on a slug change, so a late error cannot latch the new condominium", () => {
    withLogo(VILA_NOVA);
    const { rerender } = renderNavbar();

    const first = banner().getByRole("img");

    withLogo(PARQUE_AZUL);
    rerender(navbarTree(false));

    const second = banner().getByRole("img");
    expect(second).not.toBe(first);
    expect(second).toHaveAttribute("src", tenantLogoUrl("parque-azul"));

    fireEvent.error(first);

    expect(banner().getByRole("img")).toHaveAttribute(
      "src",
      tenantLogoUrl("parque-azul"),
    );
    expect(screen.queryByTestId("tenant-header-fallback")).toBeNull();
  });
});

describe("TenantHeaderLogo — the card behind the logo", () => {
  const PLATE_TOKENS = [
    "dark:bg-foreground",
    "inline-flex",
    "items-center",
    "px-1",
    "rounded-md",
  ];

  it("wraps the image in a card whose only paint token is dark:-gated, in both schemes", () => {
    withLogo(VILA_NOVA);

    const light = renderNavbar();
    const lightPlate = screen.getByTestId("tenant-header-logo-plate");
    expect(banner().getByRole("img").parentElement).toBe(lightPlate);
    const lightTokens = classTokens(lightPlate).sort();
    expect(lightTokens).toEqual(PLATE_TOKENS);
    light.unmount();

    renderNavbar({ dark: true });
    const darkPlate = screen.getByTestId("tenant-header-logo-plate");
    expect(banner().getByRole("img").parentElement).toBe(darkPlate);
    const darkTokens = classTokens(darkPlate).sort();
    expect(darkTokens).toEqual(PLATE_TOKENS);

    // The same array in both renders: a JavaScript branch on the scheme, or an
    // unconditional paint token, produces two different lists.
    expect(darkTokens).toEqual(lightTokens);
  });

  it("renders no card when no logo is configured", () => {
    withoutLogo();
    renderNavbar();

    expect(screen.queryByTestId("tenant-header-logo-plate")).toBeNull();
  });

  it("renders no card while the profile is pending", () => {
    answerProfile({ data: undefined, isPending: true });
    renderNavbar();

    expect(screen.queryByTestId("tenant-header-logo-plate")).toBeNull();
  });

  it("renders no card when the profile read failed", () => {
    answerProfile({ data: undefined, isError: true });
    renderNavbar();

    expect(screen.queryByTestId("tenant-header-logo-plate")).toBeNull();
  });

  it("renders no card once the bytes fail, including in the dark scheme", () => {
    withLogo(VILA_NOVA);
    const light = renderNavbar();
    fireEvent.error(banner().getByRole("img"));
    expect(screen.queryByTestId("tenant-header-logo-plate")).toBeNull();
    light.unmount();

    renderNavbar({ dark: true });
    fireEvent.error(banner().getByRole("img"));
    expect(screen.queryByTestId("tenant-header-logo-plate")).toBeNull();
  });
});

describe("TenantHeaderLogo — the three-way md:hidden rule", () => {
  it("does not hide the logo on desktop", () => {
    withLogo(VILA_NOVA);
    renderNavbar();

    const link = screen.getByRole("link", { name: "Residencial Vila Nova" });
    expect(classTokens(link)).not.toContain("md:hidden");
  });

  it("hides the fallback on desktop when there is no logo to show", () => {
    withoutLogo();
    renderNavbar();

    expect(
      classTokens(screen.getByTestId("tenant-header-fallback")),
    ).toContain("md:hidden");
  });

  it("keeps the fallback on desktop when a promised logo's bytes failed", () => {
    withLogo(VILA_NOVA);
    renderNavbar();

    fireEvent.error(banner().getByRole("img"));

    expect(
      classTokens(screen.getByTestId("tenant-header-fallback")),
    ).not.toContain("md:hidden");
  });
});
