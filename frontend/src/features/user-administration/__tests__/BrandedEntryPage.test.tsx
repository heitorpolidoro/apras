import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import BrandedEntryPage from "../pages/BrandedEntryPage";
import apiClient from "../../../api/client";
import { useAuth } from "../context/AuthContext";
import { useTenant } from "../context/useTenant";
import type { Tenant } from "../../../types/auth";
import type { DerivedTheme } from "../../../api/tenantProfile";

/**
 * `/c/:slug` — the branded entry point (APRAS-74 D2, D3, D5, D6).
 *
 * The file is organised around the two properties that are security
 * statements rather than conveniences:
 *
 * * **The readiness gate.** A branded link is opened by direct navigation, so
 *   on mount `useAuth().isLoading` is `true` and the membership list is empty
 *   for *everybody*. Resolving then would show a legitimate member the
 *   anonymous login and then the no-access panel. Both loading states are
 *   driven explicitly here.
 * * **No timing oracle** (D6). `slug → id` is a pure array lookup over the
 *   switcher's own option list, so an unknown slug and a known slug the
 *   visitor does not belong to run the same code with the same I/O — asserted
 *   by counting the requests, not by reading the source.
 */

vi.mock("../../../api/client", () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    interceptors: {
      request: { use: vi.fn(), eject: vi.fn() },
      response: { use: vi.fn(), eject: vi.fn() },
    },
  },
}));

vi.mock("../context/AuthContext", () => ({
  useAuth: vi.fn(),
  AuthProvider: ({ children }: { children: React.ReactNode }) => children,
}));

vi.mock("../context/useTenant", async () => {
  const actual =
    await vi.importActual<typeof import("../context/useTenant")>(
      "../context/useTenant",
    );
  return { ...actual, useTenant: vi.fn() };
});

const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual =
    await vi.importActual<typeof import("react-router-dom")>(
      "react-router-dom",
    );
  return { ...actual, useNavigate: () => mockNavigate };
});

const MINE: Tenant = {
  id: "11111111-1111-1111-1111-111111111111",
  name: "Condomínio Altos da Serra",
  slug: "altos-da-serra",
  is_active: true,
  created_at: "2026-01-01T00:00:00",
};

const THEME: DerivedTheme = {
  light: { primary: "oklch(0.56 0.14 262.00)" },
  dark: { primary: "oklch(0.68 0.14 262.00)" },
};

const BRANDING = {
  slug: "altos-da-serra",
  name: "Condomínio Altos da Serra",
  logo_url: "/static/uploads/altos.png",
  theme: null as DerivedTheme | null,
};

const mockLogin = vi.fn();
const mockLogout = vi.fn();
const mockSetActingTenant = vi.fn();

const asMock = (fn: unknown) => fn as unknown as ReturnType<typeof vi.fn>;

const setAuth = (over: Partial<ReturnType<typeof useAuth>> = {}) => {
  asMock(useAuth).mockReturnValue({
    user: null,
    isAuthenticated: false,
    isLoading: false,
    login: mockLogin,
    logout: mockLogout,
    ...over,
  });
};

const setTenants = (over: Partial<ReturnType<typeof useTenant>> = {}) => {
  asMock(useTenant).mockReturnValue({
    tenants: [],
    actingTenantId: null,
    actingTenant: null,
    isActingTenantAdmin: false,
    isLoading: false,
    setActingTenant: mockSetActingTenant,
    ...over,
  });
};

const renderAt = (slug: string) =>
  render(
    <MemoryRouter initialEntries={[`/c/${slug}`]}>
      <Routes>
        <Route path="/c/:slug" element={<BrandedEntryPage />} />
      </Routes>
    </MemoryRouter>,
  );

/** Every `GET` the page issued, by URL. */
const requestedUrls = () =>
  asMock(apiClient.get).mock.calls.map((call) => call[0] as string);

