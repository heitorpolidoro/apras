import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import Sidebar from "../components/Sidebar";
import { SidebarProvider } from "../context/SidebarContext";
import apiClient from "../../../api/client";
import * as AuthHook from "../context/AuthContext";
import { type User } from "../../../types/auth";
import { useSidebar } from "../context/useSidebar";

vi.mock("../../../api/client", () => ({
  default: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}));

vi.mock("../context/SimulationContext", () => ({
  useSimulation: vi.fn(() => ({
    simulatedRoleIds: [],
    isSimulating: false,
    setSimulatedRoleIds: vi.fn(),
    stopSimulation: vi.fn(),
  })),
}));

const mockedGet = vi.mocked(apiClient.get);

const renderSidebar = (
  permissions: string[] = ["tasks:read", "categories:read"],
  initialRoute = "/dashboard",
  isSuperuser = false,
) => {
  vi.spyOn(AuthHook, "useAuth").mockReturnValue({
    isAuthenticated: true,
    isLoading: false,
    user: {
      id: "u-1",
      email: "user@test.com",
      full_name: "Test User",
      role: "ADMINISTRATOR",
      is_superuser: isSuperuser,
      is_active: true,
      roles: [],
    } as User,
    login: vi.fn() as never,
    logout: vi.fn(),
  });

  mockedGet.mockImplementation(((url: string) =>
    url === "/permissions/me"
      ? Promise.resolve({
          data: {
            tenant_id: "t-1",
            permissions: [...permissions],
            landing_path: null,
            disabled_modules: [],
          },
        })
      : Promise.resolve({ data: [] })) as never);

  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[initialRoute]}>
        <SidebarProvider>
          <Sidebar />
        </SidebarProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
};

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
});

describe("Sidebar component", () => {
  it("renders the sidebar brand and visible groups for the user", async () => {
    renderSidebar(["tasks:read", "categories:read", "announcements:read"]);

    // Brand
    expect(screen.getByText("APRAS")).toBeInTheDocument();

    // Group headers for groups with visible items
    expect(await screen.findByText("Operações")).toBeInTheDocument();
    expect(screen.getByText("Comunidade & Convivência")).toBeInTheDocument();

    // Links inside those groups
    expect(screen.getByRole("link", { name: "Tarefas" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Categorias" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Comunicados" })).toBeInTheDocument();

    // Groups with no allowed items are hidden
    expect(screen.queryByText("Sistema")).toBeNull();
    expect(screen.queryByText("Financeiro & Planos")).toBeNull();
  });

  it("toggles desktop collapsed mode and persists in localStorage", async () => {
    renderSidebar(["tasks:read"]);

    const collapseButton = screen.getByRole("button", { name: "Recolher menu" });
    expect(collapseButton).toBeInTheDocument();

    // Click collapse
    fireEvent.click(collapseButton);

    // LocalStorage should record true
    expect(localStorage.getItem("apras_sidebar_collapsed")).toBe("true");

    // The button now says "Expandir menu"
    const expandButton = screen.getByRole("button", { name: "Expandir menu" });
    expect(expandButton).toBeInTheDocument();

    // Click expand
    fireEvent.click(expandButton);
    expect(localStorage.getItem("apras_sidebar_collapsed")).toBe("false");
  });

  it("allows expanding and collapsing individual groups via accordion header", async () => {
    renderSidebar(["tasks:read", "categories:read"]);

    const groupButton = await screen.findByRole("button", { name: /Operações/ });
    expect(groupButton).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByRole("link", { name: "Tarefas" })).toBeInTheDocument();

    // Collapse the group
    fireEvent.click(groupButton);
    expect(groupButton).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByRole("link", { name: "Tarefas" })).toBeNull();

    // Expand the group again
    fireEvent.click(groupButton);
    expect(groupButton).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByRole("link", { name: "Tarefas" })).toBeInTheDocument();
  });

  it("highlights the active link with text-primary", async () => {
    renderSidebar(["tasks:read", "categories:read"], "/tasks");

    const tarefasLink = await screen.findByRole("link", { name: "Tarefas" });
    expect(tarefasLink.className).toContain("text-primary");

    const categoriesLink = screen.getByRole("link", { name: "Categorias" });
    expect(categoriesLink.className).not.toContain("bg-primary/10");
  });

  it("renders Início link and highlights when on /", async () => {
    renderSidebar(["tasks:read"], "/");

    const homeLink = await screen.findByRole("link", { name: "Início" });
    expect(homeLink).toBeInTheDocument();
    expect(homeLink.className).toContain("text-primary");
    expect(homeLink).toHaveAttribute("href", "/");
  });

