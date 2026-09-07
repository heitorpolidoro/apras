import {
  render,
  screen,
  fireEvent,
  waitFor,
  within,
} from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MyInfractionsPage } from "../pages/MyInfractionsPage";
import { ContestationForm } from "../components/ContestationForm";
import { InfractionStageTimeline } from "../components/InfractionStageTimeline";
import * as api from "../../../api/infractions";
import { useMyPermissions } from "../../../hooks/usePermissionQueries";
import { settledPermissions } from "../../../test/permissionFixtures";
import type {
  Infraction,
  InfractionTimelineEntry,
} from "../../../types/infraction";

vi.mock("../../../api/infractions");

/** The resident who contests **and** may attach (APRAS-53 §3.6(a)). */
const RESIDENT_WITH_ATTACHMENTS = [
  "infractions:contest",
  "infractions:my_lots_read",
  "uploads:photo_create",
];

vi.mock("../../../hooks/usePermissionQueries", () => ({
  useMyPermissions: vi.fn(),
  usePermissionCatalogue: vi.fn(() => ({ data: [], isPending: false })),
}));

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

const withProvider = (node: React.ReactNode) =>
  render(
    <QueryClientProvider
      client={
        new QueryClient({
          defaultOptions: { queries: { retry: false, gcTime: 0 } },
        })
      }
    >
      {node}
    </QueryClientProvider>,
  );

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(useMyPermissions).mockReturnValue(
    settledPermissions(RESIDENT_WITH_ATTACHMENTS) as never,
  );
});

describe("MyInfractionsPage", () => {

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
        // Present and empty: a defense with no attachment is a valid defense.
        attachment_urls: [],
      }),
    );
  });
});

describe("InfractionStageTimeline — attachments (APRAS-53 ER-2)", () => {
  const entry = (
    overrides: Partial<InfractionTimelineEntry> = {},
  ): InfractionTimelineEntry => ({
    kind: "CONTESTATION",
    id: "entry-1",
    at: "2026-09-02T10:00:00",
    actor: null,
    action: null,
    note: "Estava viajando.",
    fine_amount: null,
    fine_amount_overridden: null,
    defense_due_on: null,
    policy_step_order: null,
    suggestion_followed: null,
    attachment_urls: [],
    ...overrides,
  });

  it("renders a contestation's attachments read-only", () => {
    render(
      <InfractionStageTimeline
        entries={[
          entry({ attachment_urls: ["/static/uploads/2026/09/defesa.png"] }),
        ]}
      />,
    );

    const block = screen.getByTestId("timeline-attachments");
    expect(block).toHaveTextContent("/static/uploads/2026/09/defesa.png");
    expect(screen.getByAltText("Anexo 1")).toHaveAttribute(
      "src",
      "/static/uploads/2026/09/defesa.png",
    );
    // Read-only: nothing in this component removes or replaces an attachment.
    expect(
      within(block).queryByTestId("attachment-remove"),
    ).not.toBeInTheDocument();
  });

  it("renders no attachment block when the entry carries none", () => {
    render(<InfractionStageTimeline entries={[entry()]} />);

    expect(
      screen.queryByTestId("timeline-attachments"),
    ).not.toBeInTheDocument();
  });
});

describe("ContestationForm", () => {
  it("is enabled inside the deadline", () => {
    withProvider(
      <ContestationForm
        infractionId="inf-1"
        defenseDueOn={OPEN_DEADLINE}
        onSubmit={vi.fn()}
      />,
    );

    expect(screen.getByTestId("contestation-form")).toBeInTheDocument();
    // Still disabled until something is typed: an empty defense is a 422.
    expect(screen.getByTestId("submit-contestation")).toBeDisabled();
    fireEvent.change(screen.getByLabelText("Sua defesa"), {
      target: { value: "x" },
    });
    expect(screen.getByTestId("submit-contestation")).toBeEnabled();
  });

  it("is disabled with an explanatory message outside the deadline", () => {
    withProvider(
      <ContestationForm
        infractionId="inf-1"
        defenseDueOn={PAST_DEADLINE}
        onSubmit={vi.fn()}
      />,
    );

    expect(screen.getByTestId("contestation-unavailable")).toHaveTextContent(
      PAST_DEADLINE,
    );
    expect(screen.queryByTestId("submit-contestation")).not.toBeInTheDocument();
  });

  it("is disabled with a different message when no NOTIFICACAO exists", () => {
    withProvider(
      <ContestationForm
        infractionId="inf-1"
        defenseDueOn={null}
        onSubmit={vi.fn()}
      />,
    );

    expect(screen.getByTestId("contestation-unavailable")).toHaveTextContent(
      "Não há prazo de defesa aberto",
    );
  });
});
