import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import VoteBallotCard from "../VoteBallotCard";
import {
  useMyBallot,
  useCastBallot,
  useRetractBallot,
} from "../../hooks/useVoting";
import type { MyBallotRead, VoteRead } from "../../../../types/voting";

vi.mock("../../hooks/useVoting", () => ({
  useMyBallot: vi.fn(),
  useCastBallot: vi.fn(),
  useRetractBallot: vi.fn(),
}));

const openVote: VoteRead = {
  id: "vote-1",
  assembly_id: "assembly-1",
  kind: "ASSEMBLEIA",
  title: "Orçamento 2026",
  description: null,
  vote_type: "SINGLE_CHOICE",
  status: "OPEN",
  is_anonymous: false,
  opens_at: "2020-01-01T00:00:00",
  closes_at: "2999-12-01T00:00:00",
  created_by_id: "admin-1",
  created_at: "2020-01-01T00:00:00",
  updated_at: "2020-01-01T00:00:00",
  closed_at: null,
  options: [
    { id: "opt-1", vote_id: "vote-1", label: "Sim", order_index: 0 },
    { id: "opt-2", vote_id: "vote-1", label: "Não", order_index: 1 },
  ],
};

const eligibleLots = [{ id: "lot-1", label: "A/1" }];

const holderBallot: MyBallotRead = {
  id: "ballot-1",
  vote_id: "vote-1",
  lot_id: "lot-1",
  lot_label: "A/1",
  voter_user_id: "user-1",
  voter_name: "Fulano",
  is_retraction: false,
  selected_option_ids: ["opt-1"],
  cast_at: "2026-02-01T10:00:00",
  can_edit: true,
};

const peerBallot: MyBallotRead = { ...holderBallot, can_edit: false };

const mockHooks = (
  ballots: MyBallotRead[],
  cast = vi.fn(),
  retract = vi.fn(),
) => {
  vi.mocked(useMyBallot).mockReturnValue({
    data: ballots,
    isLoading: false,
  } as never);
  vi.mocked(useCastBallot).mockReturnValue({
    mutate: cast,
    isPending: false,
  } as never);
  vi.mocked(useRetractBallot).mockReturnValue({
    mutate: retract,
    isPending: false,
  } as never);
};

