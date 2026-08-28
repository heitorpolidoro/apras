import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import CategoriesPage from "../CategoriesPage";
import {
  useCategories,
  useCreateCategory,
  useUpdateCategory,
  useDeleteCategory,
} from "../../hooks/useCategories";
import { useAuth, UserRole } from "../../../user-administration/context/AuthContext";

vi.mock("../../hooks/useCategories", () => ({
  useCategories: vi.fn(),
  useCreateCategory: vi.fn(),
  useUpdateCategory: vi.fn(),
  useDeleteCategory: vi.fn(),
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

// CategoriesPage now reads its effective role via useEffectiveIdentity, which
// combines useAuth (mocked above, varies per test) with useSimulation. Keep
// simulation permanently inactive here so canWrite continues to reflect the
// real user's role exactly like before this hook existed.
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

// useEffectiveIdentity also calls useUserTypes (APRAS-9 role-type fold-in);
// mock it so these tests don't need a QueryClientProvider wrapper.
vi.mock("../../../../hooks/useUserTypes", () => ({
  useUserTypes: vi.fn(() => ({ data: [] })),
}));

const mockCategories = [
  { id: "cat-1", name: "General", color: "#808080", is_active: true },
  { id: "cat-2", name: "Jurídico", color: "#6366f1", is_active: true },
];

const makeHooks = (overrides: {
  create?: Partial<{ mutate: ReturnType<typeof vi.fn>; isPending: boolean }>;
  update?: Partial<{ mutate: ReturnType<typeof vi.fn>; isPending: boolean }>;
  delete?: Partial<{ mutate: ReturnType<typeof vi.fn>; isPending: boolean }>;
} = {}) => {
  vi.mocked(useCreateCategory).mockReturnValue({
    mutate: overrides.create?.mutate ?? vi.fn(),
    isPending: overrides.create?.isPending ?? false,
  } as any);
  vi.mocked(useUpdateCategory).mockReturnValue({
    mutate: overrides.update?.mutate ?? vi.fn(),
    isPending: overrides.update?.isPending ?? false,
  } as any);
  vi.mocked(useDeleteCategory).mockReturnValue({
    mutate: overrides.delete?.mutate ?? vi.fn(),
    isPending: overrides.delete?.isPending ?? false,
  } as any);
};

describe("CategoriesPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useCategories).mockReturnValue({
      data: mockCategories,
      isLoading: false,
    } as any);
    makeHooks();
  });

  it("renders title and new category button", () => {
    render(<CategoriesPage />);
    expect(screen.getByText("Categorias")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Nova Categoria/i })).toBeInTheDocument();
  });

  it("renders loading state", () => {
    vi.mocked(useCategories).mockReturnValue({ data: undefined, isLoading: true } as any);
    render(<CategoriesPage />);
    expect(screen.getByText("Carregando categorias...")).toBeInTheDocument();
  });

  it("renders empty state when no categories", () => {
    vi.mocked(useCategories).mockReturnValue({ data: [], isLoading: false } as any);
    render(<CategoriesPage />);
    expect(screen.getByText("Nenhuma categoria cadastrada.")).toBeInTheDocument();
  });

  it("renders category list with names", () => {
    render(<CategoriesPage />);
    expect(screen.getByText("General")).toBeInTheDocument();
    expect(screen.getByText("Jurídico")).toBeInTheDocument();
  });

  it("shows create form when new category button is clicked", () => {
    render(<CategoriesPage />);
    fireEvent.click(screen.getByRole("button", { name: /Nova Categoria/i }));
    expect(screen.getByPlaceholderText("Nome da categoria")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Salvar/i })).toBeInTheDocument();
  });

  it("hides form when cancel is clicked", () => {
    render(<CategoriesPage />);
    fireEvent.click(screen.getByRole("button", { name: /Nova Categoria/i }));
    fireEvent.click(screen.getByRole("button", { name: /Cancelar/i }));
    expect(screen.queryByPlaceholderText("Nome da categoria")).not.toBeInTheDocument();
  });

  it("calls createMutation when form is submitted", () => {
    const mutate = vi.fn((_data, options) => options?.onSuccess?.());
    makeHooks({ create: { mutate } });
    render(<CategoriesPage />);

    fireEvent.click(screen.getByRole("button", { name: /Nova Categoria/i }));
    fireEvent.change(screen.getByPlaceholderText("Nome da categoria"), {
      target: { value: "Finance" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Salvar/i }));

    expect(mutate).toHaveBeenCalledWith(
      expect.objectContaining({ name: "Finance" }),
      expect.any(Object),
    );
  });

  it("does not submit when name is empty", () => {
    const mutate = vi.fn();
    makeHooks({ create: { mutate } });
    render(<CategoriesPage />);

    fireEvent.click(screen.getByRole("button", { name: /Nova Categoria/i }));
    fireEvent.click(screen.getByRole("button", { name: /Salvar/i }));

    expect(mutate).not.toHaveBeenCalled();
  });

  it("shows edit form when pencil button is clicked", () => {
    render(<CategoriesPage />);
    fireEvent.click(document.querySelectorAll('svg.lucide-pencil')[0].closest("button")!);
    expect(screen.getByDisplayValue("General")).toBeInTheDocument();
  });

  it("calls updateMutation when edit form is submitted", () => {
    const mutate = vi.fn((_data, options) => options?.onSuccess?.());
    makeHooks({ update: { mutate } });
    render(<CategoriesPage />);

    fireEvent.click(document.querySelectorAll('svg.lucide-pencil')[0].closest("button")!);
    fireEvent.change(screen.getByDisplayValue("General"), { target: { value: "General Updated" } });
    fireEvent.click(document.querySelector('svg.lucide-check')!.closest("button")!);

    expect(mutate).toHaveBeenCalledWith(
      expect.objectContaining({ id: "cat-1", data: expect.objectContaining({ name: "General Updated" }) }),
      expect.any(Object),
    );
  });

  it("cancels edit when X button is clicked", () => {
    render(<CategoriesPage />);
    fireEvent.click(document.querySelectorAll('svg.lucide-pencil')[0].closest("button")!);
    expect(screen.getByDisplayValue("General")).toBeInTheDocument();

    fireEvent.click(document.querySelector('svg.lucide-x')!.closest("button")!);

    expect(screen.queryByDisplayValue("General")).not.toBeInTheDocument();
    expect(screen.getByText("General")).toBeInTheDocument();
  });

  it("shows inline confirm when trash button is clicked", () => {
    render(<CategoriesPage />);
    fireEvent.click(document.querySelectorAll('svg.lucide-trash-2')[0].closest("button")!);
    expect(screen.getByText(/Excluir a categoria/)).toBeInTheDocument();
  });

  it("calls deleteMutation when inline confirm is accepted", () => {
    const mutate = vi.fn((_id, options) => options?.onSuccess?.());
    makeHooks({ delete: { mutate } });
    render(<CategoriesPage />);

    fireEvent.click(document.querySelectorAll('svg.lucide-trash-2')[0].closest("button")!);
    fireEvent.click(document.querySelector('svg.lucide-check')!.closest("button")!);

    expect(mutate).toHaveBeenCalledWith("cat-1", expect.any(Object));
  });

  it("dismisses delete confirm when X is clicked", () => {
    const mutate = vi.fn();
    makeHooks({ delete: { mutate } });
    render(<CategoriesPage />);

    fireEvent.click(document.querySelectorAll('svg.lucide-trash-2')[0].closest("button")!);
    expect(screen.getByText(/Excluir a categoria/)).toBeInTheDocument();

    fireEvent.click(document.querySelector('svg.lucide-x')!.closest("button")!);
    expect(screen.queryByText(/Excluir a categoria/)).not.toBeInTheDocument();
    expect(mutate).not.toHaveBeenCalled();
  });

  it("shows error alert on create failure", async () => {
    const mutate = vi.fn((_data, options) =>
      options?.onError?.({ response: { data: { detail: "Duplicate name" } } }),
    );
    makeHooks({ create: { mutate } });
    render(<CategoriesPage />);

    fireEvent.click(screen.getByRole("button", { name: /Nova Categoria/i }));
    fireEvent.change(screen.getByPlaceholderText("Nome da categoria"), {
      target: { value: "Finance" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Salvar/i }));

    await waitFor(() => {
      expect(screen.getByText("Duplicate name")).toBeInTheDocument();
    });
  });

  it("shows error on update failure", async () => {
    const mutate = vi.fn((_data, options) =>
      options?.onError?.({ response: { data: { detail: "Update failed" } } }),
    );
    makeHooks({ update: { mutate } });
    render(<CategoriesPage />);

    fireEvent.click(document.querySelectorAll("svg.lucide-pencil")[0].closest("button")!);
    fireEvent.click(document.querySelector("svg.lucide-check")!.closest("button")!);

    await waitFor(() => {
      expect(screen.getByText("Update failed")).toBeInTheDocument();
    });
  });

  it("shows error on delete failure", async () => {
    const mutate = vi.fn((_id, options) =>
      options?.onError?.({ response: { data: { detail: "Delete failed" } } }),
    );
    makeHooks({ delete: { mutate } });
    render(<CategoriesPage />);

    fireEvent.click(document.querySelectorAll("svg.lucide-trash-2")[0].closest("button")!);
    fireEvent.click(document.querySelector("svg.lucide-check")!.closest("button")!);

    await waitFor(() => {
      expect(screen.getByText("Delete failed")).toBeInTheDocument();
    });
  });

  it("updates color in edit form when preset color button is clicked", () => {
    render(<CategoriesPage />);
    fireEvent.click(document.querySelectorAll("svg.lucide-pencil")[0].closest("button")!);

    const presetBtn = screen.getByRole("button", { name: "#8b5cf6" });
    fireEvent.click(presetBtn);

    expect(screen.getByDisplayValue("General")).toBeInTheDocument();
  });

  it("updates color via native color input in create form", () => {
    render(<CategoriesPage />);
    fireEvent.click(screen.getByRole("button", { name: /Nova Categoria/i }));

    const colorInput = document.querySelector("input[type='color']") as HTMLInputElement;
    fireEvent.change(colorInput, { target: { value: "#ff0000" } });

    expect(screen.getByPlaceholderText("Nome da categoria")).toBeInTheDocument();
  });

  it("does not call create mutation when form is submitted with empty name", () => {
    const mutate = vi.fn();
    makeHooks({ create: { mutate } });
    render(<CategoriesPage />);

    fireEvent.click(screen.getByRole("button", { name: /Nova Categoria/i }));
    const form = screen.getByPlaceholderText("Nome da categoria").closest("form")!;
    fireEvent.submit(form);

    expect(mutate).not.toHaveBeenCalled();
  });

  it("does not call update mutation when form is submitted with empty name", () => {
    const mutate = vi.fn();
    makeHooks({ update: { mutate } });
    render(<CategoriesPage />);

    fireEvent.click(document.querySelectorAll("svg.lucide-pencil")[0].closest("button")!);
    fireEvent.change(screen.getByDisplayValue("General"), { target: { value: "" } });
    const form = document.querySelector("input[value='']")!.closest("form")!;
    fireEvent.submit(form);

    expect(mutate).not.toHaveBeenCalled();
  });

  it("shows fallback translation when create error has no detail", async () => {
    const mutate = vi.fn((_data, options) => options?.onError?.({}));
    makeHooks({ create: { mutate } });
    render(<CategoriesPage />);

    fireEvent.click(screen.getByRole("button", { name: /Nova Categoria/i }));
    fireEvent.change(screen.getByPlaceholderText("Nome da categoria"), {
      target: { value: "Finance" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Salvar/i }));

    await waitFor(() => {
      expect(screen.getByText("Erro ao criar categoria.")).toBeInTheDocument();
    });
  });

  it("shows fallback translation when update error has no detail", async () => {
    const mutate = vi.fn((_data, options) => options?.onError?.({}));
    makeHooks({ update: { mutate } });
    render(<CategoriesPage />);

    fireEvent.click(document.querySelectorAll("svg.lucide-pencil")[0].closest("button")!);
    fireEvent.click(document.querySelector("svg.lucide-check")!.closest("button")!);

    await waitFor(() => {
      expect(screen.getByText("Erro ao atualizar categoria.")).toBeInTheDocument();
    });
  });

  it("shows fallback translation when delete error has no detail", async () => {
    const mutate = vi.fn((_id, options) => options?.onError?.({}));
    makeHooks({ delete: { mutate } });
    render(<CategoriesPage />);

    fireEvent.click(document.querySelectorAll("svg.lucide-trash-2")[0].closest("button")!);
    fireEvent.click(document.querySelector("svg.lucide-check")!.closest("button")!);

    await waitFor(() => {
      expect(screen.getByText("Erro ao excluir categoria.")).toBeInTheDocument();
    });
  });

  it("MANAGER user does not see the New Category button", () => {
    vi.mocked(useAuth).mockReturnValue({
      user: { id: "manager-1", role: UserRole.MANAGER },
    } as any); // skipcq: JS-0323
    render(<CategoriesPage />);
    expect(screen.queryByRole("button", { name: /Nova Categoria/i })).not.toBeInTheDocument();
  });

  it("ADMINISTRATOR user sees the New Category button", () => {
    vi.mocked(useAuth).mockReturnValue({
      user: { id: "admin-1", role: UserRole.ADMINISTRATOR },
    } as any); // skipcq: JS-0323
    render(<CategoriesPage />);
    expect(screen.getByRole("button", { name: /Nova Categoria/i })).toBeInTheDocument();
  });

  it("MANAGER user does not see edit/delete buttons in category list", () => {
    vi.mocked(useAuth).mockReturnValue({
      user: { id: "manager-1", role: UserRole.MANAGER },
    } as any); // skipcq: JS-0323
    render(<CategoriesPage />);
    expect(document.querySelectorAll("svg.lucide-pencil")).toHaveLength(0);
    expect(document.querySelectorAll("svg.lucide-trash-2")).toHaveLength(0);
  });
});
