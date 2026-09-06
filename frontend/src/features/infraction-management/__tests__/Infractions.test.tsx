import {
  render,
  screen,
  fireEvent,
  waitFor,
  within,
} from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  MemoryRouter,
  Route,
  Routes,
  useLocation,
} from "react-router-dom";
import { InfractionsPage } from "../pages/InfractionsPage";
import { InfractionStageTimeline } from "../components/InfractionStageTimeline";
import { InfractionDetailsView } from "../components/InfractionDetailsView";
import * as api from "../../../api/infractions";
import * as occurrencesApi from "../../../api/occurrences";
import * as lotsApi from "../../../api/lots";
import * as residentsApi from "../../../api/residents";
import type { Infraction } from "../../../types/infraction";

vi.mock("../../../api/infractions");
vi.mock("../../../api/occurrences");
vi.mock("../../../api/lots");
vi.mock("../../../api/residents");

const infraction: Infraction = {
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
  evidence_urls: ["http://null/a.jpg"],
  source_occurrence_id: "occ-1",
  source_occurrence_protocol: "OCO-2026-000009",
  current_stage: "NOTIFICACAO",
  current_stage_at: "2026-09-02T10:00:00",
  defense_due_on: "2026-10-02",
  timeline: [
    {
      kind: "STAGE",
      id: "stage-1",
      at: "2026-09-01T10:00:00",
      actor: { id: "u-1", full_name: "Síndico" },
      action: "AVISO",
      note: "Aviso entregue.",
      fine_amount: null,
      fine_amount_overridden: null,
      defense_due_on: null,
      policy_step_order: 1,
      suggestion_followed: true,
      attachment_urls: [],
    },
    {
      kind: "STAGE",
      id: "stage-2",
      at: "2026-09-02T10:00:00",
      actor: { id: "u-1", full_name: "Síndico" },
      action: "NOTIFICACAO",
      note: "Notificação enviada.",
      fine_amount: null,
      fine_amount_overridden: null,
      defense_due_on: "2026-10-02",
      policy_step_order: 2,
      suggestion_followed: true,
      attachment_urls: [],
    },
    {
      kind: "CONTESTATION",
      id: "cont-1",
      at: "2026-09-03T10:00:00",
      actor: { id: "u-2", full_name: "Maria Souza" },
      action: null,
      note: "Estava viajando.",
      fine_amount: null,
      fine_amount_overridden: null,
      defense_due_on: null,
      policy_step_order: null,
      suggestion_followed: null,
      attachment_urls: [],
    },
  ],
  created_at: "2026-09-01T09:00:00",
};

const createClient = () =>
  new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });

const renderPage = () =>
  render(
    <QueryClientProvider client={createClient()}>
      <MemoryRouter>
        <InfractionsPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );

describe("InfractionsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.getInfractions).mockResolvedValue({
      items: [infraction],
      total: 1,
      skip: 0,
      limit: 20,
    });
    vi.mocked(api.getInfractionRules).mockResolvedValue([
      {
        id: "rule-1",
        article: "art. 12",
        origin: "REGIMENTO_INTERNO",
        description: "Sossego",
        recidivism_window_days: 365,
        is_active: true,
        steps: [],
        created_at: "2026-01-01T00:00:00",
        updated_at: "2026-01-01T00:00:00",
      },
    ]);
  });

  it("renders the list with the derived current stage", async () => {
    renderPage();

    // "art. 12" is both a filter option and the row's title, so the count is
    // part of the assertion rather than an accident of the query.
    expect(await screen.findAllByText("art. 12")).toHaveLength(2);
    expect(screen.getByTestId("infractions-total")).toHaveTextContent("1");
    expect(screen.getByTestId(`infraction-row-${infraction.id}`)).toHaveTextContent(
      "Notificação",
    );
  });

  it.each([
    ["Filtrar por regra", "rule-1", "rule_id"],
    ["Filtrar por lote", "lot-1", "lot_id"],
    ["Filtrar por responsável", "res-1", "responsible_id"],
    ["Filtrar por estágio atual", "NONE", "stage"],
    ["De", "2026-09-01", "date_from"],
    ["Até", "2026-09-30", "date_to"],
  ])(
    "the %s filter puts its own query parameter on the request",
    async (label, value, expectedKey) => {
      // One render per filter, deliberately: the lot and responsible options
      // are derived from the *current* page, so applying one filter first
      // would empty the next select while the refetch is in flight and the
      // assertion would be about React Query's cache rather than about the
      // filter.
      const { unmount } = renderPage();
      await screen.findAllByText("art. 12");

      fireEvent.change(screen.getByLabelText(label), { target: { value } });
      await waitFor(() =>
        expect(vi.mocked(api.getInfractions)).toHaveBeenCalledWith(
          expect.objectContaining({ [expectedKey]: value }),
        ),
      );
      unmount();
    },
  );

  it("`stage=NONE` is a real option, because 'no stage yet' is a real state", async () => {
    renderPage();
    await screen.findAllByText("art. 12");

    const select = screen.getByLabelText(
      "Filtrar por estágio atual",
    ) as HTMLSelectElement;
    expect(
      Array.from(select.options).map((option) => option.value),
    ).toEqual(["", "NONE", "AVISO", "NOTIFICACAO", "MULTA"]);
  });
});

