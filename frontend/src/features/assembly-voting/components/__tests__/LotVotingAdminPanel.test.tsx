import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import LotVotingAdminPanel from "../LotVotingAdminPanel";
import { useLots } from "../../../lot-management/hooks/useLots";
import { useUpdateLotDelinquency } from "../../hooks/useVoting";
import { useEffectiveIdentity } from "../../../user-administration/context/useEffectiveIdentity";
import { UserRole } from "../../../../types/auth";

vi.mock("../../../lot-management/hooks/useLots", () => ({
  useLots: vi.fn(),
}));

vi.mock("../../hooks/useVoting", () => ({
  useUpdateLotDelinquency: vi.fn(),
  useLotVoterEligibility: vi.fn(() => ({ data: [] })),
  useAddLotVoterEligibility: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  useRemoveLotVoterEligibility: vi.fn(() => ({
    mutate: vi.fn(),
    isPending: false,
  })),
}));

vi.mock("../../../user-administration/context/useEffectiveIdentity", () => ({
  useEffectiveIdentity: vi.fn(),
}));

const lot = {
  id: "lot-1",
  block: "A",
  lot_number: "1",
  status: "OCCUPIED",
  is_deleted: false,
  is_delinquent: false,
  created_at: "2026-01-01T00:00:00",
  updated_at: "2026-01-01T00:00:00",
};

const selectLot = () =>
  fireEvent.change(screen.getByLabelText(/Lote/), {
    target: { value: "lot-1" },
  });

describe("LotVotingAdminPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useEffectiveIdentity).mockReturnValue({
      role: UserRole.ADMINISTRATOR,
    } as never);
    vi.mocked(useLots).mockReturnValue({
      data: { items: [lot], total: 1, skip: 0, limit: 100 },
    } as never);
    vi.mocked(useUpdateLotDelinquency).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as never);
  });

  it("marks a lot as delinquent", () => {
    const mutate = vi.fn();
    vi.mocked(useUpdateLotDelinquency).mockReturnValue({
      mutate,
      isPending: false,
    } as never);

    render(<LotVotingAdminPanel />);
    selectLot();

    expect(screen.getByTestId("delinquency-state")).toHaveTextContent(
      "Lote adimplente: pode votar.",
    );
    fireEvent.click(
      screen.getByRole("button", { name: "Marcar como inadimplente" }),
    );

    expect(mutate).toHaveBeenCalledWith(
      { lotId: "lot-1", isDelinquent: true },
      expect.anything(),
    );
  });

  it("offers the settle action for an already delinquent lot", () => {
    vi.mocked(useLots).mockReturnValue({
      data: {
        items: [{ ...lot, is_delinquent: true }],
        total: 1,
        skip: 0,
        limit: 100,
      },
    } as never);

    render(<LotVotingAdminPanel />);
    selectLot();

    expect(screen.getByTestId("delinquency-state")).toHaveTextContent(
      "Lote inadimplente: voto suspenso.",
    );
    expect(
      screen.getByRole("button", { name: "Marcar como adimplente" }),
    ).toBeInTheDocument();
  });

  it("hides the delinquency action from a MANAGER but keeps the voter list", () => {
    vi.mocked(useEffectiveIdentity).mockReturnValue({
      role: UserRole.MANAGER,
    } as never);

    render(<LotVotingAdminPanel />);
    selectLot();

    expect(
      screen.queryByRole("button", { name: "Marcar como inadimplente" }),
    ).not.toBeInTheDocument();
    expect(
      screen.getByText("Elegíveis extras do lote"),
    ).toBeInTheDocument();
  });

  it("surfaces the API error when the flag cannot be changed", () => {
    vi.mocked(useUpdateLotDelinquency).mockReturnValue({
      mutate: vi.fn((_payload, options) =>
        options?.onError?.({
          response: { data: { detail: "Sem permissão" } },
        }),
      ),
      isPending: false,
    } as never);

    render(<LotVotingAdminPanel />);
    selectLot();
    fireEvent.click(
      screen.getByRole("button", { name: "Marcar como inadimplente" }),
    );

    expect(screen.getByText("Sem permissão")).toBeInTheDocument();
  });

  it("shows nothing lot-specific until a lot is picked", () => {
    render(<LotVotingAdminPanel />);
    expect(screen.queryByTestId("delinquency-state")).not.toBeInTheDocument();
  });
});
