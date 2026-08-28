import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import AssemblyVotingPage from "../AssemblyVotingPage";
import {
  useAssemblies,
  useCloseAssembly,
  useCloseVote,
  useCreateAssembly,
  useCreateVote,
  useEligibleLots,
  useUpdateAssembly,
  useVotes,
} from "../../hooks/useVoting";
import { useEffectiveIdentity } from "../../../user-administration/context/useEffectiveIdentity";
import { UserRole } from "../../../../types/auth";

vi.mock("../../hooks/useVoting", () => ({
  useAssemblies: vi.fn(),
  useCloseAssembly: vi.fn(),
  useCloseVote: vi.fn(),
  useCreateAssembly: vi.fn(),
  useCreateVote: vi.fn(),
  useEligibleLots: vi.fn(),
  useUpdateAssembly: vi.fn(),
  useVotes: vi.fn(),
  useMyBallot: vi.fn(() => ({ data: [], isLoading: false })),
  useCastBallot: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  useRetractBallot: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  useTally: vi.fn(() => ({ data: undefined, isLoading: false })),
  useAssemblyMinutes: vi.fn(() => ({ data: "", isLoading: false })),
  useSaveAssemblyMinutes: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  useUpdateLotDelinquency: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  useLotVoterEligibility: vi.fn(() => ({ data: [] })),
  useAddLotVoterEligibility: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  useRemoveLotVoterEligibility: vi.fn(() => ({
    mutate: vi.fn(),
    isPending: false,
  })),
}));

vi.mock("../../../lot-management/hooks/useLots", () => ({
  useLots: vi.fn(() => ({
    data: { items: [], total: 0, skip: 0, limit: 100 },
  })),
}));

vi.mock("../../../user-administration/context/useEffectiveIdentity", () => ({
  useEffectiveIdentity: vi.fn(),
}));

const assembly = {
  id: "assembly-1",
  title: "AGO 2026",
  type: "AGO" as const,
  held_on: "2026-03-01",
  agenda: null,
  status: "OPEN" as const,
  created_by_id: "admin-1",
  created_at: "2026-01-01T00:00:00",
  updated_at: "2026-01-01T00:00:00",
  closed_at: null,
};

const draftAssembly = { ...assembly, status: "DRAFT" as const };

const vote = {
  id: "vote-1",
  assembly_id: "assembly-1",
  kind: "ASSEMBLEIA" as const,
  title: "Orçamento 2026",
  description: null,
  vote_type: "SINGLE_CHOICE" as const,
  status: "OPEN" as const,
  is_anonymous: false,
  opens_at: "2020-01-01T00:00:00",
  closes_at: "2999-01-01T00:00:00",
  created_by_id: "admin-1",
  created_at: "2026-01-01T00:00:00",
  updated_at: "2026-01-01T00:00:00",
  closed_at: null,
  options: [{ id: "opt-1", vote_id: "vote-1", label: "Sim", order_index: 0 }],
};

const setRole = (role: UserRole) => {
  vi.mocked(useEffectiveIdentity).mockReturnValue({ role } as never);
};

