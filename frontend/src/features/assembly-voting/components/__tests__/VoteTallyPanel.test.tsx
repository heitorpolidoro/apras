import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import VoteTallyPanel from "../VoteTallyPanel";
import { useTally } from "../../hooks/useVoting";
import type { TallyRead, VoteRead } from "../../../../types/voting";

vi.mock("../../hooks/useVoting", () => ({
  useTally: vi.fn(),
}));

const assemblyVote: VoteRead = {
  id: "vote-1",
  assembly_id: "assembly-1",
  kind: "ASSEMBLEIA",
  title: "Orçamento 2026",
  description: null,
  vote_type: "SINGLE_CHOICE",
  status: "OPEN",
  is_anonymous: false,
  opens_at: "2026-01-01T00:00:00",
  closes_at: "2026-12-01T00:00:00",
  created_by_id: "admin-1",
  created_at: "2026-01-01T00:00:00",
  updated_at: "2026-01-01T00:00:00",
  closed_at: null,
  options: [
    { id: "opt-1", vote_id: "vote-1", label: "Sim", order_index: 0 },
    { id: "opt-2", vote_id: "vote-1", label: "Não", order_index: 1 },
  ],
};

const poll: VoteRead = {
  ...assemblyVote,
  id: "vote-2",
  assembly_id: null,
  kind: "ENQUETE",
  title: "Cor da fachada",
};

const mockTally = (tally: TallyRead) => {
  vi.mocked(useTally).mockReturnValue({
    data: tally,
    isLoading: false,
  } as never);
};

describe("VoteTallyPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows only the voter count while the vote is open", () => {
    mockTally({
      vote_id: "vote-1",
      kind: "ASSEMBLEIA",
      status: "OPEN",
      is_anonymous: false,
      voters_count: 3,
      total_lots: 10,
    });

    render(<VoteTallyPanel vote={assemblyVote} />);

    expect(screen.getByTestId("tally-voters-count")).toHaveTextContent("3");
    expect(screen.queryByTestId("tally-results")).not.toBeInTheDocument();
    expect(screen.queryByTestId("tally-attributions")).not.toBeInTheDocument();
    expect(
      screen.getByText(
        "O resultado por opção só aparece depois do fechamento.",
      ),
    ).toBeInTheDocument();
  });

  it("shows the active-lot denominator only for assemblies", () => {
    mockTally({
      vote_id: "vote-1",
      kind: "ASSEMBLEIA",
      status: "OPEN",
      is_anonymous: false,
      voters_count: 3,
      total_lots: 10,
    });
    const { unmount } = render(<VoteTallyPanel vote={assemblyVote} />);
    expect(screen.getByTestId("tally-denominator")).toHaveTextContent("10");
    unmount();

    mockTally({
      vote_id: "vote-2",
      kind: "ENQUETE",
      status: "OPEN",
      is_anonymous: false,
      voters_count: 12,
    });
    render(<VoteTallyPanel vote={poll} />);
    expect(screen.queryByTestId("tally-denominator")).not.toBeInTheDocument();
    expect(screen.getByTestId("tally-voters-count")).toHaveTextContent("12");
  });

  it("renders per-option results and attribution once closed", () => {
    mockTally({
      vote_id: "vote-1",
      kind: "ASSEMBLEIA",
      status: "CLOSED",
      is_anonymous: false,
      voters_count: 1,
      total_lots: 10,
      results: [
        { option_id: "opt-1", label: "Sim", count: 1 },
        { option_id: "opt-2", label: "Não", count: 0 },
      ],
      attributions: [
        {
          lot_id: "lot-1",
          lot_label: "A/1",
          selected_labels: ["Sim"],
          cast_at: "2026-02-01T10:00:00",
        },
      ],
    });

    render(<VoteTallyPanel vote={{ ...assemblyVote, status: "CLOSED" }} />);

    expect(screen.getByTestId("tally-results")).toBeInTheDocument();
    expect(screen.getByTestId("tally-attributions")).toHaveTextContent("A/1");
    expect(
      screen.queryByText(
        "O resultado por opção só aparece depois do fechamento.",
      ),
    ).not.toBeInTheDocument();
  });

  it("shows the anonymity notice and no attribution for an anonymous poll", () => {
    mockTally({
      vote_id: "vote-2",
      kind: "ENQUETE",
      status: "CLOSED",
      is_anonymous: true,
      voters_count: 5,
      results: [{ option_id: "opt-1", label: "Bege", count: 5 }],
    });

    render(
      <VoteTallyPanel
        vote={{ ...poll, status: "CLOSED", is_anonymous: true }}
      />,
    );

    expect(screen.getByTestId("tally-results")).toBeInTheDocument();
    expect(screen.queryByTestId("tally-attributions")).not.toBeInTheDocument();
    expect(
      screen.getByText("Enquete anônima: só o agregado é exibido."),
    ).toBeInTheDocument();
  });
});