const MobileTestController: React.FC = () => {
  const { toggleMobile } = useSidebar();
  return (
    <button onClick={toggleMobile} data-testid="test-toggle-mobile">
      Toggle Mobile
    </button>
  );
};

const renderSidebarWithController = (
  permissions: string[] = ["tasks:read", "categories:read"],
  initialRoute = "/dashboard",
) => {
  vi.spyOn(AuthHook, "useAuth").mockReturnValue({
    isAuthenticated: true,
    isLoading: false,
    user: {
      id: "u-1",
      email: "user@test.com",
      full_name: "Test User",
      role: "ADMINISTRATOR",
      is_superuser: false,
      is_active: true,
      roles: [],
    } as User,
    login: vi.fn() as never,
    logout: vi.fn(),
  });

  mockedGet.mockImplementation(((url: string) =>
    url === "/permissions/me"
      ? Promise.resolve({
          data: {
            tenant_id: "t-1",
            permissions: [...permissions],
            landing_path: null,
            disabled_modules: [],
          },
        })
      : Promise.resolve({ data: [] })) as never);

  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[initialRoute]}>
        <SidebarProvider>
          <MobileTestController />
          <Sidebar />
        </SidebarProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
};

  it("handles mobile off-canvas drawer opening and closing via close button", async () => {
    renderSidebarWithController(["tasks:read"]);

    // Initially closed
    expect(screen.queryByRole("button", { name: "Fechar" })).toBeNull();

    // Toggle open
    fireEvent.click(screen.getByTestId("test-toggle-mobile"));
    const closeButton = await screen.findByRole("button", { name: "Fechar" });
    expect(closeButton).toBeInTheDocument();

    // Click close button
    fireEvent.click(closeButton);
    expect(screen.queryByRole("button", { name: "Fechar" })).toBeNull();
  });

  it("handles mobile off-canvas drawer closing via backdrop click", async () => {
    const { container } = renderSidebarWithController(["tasks:read"]);

    // Toggle open
    fireEvent.click(screen.getByTestId("test-toggle-mobile"));
    await screen.findByRole("button", { name: "Fechar" });

    // Find backdrop overlay (fixed inset-0)
    const backdrop = container.querySelector(".fixed.inset-0.z-50");
    expect(backdrop).toBeInTheDocument();

    // Click backdrop
    if (backdrop) {
      fireEvent.click(backdrop);
    }
    expect(screen.queryByRole("button", { name: "Fechar" })).toBeNull();
  });

  it("handles mobile off-canvas drawer closing on link click", async () => {
    renderSidebarWithController(["tasks:read"]);

    // Toggle open
    fireEvent.click(screen.getByTestId("test-toggle-mobile"));
    await screen.findByRole("button", { name: "Fechar" });

    // Wait for links to appear after permissions query settles
    const links = await screen.findAllByRole("link", { name: "Tarefas" });
    expect(links.length).toBeGreaterThanOrEqual(1);

    // Click mobile drawer link (the last one rendered)
    fireEvent.click(links[links.length - 1]);

    // Drawer should close
    expect(screen.queryByRole("button", { name: "Fechar" })).toBeNull();
  });
});
