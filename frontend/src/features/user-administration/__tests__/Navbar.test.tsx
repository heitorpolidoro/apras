import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";
import Navbar from "../components/Navbar";
import * as AuthHook from "../context/AuthContext";
import { UserRole } from "../context/AuthContext";

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
      },
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
      },
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
      },
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
      },
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
});