describe("AssemblyVotingPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setRole(UserRole.ADMINISTRATOR);
    vi.mocked(useAssemblies).mockReturnValue({
      data: [assembly],
      isLoading: false,
    } as never);
    vi.mocked(useVotes).mockReturnValue({
      data: [vote],
      isLoading: false,
    } as never);
    vi.mocked(useEligibleLots).mockReturnValue({ data: [] } as never);
    vi.mocked(useCreateAssembly).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as never);
    vi.mocked(useCloseAssembly).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as never);
    vi.mocked(useCreateVote).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as never);
    vi.mocked(useCloseVote).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as never);
    vi.mocked(useUpdateAssembly).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as never);
  });

  it("lists assemblies and their votes", () => {
    render(<AssemblyVotingPage />);
    expect(screen.getByText("Assembleias e Enquetes")).toBeInTheDocument();
    expect(screen.getByText("AGO 2026")).toBeInTheDocument();
    expect(screen.getByText("Orçamento 2026")).toBeInTheDocument();
  });

  it("offers assembly creation to the board", () => {
    render(<AssemblyVotingPage />);
    expect(
      screen.getByRole("button", { name: "Nova Assembleia" }),
    ).toBeInTheDocument();
  });

  it("does not offer assembly creation to a MANAGER, only polls", () => {
    setRole(UserRole.MANAGER);
    render(<AssemblyVotingPage />);
    expect(
      screen.queryByRole("button", { name: "Nova Assembleia" }),
    ).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Enquete" }));
    expect(
      screen.getByRole("button", { name: "Nova enquete" }),
    ).toBeInTheDocument();
  });

  it("does not offer any creation to a RESIDENT", () => {
    setRole(UserRole.RESIDENT);
    render(<AssemblyVotingPage />);
    expect(
      screen.queryByRole("button", { name: "Nova Assembleia" }),
    ).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Enquete" }));
    expect(
      screen.queryByRole("button", { name: "Nova enquete" }),
    ).not.toBeInTheDocument();
  });

  it("shows the ballot and tally panels once a vote is selected", () => {
    render(<AssemblyVotingPage />);
    fireEvent.click(screen.getByRole("button", { name: /Orçamento 2026/ }));
    expect(screen.getByText("Seu voto")).toBeInTheDocument();
  });

  it("creates an assembly from the board form", () => {
    const mutate = vi.fn();
    vi.mocked(useCreateAssembly).mockReturnValue({
      mutate,
      isPending: false,
    } as never);
    render(<AssemblyVotingPage />);

    fireEvent.click(screen.getByRole("button", { name: "Nova Assembleia" }));
    fireEvent.change(screen.getByLabelText("Título"), {
      target: { value: "AGE 2026" },
    });
    fireEvent.change(screen.getByLabelText("Tipo"), {
      target: { value: "AGE" },
    });
    fireEvent.change(screen.getByLabelText("Data de realização"), {
      target: { value: "2026-05-10" },
    });
    fireEvent.change(screen.getByLabelText("Pauta"), {
      target: { value: "1. Obras" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Criar assembleia" }));

    expect(mutate).toHaveBeenCalledWith(
      {
        title: "AGE 2026",
        type: "AGE",
        held_on: "2026-05-10",
        agenda: "1. Obras",
      },
      expect.anything(),
    );
  });

  it("creates an agenda vote bound to the selected assembly", () => {
    const mutate = vi.fn();
    vi.mocked(useCreateVote).mockReturnValue({
      mutate,
      isPending: false,
    } as never);
    render(<AssemblyVotingPage />);

    fireEvent.click(screen.getByRole("button", { name: /AGO 2026/ }));
    fireEvent.click(
      screen.getByRole("button", { name: "Nova votação de pauta" }),
    );
    fireEvent.change(screen.getByLabelText("Título"), {
      target: { value: "Obra da piscina" },
    });
    fireEvent.change(screen.getByLabelText("Tipo de resposta"), {
      target: { value: "MULTIPLE_CHOICE" },
    });
    fireEvent.change(screen.getByLabelText("Fecha em"), {
      target: { value: "2026-06-01T12:00" },
    });
    fireEvent.change(screen.getByLabelText("Texto da opção 1"), {
      target: { value: "Sim" },
    });
    fireEvent.change(screen.getByLabelText("Texto da opção 2"), {
      target: { value: "Não" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Criar votação" }));

    expect(mutate).toHaveBeenCalledWith(
      expect.objectContaining({
        assembly_id: "assembly-1",
        kind: "ASSEMBLEIA",
        title: "Obra da piscina",
        vote_type: "MULTIPLE_CHOICE",
        is_anonymous: false,
        options: [
          { label: "Sim", order_index: 0 },
          { label: "Não", order_index: 1 },
        ],
      }),
      expect.anything(),
    );
  });

  it("creates an anonymous poll and shows the anonymity copy", () => {
    const mutate = vi.fn();
    vi.mocked(useCreateVote).mockReturnValue({
      mutate,
      isPending: false,
    } as never);
    render(<AssemblyVotingPage />);

    fireEvent.click(screen.getByRole("button", { name: "Enquete" }));
    fireEvent.click(screen.getByRole("button", { name: "Nova enquete" }));
    fireEvent.click(screen.getByLabelText("Enquete anônima"));

    expect(
      screen.getByText("Sua resposta não é exibida com seu nome."),
    ).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Título"), {
      target: { value: "Cor da fachada" },
    });
    fireEvent.change(screen.getByLabelText("Fecha em"), {
      target: { value: "2026-06-01T12:00" },
    });
    fireEvent.change(screen.getByLabelText("Texto da opção 1"), {
      target: { value: "Bege" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Adicionar opção" }));
    fireEvent.change(screen.getByLabelText("Texto da opção 3"), {
      target: { value: "Cinza" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Criar votação" }));

    expect(mutate).toHaveBeenCalledWith(
      expect.objectContaining({
        assembly_id: null,
        kind: "ENQUETE",
        is_anonymous: true,
        options: [
          { label: "Bege", order_index: 0 },
          { label: "Cinza", order_index: 1 },
        ],
      }),
      expect.anything(),
    );
  });

  it("closes a vote early", () => {
    const mutate = vi.fn();
    vi.mocked(useCloseVote).mockReturnValue({
      mutate,
      isPending: false,
    } as never);
    render(<AssemblyVotingPage />);

    fireEvent.click(screen.getByRole("button", { name: "Fechar votação" }));
    expect(mutate).toHaveBeenCalledWith("vote-1", expect.anything());
  });

  it("shows the empty states when there is nothing yet", () => {
    vi.mocked(useAssemblies).mockReturnValue({
      data: [],
      isLoading: false,
    } as never);
    vi.mocked(useVotes).mockReturnValue({
      data: [],
      isLoading: false,
    } as never);
    render(<AssemblyVotingPage />);

    expect(
      screen.getByText("Nenhuma assembleia cadastrada."),
    ).toBeInTheDocument();
    expect(screen.getByText("Nenhuma votação cadastrada.")).toBeInTheDocument();
  });

  it("shows loading states while fetching", () => {
    vi.mocked(useAssemblies).mockReturnValue({
      data: undefined,
      isLoading: true,
    } as never);
    vi.mocked(useVotes).mockReturnValue({
      data: undefined,
      isLoading: true,
    } as never);
    render(<AssemblyVotingPage />);

    expect(screen.getByText("Carregando assembleias...")).toBeInTheDocument();
    expect(screen.getByText("Carregando votações...")).toBeInTheDocument();
  });

  it("surfaces API errors raised by the mutations", () => {
    vi.mocked(useCloseVote).mockReturnValue({
      mutate: vi.fn((_id, options) =>
        options?.onError?.({
          response: { data: { detail: "Esta votação já está fechada." } },
        }),
      ),
      isPending: false,
    } as never);
    render(<AssemblyVotingPage />);

    fireEvent.click(screen.getByRole("button", { name: "Fechar votação" }));
    expect(
      screen.getByText("Esta votação já está fechada."),
    ).toBeInTheDocument();
  });

  it("surfaces creation errors from both forms", () => {
    vi.mocked(useCreateAssembly).mockReturnValue({
      mutate: vi.fn((_payload, options) =>
        options?.onError?.({
          response: { data: { detail: "Assembleia inválida" } },
        }),
      ),
      isPending: false,
    } as never);
    vi.mocked(useCreateVote).mockReturnValue({
      mutate: vi.fn((_payload, options) =>
        options?.onError?.({
          response: { data: { detail: "Votação de assembleia é sempre nominal." } },
        }),
      ),
      isPending: false,
    } as never);
    render(<AssemblyVotingPage />);

    fireEvent.click(screen.getByRole("button", { name: "Nova Assembleia" }));
    fireEvent.click(screen.getByRole("button", { name: "Criar assembleia" }));
    expect(screen.getByText("Assembleia inválida")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /AGO 2026/ }));
    fireEvent.click(
      screen.getByRole("button", { name: "Nova votação de pauta" }),
    );
    fireEvent.click(screen.getByRole("button", { name: "Criar votação" }));
    expect(
      screen.getByText("Votação de assembleia é sempre nominal."),
    ).toBeInTheDocument();
  });

  it("clears both forms after a successful creation", () => {
    vi.mocked(useCreateAssembly).mockReturnValue({
      mutate: vi.fn((_payload, options) => options?.onSuccess?.()),
      isPending: false,
    } as never);
    vi.mocked(useCreateVote).mockReturnValue({
      mutate: vi.fn((_payload, options) => options?.onSuccess?.()),
      isPending: false,
    } as never);
    render(<AssemblyVotingPage />);

    fireEvent.click(screen.getByRole("button", { name: "Nova Assembleia" }));
    fireEvent.click(screen.getByRole("button", { name: "Criar assembleia" }));
    expect(
      screen.queryByRole("button", { name: "Criar assembleia" }),
    ).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /AGO 2026/ }));
    fireEvent.click(
      screen.getByRole("button", { name: "Nova votação de pauta" }),
    );
    fireEvent.click(screen.getByRole("button", { name: "Criar votação" }));
    expect(
      screen.queryByRole("button", { name: "Criar votação" }),
    ).not.toBeInTheDocument();
  });

  it("surfaces the error raised when closing an assembly", () => {
    vi.mocked(useCloseAssembly).mockReturnValue({
      mutate: vi.fn((_id, options) =>
        options?.onError?.({
          response: { data: { detail: "Assembleia já está fechada." } },
        }),
      ),
      isPending: false,
    } as never);
    render(<AssemblyVotingPage />);

    fireEvent.click(screen.getByRole("button", { name: "Encerrar assembleia" }));
    expect(screen.getByText("Assembleia já está fechada.")).toBeInTheDocument();
  });

  it("closes an assembly through the board action", () => {
    const mutate = vi.fn();
    vi.mocked(useCloseAssembly).mockReturnValue({
      mutate,
      isPending: false,
    } as never);
    render(<AssemblyVotingPage />);

    fireEvent.click(screen.getByRole("button", { name: "Encerrar assembleia" }));
    expect(mutate).toHaveBeenCalledWith("assembly-1", expect.anything());
  });

  it("releases a DRAFT assembly so its votes start accepting ballots", () => {
    const mutate = vi.fn();
    vi.mocked(useAssemblies).mockReturnValue({
      data: [draftAssembly],
      isLoading: false,
    } as never);
    vi.mocked(useUpdateAssembly).mockReturnValue({
      mutate,
      isPending: false,
    } as never);
    render(<AssemblyVotingPage />);

    expect(
      screen.getByText(
        "Libere a pauta para que as votações passem a aceitar cédulas.",
      ),
    ).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Liberar pauta" }));
    expect(mutate).toHaveBeenCalledWith(
      { id: "assembly-1", data: { status: "OPEN" } },
      expect.anything(),
    );
  });

  it("does not offer the release action once the assembly is open", () => {
    render(<AssemblyVotingPage />);

    expect(
      screen.queryByRole("button", { name: "Liberar pauta" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText(
        "Libere a pauta para que as votações passem a aceitar cédulas.",
      ),
    ).not.toBeInTheDocument();
  });

  it("does not offer the release action to a non-board role", () => {
    setRole(UserRole.MANAGER);
    vi.mocked(useAssemblies).mockReturnValue({
      data: [draftAssembly],
      isLoading: false,
    } as never);
    render(<AssemblyVotingPage />);

    expect(
      screen.queryByRole("button", { name: "Liberar pauta" }),
    ).not.toBeInTheDocument();
  });

  it("surfaces the error raised when releasing an assembly", () => {
    vi.mocked(useAssemblies).mockReturnValue({
      data: [draftAssembly],
      isLoading: false,
    } as never);
    vi.mocked(useUpdateAssembly).mockReturnValue({
      mutate: vi.fn((_payload, options) =>
        options?.onError?.({
          response: { data: { detail: "Assembleia fechada não pode ser editada." } },
        }),
      ),
      isPending: false,
    } as never);
    render(<AssemblyVotingPage />);

    fireEvent.click(screen.getByRole("button", { name: "Liberar pauta" }));
    expect(
      screen.getByText("Assembleia fechada não pode ser editada."),
    ).toBeInTheDocument();
  });

  it("falls back to the generic copy when releasing fails without a detail", () => {
    vi.mocked(useAssemblies).mockReturnValue({
      data: [draftAssembly],
      isLoading: false,
    } as never);
    vi.mocked(useUpdateAssembly).mockReturnValue({
      mutate: vi.fn((_payload, options) => options?.onError?.({})),
      isPending: false,
    } as never);
    render(<AssemblyVotingPage />);

    fireEvent.click(screen.getByRole("button", { name: "Liberar pauta" }));
    expect(screen.getByText("Erro ao liberar a pauta.")).toBeInTheDocument();
  });
});
