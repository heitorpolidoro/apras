import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter } from "react-router-dom";
import Navbar from "../components/Navbar";
import { SidebarProvider } from "../context/SidebarContext";
import * as AuthHook from "../context/AuthContext";
import { useRoles } from "../../../hooks/useRoles";
import { useMyPermissions } from "../../../hooks/usePermissionQueries";
import {
  PERMISSIONS_BY_ROLE,
  settledPermissions,
} from "../../../test/permissionFixtures";

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

beforeEach(() => {
  vi.mocked(useMyPermissions).mockImplementation(
    () =>
      settledPermissions(
        (AuthHook.useAuth().user?.roles ?? []).flatMap(
          (item) => PERMISSIONS_BY_ROLE[item.name] ?? [],
        ),
      ) as never,
  );
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

  it("applies active class to dashboard link when on /dashboard", () => {
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

    const tarefasLink = screen.getByText("Tarefas");
    expect(tarefasLink.className).toContain("text-primary");
  });

  it("applies active class to admin link when on /admin/users", () => {
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
      <MemoryRouter initialEntries={["/admin/users"]}>
        <Navbar />
      </MemoryRouter>,
    );

    const adminLink = screen.getByText("Administração");
    expect(adminLink.className).toContain("text-primary");
  });

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

  it("applies active class to categories link when on /categories", () => {
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
      <MemoryRouter initialEntries={["/categories"]}>
        <Navbar />
      </MemoryRouter>,
    );

    const link = screen.getByText("Categorias");
    expect(link.className).toContain("text-primary");
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

  it("fires language change when a language button is clicked", () => {
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
      <MemoryRouter>
        <Navbar />
      </MemoryRouter>,
    );

    fireEvent.click(screen.getByText("PT"));
    expect(screen.getByText("Tarefas")).toBeInTheDocument();
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

  it("renders hamburger toggle button on mobile and desktop collapse button", () => {
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

    // Desktop collapse toggle buttons (both in Navbar header and Sidebar brand header)
    const desktopToggles = screen.getAllByRole("button", { name: "Recolher menu" });
    expect(desktopToggles.length).toBeGreaterThanOrEqual(1);

    // Clicking desktop toggle updates its state across buttons
    fireEvent.click(desktopToggles[0]);
    expect(screen.getAllByRole("button", { name: "Expandir menu" }).length).toBeGreaterThanOrEqual(1);
  });
});
