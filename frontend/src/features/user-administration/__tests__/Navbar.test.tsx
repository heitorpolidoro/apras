import { render, screen, fireEvent, within } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { useTranslation } from "react-i18next";
import Navbar from "../components/Navbar";
import { SidebarProvider } from "../context/SidebarContext";
import { useSimulation } from "../context/SimulationContext";
import * as AuthHook from "../context/AuthContext";
import type { User } from "../../../types/auth";
import { useRoles } from "../../../hooks/useRoles";
import { useMyPermissions } from "../../../hooks/usePermissionQueries";
import {
  PERMISSIONS_BY_ROLE,
  settledPermissions,
} from "../../../test/permissionFixtures";
import { classTokens } from "../../../test/classTokens";

// Navbar reads the effective (possibly simulated) role via
// useEffectiveIdentity, which combines useAuth (spied on per-test below) with
// useSimulation. Keep simulation permanently inactive so the admin-link
// visibility assertions keep reflecting the real user's role exactly like
// before this hook existed.
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

// SimulationControls (rendered only for a caller holding `roles:update`)
// fetches the tenant's roles; avoid a real network call in tests. The menus
// themselves derive from `/permissions/me`, not from this list.
vi.mock("../../../hooks/useRoles", () => ({
  useRoles: vi.fn(() => ({
    data: [{ id: "type-1", name: "Test Type" }],
  })),
}));

// IAM F4: every link is decided by `useCanShowMenu` over `/permissions/me`.
// The mock derives the payload from whatever role the per-test `useAuth` spy
// is returning, so each case below keeps stating its scenario in one place —
// the user fixture — and no case has to repeat its own permission list.
vi.mock("../../../hooks/usePermissionQueries", () => ({
  useMyPermissions: vi.fn(),
  usePermissionCatalogue: vi.fn(() => ({ data: [], isPending: false })),
}));

// APRAS-91. `vitest.config.ts` sets neither `restoreMocks` nor `clearMocks`, so
// a per-test override of either module mock below would leak into every later
// case in this file. Capture both implementations once, here, and restore them
// in `afterEach`.
//
// The `useTranslation` implementation captured here is the repository-wide one
// from `src/test/setup.ts`; every per-test stub spreads it so that `t` keeps
// working. The real `Sidebar` is in the tree (deliberately not mocked) and
// calls `useTranslation().t`, so a stub that returned only `i18n` would crash
// the render rather than assert anything.
const setupUseTranslation = vi.mocked(useTranslation).getMockImplementation();
const setupUseSimulation = vi.mocked(useSimulation).getMockImplementation();

/**
 * Override `useTranslation`'s `i18n` for one test, keeping setup's `t`.
 *
 * Setup's factory builds a **fresh** `changeLanguage` spy on every call, so a
 * call-count assertion is only possible against a stub that owns its own spy.
 */
const stubI18n = (i18nOverrides: {
  language: string;
  resolvedLanguage?: string;
  changeLanguage?: (code: string) => unknown;
}) => {
  const base = setupUseTranslation?.();
  vi.mocked(useTranslation).mockImplementation(
    () =>
      ({
        ...base,
        i18n: { ...base?.i18n, ...i18nOverrides },
      }) as unknown as ReturnType<typeof useTranslation>,
  );
};

/**
 * Render `<Navbar />` for a user fixture and return a `within` scope bound to
 * the tree's only `banner` — `Navbar.tsx`'s own `<header>`.
 *
 * Scoping every new assertion this way is what makes it structurally incapable
 * of the APRAS-87 failure: an element rendered by `Sidebar` cannot satisfy a
 * `within(header)` query, whatever its text.
 */
const renderBanner = (user: User, route = "/dashboard") => {
  vi.spyOn(AuthHook, "useAuth").mockReturnValue({
    isAuthenticated: true,
    isLoading: false,
    user,
    login: vi.fn() as never,
    logout: vi.fn(),
  });

  render(
    <MemoryRouter initialEntries={[route]}>
      <SidebarProvider>
        <Navbar />
      </SidebarProvider>
    </MemoryRouter>,
  );

  return within(screen.getByRole("banner"));
};

