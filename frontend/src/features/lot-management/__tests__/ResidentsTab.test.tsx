import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ResidentsTab } from "../components/ResidentsTab";
import * as residentsApi from "../../../api/residents";
import * as usersHook from "../../../hooks/useUsers";
import { ResidentRelationship } from "../../../types/resident";
import { UserRole } from "../../../types/auth";

vi.mock("../../../api/residents");
vi.mock("../../../hooks/useUsers");

const mockResidentsData = {
  items: [
    {
      id: "res-1",
      lot_id: "lot-1",
      user_id: null,
      full_name: "Maria Oliveira",
      cpf: "11144477735",
      rg: "12345678",
      birth_date: "1990-05-15",
      phone: "11988887777",
      email: "maria@test.com",
      relationship_type: ResidentRelationship.TITULAR,
      is_active: true,
      notes: "Responsável principal",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
      user: null,
      lot: { id: "lot-1", block: "A", lot_number: "101" },
    },
    {
      id: "res-2",
      lot_id: "lot-1",
      user_id: "user-1",
      full_name: "João Oliveira",
      cpf: "52998224725",
      rg: null,
      birth_date: null,
      phone: null,
      email: null,
      relationship_type: ResidentRelationship.CONJUGE,
      is_active: true,
      notes: null,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
      user: {
        id: "user-1",
        full_name: "João Oliveira User",
        email: "joao@test.com",
        role: UserRole.DIRECTOR,
      },
      lot: { id: "lot-1", block: "A", lot_number: "101" },
    },
  ],
  total: 2,
  skip: 0,
  limit: 100,
};

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
    },
  });

const renderComponent = (canManage = true) => {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <ResidentsTab lotId="lot-1" canManage={canManage} />
    </QueryClientProvider>
  );
};

describe("ResidentsTab", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(residentsApi.getLotResidents).mockResolvedValue(mockResidentsData as any);
    vi.mocked(usersHook.useUsers).mockReturnValue({
      users: [
        {
          id: "user-2",
          email: "user2@test.com",
          full_name: "User Two",
          role: UserRole.DIRECTOR,
          is_active: true,
        },
      ],
      isLoading: false,
      error: null,
    } as any);
  });

  it("renders resident list and action buttons for authorized user", async () => {
    renderComponent(true);

    expect(await screen.findByText("Maria Oliveira")).toBeInTheDocument();
    expect(screen.getByText("João Oliveira")).toBeInTheDocument();
    expect(screen.getByText("Titular")).toBeInTheDocument();
    expect(screen.getByText("Cônjuge")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Novo Morador" })).toBeInTheDocument();
  });

  it("hides management actions when canManage is false", async () => {
    renderComponent(false);

    expect(await screen.findByText("Maria Oliveira")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Novo Morador" })).not.toBeInTheDocument();
  });

  it("filters residents by search query", async () => {
    renderComponent(true);

    expect(await screen.findByText("Maria Oliveira")).toBeInTheDocument();
    expect(screen.getByText("João Oliveira")).toBeInTheDocument();

    const searchInput = screen.getByPlaceholderText("Buscar morador por nome, CPF ou e-mail...");
    fireEvent.change(searchInput, { target: { value: "Maria" } });

    expect(screen.getByText("Maria Oliveira")).toBeInTheDocument();
    expect(screen.queryByText("João Oliveira")).not.toBeInTheDocument();
  });

  it("opens create resident modal and submits new resident", async () => {
    vi.mocked(residentsApi.createResident).mockResolvedValue(mockResidentsData.items[0] as any);

    renderComponent(true);

    expect(await screen.findByText("Maria Oliveira")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Novo Morador" }));

    expect(screen.getByRole("heading", { name: "Novo Morador" })).toBeInTheDocument();

    const inputs = screen.getAllByRole("textbox");
    fireEvent.change(inputs[1], { target: { value: "Novo Morador Teste" } }); // Name
    fireEvent.change(inputs[2], { target: { value: "11144477735" } }); // CPF

    fireEvent.click(screen.getByRole("button", { name: "Salvar" }));

    await waitFor(() => {
      expect(residentsApi.createResident).toHaveBeenCalledWith(
        "lot-1",
        expect.objectContaining({
          full_name: "Novo Morador Teste",
          cpf: "11144477735",
        })
      );
    });
  });

  it("opens edit resident modal and updates profile", async () => {
    vi.mocked(residentsApi.updateResident).mockResolvedValue(mockResidentsData.items[0] as any);

    renderComponent(true);

    expect(await screen.findByText("Maria Oliveira")).toBeInTheDocument();

    const editButtons = screen.getAllByTitle("Editar");
    fireEvent.click(editButtons[0]);

    expect(screen.getByRole("heading", { name: "Editar Morador" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Salvar" }));

    await waitFor(() => {
      expect(residentsApi.updateResident).toHaveBeenCalledWith(
        "res-1",
        expect.objectContaining({
          full_name: "Maria Oliveira",
        })
      );
    });
  });

  it("deactivates resident after confirmation", async () => {
    vi.mocked(residentsApi.deleteResident).mockResolvedValue();

    renderComponent(true);

    expect(await screen.findByText("Maria Oliveira")).toBeInTheDocument();

    const deactivateButtons = screen.getAllByTitle("Desativar");
    fireEvent.click(deactivateButtons[0]);

    expect(screen.getByRole("heading", { name: "Desativar Morador" })).toBeInTheDocument();

    const confirmButtons = screen.getAllByRole("button", { name: "Desativar" });
    fireEvent.click(confirmButtons[confirmButtons.length - 1]);

    await waitFor(() => {
      expect(residentsApi.deleteResident).toHaveBeenCalledWith("res-1");
    });
  });

  it("links user account to resident", async () => {
    vi.mocked(residentsApi.linkResidentUser).mockResolvedValue(mockResidentsData.items[0] as any);

    renderComponent(true);

    expect(await screen.findByText("Maria Oliveira")).toBeInTheDocument();

    const linkButton = screen.getByTitle("Vincular Conta");
    fireEvent.click(linkButton);

    expect(screen.getByText(/Vincular Conta de Usuário/)).toBeInTheDocument();

    const radioButton = screen.getByRole("radio");
    fireEvent.click(radioButton);

    const submitButtons = screen.getAllByRole("button", { name: "Vincular Conta" });
    fireEvent.click(submitButtons[submitButtons.length - 1]);

    await waitFor(() => {
      expect(residentsApi.linkResidentUser).toHaveBeenCalledWith("res-1", "user-2");
    });

  });

  it("unlinks user account from resident", async () => {
    vi.mocked(residentsApi.unlinkResidentUser).mockResolvedValue(mockResidentsData.items[1] as any);

    renderComponent(true);

    expect(await screen.findByText("João Oliveira")).toBeInTheDocument();

    const unlinkButton = screen.getByTitle("Desvincular");
    fireEvent.click(unlinkButton);

    expect(screen.getByRole("heading", { name: "Desvincular Conta de Usuário" })).toBeInTheDocument();

    const confirmButtons = screen.getAllByRole("button", { name: "Desvincular" });
    fireEvent.click(confirmButtons[confirmButtons.length - 1]);

    await waitFor(() => {
      expect(residentsApi.unlinkResidentUser).toHaveBeenCalledWith("res-2");
    });
  });
});