describe("BrandedEntryPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    asMock(apiClient.get).mockResolvedValue({ data: { ...BRANDING } });
    setAuth();
    setTenants();
  });

  afterEach(() => {
    document.getElementById("public-brand-theme")?.remove();
  });

  // -------------------------------------------------------------------
  // Anonymous: the branded login
  // -------------------------------------------------------------------

  it("renders the branded login with the condominium's name and logo, and no redirect", async () => {
    renderAt("altos-da-serra");

    expect(
      await screen.findByRole("heading", { name: "Condomínio Altos da Serra" }),
    ).toBeInTheDocument();
    expect(screen.getByAltText("Condomínio Altos da Serra")).toHaveAttribute(
      "src",
      "/static/uploads/altos.png",
    );
    expect(screen.getByLabelText(/E-mail/i)).toBeInTheDocument();
    expect(mockNavigate).not.toHaveBeenCalled();
    expect(requestedUrls()).toEqual([
      "/public/tenants/altos-da-serra/branding",
    ]);
  });

  it("submits the branded form through AuthContext.login", async () => {
    asMock(apiClient.post).mockResolvedValue({
      data: { access_token: "branded-token" },
    });

    renderAt("altos-da-serra");
    await screen.findByLabelText(/E-mail/i);

    fireEvent.change(screen.getByLabelText(/E-mail/i), {
      target: { value: "morador@example.com" },
    });
    fireEvent.change(screen.getByLabelText(/Senha/i), {
      target: { value: "pass" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Entrar/i }));

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith(
        "/auth/login?remember_me=false",
        expect.any(FormData),
        expect.any(Object),
      );
    });
    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith("branded-token", false);
    });
  });

  it("falls back to the unbranded form when the branding read 404s", async () => {
    asMock(apiClient.get).mockRejectedValue({ response: { status: 404 } });

    renderAt("condominio-inexistente");

    expect(await screen.findByLabelText(/E-mail/i)).toBeInTheDocument();
    expect(screen.queryByText(/não tem acesso/i)).toBeNull();
  });

  // -------------------------------------------------------------------
  // The readiness gate
  // -------------------------------------------------------------------

  it("shows only the spinner while /auth/me is still in flight, for a member", async () => {
    setAuth({ isLoading: true });

    const { container } = renderAt("altos-da-serra");

    await waitFor(() => {
      expect(container.querySelector(".animate-spin")).not.toBeNull();
    });
    expect(screen.queryByLabelText(/E-mail/i)).toBeNull();
    expect(screen.queryByText(/não tem acesso/i)).toBeNull();
    expect(mockSetActingTenant).not.toHaveBeenCalled();
    expect(mockNavigate).not.toHaveBeenCalled();
  });

  it("shows only the spinner while GET /tenants is still in flight, then switches once it resolves", async () => {
    setAuth({ isAuthenticated: true });
    setTenants({ isLoading: true, tenants: [] });

    const { container, rerender } = renderAt("altos-da-serra");

    expect(container.querySelector(".animate-spin")).not.toBeNull();
    expect(screen.queryByLabelText(/E-mail/i)).toBeNull();
    expect(screen.queryByText(/não tem acesso/i)).toBeNull();

    setTenants({ isLoading: false, tenants: [MINE] });
    rerender(
      <MemoryRouter initialEntries={["/c/altos-da-serra"]}>
        <Routes>
          <Route path="/c/:slug" element={<BrandedEntryPage />} />
        </Routes>
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(mockSetActingTenant).toHaveBeenCalledWith(MINE.id);
    });
    expect(mockNavigate).toHaveBeenCalledWith("/", { replace: true });
  });

  it.each([
    ["a known slug the visitor does not belong to", "vila-das-flores"],
    ["a slug no condominium carries", "condominio-inexistente"],
  ])(
    "renders the identical spinner before resolution for %s",
    async (_label, slug) => {
      setAuth({ isAuthenticated: true });
      setTenants({ isLoading: true, tenants: [] });

      const { container } = renderAt(slug);

      expect(container.querySelector(".animate-spin")).not.toBeNull();
      expect(screen.queryByText(/não tem acesso/i)).toBeNull();
      expect(screen.queryByLabelText(/E-mail/i)).toBeNull();
    },
  );

  // -------------------------------------------------------------------
  // Signed in: the switch
  // -------------------------------------------------------------------

  it("switches a signed-in member into the condominium and navigates home", async () => {
    setAuth({ isAuthenticated: true });
    setTenants({ tenants: [MINE], actingTenantId: "other-id" });

    renderAt("altos-da-serra");

    await waitFor(() => {
      expect(mockSetActingTenant).toHaveBeenCalledWith(MINE.id);
    });
    expect(mockSetActingTenant).toHaveBeenCalledTimes(1);
    expect(mockNavigate).toHaveBeenCalledWith("/", { replace: true });
  });

  it("navigates without switching when the slug is already the acting tenant", async () => {
    setAuth({ isAuthenticated: true });
    setTenants({ tenants: [MINE], actingTenantId: MINE.id });

    renderAt("altos-da-serra");

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith("/", { replace: true });
    });
    expect(mockSetActingTenant).not.toHaveBeenCalled();
  });

  // -------------------------------------------------------------------
  // Signed in: no access — one component, one code path, no I/O
  // -------------------------------------------------------------------

  it.each([
    ["a known slug the visitor does not belong to", "vila-das-flores"],
    ["a slug no condominium carries", "condominio-inexistente"],
  ])("renders the same no-access panel for %s", async (_label, slug) => {
    setAuth({ isAuthenticated: true });
    setTenants({ tenants: [MINE], actingTenantId: MINE.id });

    renderAt(slug);

    expect(
      await screen.findByText("Você não tem acesso a este condomínio"),
    ).toBeInTheDocument();
    expect(mockNavigate).not.toHaveBeenCalled();
    expect(mockSetActingTenant).not.toHaveBeenCalled();
    // The only request either branch makes is the branding read, which does
    // not feed the decision: the resolution itself is an array lookup.
    expect(requestedUrls()).toEqual([`/public/tenants/${slug}/branding`]);
  });

  it("renders byte-identical markup for the unknown slug and the not-a-member branch, before and after resolution", async () => {
    // D6 stated as an equality rather than as two look-alike assertions: the
    // two branches must be *indistinguishable*, so the proof is that the DOM
    // one produces equals the DOM the other produces — spinner and panel
    // alike — in a single test that holds both renders at once.
    const UNKNOWN = "condominio-inexistente";
    const NOT_MINE = "vila-das-flores";

    // Before resolution: the gate, symmetric across both branches.
    setAuth({ isAuthenticated: true });
    setTenants({ isLoading: true, tenants: [] });

    const gated = renderAt(NOT_MINE);
    const gatedNotMine = gated.container.innerHTML;
    gated.unmount();

    const gatedUnknownRender = renderAt(UNKNOWN);
    const gatedUnknown = gatedUnknownRender.container.innerHTML;
    gatedUnknownRender.unmount();

    expect(gatedNotMine).toEqual(gatedUnknown);
    expect(gatedNotMine).toContain("animate-spin");

    // After resolution: the panel, symmetric across both branches.
    setTenants({ tenants: [MINE], actingTenantId: MINE.id });

    const settled = renderAt(NOT_MINE);
    await screen.findByText("Você não tem acesso a este condomínio");
    const panelNotMine = settled.container.innerHTML;
    settled.unmount();

    const settledUnknown = renderAt(UNKNOWN);
    await screen.findByText("Você não tem acesso a este condomínio");
    const panelUnknown = settledUnknown.container.innerHTML;
    settledUnknown.unmount();

    expect(panelNotMine).toEqual(panelUnknown);
    // Neither branch leaks the slug it was asked about into the markup.
    expect(panelNotMine).not.toContain(NOT_MINE);
    expect(panelUnknown).not.toContain(UNKNOWN);
  });

  it("offers 'meus condomínios' only when the visitor has a membership, and always 'Sair'", async () => {
    setAuth({ isAuthenticated: true });
    setTenants({ tenants: [MINE], actingTenantId: MINE.id });

    renderAt("vila-das-flores");
    await screen.findByText("Você não tem acesso a este condomínio");

    fireEvent.click(
      screen.getByRole("button", { name: "Ir para os meus condomínios" }),
    );
    expect(mockNavigate).toHaveBeenCalledWith("/");

    fireEvent.click(screen.getByRole("button", { name: "Sair" }));
    expect(mockLogout).toHaveBeenCalled();
  });

  it("hides 'meus condomínios' for a signed-in visitor with no membership at all", async () => {
    setAuth({ isAuthenticated: true });
    setTenants({ tenants: [] });

    renderAt("vila-das-flores");
    await screen.findByText("Você não tem acesso a este condomínio");

    expect(
      screen.queryByRole("button", { name: "Ir para os meus condomínios" }),
    ).toBeNull();
    expect(screen.getByRole("button", { name: "Sair" })).toBeInTheDocument();
  });

  // -------------------------------------------------------------------
  // The theme (APRAS-68's, injected under this page's own id)
  // -------------------------------------------------------------------

  it("injects no #public-brand-theme element when the condominium has no colours", async () => {
    renderAt("altos-da-serra");
    await screen.findByLabelText(/E-mail/i);

    expect(document.getElementById("public-brand-theme")).toBeNull();
  });

  it("injects exactly one #public-brand-theme element for a themed condominium and removes it on unmount", async () => {
    asMock(apiClient.get).mockResolvedValue({
      data: { ...BRANDING, theme: THEME },
    });

    const { unmount } = renderAt("altos-da-serra");
    await screen.findByLabelText(/E-mail/i);

    await waitFor(() => {
      expect(document.getElementById("public-brand-theme")).not.toBeNull();
    });
    expect(
      document.querySelectorAll("#public-brand-theme, style#public-brand-theme")
        .length,
    ).toBe(1);
    expect(document.getElementById("tenant-brand-theme")).toBeNull();

    unmount();
    expect(document.getElementById("public-brand-theme")).toBeNull();
  });

  it("injects nothing for a signed-in visitor, so the two injectors never fight", async () => {
    asMock(apiClient.get).mockResolvedValue({
      data: { ...BRANDING, theme: THEME },
    });
    setAuth({ isAuthenticated: true });
    setTenants({ tenants: [MINE], actingTenantId: MINE.id });

    renderAt("vila-das-flores");
    await screen.findByText("Você não tem acesso a este condomínio");

    expect(document.getElementById("public-brand-theme")).toBeNull();
  });
});