describe("VoteBallotCard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("offers change and retract to the ballot holder while the window is open", () => {
    mockHooks([holderBallot]);
    render(<VoteBallotCard vote={openVote} eligibleLots={eligibleLots} />);

    expect(screen.getByRole("button", { name: "Trocar voto" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retirar voto" })).toBeInTheDocument();
  });

  it("shows another eligible voter's ballot read-only, with no action buttons", () => {
    mockHooks([peerBallot]);
    render(<VoteBallotCard vote={openVote} eligibleLots={eligibleLots} />);

    expect(
      screen.getByText(
        "Votado por Fulano. Você também pode votar se ele retirar a cédula.",
      ),
    ).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Trocar voto" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Retirar voto" })).not.toBeInTheDocument();
  });

  it("hides the actions once the voting window is over", () => {
    mockHooks([holderBallot]);
    render(
      <VoteBallotCard
        vote={{ ...openVote, status: "CLOSED" }}
        eligibleLots={eligibleLots}
      />,
    );

    expect(screen.queryByRole("button", { name: "Trocar voto" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Retirar voto" })).not.toBeInTheDocument();
    expect(screen.getByText("A votação está fechada.")).toBeInTheDocument();
  });

  it("casts a ballot for the selected lot when nothing was cast yet", () => {
    const cast = vi.fn();
    mockHooks([], cast);
    render(<VoteBallotCard vote={openVote} eligibleLots={eligibleLots} />);

    fireEvent.click(screen.getByLabelText("Sim"));
    fireEvent.click(screen.getByRole("button", { name: "Votar" }));

    expect(cast).toHaveBeenCalledWith(
      {
        voteId: "vote-1",
        data: { lot_id: "lot-1", selected_option_ids: ["opt-1"] },
      },
      expect.anything(),
    );
  });

  it("retracts the holder's ballot for its own lot", () => {
    const retract = vi.fn();
    mockHooks([holderBallot], vi.fn(), retract);
    render(<VoteBallotCard vote={openVote} eligibleLots={eligibleLots} />);

    fireEvent.click(screen.getByRole("button", { name: "Retirar voto" }));

    expect(retract).toHaveBeenCalledWith(
      { voteId: "vote-1", data: { lot_id: "lot-1" } },
      expect.anything(),
    );
  });

  it("confirms a change with the option picked in the change form", () => {
    const cast = vi.fn();
    mockHooks([holderBallot], cast);
    render(<VoteBallotCard vote={openVote} eligibleLots={eligibleLots} />);

    fireEvent.click(screen.getByRole("button", { name: "Trocar voto" }));
    fireEvent.click(screen.getByLabelText("Não"));
    fireEvent.click(screen.getByRole("button", { name: "Confirmar troca" }));

    expect(cast).toHaveBeenCalledWith(
      {
        voteId: "vote-1",
        data: { lot_id: "lot-1", selected_option_ids: ["opt-2"] },
      },
      expect.anything(),
    );
  });

  it("abandons the change form on cancel", () => {
    mockHooks([holderBallot]);
    render(<VoteBallotCard vote={openVote} eligibleLots={eligibleLots} />);

    fireEvent.click(screen.getByRole("button", { name: "Trocar voto" }));
    fireEvent.click(screen.getByRole("button", { name: "Cancelar" }));

    expect(
      screen.queryByRole("button", { name: "Confirmar troca" }),
    ).not.toBeInTheDocument();
  });

  it("lets a multi-lot voter pick which unit to vote for", () => {
    const cast = vi.fn();
    mockHooks([], cast);
    render(
      <VoteBallotCard
        vote={openVote}
        eligibleLots={[
          { id: "lot-1", label: "A/1" },
          { id: "lot-2", label: "A/2" },
        ]}
      />,
    );

    fireEvent.change(screen.getByLabelText("Votar pelo lote"), {
      target: { value: "lot-2" },
    });
    fireEvent.click(screen.getByLabelText("Sim"));
    fireEvent.click(screen.getByRole("button", { name: "Votar" }));

    expect(cast).toHaveBeenCalledWith(
      {
        voteId: "vote-1",
        data: { lot_id: "lot-2", selected_option_ids: ["opt-1"] },
      },
      expect.anything(),
    );
  });

  it("accumulates selections in a multiple-choice vote", () => {
    const cast = vi.fn();
    mockHooks([], cast);
    render(
      <VoteBallotCard
        vote={{ ...openVote, vote_type: "MULTIPLE_CHOICE" }}
        eligibleLots={eligibleLots}
      />,
    );

    fireEvent.click(screen.getByLabelText("Sim"));
    fireEvent.click(screen.getByLabelText("Não"));
    fireEvent.click(screen.getByLabelText("Não"));
    fireEvent.click(screen.getByLabelText("Não"));
    fireEvent.click(screen.getByRole("button", { name: "Votar" }));

    expect(cast).toHaveBeenCalledWith(
      {
        voteId: "vote-1",
        data: { lot_id: "lot-1", selected_option_ids: ["opt-1", "opt-2"] },
      },
      expect.anything(),
    );
  });

  it("shows the anonymity copy on an anonymous poll", () => {
    mockHooks([]);
    render(
      <VoteBallotCard
        vote={{
          ...openVote,
          kind: "ENQUETE",
          assembly_id: null,
          is_anonymous: true,
        }}
      />,
    );

    expect(
      screen.getByText("Sua resposta não é exibida com seu nome."),
    ).toBeInTheDocument();
  });

  it("surfaces the API error message when a ballot is refused", () => {
    const cast = vi.fn((_payload, options) =>
      options?.onError?.({
        response: { data: { detail: "Lote inadimplente: direito de voto suspenso." } },
      }),
    );
    mockHooks([], cast);
    render(<VoteBallotCard vote={openVote} eligibleLots={eligibleLots} />);

    fireEvent.click(screen.getByLabelText("Sim"));
    fireEvent.click(screen.getByRole("button", { name: "Votar" }));

    expect(
      screen.getByText("Lote inadimplente: direito de voto suspenso."),
    ).toBeInTheDocument();
  });

  it("surfaces the API error message when a retraction is refused", () => {
    const retract = vi.fn((_payload, options) =>
      options?.onError?.({
        response: { data: { detail: "Não há cédula ativa para retirar." } },
      }),
    );
    mockHooks([holderBallot], vi.fn(), retract);
    render(<VoteBallotCard vote={openVote} eligibleLots={eligibleLots} />);

    fireEvent.click(screen.getByRole("button", { name: "Retirar voto" }));

    expect(
      screen.getByText("Não há cédula ativa para retirar."),
    ).toBeInTheDocument();
  });

  it("clears the form after a successful ballot", () => {
    const cast = vi.fn((_payload, options) => options?.onSuccess?.());
    mockHooks([], cast);
    render(<VoteBallotCard vote={openVote} eligibleLots={eligibleLots} />);

    fireEvent.click(screen.getByLabelText("Sim"));
    fireEvent.click(screen.getByRole("button", { name: "Votar" }));

    expect(screen.getByRole("button", { name: "Votar" })).toBeDisabled();
  });

  it("sends a null lot_id when retracting a poll ballot", () => {
    const retract = vi.fn();
    mockHooks(
      [{ ...holderBallot, lot_id: null, lot_label: null }],
      vi.fn(),
      retract,
    );
    render(
      <VoteBallotCard
        vote={{ ...openVote, kind: "ENQUETE", assembly_id: null }}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Retirar voto" }));

    expect(retract).toHaveBeenCalledWith(
      { voteId: "vote-1", data: { lot_id: null } },
      expect.anything(),
    );
  });
});