describe("InfractionStageTimeline", () => {
  it("renders stages and contestations in order and exposes no edit control", () => {
    render(<InfractionStageTimeline entries={infraction.timeline} />);

    const rendered = screen.getByTestId("infraction-timeline");
    expect(rendered.children).toHaveLength(3);
    expect(screen.getAllByTestId("timeline-stage")).toHaveLength(2);
    expect(screen.getAllByTestId("timeline-contestation")).toHaveLength(1);

    // ER-3: the history is append-only, and the UI must not suggest otherwise.
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
    expect(screen.queryByText(/Editar/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Remover/)).not.toBeInTheDocument();
  });

  it("says so when nothing has been applied yet", () => {
    render(<InfractionStageTimeline entries={[]} />);
    expect(screen.getByTestId("timeline-empty")).toBeInTheDocument();
  });
});

describe("InfractionDetailsView", () => {
  it("renders the header, the derived stage and a link back to the occurrence", () => {
    render(
      <MemoryRouter>
        <InfractionDetailsView infraction={infraction} />
      </MemoryRouter>,
    );

    expect(screen.getByTestId("responsible-name")).toHaveTextContent(
      "Maria Souza",
    );
    expect(screen.getByTestId("current-stage")).toHaveTextContent("Notificação");
    const link = screen.getByTestId("source-occurrence-link");
    expect(link).toHaveTextContent("OCO-2026-000009");
    expect(link).toHaveAttribute("href", expect.stringContaining("occ-1"));
  });
});

