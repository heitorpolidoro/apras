import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import ReservableSpacesPage from "../ReservableSpacesPage";
import {
  useReservableSpaces,
  useCreateReservableSpace,
  useUpdateReservableSpace,
  useDeactivateReservableSpace,
} from "../../hooks/useReservations";
import { useAuth, UserRole } from "../../../user-administration/context/AuthContext";

vi.mock("../../hooks/useReservations", () => ({
  useReservableSpaces: vi.fn(),
  useCreateReservableSpace: vi.fn(),
  useUpdateReservableSpace: vi.fn(),
  useDeactivateReservableSpace: vi.fn(),
}));

vi.mock(
  "../../../user-administration/context/AuthContext",
  async () => {
    const actual = await vi.importActual<
      typeof import("../../../user-administration/context/AuthContext")
    >("../../../user-administration/context/AuthContext");
    return {
      ...actual,
      useAuth: vi.fn(() => ({
        user: { id: "admin-1", role: actual.UserRole.ADMINISTRATOR },
      })),
    };
  },
);

vi.mock("../../../user-administration/context/SimulationContext", () => ({
  useSimulation: vi.fn(() => ({
    simulatedRole: null,
    simulatedUserTypeIds: [],
    isSimulating: false,
    setSimulatedRole: vi.fn(),
    setSimulatedUserTypeIds: vi.fn(),
    stopSimulation: vi.fn(),
  })),
}));

vi.mock("../../../../hooks/useUserTypes", () => ({
  useUserTypes: vi.fn(() => ({ data: [] })),
}));

const mockSpaces = [
  {
    id: "space-1",
    name: "Salão de Festas",
    description: "Party room",
    capacity: 50,
    requires_approval: false,
    is_active: true,
    created_at: "2026-01-01T00:00:00",
  },
  {
    id: "space-2",
    name: "Quadra",
    description: null,
    capacity: null,
    requires_approval: true,
    is_active: true,
    created_at: "2026-01-01T00:00:00",
  },
];

const makeHooks = (overrides: {
  create?: Partial<{ mutate: ReturnType<typeof vi.fn>; isPending: boolean }>;
  update?: Partial<{ mutate: ReturnType<typeof vi.fn>; isPending: boolean }>;
  deactivate?: Partial<{ mutate: ReturnType<typeof vi.fn>; isPending: boolean }>;
} = {}) => {
  vi.mocked(useCreateReservableSpace).mockReturnValue({
    mutate: overrides.create?.mutate ?? vi.fn(),
    isPending: overrides.create?.isPending ?? false,
  } as any);
  vi.mocked(useUpdateReservableSpace).mockReturnValue({
    mutate: overrides.update?.mutate ?? vi.fn(),
    isPending: overrides.update?.isPending ?? false,
  } as any);
  vi.mocked(useDeactivateReservableSpace).mockReturnValue({
    mutate: overrides.deactivate?.mutate ?? vi.fn(),
    isPending: overrides.deactivate?.isPending ?? false,
  } as any);
};

