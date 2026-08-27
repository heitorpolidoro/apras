import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";
import Navbar from "../components/Navbar";
import * as AuthHook from "../context/AuthContext";
import { UserRole } from "../context/AuthContext";
import { useUserTypes } from "../../../hooks/useUserTypes";

// Navbar reads the effective (possibly simulated) role via
// useEffectiveIdentity, which combines useAuth (spied on per-test below) with
// useSimulation. Keep simulation permanently inactive so the admin-link
// visibility assertions keep reflecting the real user's role exactly like
// before this hook existed.
vi.mock("../context/SimulationContext", () => ({
  useSimulation: vi.fn(() => ({
    simulatedRole: null,
    simulatedUserTypeIds: [],
    isSimulating: false,
    setSimulatedRole: vi.fn(),
    setSimulatedUserTypeIds: vi.fn(),
    stopSimulation: vi.fn(),
  })),
}));

// SimulationControls (rendered only for a real ADMINISTRATOR) fetches
// UserTypes; avoid a real network call in tests. Also backs useMenuAccess
// (via useEffectiveIdentity), so it includes a type granting tasks/categories
// access for the DIRECTOR fixtures below that assign it via user_types.
vi.mock("../../../hooks/useUserTypes", () => ({
  useUserTypes: vi.fn(() => ({
    data: [{ id: "type-1", name: "Test Type", allowed_menus: ["tasks", "categories"] }],
  })),
}));

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
        role: UserRole.DIRECTOR,
        is_active: true,
        user_types: [{ id: "type-1", name: "Test Type" }],
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
        role: UserRole.ADMINISTRATOR,
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
        role: UserRole.DIRECTOR,
        is_active: true,
        user_types: [{ id: "type-1", name: "Test Type" }],
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
        role: UserRole.ADMINISTRATOR,
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
        role: UserRole.DIRECTOR,
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
        role: UserRole.DIRECTOR,
        is_active: true,
        user_types: [{ id: "type-1", name: "Test Type" }],
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

  it("renders user type name when user has a type label", () => {
    vi.spyOn(AuthHook, "useAuth").mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      user: {
        id: "1",

        email: "test@example.com",
        full_name: "Test User",
        role: UserRole.DIRECTOR,
        is_active: true,
        user_types: [{ name: "Gerente" }],
      } as any,
      login: vi.fn() as any,
      logout: vi.fn(),
    });

    render(
      <MemoryRouter>
        <Navbar />
      </MemoryRouter>,
    );

    expect(screen.getByText("Gerente")).toBeInTheDocument();
  });

  it("renders the simulation toggle for a real ADMINISTRATOR", () => {
    vi.spyOn(AuthHook, "useAuth").mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      user: {
        id: "1",
        email: "admin@example.com",
        full_name: "Admin User",
        role: UserRole.ADMINISTRATOR,
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
        role: UserRole.DIRECTOR,
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
        role: UserRole.ADMINISTRATOR,
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
        role: UserRole.MANAGER,
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
        role: UserRole.DIRECTOR,
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
        role: UserRole.GUEST,
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
        role: UserRole.DIRECTOR,
        is_active: true,
        user_types: [{ id: "type-1", name: "Test Type" }],
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

  // ── UserType-gated Tarefas/Categorias links (APRAS-8) ───────────────────

  it("hides Tarefas and Categorias links for a DIRECTOR with no UserType", () => {
    vi.spyOn(AuthHook, "useAuth").mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      user: {
        id: "1",
        email: "director@example.com",
        full_name: "Director User",
        role: UserRole.DIRECTOR,
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

    expect(screen.queryByText("Tarefas")).toBeNull();
    expect(screen.queryByText("Categorias")).toBeNull();
  });

  it("hides Tarefas and Categorias links when the assigned UserType grants neither", () => {
    vi.spyOn(AuthHook, "useAuth").mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      user: {
        id: "1",
        email: "director@example.com",
        full_name: "Director User",
        role: UserRole.DIRECTOR,
        is_active: true,
        user_types: [{ id: "type-2", name: "No Access Type" }],
      } as any,
      login: vi.fn() as any,
      logout: vi.fn(),
    });
    vi.mocked(useUserTypes).mockReturnValue({
      data: [{ id: "type-2", name: "No Access Type", allowed_menus: [] }],
    } as any); // skipcq: JS-0323

    render(
      <MemoryRouter initialEntries={["/dashboard"]}>
        <Navbar />
      </MemoryRouter>,
    );

    expect(screen.queryByText("Tarefas")).toBeNull();
    expect(screen.queryByText("Categorias")).toBeNull();
  });

  it("shows only Tarefas when the UserType grants tasks but not categories", () => {
    vi.spyOn(AuthHook, "useAuth").mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      user: {
        id: "1",
        email: "director@example.com",
        full_name: "Director User",
        role: UserRole.DIRECTOR,
        is_active: true,
        user_types: [{ id: "type-3", name: "Tasks Only" }],
      } as any,
      login: vi.fn() as any,
      logout: vi.fn(),
    });
    vi.mocked(useUserTypes).mockReturnValue({
      data: [{ id: "type-3", name: "Tasks Only", allowed_menus: ["tasks"] }],
    } as any); // skipcq: JS-0323

    render(
      <MemoryRouter initialEntries={["/dashboard"]}>
        <Navbar />
      </MemoryRouter>,
    );

    expect(screen.getByText("Tarefas")).toBeInTheDocument();
    expect(screen.queryByText("Categorias")).toBeNull();
  });

  it("shows Tarefas and Categorias for ADMINISTRATOR even with no UserType", () => {
    vi.spyOn(AuthHook, "useAuth").mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      user: {
        id: "1",
        email: "admin@example.com",
        full_name: "Admin User",
        role: UserRole.ADMINISTRATOR,
        is_active: true,
      },
      login: vi.fn() as any,
      logout: vi.fn(),
    });
    vi.mocked(useUserTypes).mockReturnValue({ data: [] } as any); // skipcq: JS-0323

    render(
      <MemoryRouter initialEntries={["/dashboard"]}>
        <Navbar />
      </MemoryRouter>,
    );

    expect(screen.getByText("Tarefas")).toBeInTheDocument();
    expect(screen.getByText("Categorias")).toBeInTheDocument();
  });
});
