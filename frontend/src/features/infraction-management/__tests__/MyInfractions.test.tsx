import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MyInfractionsPage } from "../pages/MyInfractionsPage";
import { ContestationForm } from "../components/ContestationForm";
import * as api from "../../../api/infractions";
import type { Infraction } from "../../../types/infraction";

vi.mock("../../../api/infractions");

const OPEN_DEADLINE = new Date(Date.now() + 30 * 86400000)
  .toISOString()
  .slice(0, 10);
const PAST_DEADLINE = new Date(Date.now() - 30 * 86400000)
  .toISOString()
  .slice(0, 10);

const mine = (defenseDueOn: string | null): Infraction => ({
  id: "inf-1",
  rule: {
    id: "rule-1",
    article: "art. 12",
    origin: "REGIMENTO_INTERNO",
    description: "Sossego",
  },
  lot: { id: "lot-1", block: "A", lot_number: "101" },
  responsible: { id: "res-1", full_name: "Maria Souza", lot_id: "lot-1" },
  occurred_on: "2026-09-01",
  description: "Som alto às 23h.",
  evidence_urls: [],
  source_occurrence_id: null,
  source_occurrence_protocol: null,
  current_stage: defenseDueOn ? "NOTIFICACAO" : null,
  current_stage_at: null,
  defense_due_on: defenseDueOn,
  timeline: [],
  created_at: "2026-09-01T09:00:00",
});

const renderPage = () =>
  render(
    <QueryClientProvider
      client={
        new QueryClient({
          defaultOptions: { queries: { retry: false, gcTime: 0 } },
        })
      }
    >
      <MyInfractionsPage />
    </QueryClientProvider>,
  );

describe("MyInfractionsPage", () => {
  beforeEach(() => vi.clearAllMocks());

  it("lists the caller's own infractions and highlights the open deadline", async () => {
    vi.mocked(api.getMyInfractions).mockResolvedValue([mine(OPEN_DEADLINE)]);

    renderPage();

    expect(await screen.findByTestId("my-infraction-inf-1")).toBeInTheDocument();
    expect(screen.getByTestId("deadline-inf-1")).toHaveTextContent(
      OPEN_DEADLINE,
    );
  });

  it("an unlinked caller sees an empty list, never a refusal", async () => {
    // `infractions:my_lots_read` is a filter, not an inverted gate: the API
    // answers 200 with `[]`, so this page says so rather than showing an error.
    vi.mocked(api.getMyInfractions).mockResolvedValue([]);

    renderPage();

    expect(
      await screen.findByTestId("my-infractions-empty"),
    ).toBeInTheDocument();
  });

  it("submits a contestation for the infraction whose deadline is open", async () => {
    vi.mocked(api.getMyInfractions).mockResolvedValue([mine(OPEN_DEADLINE)]);
    vi.mocked(api.addContestation).mockResolvedValue(mine(OPEN_DEADLINE));

    renderPage();
    await screen.findByTestId("my-infraction-inf-1");

    fireEvent.change(screen.getByLabelText("Sua defesa"), {
      target: { value: "Estava viajando." },
    });
    fireEvent.click(screen.getByTestId("submit-contestation"));

    await waitFor(() =>
      expect(vi.mocked(api.addContestation)).toHaveBeenCalledWith("inf-1", {
        body: "Estava viajando.",
      }),
    );
  });
});

describe("ContestationForm", () => {
  it("is enabled inside the deadline", () => {
    render(<ContestationForm defenseDueOn={OPEN_DEADLINE} onSubmit={vi.fn()} />);

    expect(screen.getByTestId("contestation-form")).toBeInTheDocument();
    // Still disabled until something is typed: an empty defense is a 422.
    expect(screen.getByTestId("submit-contestation")).toBeDisabled();
    fireEvent.change(screen.getByLabelText("Sua defesa"), {
      target: { value: "x" },
    });
    expect(screen.getByTestId("submit-contestation")).toBeEnabled();
  });

  it("is disabled with an explanatory message outside the deadline", () => {
    render(<ContestationForm defenseDueOn={PAST_DEADLINE} onSubmit={vi.fn()} />);

    expect(screen.getByTestId("contestation-unavailable")).toHaveTextContent(
      PAST_DEADLINE,
    );
    expect(screen.queryByTestId("submit-contestation")).not.toBeInTheDocument();
  });

  it("is disabled with a different message when no NOTIFICACAO exists", () => {
    render(<ContestationForm defenseDueOn={null} onSubmit={vi.fn()} />);

    expect(screen.getByTestId("contestation-unavailable")).toHaveTextContent(
      "Não há prazo de defesa aberto",
    );
  });
});