describe("InfractionsPage detail", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.getInfractions).mockResolvedValue({
      items: [infraction],
      total: 1,
      skip: 0,
      limit: 20,
    });
    vi.mocked(api.getInfractionRules).mockResolvedValue([]);
    vi.mocked(api.getInfraction).mockResolvedValue(infraction);
    vi.mocked(api.getNextStep).mockResolvedValue({
      recidivism_count: 0,
      window_start: "2025-09-01",
      cycle_closed_at: null,
      stages_applied: 2,
      ladder_index: 3,
      suggested_step_order: 3,
      suggested_action: "MULTA",
      reason: "SUGGESTED",
      defense_deadline_days: null,
      fine_amount: 250,
      fine_amount_unavailable_reason: null,
      is_saturated: true,
    });
    vi.mocked(api.addInfractionStage).mockResolvedValue(infraction);
  });

  it("selecting a row opens the detail and its next-step panel", async () => {
    renderPage();
    fireEvent.click(await screen.findByTestId(`infraction-row-${infraction.id}`));

    expect(await screen.findByTestId("infraction-details")).toBeInTheDocument();
    expect(await screen.findByTestId("next-step-panel")).toBeInTheDocument();
    expect(screen.getByTestId("evidence-list")).not.toBeNull();
  });

  it("applying the suggestion posts `action: null` for the selected process", async () => {
    renderPage();
    fireEvent.click(await screen.findByTestId(`infraction-row-${infraction.id}`));
    await screen.findByTestId("next-step-panel");

    fireEvent.change(screen.getByLabelText("Observação"), {
      target: { value: "Multa aplicada." },
    });
    fireEvent.click(screen.getByTestId("apply-suggestion"));

    await waitFor(() =>
      expect(vi.mocked(api.addInfractionStage)).toHaveBeenCalledWith("inf-1", {
        action: null,
        note: "Multa aplicada.",
      }),
    );
  });

  it("opens the create modal and submits through it", async () => {
    vi.mocked(api.createInfraction).mockResolvedValue(infraction);
    renderPage();
    await screen.findAllByText("art. 12");

    fireEvent.click(screen.getByTestId("open-new-infraction"));
    expect(screen.getByTestId("new-infraction-modal")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// The occurrence bridge (ER-6), round-1 review CR2
// ---------------------------------------------------------------------------
//
// Mounted with the **real** router at a real URL, because the whole protocol
// is two query parameters: a `MemoryRouter` with no `initialEntries` would
// assert nothing about them.

describe("InfractionsPage — the occurrence bridge", () => {
  const occurrence = {
    id: "occ-1",
    protocol_number: "OCO-2026-000009",
    lot_id: "lot-1",
    description: "Som alto depois das 23h.",
    created_at: "2026-08-30T12:00:00",
    timeline: [],
    infraction_ids: [],
  };

  // `MemoryRouter` never touches `window.location`, so the URL is observed
  // through the router itself.
  const LocationProbe = () => (
    <span data-testid="location-search">{useLocation().search}</span>
  );

  const renderAt = (url: string) =>
    render(
      <QueryClientProvider client={createClient()}>
        <MemoryRouter initialEntries={[url]}>
          <LocationProbe />
          <Routes>
            <Route path="/infractions" element={<InfractionsPage />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    );

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.getInfractions).mockResolvedValue({
      items: [infraction],
      total: 1,
      skip: 0,
      limit: 20,
    });
    vi.mocked(api.getInfractionRules).mockResolvedValue([
      {
        id: "rule-1",
        article: "art. 12",
        origin: "REGIMENTO_INTERNO",
        description: "Sossego",
        recidivism_window_days: 365,
        is_active: true,
        steps: [],
        created_at: "2026-01-01T00:00:00",
        updated_at: "2026-01-01T00:00:00",
      },
    ]);
    vi.mocked(api.getInfraction).mockResolvedValue(infraction);
    vi.mocked(api.getNextStep).mockResolvedValue({
      recidivism_count: 0,
      window_start: "2025-09-01",
      cycle_closed_at: null,
      stages_applied: 2,
      ladder_index: 3,
      suggested_step_order: 3,
      suggested_action: "MULTA",
      reason: "SUGGESTED",
      defense_deadline_days: null,
      fine_amount: 250,
      fine_amount_unavailable_reason: null,
      is_saturated: true,
    });
    vi.mocked(occurrencesApi.getOccurrenceById).mockResolvedValue(
      occurrence as never,
    );
    vi.mocked(lotsApi.getLots).mockResolvedValue({
      items: [{ id: "lot-1", block: "A", lot_number: "101" }],
      total: 1,
      skip: 0,
      limit: 200,
    } as never);
    vi.mocked(residentsApi.getLotResidents).mockResolvedValue({
      items: [
        { id: "res-1", full_name: "Maria", lot_id: "lot-1", is_active: true },
      ],
      total: 1,
      skip: 0,
      limit: 200,
    } as never);
    vi.mocked(api.promoteOccurrence).mockResolvedValue(infraction);
    vi.mocked(api.getCycleCloses).mockResolvedValue([]);
  });

  it("`?occurrence=` opens the modal in promote mode against that occurrence", async () => {
    renderAt("/infractions?occurrence=occ-1");

    expect(await screen.findByTestId("new-infraction-modal")).toBeInTheDocument();
    expect(vi.mocked(occurrencesApi.getOccurrenceById)).toHaveBeenCalledWith(
      "occ-1",
    );
    expect(screen.getByTestId("promotion-source")).toHaveTextContent(
      "OCO-2026-000009",
    );
    // The lot came from the occurrence, so it is shown and not offered.
    expect(screen.getByTestId("locked-lot")).toBeInTheDocument();
  });

  it("`?occurrence=` submits through POST /infractions/from-occurrence/{id}", async () => {
    renderAt("/infractions?occurrence=occ-1");
    // Scoped to the modal: the page's own "responsável" *filter* carries the
    // same visible label, and an unscoped query would find both.
    const modal = within(await screen.findByTestId("new-infraction-modal"));

    await waitFor(() =>
      expect(
        (modal.getByLabelText("Responsável") as HTMLSelectElement).options
          .length,
      ).toBe(2),
    );
    fireEvent.change(modal.getByLabelText("Responsável"), {
      target: { value: "res-1" },
    });
    fireEvent.click(screen.getByTestId("submit-new-infraction"));

    await waitFor(() =>
      expect(vi.mocked(api.promoteOccurrence)).toHaveBeenCalledWith("occ-1", {
        rule_id: "rule-1",
        responsible_resident_id: "res-1",
        lot_id: null,
        description: "Som alto depois das 23h.",
        occurred_on: "2026-08-30",
      }),
    );
    // `POST /infractions` must NOT be the endpoint: it sets
    // `source_occurrence_id = null` by construction, which would lose the link.
    expect(vi.mocked(api.createInfraction)).not.toHaveBeenCalled();
  });

  it("a successful promotion lands on the new process and clears ?occurrence=", async () => {
    // `onSuccess: (created) => select(created.id)` is the step that both
    // navigates and clears the query string, and it is what makes the
    // occurrence's "already promoted" link resolve on the way back.
    renderAt("/infractions?occurrence=occ-1");
    const modal = within(await screen.findByTestId("new-infraction-modal"));

    await waitFor(() =>
      expect(
        (modal.getByLabelText("Responsável") as HTMLSelectElement).options
          .length,
      ).toBe(2),
    );
    fireEvent.change(modal.getByLabelText("Responsável"), {
      target: { value: "res-1" },
    });
    fireEvent.click(screen.getByTestId("submit-new-infraction"));

    await waitFor(() =>
      expect(screen.getByTestId("location-search")).toHaveTextContent(
        `infraction=${infraction.id}`,
      ),
    );
    expect(screen.getByTestId("location-search")).not.toHaveTextContent(
      "occurrence=",
    );
    expect(
      screen.queryByTestId("new-infraction-modal"),
    ).not.toBeInTheDocument();
    expect(await screen.findByTestId("infraction-details")).toBeInTheDocument();
  });

  it("closes a recidivism cycle from the infraction, and lists it after", async () => {
    // Round-3 item 1: `CycleCloseModal`, `useCloseCycle` and `useCycleCloses`
    // had no production caller, so ER-9's manual close and
    // `infractions:cycle_close` had no path from the UI at all -- the same
    // defect class as the promotion bridge two rounds earlier.
    vi.mocked(api.getCycleCloses)
      .mockResolvedValueOnce([])
      .mockResolvedValue([
        {
          id: "cyc-1",
          rule: infraction.rule,
          responsible: infraction.responsible,
          lot_id: null,
          justification: "Troca de inquilino não refletida no cadastro.",
          closed_by: { id: "u-1", full_name: "Síndico" },
          closed_at: "2026-09-06T10:00:00",
        },
      ]);
    vi.mocked(api.closeCycle).mockResolvedValue({
      id: "cyc-1",
      rule: infraction.rule,
      responsible: infraction.responsible,
      lot_id: null,
      justification: "Troca de inquilino não refletida no cadastro.",
      closed_by: { id: "u-1", full_name: "Síndico" },
      closed_at: "2026-09-06T10:00:00",
    });

    renderAt(`/infractions?infraction=${infraction.id}`);

    expect(await screen.findByTestId("cycles-empty")).toBeInTheDocument();
    fireEvent.click(await screen.findByTestId("open-cycle-close"));

    // The pair is pinned to the infraction on screen, never re-chosen.
    const modal = within(screen.getByTestId("cycle-close-modal"));
    expect(modal.getByTestId("cycle-close-pair")).toHaveTextContent("art. 12");
    expect(modal.getByTestId("cycle-close-pair")).toHaveTextContent(
      "Maria Souza",
    );
    expect(screen.getByTestId("submit-cycle-close")).toBeDisabled();

    fireEvent.change(modal.getByLabelText("Justificativa"), {
      target: { value: "Troca de inquilino não refletida no cadastro." },
    });
    fireEvent.click(screen.getByTestId("submit-cycle-close"));

    await waitFor(() =>
      expect(vi.mocked(api.closeCycle)).toHaveBeenCalledWith({
        rule_id: "rule-1",
        responsible_resident_id: "res-1",
        lot_id: null,
        justification: "Troca de inquilino não refletida no cadastro.",
      }),
    );

    // ER-9: "o encerramento é listado por GET /infractions/cycles".
    expect(await screen.findByTestId("cycle-close-cyc-1")).toHaveTextContent(
      "Troca de inquilino",
    );
    expect(
      screen.queryByTestId("cycle-close-modal"),
    ).not.toBeInTheDocument();
  });

  it("keeps the cycle-close modal open and shows the refusal on a 422", async () => {
    vi.mocked(api.getCycleCloses).mockResolvedValue([]);
    vi.mocked(api.closeCycle).mockRejectedValueOnce({
      response: { data: { detail: "justification must not be empty" } },
    });

    renderAt(`/infractions?infraction=${infraction.id}`);
    fireEvent.click(await screen.findByTestId("open-cycle-close"));

    const modal = within(screen.getByTestId("cycle-close-modal"));
    fireEvent.change(modal.getByLabelText("Justificativa"), {
      target: { value: "   x" },
    });
    fireEvent.click(screen.getByTestId("submit-cycle-close"));

    expect(await screen.findByTestId("cycle-close-error")).toHaveTextContent(
      "justification must not be empty",
    );
    expect(screen.getByTestId("cycle-close-modal")).toBeInTheDocument();
  });

  it("`?infraction=` opens that infraction's detail", async () => {
    renderAt("/infractions?infraction=inf-1");

    expect(await screen.findByTestId("infraction-details")).toBeInTheDocument();
    expect(vi.mocked(api.getInfraction)).toHaveBeenCalledWith("inf-1");
    expect(screen.queryByTestId("new-infraction-modal")).not.toBeInTheDocument();
  });

  it("shows the server's refusal and keeps the form open (round-2 N-2)", async () => {
    // §7.7's two 422s and §6.3/§6.5's 409s are *expected answers* a síndico
    // has to read. Round 2 fired the mutation and closed the modal in the same
    // tick, so the reason was discarded and the user saw a modal close and no
    // infraction appear.
    vi.mocked(api.promoteOccurrence).mockRejectedValueOnce({
      response: {
        data: { detail: "The responsible resident does not belong to this lot" },
      },
    });

    renderAt("/infractions?occurrence=occ-1");
    const modal = within(await screen.findByTestId("new-infraction-modal"));
    await waitFor(() =>
      expect(
        (modal.getByLabelText("Responsável") as HTMLSelectElement).options
          .length,
      ).toBe(2),
    );
    fireEvent.change(modal.getByLabelText("Responsável"), {
      target: { value: "res-1" },
    });
    fireEvent.click(screen.getByTestId("submit-new-infraction"));

    expect(await screen.findByTestId("modal-error")).toHaveTextContent(
      "The responsible resident does not belong to this lot",
    );
    // Still open, with the values still in it.
    expect(screen.getByTestId("new-infraction-modal")).toBeInTheDocument();
  });

  it("closing the promote modal clears the parameter from the URL", async () => {
    // The URL *is* the state, so dismissing has to rewrite it -- otherwise a
    // reload would reopen a modal the user closed.
    renderAt("/infractions?occurrence=occ-1");
    await screen.findByTestId("new-infraction-modal");

    fireEvent.click(screen.getByRole("button", { name: "Cancelar" }));

    await waitFor(() =>
      expect(
        screen.queryByTestId("new-infraction-modal"),
      ).not.toBeInTheDocument(),
    );
    expect(screen.getByTestId("location-search")).toHaveTextContent("");
  });

  it("selecting a row is addressable: it puts ?infraction= on the URL", async () => {
    renderAt("/infractions");

    fireEvent.click(await screen.findByTestId(`infraction-row-${infraction.id}`));

    expect(await screen.findByTestId("infraction-details")).toBeInTheDocument();
    // A pasted link reproduces the same view, which is the whole point of
    // reading the selection from the query string rather than from state.
    expect(screen.getByTestId("location-search")).toHaveTextContent(
      `infraction=${infraction.id}`,
    );
  });
});
