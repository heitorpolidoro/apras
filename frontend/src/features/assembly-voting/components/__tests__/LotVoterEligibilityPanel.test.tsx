import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import LotVoterEligibilityPanel from "../LotVoterEligibilityPanel";
import {
  useAddLotVoterEligibility,
  useLotVoterEligibility,
  useRemoveLotVoterEligibility,
} from "../../hooks/useVoting";

vi.mock("../../hooks/useVoting", () => ({
  useAddLotVoterEligibility: vi.fn(),
  useLotVoterEligibility: vi.fn(),
  useRemoveLotVoterEligibility: vi.fn(),
}));

const entry = {
  id: "elig-1",
  lot_id: "lot-1",
  user_id: "user-9",
  user_name: "Cônjuge",
  added_by_id: "manager-1",
  added_at: "2026-01-01T00:00:00",
};

describe("LotVoterEligibilityPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useAddLotVoterEligibility).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as never);
    vi.mocked(useRemoveLotVoterEligibility).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as never);
  });

  it("shows the empty state when the lot has no extra voter", () => {
    vi.mocked(useLotVoterEligibility).mockReturnValue({ data: [] } as never);
    render(<LotVoterEligibilityPanel lotId="lot-1" />);
    expect(
      screen.getByText("Nenhum elegível extra cadastrado."),
    ).toBeInTheDocument();
  });

  it("lists the extra voters and removes one", () => {
    const mutate = vi.fn();
    vi.mocked(useLotVoterEligibility).mockReturnValue({
      data: [entry],
    } as never);
    vi.mocked(useRemoveLotVoterEligibility).mockReturnValue({
      mutate,
      isPending: false,
    } as never);

    render(<LotVoterEligibilityPanel lotId="lot-1" />);
    expect(screen.getByText("Cônjuge")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Remover" }));
    expect(mutate).toHaveBeenCalledWith(
      { lotId: "lot-1", userId: "user-9" },
      expect.anything(),
    );
  });

  it("adds an extra voter by user id", () => {
    const mutate = vi.fn();
    vi.mocked(useLotVoterEligibility).mockReturnValue({ data: [] } as never);
    vi.mocked(useAddLotVoterEligibility).mockReturnValue({
      mutate,
      isPending: false,
    } as never);

    render(<LotVoterEligibilityPanel lotId="lot-1" />);
    fireEvent.change(screen.getByLabelText("ID do usuário"), {
      target: { value: "user-9" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Adicionar elegível" }));

    expect(mutate).toHaveBeenCalledWith(
      { lotId: "lot-1", userId: "user-9" },
      expect.anything(),
    );
  });

  it("ignores an empty user id", () => {
    const mutate = vi.fn();
    vi.mocked(useLotVoterEligibility).mockReturnValue({ data: [] } as never);
    vi.mocked(useAddLotVoterEligibility).mockReturnValue({
      mutate,
      isPending: false,
    } as never);

    render(<LotVoterEligibilityPanel lotId="lot-1" />);
    fireEvent.click(screen.getByRole("button", { name: "Adicionar elegível" }));

    expect(mutate).not.toHaveBeenCalled();
  });

  it("surfaces API errors from add and remove", () => {
    vi.mocked(useLotVoterEligibility).mockReturnValue({
      data: [entry],
    } as never);
    vi.mocked(useAddLotVoterEligibility).mockReturnValue({
      mutate: vi.fn((_payload, options) =>
        options?.onError?.({ response: { data: { detail: "Duplicado" } } }),
      ),
      isPending: false,
    } as never);
    vi.mocked(useRemoveLotVoterEligibility).mockReturnValue({
      mutate: vi.fn((_payload, options) =>
        options?.onError?.({ response: { data: { detail: "Não encontrado" } } }),
      ),
      isPending: false,
    } as never);

    render(<LotVoterEligibilityPanel lotId="lot-1" />);

    fireEvent.change(screen.getByLabelText("ID do usuário"), {
      target: { value: "user-9" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Adicionar elegível" }));
    expect(screen.getByText("Duplicado")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Remover" }));
    expect(screen.getByText("Não encontrado")).toBeInTheDocument();
  });
});