const directorUser = (): User =>
  ({
    id: "1",
    email: "director@example.com",
    full_name: "Director User",
    is_superuser: false,
    roles: [{ id: "profile-director", name: "DIRECTOR" }],
    is_active: true,
  }) as unknown as User;

beforeEach(() => {
  // `SidebarProvider` seeds `isCollapsed` from `apras_sidebar_collapsed`, and
  // other cases in this file click `Recolher menu`, which writes `"true"`.
  // Without this clear the header-margin case would pass or fail by test order.
  localStorage.clear();
  vi.mocked(useMyPermissions).mockImplementation(
    () =>
      settledPermissions(
        (AuthHook.useAuth().user?.roles ?? []).flatMap(
          (item) => PERMISSIONS_BY_ROLE[item.name] ?? [],
        ),
      ) as never,
  );
});

afterEach(() => {
  if (setupUseTranslation) {
    vi.mocked(useTranslation).mockImplementation(setupUseTranslation);
  }
  if (setupUseSimulation) {
    vi.mocked(useSimulation).mockImplementation(setupUseSimulation);
  }
});

describe("Navbar", () => {
  it("renders nothing when not authenticated", () => {
    vi.spyOn(AuthHook, "useAuth").mockReturnValue({
      isAuthenticated: false,
      isLoading: false,
      user: null,
      login: vi.fn() as any,
      logout: vi.fn(),
    });

    const { container } = render(
      <MemoryRouter>
        <Navbar />
      </MemoryRouter>,
    );

    expect(container.firstChild).toBeNull();
  });

  it("renders navbar with brand and basic links when authenticated as DIRECTOR", () => {
    vi.spyOn(AuthHook, "useAuth").mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      user: {
        id: "1",

        email: "test@example.com",
        full_name: "Test User",
        is_superuser: false,
        roles: [{ id: "profile-director", name: "DIRECTOR" }, { id: "type-1", name: "Test Type" }],
        is_active: true,
      } as any,
      login: vi.fn() as any,
      logout: vi.fn(),
    });

    render(
      <MemoryRouter initialEntries={["/dashboard"]}>
        <Navbar />
      </MemoryRouter>,
    );

    expect(screen.getByText("APRAS")).toBeDefined();
    expect(screen.getByText("Tarefas")).toBeDefined();
    expect(screen.getByText("Sair")).toBeDefined();
    expect(screen.getByText(/Test User/)).toBeDefined();
    expect(screen.queryByText("Administração")).toBeNull();
  });

  it("renders admin link when user is ADMINISTRATOR", () => {
    vi.spyOn(AuthHook, "useAuth").mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      user: {
        id: "1",

        email: "admin@example.com",
        full_name: "Admin User",
        is_superuser: true,
        roles: [{ id: "profile-administrator", name: "ADMINISTRATOR" }],
        is_active: true,
      },
      login: vi.fn() as any,
      logout: vi.fn(),
    });

    render(
      <MemoryRouter initialEntries={["/dashboard"]}>
        <Navbar />
      </MemoryRouter>,
    );

    expect(screen.getByText("Administração")).toBeDefined();
  });

  // APRAS-91: the three Sidebar active-highlight assertions that used to sit
  // here are gone. The `/tasks` one duplicated `Sidebar.test.tsx`'s
  // "highlights the active link with text-primary-text"; the `/categories` and
  // `/admin/users` ones moved to `Sidebar.test.tsx`, which is where a reader
  // looks for Sidebar's active highlight. Navbar's own active markup is
  // covered by the banner-scoped cases at the end of this file.

  it("calls logout when Sair button is clicked", () => {
    const mockLogout = vi.fn();
    vi.spyOn(AuthHook, "useAuth").mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      user: {
        id: "1",

        email: "test@example.com",
        full_name: "Test User",
        is_superuser: false,
        roles: [{ id: "profile-director", name: "DIRECTOR" }],
        is_active: true,
      },
      login: vi.fn() as any,
      logout: mockLogout,
    });

    render(
      <MemoryRouter>
        <Navbar />
      </MemoryRouter>,
    );

    fireEvent.click(screen.getByText("Sair"));
    expect(mockLogout).toHaveBeenCalledOnce();
  });

  it("renders role name when user has a role label", () => {
    vi.spyOn(AuthHook, "useAuth").mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      user: {
        id: "1",

        email: "test@example.com",
        full_name: "Test User",
        is_superuser: false,
        roles: [{ id: "profile-director", name: "DIRECTOR" }, { name: "Gerente" }],
        is_active: true,
      } as any,
      login: vi.fn() as any,
      logout: vi.fn(),
    });

    render(
      <MemoryRouter>
        <Navbar />
      </MemoryRouter>,
    );

    // The badge joins **every** role name (§8.2), not a single enum label.
    expect(screen.getByText("DIRECTOR, Gerente")).toBeInTheDocument();
  });

  it("renders 'Administrador global' when user is superuser", () => {
    vi.spyOn(AuthHook, "useAuth").mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      user: {
        id: "1",
        email: "heitor.polidoro@gmail.com",
        full_name: "Heitor Polidoro",
        is_superuser: true,
        roles: [{ id: "role-admin", name: "Administrador (papel)" }],
        is_active: true,
      } as unknown as User,
      login: vi.fn(),
      logout: vi.fn(),
    });

    render(
      <MemoryRouter>
        <Navbar />
      </MemoryRouter>,
    );

    expect(screen.getByText("Administrador global")).toBeInTheDocument();
  });

  it("renders 'Administrador global (Morador)' when superuser has another tenant role", () => {
    vi.spyOn(AuthHook, "useAuth").mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      user: {
        id: "1",
        email: "heitor.polidoro@gmail.com",
        full_name: "Heitor Polidoro",
        is_superuser: true,
        roles: [{ id: "role-resident", name: "Morador (papel)" }],
        is_active: true,
      } as unknown as User,
      login: vi.fn(),
      logout: vi.fn(),
    });

    render(
      <MemoryRouter>
        <Navbar />
      </MemoryRouter>,
    );

    expect(screen.getByText("Administrador global (Morador)")).toBeInTheDocument();
  });

  it("strips (papel) suffix from role names for regular users", () => {
    vi.spyOn(AuthHook, "useAuth").mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      user: {
        id: "2",
        email: "resident@example.com",
        full_name: "Resident User",
        is_superuser: false,
        roles: [{ id: "role-resident", name: "Morador (papel)" }],
        is_active: true,
      } as unknown as User,
      login: vi.fn(),
      logout: vi.fn(),
    });

    render(
      <MemoryRouter>
        <Navbar />
      </MemoryRouter>,
    );

    expect(screen.getByText("Morador")).toBeInTheDocument();
    expect(screen.queryByText("Morador (papel)")).toBeNull();
  });

  it("renders the simulation toggle for a real ADMINISTRATOR", () => {
    vi.spyOn(AuthHook, "useAuth").mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      user: {
        id: "1",
        email: "admin@example.com",
        full_name: "Admin User",
        is_superuser: true,
        roles: [{ id: "profile-administrator", name: "ADMINISTRATOR" }],
        is_active: true,
      },
      login: vi.fn() as any,
      logout: vi.fn(),
    });

    render(
      <MemoryRouter initialEntries={["/dashboard"]}>
        <Navbar />
      </MemoryRouter>,
    );

    expect(screen.getByText("Simular")).toBeInTheDocument();
  });

  it("does not render the simulation toggle for a non-administrator", () => {
    vi.spyOn(AuthHook, "useAuth").mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      user: {
        id: "1",
        email: "director@example.com",
        full_name: "Director User",
        is_superuser: false,
        roles: [{ id: "profile-director", name: "DIRECTOR" }],
        is_active: true,
      },
      login: vi.fn() as any,
      logout: vi.fn(),
    });

    render(
      <MemoryRouter initialEntries={["/dashboard"]}>
        <Navbar />
      </MemoryRouter>,
    );

    expect(screen.queryByText("Simular")).not.toBeInTheDocument();
  });

  it("renders contact-info link when user is ADMINISTRATOR", () => {
    vi.spyOn(AuthHook, "useAuth").mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      user: {
        id: "1",
        email: "admin@example.com",
        full_name: "Admin User",
        is_superuser: true,
        roles: [{ id: "profile-administrator", name: "ADMINISTRATOR" }],
        is_active: true,
      },
      login: vi.fn() as any,
      logout: vi.fn(),
    });

    render(
      <MemoryRouter initialEntries={["/dashboard"]}>
        <Navbar />
      </MemoryRouter>,
    );

    expect(screen.getByText("Informações de Contato")).toBeDefined();
  });

  it("renders contact-info link when user is MANAGER", () => {
    vi.spyOn(AuthHook, "useAuth").mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      user: {
        id: "1",
        email: "manager@example.com",
        full_name: "Manager User",
        is_superuser: false,
        roles: [{ id: "profile-manager", name: "MANAGER" }],
        is_active: true,
      },
      login: vi.fn() as any,
      logout: vi.fn(),
    });

    render(
      <MemoryRouter initialEntries={["/dashboard"]}>
        <Navbar />
      </MemoryRouter>,
    );

    expect(screen.getByText("Informações de Contato")).toBeDefined();
  });

  it("hides contact-info link when user is DIRECTOR", () => {
    vi.spyOn(AuthHook, "useAuth").mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      user: {
        id: "1",
        email: "director@example.com",
        full_name: "Director User",
        is_superuser: false,
        roles: [{ id: "profile-director", name: "DIRECTOR" }],
        is_active: true,
      },
      login: vi.fn() as any,
      logout: vi.fn(),
    });

    render(
      <MemoryRouter initialEntries={["/dashboard"]}>
        <Navbar />
      </MemoryRouter>,
    );

    expect(screen.queryByText("Informações de Contato")).toBeNull();
  });

  it("hides contact-info link when user is GUEST", () => {
    vi.spyOn(AuthHook, "useAuth").mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      user: {
        id: "1",
        email: "guest@example.com",
        full_name: "Guest User",
        is_superuser: false,
        roles: [{ id: "profile-guest", name: "GUEST" }],
        is_active: true,
      },
      login: vi.fn() as any,
      logout: vi.fn(),
    });

    render(
      <MemoryRouter initialEntries={["/dashboard"]}>
        <Navbar />
      </MemoryRouter>,
    );

    expect(screen.queryByText("Informações de Contato")).toBeNull();
  });

  // ── Role-gated Tarefas/Categorias links (APRAS-8) ───────────────────

  it("shows Tarefas and Categorias to a DIRECTOR, gate or no gate (§4.2)", () => {
    vi.spyOn(AuthHook, "useAuth").mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      user: {
        id: "1",
        email: "director@example.com",
        full_name: "Director User",
        is_superuser: false,
        roles: [{ id: "profile-director", name: "DIRECTOR" }],
        is_active: true,
      },
      login: vi.fn() as any,
      logout: vi.fn(),
    });

    render(
      <MemoryRouter initialEntries={["/dashboard"]}>
        <Navbar />
      </MemoryRouter>,
    );

    // **The frontend twin of §4.2's widening.** This case asserted the
    // opposite while `useMenuAccess` ANDed `allowed_menus` on top of the
    // permission: a DIRECTOR belonging to no menu-granting role saw neither
    // link, even though the bundle carried `tasks:read` and the backend
    // would have answered 403 on the way in. IAM F5 deleted the gate from
    // all 12 handlers, so the menu and the API agree by construction.
    expect(screen.getByText("Tarefas")).toBeInTheDocument();
    expect(screen.getByText("Categorias")).toBeInTheDocument();
  });

  it("hides Tarefas and Categorias from a caller whose bundle grants neither", () => {
    vi.spyOn(AuthHook, "useAuth").mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      user: {
        id: "1",
        email: "director@example.com",
        full_name: "Director User",
        is_superuser: false,
        roles: [{ id: "type-2", name: "No Access Type" }],
        is_active: true,
      } as any,
      login: vi.fn() as any,
      logout: vi.fn(),
    });
    vi.mocked(useRoles).mockReturnValue({
      data: [{ id: "type-2", name: "No Access Type" }],
    } as any); // skipcq: JS-0323
    vi.mocked(useMyPermissions).mockReturnValue(
      settledPermissions([]) as never,
    );

    render(
      <MemoryRouter initialEntries={["/dashboard"]}>
        <Navbar />
      </MemoryRouter>,
    );

    expect(screen.queryByText("Tarefas")).toBeNull();
    expect(screen.queryByText("Categorias")).toBeNull();
  });

  it("shows only Tarefas when the role grants tasks but not categories", () => {
    vi.spyOn(AuthHook, "useAuth").mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      user: {
        id: "1",
        email: "director@example.com",
        full_name: "Director User",
        is_superuser: false,
        roles: [{ id: "type-3", name: "Tasks Only" }],
        is_active: true,
      } as any,
      login: vi.fn() as any,
      logout: vi.fn(),
    });
    vi.mocked(useRoles).mockReturnValue({
      data: [{ id: "type-3", name: "Tasks Only" }],
    } as any); // skipcq: JS-0323
    // The role's *bundle* is what decides now, not a menu key.
    vi.mocked(useMyPermissions).mockReturnValue(
      settledPermissions(["tasks:read"]) as never,
    );

    render(
      <MemoryRouter initialEntries={["/dashboard"]}>
        <Navbar />
      </MemoryRouter>,
    );

    expect(screen.getByText("Tarefas")).toBeInTheDocument();
    expect(screen.queryByText("Categorias")).toBeNull();
  });

  // ── PORTEIRO scoping (APRAS-12) ─────────────────────────────────────────

  it("shows PORTEIRO the links its permissions allow and no administration", () => {
    vi.spyOn(AuthHook, "useAuth").mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      user: {
        id: "1",
        email: "porteiro@example.com",
        full_name: "Porteiro User",
        is_superuser: false,
        roles: [{ id: "profile-porteiro", name: "PORTEIRO" }],
        is_active: true,
      } as any,
      login: vi.fn() as any,
      logout: vi.fn(),
    });
    vi.mocked(useRoles).mockReturnValue({ data: [] } as any); // skipcq: JS-0323

    render(
      <MemoryRouter initialEntries={["/gate"]}>
        <Navbar />
      </MemoryRouter>,
    );

    expect(screen.getByText("APRAS")).toBeDefined();
    expect(screen.getByText(/nav\.gate|Portaria/)).toBeInTheDocument();
    // §4.2's widening, third and last sighting: PORTEIRO genuinely holds
    // `tasks:read` and `categories:read`, and the `allowed_menus` gate that
    // hid the two links in front of those permissions is gone. The backend
    // has always answered 200 on both — `parity_matrix_baseline.json` says
    // so — and the menu now says the same thing.
    expect(screen.getByText("Tarefas")).toBeInTheDocument();
    expect(screen.getByText("Categorias")).toBeInTheDocument();
    // §5.2 accepted widenings: PORTEIRO genuinely holds `lots:read`,
    // `packages:queue_read` and `reservations:read`, so the backend has always
    // answered these three 200. The link now says so.
    expect(screen.getByText("Lotes")).toBeInTheDocument();
    expect(screen.getByText(/nav\.packages|Encomendas/)).toBeInTheDocument();
    expect(screen.getByText(/nav\.reservations|Reservas/)).toBeInTheDocument();
    expect(screen.queryByText(/nav\.authorizations|Autorizações/)).toBeNull();
    expect(screen.queryByText(/nav\.occurrences|Ocorrências/)).toBeNull();
    expect(screen.queryByText(/nav\.documents|Documentos/)).toBeNull();
    expect(screen.queryByText(/projects\.navItem|Obras/)).toBeNull();
    expect(screen.queryByText(/nav\.announcements|Comunicados/)).toBeNull();
    expect(screen.queryByText(/nav\.finance|Financeiro/)).toBeNull();
    expect(screen.queryByText("Informações de Contato")).toBeNull();
    expect(screen.queryByText("Administração")).toBeNull();
    expect(screen.queryByText(/nav\.photoApprovals|Aprovações de Fotos/)).toBeNull();
    expect(screen.queryByText(/nav\.accessControl|Controle de Acesso/)).toBeNull();
    expect(screen.queryByText(/nav\.gateMonitor|Monitor da Portaria/)).toBeNull();
  });

  it("shows Tarefas and Categorias for ADMINISTRATOR even with no Role", () => {
    vi.spyOn(AuthHook, "useAuth").mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      user: {
        id: "1",
        email: "admin@example.com",
        full_name: "Admin User",
        is_superuser: true,
        roles: [{ id: "profile-administrator", name: "ADMINISTRATOR" }],
        is_active: true,
      },
      login: vi.fn() as any,
      logout: vi.fn(),
    });
    vi.mocked(useRoles).mockReturnValue({ data: [] } as any); // skipcq: JS-0323

    render(
      <MemoryRouter initialEntries={["/dashboard"]}>
        <Navbar />
      </MemoryRouter>,
    );

    expect(screen.getByText("Tarefas")).toBeInTheDocument();
    expect(screen.getByText("Categorias")).toBeInTheDocument();
  });

  it("renders hamburger toggle button on mobile and desktop collapse button in sidebar", () => {
    vi.spyOn(AuthHook, "useAuth").mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      user: {
        id: "1",
        email: "director@example.com",
        full_name: "Director User",
        is_superuser: false,
        roles: [{ id: "profile-director", name: "DIRECTOR" }],
        is_active: true,
      },
      login: vi.fn() as never,
      logout: vi.fn(),
    });

    render(
      <MemoryRouter initialEntries={["/dashboard"]}>
        <SidebarProvider>
          <Navbar />
        </SidebarProvider>
      </MemoryRouter>,
    );

    // Mobile hamburger menu toggle button
    const mobileToggle = screen.getByRole("button", { name: "Abrir menu" });
    expect(mobileToggle).toBeInTheDocument();

    // Desktop collapse toggle button inside Sidebar
    const desktopToggle = screen.getByRole("button", { name: "Recolher menu" });
    expect(desktopToggle).toBeInTheDocument();

    // Clicking desktop toggle updates its state
    fireEvent.click(desktopToggle);
    expect(screen.getByRole("button", { name: "Expandir menu" })).toBeInTheDocument();
  });

  it("renders simulated role label under username when in simulation mode", () => {
    vi.spyOn(AuthHook, "useAuth").mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      user: {
        id: "1",
        email: "admin@example.com",
        full_name: "Admin User",
        is_superuser: true,
        roles: [{ id: "profile-admin", name: "ADMINISTRATOR" }],
        is_active: true,
      },
      login: vi.fn() as never,
      logout: vi.fn(),
    });

    vi.mocked(useSimulation).mockReturnValue({
      simulatedRoleIds: ["role-porteiro"],
      isSimulating: true,
      setSimulatedRoleIds: vi.fn(),
      stopSimulation: vi.fn(),
    });

    vi.mocked(useRoles).mockReturnValue({
      data: [{ id: "role-porteiro", name: "Porteiro" }],
    } as any);

    render(
      <MemoryRouter initialEntries={["/"]}>
        <SidebarProvider>
          <Navbar />
        </SidebarProvider>
      </MemoryRouter>,
    );

    expect(screen.getByText("Admin User")).toBeInTheDocument();
    expect(screen.getByText("Admin global como Porteiro")).toBeInTheDocument();
  });

  // ── Navbar's own state-driven markup (APRAS-91) ──────────────────────────
  //
  // Everything below resolves its element from `within(screen.getByRole(
  // "banner"))` — `Navbar.tsx`'s `<header>` is the only `banner` in the tree,
  // because `Sidebar` renders an `<aside>` and a plain `<div>` drawer. `Sidebar`
  // is deliberately left unmocked: the header's `md:ml-*` margin only exists
  // because the real `Sidebar` and the real `SidebarProvider` are both present.
  describe("own markup, scoped to the banner", () => {
    it("marks PT active and EN inactive with the default fixture", () => {
      // `src/test/setup.ts` supplies `language: "pt"` and **no**
      // `resolvedLanguage`, so this case also exercises the `??` fallback.
      const banner = renderBanner(directorUser());

      const pt = banner.getByRole("button", { name: "PT" });
      const en = banner.getByRole("button", { name: "EN" });

      expect(classTokens(pt)).toContain("bg-primary");
      expect(classTokens(pt)).toContain("text-primary-foreground");
      expect(classTokens(en)).toContain("text-muted-foreground");
      expect(classTokens(en)).not.toContain("bg-primary");
      expect(classTokens(en)).not.toContain("text-primary-foreground");
    });

    it("marks EN active from resolvedLanguage even while language is still pt", () => {
      // Pins `resolvedLanguage`'s precedence over `language`: the two disagree
      // here, and the markup must follow `resolvedLanguage`.
      stubI18n({ language: "pt", resolvedLanguage: "en" });

      const banner = renderBanner(directorUser());

      const pt = banner.getByRole("button", { name: "PT" });
      const en = banner.getByRole("button", { name: "EN" });

      expect(classTokens(en)).toContain("bg-primary");
      expect(classTokens(en)).toContain("text-primary-foreground");
      expect(classTokens(pt)).toContain("text-muted-foreground");
      expect(classTokens(pt)).not.toContain("bg-primary");
      expect(classTokens(pt)).not.toContain("text-primary-foreground");
    });

    it("treats the regional tag pt-BR as PT active", () => {
      stubI18n({ language: "pt", resolvedLanguage: "pt-BR" });

      const banner = renderBanner(directorUser());

      expect(classTokens(banner.getByRole("button", { name: "PT" }))).toContain(
        "bg-primary",
      );
      expect(
        classTokens(banner.getByRole("button", { name: "EN" })),
      ).toContain("text-muted-foreground");
    });

    it("calls changeLanguage exactly once with 'en' when EN is clicked", () => {
      const changeLanguage = vi.fn();
      stubI18n({ language: "pt", changeLanguage });

      const banner = renderBanner(directorUser());

      fireEvent.click(banner.getByRole("button", { name: "EN" }));

      expect(changeLanguage).toHaveBeenCalledTimes(1);
      expect(changeLanguage).toHaveBeenCalledWith("en");
    });

    // ── The language buttons' programmatic state (APRAS-97) ───────────────
    //
    // The colour pair above is one channel; `aria-pressed` is the second, and
    // both must be fed by the single `currentLang.startsWith(lang.code)`
    // evaluation inside the `LANGUAGES.map` callback. Each case below asserts
    // the attribute on **both** buttons, because an `aria-pressed="true"`
    // hard-coded on one or on both satisfies any single-button assertion.
    // Three of them also re-assert the colour pair on the same two elements,
    // so a divergence between the channels fails one case rather than going
    // unnoticed.

    it("gives both language buttons an explicit type of button", () => {
      // Banner-scoped: the mobile hamburger already carries `type="button"`
      // and would otherwise satisfy this without the language buttons.
      const banner = renderBanner(directorUser());

      expect(banner.getByRole("button", { name: "PT" })).toHaveAttribute(
        "type",
        "button",
      );
      expect(banner.getByRole("button", { name: "EN" })).toHaveAttribute(
        "type",
        "button",
      );
    });

    it("announces PT pressed and EN not pressed with the default fixture", () => {
      // `src/test/setup.ts` supplies `language: "pt"` and no
      // `resolvedLanguage`, so this also pins the `??` fallback's result.
      const banner = renderBanner(directorUser());

      const pt = banner.getByRole("button", { name: "PT" });
      const en = banner.getByRole("button", { name: "EN" });

      expect(pt).toHaveAttribute("aria-pressed", "true");
      expect(en).toHaveAttribute("aria-pressed", "false");

      // Same two elements, other channel: colour and announcement agree.
      expect(classTokens(pt)).toContain("bg-primary");
      expect(classTokens(pt)).toContain("text-primary-foreground");
      expect(classTokens(en)).toContain("text-muted-foreground");
      expect(classTokens(en)).not.toContain("bg-primary");
    });

    it("swaps the pressed state when resolvedLanguage is en", () => {
      // Kills an `aria-pressed` read off `i18n.language` (still "pt") instead
      // of `currentLang`, and one hard-coded onto the first button.
      stubI18n({ language: "pt", resolvedLanguage: "en" });

      const banner = renderBanner(directorUser());

      const pt = banner.getByRole("button", { name: "PT" });
      const en = banner.getByRole("button", { name: "EN" });

      expect(pt).toHaveAttribute("aria-pressed", "false");
      expect(en).toHaveAttribute("aria-pressed", "true");

      expect(classTokens(en)).toContain("bg-primary");
      expect(classTokens(en)).toContain("text-primary-foreground");
      expect(classTokens(pt)).toContain("text-muted-foreground");
      expect(classTokens(pt)).not.toContain("bg-primary");
    });

    it("announces PT pressed for the regional tag pt-BR", () => {
      // Kills an `aria-pressed` derived from `currentLang === lang.code`:
      // "pt-BR" equals neither code, so both buttons would read "false" while
      // the colours still mark PT active — which the class assertions below
      // report as a disagreement between the two channels.
      stubI18n({ language: "pt", resolvedLanguage: "pt-BR" });

      const banner = renderBanner(directorUser());

      const pt = banner.getByRole("button", { name: "PT" });
      const en = banner.getByRole("button", { name: "EN" });

      expect(pt).toHaveAttribute("aria-pressed", "true");
      expect(en).toHaveAttribute("aria-pressed", "false");

      expect(classTokens(pt)).toContain("bg-primary");
      expect(classTokens(pt)).toContain("text-primary-foreground");
      expect(classTokens(en)).toContain("text-muted-foreground");
    });

    it("paints a superuser's role subtitle with the brand text token", () => {
      // Navbar's only brand-text call site. `text-primary-text`, never the bare
      // surface token and never the brand tint.
      const banner = renderBanner({
        id: "1",
        email: "admin@example.com",
        full_name: "Admin User",
        is_superuser: true,
        roles: [{ id: "role-resident", name: "Morador (papel)" }],
        is_active: true,
      } as unknown as User);

      const subtitle = banner.getByText("Administrador global (Morador)");
      expect(subtitle.tagName).toBe("SPAN");
      expect(classTokens(subtitle)).toContain("text-primary-text");
      expect(classTokens(subtitle)).not.toContain("text-primary");
      expect(classTokens(subtitle)).not.toContain("text-primary/90");
    });

    it("paints the role subtitle amber while simulating", () => {
      vi.mocked(useSimulation).mockReturnValue({
        simulatedRoleIds: ["role-porteiro"],
        isSimulating: true,
        setSimulatedRoleIds: vi.fn(),
        stopSimulation: vi.fn(),
      });
      vi.mocked(useRoles).mockReturnValue({
        data: [{ id: "role-porteiro", name: "Porteiro" }],
      } as unknown as ReturnType<typeof useRoles>);

      const banner = renderBanner({
        id: "1",
        email: "admin@example.com",
        full_name: "Admin User",
        is_superuser: true,
        roles: [{ id: "profile-administrator", name: "ADMINISTRATOR" }],
        is_active: true,
      } as unknown as User);

      const subtitle = banner.getByText("Admin global como Porteiro");
      expect(classTokens(subtitle)).toContain("text-amber-600");
      expect(classTokens(subtitle)).not.toContain("text-primary-text");
      expect(classTokens(subtitle)).not.toContain("text-primary");
    });

    it("paints a plain user's role subtitle muted and with no brand token", () => {
      // `user.roles` must be non-empty: `roleSubtitle` is `null` for a
      // non-superuser with no roles and the span is then never rendered, which
      // would make this case fail for the wrong reason.
      const banner = renderBanner({
        id: "1",
        email: "guest@example.com",
        full_name: "Guest User",
        is_superuser: false,
        roles: [{ id: "profile-guest", name: "GUEST" }],
        is_active: true,
      } as unknown as User);

      const subtitle = banner.getByText("GUEST");
      expect(classTokens(subtitle)).toContain("text-muted-foreground");
      expect(classTokens(subtitle)).not.toContain("text-amber-600");
      expect(classTokens(subtitle)).not.toContain("text-primary-text");
      expect(classTokens(subtitle)).not.toContain("text-primary");
    });

    it("tracks the sidebar width in the header's desktop margin", () => {
      // `beforeEach` clears `apras_sidebar_collapsed`, so the provider starts
      // expanded whatever a previous case left behind.
      renderBanner(directorUser());

      expect(classTokens(screen.getByRole("banner"))).toContain("md:ml-64");

      // The real Sidebar's collapse control, not a mock: this is the only way
      // the header's margin changes.
      fireEvent.click(screen.getByRole("button", { name: "Recolher menu" }));

      const collapsed = classTokens(screen.getByRole("banner"));
      expect(collapsed).toContain("md:ml-20");
      expect(collapsed).not.toContain("md:ml-64");
    });

    it("exposes exactly one link in the banner, the appName logo pointing at /", () => {
      const banner = renderBanner(directorUser());

      const links = banner.getAllByRole("link");
      expect(links).toHaveLength(1);
      expect(links[0]).toHaveAttribute("href", "/");
      expect(banner.getByRole("link", { name: "APRAS" })).toBe(links[0]);
    });
  });
});
