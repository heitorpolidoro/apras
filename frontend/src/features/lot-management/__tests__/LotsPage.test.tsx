import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { LotsPage } from "../components/LotsPage";
import * as AuthHook from "../../user-administration/context/AuthContext";
import { UserRole } from "../../../types/auth";
import * as lotsApi from "../../../api/lots";
import * as usersHook from "../../../hooks/useUsers";
import { LotStatus, LotAssociationType } from "../../../types/lot";

vi.mock("../../../api/lots");
vi.mock("../../../hooks/useUsers");

vi.mock("../../user-administration/context/SimulationContext", () => ({
  useSimulation: vi.fn(() => ({
    simulatedRole: null,
    simulatedUserTypeIds: [],
    isSimulating: false,
  })),
}));

const mockLotsData = {
  items: [
    {
      id: "lot-1",
      block: "A",
      lot_number: "101",
      address: "Rua Primavera 100",
      postal_code: "12345-000",
      area_sqm: 500,
      fraction_ideal: 0.05,
      status: LotStatus.VACANT,
      notes: "Esquina",
      is_deleted: false,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    },
    {
      id: "lot-2",
      block: "B",
      lot_number: "202",
      address: "Rua Flores 200",
      postal_code: "12345-001",
      area_sqm: 450,
      fraction_ideal: 0.04,
      status: LotStatus.OCCUPIED,
      notes: "Casa verde",
      is_deleted: false,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    },
  ],
  total: 2,
  skip: 0,
  limit: 100,
};

const mockLotDetailData = {
  ...mockLotsData.items[0],
  users: [
    {
      id: "link-1",
      user_id: "user-1",
      lot_id: "lot-1",
      association_type: LotAssociationType.PROPRIETARIO,
      is_primary: true,
      start_date: null,
      end_date: null,
      created_at: "2026-01-01T00:00:00Z",
      user: {
        id: "user-1",
        full_name: "Carlos Silva",
        email: "carlos@test.com",
        role: UserRole.DIRECTOR,
      },
    },
  ],
};

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
    },
  });

const renderComponent = (role: UserRole = UserRole.ADMINISTRATOR) => {
  vi.spyOn(AuthHook, "useAuth").mockReturnValue({
    isAuthenticated: true,
    isLoading: false,
    user: {
      id: "admin-1",
      email: "admin@test.com",
      full_name: "Admin User",
      role,
      is_active: true,
    },
    login: vi.fn() as any,
    logout: vi.fn(),
  });

  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <LotsPage />
      </MemoryRouter>
    </QueryClientProvider>
  );
};