describe("ReservableSpacesPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useAuth).mockReturnValue({
      user: { id: "admin-1", role: UserRole.ADMINISTRATOR },
    } as any);
    vi.mocked(useReservableSpaces).mockReturnValue({
      data: mockSpaces,
      isLoading: false,
    } as any);
    makeHooks();
  });

  it("renders title and new space button for ADMINISTRATOR", () => {
    render(<ReservableSpacesPage />);
    expect(screen.getByText("Espaços Reserváveis")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Novo Espaço/i })).toBeInTheDocument();
  });

  it("renders loading state", () => {
    vi.mocked(useReservableSpaces).mockReturnValue({
      data: undefined,
      isLoading: true,
    } as any);
    render(<ReservableSpacesPage />);
    expect(screen.getByText("Carregando espaços...")).toBeInTheDocument();
  });

  it("renders empty state when no spaces", () => {
    vi.mocked(useReservableSpaces).mockReturnValue({ data: [], isLoading: false } as any);
    render(<ReservableSpacesPage />);
    expect(screen.getByText("Nenhum espaço cadastrado.")).toBeInTheDocument();
  });

  it("renders space list with names", () => {
    render(<ReservableSpacesPage />);
    expect(screen.getByText("Salão de Festas")).toBeInTheDocument();
    expect(screen.getByText("Quadra")).toBeInTheDocument();
  });

  it("shows create form when new space button is clicked", () => {
    render(<ReservableSpacesPage />);
    fireEvent.click(screen.getByRole("button", { name: /Novo Espaço/i }));
    expect(screen.getByPlaceholderText("Nome do espaço")).toBeInTheDocument();
  });

  it("hides form when cancel is clicked", () => {
    render(<ReservableSpacesPage />);
    fireEvent.click(screen.getByRole("button", { name: /Novo Espaço/i }));
    fireEvent.click(screen.getByRole("button", { name: /Cancelar/i }));
    expect(screen.queryByPlaceholderText("Nome do espaço")).not.toBeInTheDocument();
  });

  it("calls createMutation when form is submitted", () => {
    const mutate = vi.fn((_data, options) => options?.onSuccess?.());
    makeHooks({ create: { mutate } });
    render(<ReservableSpacesPage />);

    fireEvent.click(screen.getByRole("button", { name: /Novo Espaço/i }));
    fireEvent.change(screen.getByPlaceholderText("Nome do espaço"), {
      target: { value: "Piscina" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Salvar/i }));

    expect(mutate).toHaveBeenCalledWith(
      expect.objectContaining({ name: "Piscina" }),
      expect.any(Object),
    );
  });

  it("does not submit when name is empty", () => {
    const mutate = vi.fn();
    makeHooks({ create: { mutate } });
    render(<ReservableSpacesPage />);

    fireEvent.click(screen.getByRole("button", { name: /Novo Espaço/i }));
    fireEvent.click(screen.getByRole("button", { name: /Salvar/i }));

    expect(mutate).not.toHaveBeenCalled();
  });

  it("shows edit form when pencil button is clicked", () => {
    render(<ReservableSpacesPage />);
    fireEvent.click(document.querySelectorAll("svg.lucide-pencil")[0].closest("button")!);
    expect(screen.getByDisplayValue("Salão de Festas")).toBeInTheDocument();
  });

  it("calls updateMutation when edit form is submitted", () => {
    const mutate = vi.fn((_data, options) => options?.onSuccess?.());
    makeHooks({ update: { mutate } });
    render(<ReservableSpacesPage />);

    fireEvent.click(document.querySelectorAll("svg.lucide-pencil")[0].closest("button")!);
    fireEvent.change(screen.getByDisplayValue("Salão de Festas"), {
      target: { value: "Salão Renovado" },
    });
    fireEvent.click(document.querySelector("svg.lucide-check")!.closest("button")!);

    expect(mutate).toHaveBeenCalledWith(
      expect.objectContaining({
        id: "space-1",
        data: expect.objectContaining({ name: "Salão Renovado" }),
      }),
      expect.any(Object),
    );
  });

  it("shows inline confirm when trash button is clicked", () => {
    render(<ReservableSpacesPage />);
    fireEvent.click(document.querySelectorAll("svg.lucide-trash-2")[0].closest("button")!);
    expect(screen.getByText(/Desativar o espaço/)).toBeInTheDocument();
  });

  it("calls deactivateMutation when inline confirm is accepted", () => {
    const mutate = vi.fn((_id, options) => options?.onSuccess?.());
    makeHooks({ deactivate: { mutate } });
    render(<ReservableSpacesPage />);

    fireEvent.click(document.querySelectorAll("svg.lucide-trash-2")[0].closest("button")!);
    fireEvent.click(document.querySelector("svg.lucide-check")!.closest("button")!);

    expect(mutate).toHaveBeenCalledWith("space-1", expect.any(Object));
  });

  it("dismisses delete confirm when X is clicked", () => {
    const mutate = vi.fn();
    makeHooks({ deactivate: { mutate } });
    render(<ReservableSpacesPage />);

    fireEvent.click(document.querySelectorAll("svg.lucide-trash-2")[0].closest("button")!);
    fireEvent.click(document.querySelector("svg.lucide-x")!.closest("button")!);

    expect(screen.queryByText(/Desativar o espaço/)).not.toBeInTheDocument();
    expect(mutate).not.toHaveBeenCalled();
  });

  it("shows error alert on create failure", async () => {
    const mutate = vi.fn((_data, options) =>
      options?.onError?.({ response: { data: { detail: "Duplicate name" } } }),
    );
    makeHooks({ create: { mutate } });
    render(<ReservableSpacesPage />);

    fireEvent.click(screen.getByRole("button", { name: /Novo Espaço/i }));
    fireEvent.change(screen.getByPlaceholderText("Nome do espaço"), {
      target: { value: "Piscina" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Salvar/i }));

    await waitFor(() => {
      expect(screen.getByText("Duplicate name")).toBeInTheDocument();
    });
  });

  it("fills description, capacity and checkbox in create form and submits", () => {
    const mutate = vi.fn((_data, options) => options?.onSuccess?.());
    makeHooks({ create: { mutate } });
    render(<ReservableSpacesPage />);

    fireEvent.click(screen.getByRole("button", { name: /Novo Espaço/i }));
    fireEvent.change(screen.getByPlaceholderText("Nome do espaço"), {
      target: { value: "Piscina" },
    });
    fireEvent.change(screen.getByPlaceholderText("Descrição"), {
      target: { value: "Piscina aquecida" },
    });
    fireEvent.change(screen.getByPlaceholderText("Capacidade"), {
      target: { value: "15" },
    });
    fireEvent.click(document.querySelector("input[type='checkbox']")!);
    fireEvent.click(screen.getByRole("button", { name: /Salvar/i }));

    expect(mutate).toHaveBeenCalledWith(
      expect.objectContaining({
        name: "Piscina",
        description: "Piscina aquecida",
        capacity: 15,
        requires_approval: true,
      }),
      expect.any(Object),
    );
  });

  it("fills description and capacity in edit form and submits", () => {
    const mutate = vi.fn((_data, options) => options?.onSuccess?.());
    makeHooks({ update: { mutate } });
    render(<ReservableSpacesPage />);

    fireEvent.click(document.querySelectorAll("svg.lucide-pencil")[0].closest("button")!);
    fireEvent.change(screen.getByPlaceholderText("Descrição"), {
      target: { value: "Nova descrição" },
    });
    fireEvent.change(screen.getByPlaceholderText("Capacidade"), {
      target: { value: "99" },
    });
    fireEvent.click(document.querySelector("svg.lucide-check")!.closest("button")!);

    expect(mutate).toHaveBeenCalledWith(
      expect.objectContaining({
        id: "space-1",
        data: expect.objectContaining({
          description: "Nova descrição",
          capacity: 99,
        }),
      }),
      expect.any(Object),
    );
  });

  it("shows error on update failure", async () => {
    const mutate = vi.fn((_data, options) =>
      options?.onError?.({ response: { data: { detail: "Update failed" } } }),
    );
    makeHooks({ update: { mutate } });
    render(<ReservableSpacesPage />);

    fireEvent.click(document.querySelectorAll("svg.lucide-pencil")[0].closest("button")!);
    fireEvent.click(document.querySelector("svg.lucide-check")!.closest("button")!);

    await waitFor(() => {
      expect(screen.getByText("Update failed")).toBeInTheDocument();
    });
  });

  it("shows error on deactivate failure", async () => {
    const mutate = vi.fn((_id, options) =>
      options?.onError?.({ response: { data: { detail: "Delete failed" } } }),
    );
    makeHooks({ deactivate: { mutate } });
    render(<ReservableSpacesPage />);

    fireEvent.click(document.querySelectorAll("svg.lucide-trash-2")[0].closest("button")!);
    fireEvent.click(document.querySelector("svg.lucide-check")!.closest("button")!);

    await waitFor(() => {
      expect(screen.getByText("Delete failed")).toBeInTheDocument();
    });
  });

  it("MANAGER user does not see the Novo Espaço button", () => {
    vi.mocked(useAuth).mockReturnValue({
      user: { id: "manager-1", role: UserRole.MANAGER },
    } as any); // skipcq: JS-0323
    render(<ReservableSpacesPage />);
    expect(screen.queryByRole("button", { name: /Novo Espaço/i })).not.toBeInTheDocument();
  });

  it("MANAGER user does not see edit/delete buttons", () => {
    vi.mocked(useAuth).mockReturnValue({
      user: { id: "manager-1", role: UserRole.MANAGER },
    } as any); // skipcq: JS-0323
    render(<ReservableSpacesPage />);
    expect(document.querySelectorAll("svg.lucide-pencil")).toHaveLength(0);
    expect(document.querySelectorAll("svg.lucide-trash-2")).toHaveLength(0);
  });
});
