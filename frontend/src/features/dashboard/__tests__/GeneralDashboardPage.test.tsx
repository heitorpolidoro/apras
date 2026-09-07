import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter } from "react-router-dom";
import GeneralDashboardPage from "../components/GeneralDashboardPage";
import * as AuthHook from "../../user-administration/context/AuthContext";
import * as TenantHook from "../../user-administration/context/useTenant";
import * as AccessHook from "../../user-administration/access/useCanAccess";

describe("GeneralDashboardPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const setupMocks = ({
    userName = "Carlos Silva",
    tenantName = "Condomínio Reserva das Flores",
    roles = [{ id: "role-1", name: "Administrador" }],
    accessiblePaths = ["/tasks", "/gate", "/packages"],
  } = {}) => {
    vi.spyOn(AuthHook, "useAuth").mockReturnValue({
      user: {
        id: "u-1",
        email: "carlos@example.com",
        full_name: userName,
        is_active: true,
        is_superuser: false,
        roles,
      },
      isAuthenticated: true,
      isLoading: false,
      login: vi.fn(),
      logout: vi.fn(),
    } as never);

    vi.spyOn(TenantHook, "useTenant").mockReturnValue({
      actingTenant: tenantName
        ? {
            id: "t-1",
            name: tenantName,
            is_active: true,
            created_at: "2026-01-01",
          }
        : null,
      actingTenantId: "t-1",
      tenants: [],
      isActingTenantAdmin: false,
      isLoading: false,
      setActingTenant: vi.fn(),
    } as never);

    vi.spyOn(AccessHook, "useCanOpenPath").mockReturnValue(
      (path: string | null | undefined) =>
        Boolean(path && accessiblePaths.includes(path)),
    );
  };

  it("renders welcome banner with user full name, tenant name, and role badges", () => {
    setupMocks();

    render(
      <MemoryRouter>
        <GeneralDashboardPage />
      </MemoryRouter>,
    );

    expect(screen.getByText(/Carlos Silva/)).toBeInTheDocument();
    expect(screen.getByText("Condomínio Reserva das Flores")).toBeInTheDocument();
    expect(screen.getByText("Administrador")).toBeInTheDocument();
  });

  it("renders shortcut cards only for accessible modules", () => {
    setupMocks({
      accessiblePaths: ["/tasks", "/gate"],
    });

    render(
      <MemoryRouter>
        <GeneralDashboardPage />
      </MemoryRouter>,
    );

    // Tarefas and Portaria should be rendered
    expect(screen.getByText("Tarefas")).toBeInTheDocument();
    expect(screen.getByText("Portaria & Visitantes")).toBeInTheDocument();

    // Packages, Finance, Infractions, etc. should not be rendered
    expect(screen.queryByText("Encomendas")).toBeNull();
    expect(screen.queryByText("Financeiro")).toBeNull();
    expect(screen.queryByText("Infrações")).toBeNull();
  });

  it("renders accessible shortcut cards as semantic links with proper to attribute", () => {
    setupMocks({
      accessiblePaths: ["/tasks"],
    });

    render(
      <MemoryRouter>
        <GeneralDashboardPage />
      </MemoryRouter>,
    );

    const taskLink = screen.getByText("Tarefas").closest("a");
    expect(taskLink).toBeInTheDocument();
    expect(taskLink).toHaveAttribute("href", "/tasks");
  });

  it("renders no tenant badge when actingTenant is null", () => {
    setupMocks({
      tenantName: "",
    });

    render(
      <MemoryRouter>
        <GeneralDashboardPage />
      </MemoryRouter>,
    );

    expect(screen.queryByText("Condomínio Reserva das Flores")).toBeNull();
  });
});