describe("LotsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(lotsApi.getLots).mockResolvedValue(mockLotsData);
    vi.mocked(lotsApi.getLotDetail).mockResolvedValue(mockLotDetailData);
    vi.mocked(usersHook.useUsers).mockReturnValue({
      data: [
        {
          id: "user-1",
          email: "carlos@test.com",
          full_name: "Carlos Silva",
          role: UserRole.DIRECTOR,
          is_active: true,
        },
      ],
      isLoading: false,
      error: null,
    } as any);
  });

  it("renders page header, filters, and lot table for ADMINISTRATOR", async () => {
    renderComponent(UserRole.ADMINISTRATOR);

    expect(screen.getByText("Cadastro de Lotes")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Novo Lote" })).toBeInTheDocument();

    expect(await screen.findByText("101")).toBeInTheDocument();
    expect(screen.getAllByText("Vago")[0]).toBeInTheDocument();
    expect(screen.getAllByText("Ocupado")[0]).toBeInTheDocument();
  });

  it("hides 'Novo Lote' and edit/delete actions for MANAGER role", async () => {
    renderComponent(UserRole.MANAGER);

    expect(await screen.findByText("101")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Novo Lote" })).not.toBeInTheDocument();
  });

  it("filters lots by search term", async () => {
    renderComponent(UserRole.ADMINISTRATOR);

    expect(await screen.findByText("101")).toBeInTheDocument();
    expect(screen.getByText("202")).toBeInTheDocument();

    const searchInput = screen.getByPlaceholderText("Buscar por quadra ou lote...");
    fireEvent.change(searchInput, { target: { value: "Primavera" } });

    expect(screen.getByText("101")).toBeInTheDocument();
    expect(screen.queryByText("202")).not.toBeInTheDocument();
  });

  it("opens create lot modal and submits form", async () => {
    vi.mocked(lotsApi.createLot).mockResolvedValue(mockLotsData.items[0]);

    renderComponent(UserRole.ADMINISTRATOR);

    expect(await screen.findByText("101")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Novo Lote" }));

    expect(screen.getByRole("heading", { name: "Novo Lote" })).toBeInTheDocument();

    const inputs = screen.getAllByRole("textbox");
    fireEvent.change(inputs[1], { target: { value: "C" } }); // block is input[1] after search input
    fireEvent.change(inputs[2], { target: { value: "303" } }); // lot_number

    fireEvent.click(screen.getByRole("button", { name: "Salvar" }));

    await waitFor(() => {
      expect(lotsApi.createLot).toHaveBeenCalledWith(
        expect.objectContaining({
          block: "C",
          lot_number: "303",
        })
      );
    });
  });

  it("opens link user modal and binds user to lot", async () => {
    vi.mocked(lotsApi.linkUserLot).mockResolvedValue(mockLotDetailData.users[0]);

    renderComponent(UserRole.ADMINISTRATOR);

    await waitFor(() => {
      expect(screen.getByText("101")).toBeInTheDocument();
    });

    const linkButtons = screen.getAllByTitle("Vincular Usuário");
    fireEvent.click(linkButtons[0]);

    await waitFor(() => {
      expect(screen.getByText(/Vincular Usuário \(Q: A, L: 101\)/)).toBeInTheDocument();
    });

    const comboboxes = screen.getAllByRole("combobox");
    // comboboxes[0] = Block filter, comboboxes[1] = Status filter, comboboxes[2] = User select in modal
    fireEvent.change(comboboxes[2], { target: { value: "user-1" } });

    const submitButtons = screen.getAllByRole("button", { name: "Vincular Usuário" });
    fireEvent.click(submitButtons[submitButtons.length - 1]);

    await waitFor(() => {
      expect(lotsApi.linkUserLot).toHaveBeenCalledWith(
        "lot-1",
        expect.objectContaining({ user_id: "user-1" })
      );
    });
  });

  it("views lot details and handles unlinking user", async () => {
    vi.mocked(lotsApi.unlinkUserLot).mockResolvedValue();

    renderComponent(UserRole.ADMINISTRATOR);

    await waitFor(() => {
      expect(screen.getByText("101")).toBeInTheDocument();
    });

    const detailButtons = screen.getAllByTitle("Detalhes do Lote");
    fireEvent.click(detailButtons[0]);

    await waitFor(() => {
      expect(screen.getByText("Quadra A — Lote 101")).toBeInTheDocument();
      expect(screen.getByText("Carlos Silva")).toBeInTheDocument();
      expect(screen.getByText("carlos@test.com")).toBeInTheDocument();
      expect(screen.getByText("Principal")).toBeInTheDocument();
    });

    const unlinkButton = screen.getByTitle("Desvincular");
    fireEvent.click(unlinkButton);

    const unlinkButtons = screen.getAllByRole("button", { name: "Desvincular" });
    fireEvent.click(unlinkButtons[unlinkButtons.length - 1]);

    await waitFor(() => {
      expect(lotsApi.unlinkUserLot).toHaveBeenCalledWith("lot-1", "user-1");
    });
  });

  it("deletes lot with confirmation modal", async () => {
    vi.mocked(lotsApi.deleteLot).mockResolvedValue();

    renderComponent(UserRole.ADMINISTRATOR);

    await waitFor(() => {
      expect(screen.getByText("101")).toBeInTheDocument();
    });

    const deleteButtons = screen.getAllByTitle("Excluir");
    fireEvent.click(deleteButtons[0]);

    const confirmButtons = screen.getAllByRole("button", { name: "Excluir" });
    fireEvent.click(confirmButtons[confirmButtons.length - 1]);

    await waitFor(() => {
      expect(lotsApi.deleteLot).toHaveBeenCalledWith("lot-1");
    });
  });
});
