import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { NewInfractionModal } from "../components/NewInfractionModal";
import * as lotsApi from "../../../api/lots";
import * as residentsApi from "../../../api/residents";
import type { InfractionRule } from "../../../types/infraction";

vi.mock("../../../api/lots");
vi.mock("../../../api/residents");

/**
 * Create mode and **promote mode** (ER-6), which is the half the round-1 review
 * found inert.
 *
 * The promotion assertions are about §7.4's effective-lot rule as the form
 * encodes it: when the occurrence has a lot the form must send **no** `lot_id`
 * at all (the server resolves it), and when it has none the form must ask for
 * one. Anything else and the modal would be able to produce the mismatch 422
 * the rule exists to make unreachable from a well-behaved client.
 */

const rule = (overrides: Partial<InfractionRule> = {}): InfractionRule => ({
  id: "rule-1",
  article: "art. 12",
  origin: "REGIMENTO_INTERNO",
  description: "Sossego",
  recidivism_window_days: 365,
  is_active: true,
  steps: [],
  created_at: "2026-01-01T00:00:00",
  updated_at: "2026-01-01T00:00:00",
  ...overrides,
});

const renderModal = (props: Record<string, unknown>) =>
  render(
    <QueryClientProvider
      client={
        new QueryClient({
          defaultOptions: { queries: { retry: false, gcTime: 0 } },
        })
      }
    >
      <MemoryRouter>
        {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
        <NewInfractionModal {...(props as any)} />
      </MemoryRouter>
    </QueryClientProvider>,
  );

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(lotsApi.getLots).mockResolvedValue({
    items: [
      { id: "lot-1", block: "A", lot_number: "101" },
      { id: "lot-2", block: "B", lot_number: "202" },
    ],
    total: 2,
    skip: 0,
    limit: 200,
  } as never);
  vi.mocked(residentsApi.getLotResidents).mockImplementation(
    async (lotId: string) =>
      ({
        items:
          lotId === "lot-1"
            ? [
                { id: "res-1", full_name: "Maria", lot_id: "lot-1", is_active: true },
                {
                  id: "res-x",
                  full_name: "Antigo",
                  lot_id: "lot-1",
                  is_active: false,
                },
              ]
            : [{ id: "res-2", full_name: "João", lot_id: "lot-2", is_active: true }],
        total: 1,
        skip: 0,
        limit: 200,
      }) as never,
  );
});

describe("NewInfractionModal — create mode", () => {
  it("offers every lot and only the chosen lot's **active** residents", async () => {
    renderModal({ rules: [rule()], onClose: vi.fn(), onSubmit: vi.fn() });

    await waitFor(() =>
      expect(
        (screen.getByLabelText("Lote") as HTMLSelectElement).options.length,
      ).toBeGreaterThan(1),
    );

    // Not derived from the current page of infractions: the first infraction
    // on a lot has to be registrable.
    expect(vi.mocked(lotsApi.getLots)).toHaveBeenCalled();

    await waitFor(() =>
      expect(
        Array.from(
          (screen.getByLabelText("Responsável") as HTMLSelectElement).options,
        ).map((option) => option.text),
      ).toEqual(["Selecione", "Maria"]),
    );

    fireEvent.change(screen.getByLabelText("Lote"), {
      target: { value: "lot-2" },
    });
    await waitFor(() =>
      expect(
        Array.from(
          (screen.getByLabelText("Responsável") as HTMLSelectElement).options,
        ).map((option) => option.text),
      ).toEqual(["Selecione", "João"]),
    );
  });

  it("offers only active rules and submits the five create fields", async () => {
    const onSubmit = vi.fn();
    renderModal({
      rules: [rule(), rule({ id: "rule-2", article: "art. 30", is_active: false })],
      onClose: vi.fn(),
      onSubmit,
    });

    await waitFor(() =>
      expect(
        Array.from(
          (screen.getByLabelText("Regra") as HTMLSelectElement).options,
        ).map((option) => option.value),
      ).toEqual(["rule-1"]),
    );

    expect(screen.getByTestId("submit-new-infraction")).toBeDisabled();

    // Wait for the residents of the default lot to arrive: changing a select
    // to a value it does not yet offer is a no-op, and the button would stay
    // disabled for a reason that has nothing to do with the assertion.
    await waitFor(() =>
      expect(
        (screen.getByLabelText("Responsável") as HTMLSelectElement).options
          .length,
      ).toBe(2),
    );
    fireEvent.change(screen.getByLabelText("Responsável"), {
      target: { value: "res-1" },
    });
    fireEvent.change(screen.getByLabelText("Data do fato"), {
      target: { value: "2026-09-01" },
    });
    fireEvent.change(screen.getByLabelText("Descrição"), {
      target: { value: "Som alto." },
    });
    fireEvent.click(screen.getByTestId("submit-new-infraction"));

    expect(onSubmit).toHaveBeenCalledWith({
      rule_id: "rule-1",
      lot_id: "lot-1",
      responsible_resident_id: "res-1",
      occurred_on: "2026-09-01",
      description: "Som alto.",
    });
  });
});

describe("NewInfractionModal — promote mode (§7.4)", () => {
  const withLot = {
    id: "occ-1",
    protocol_number: "OCO-2026-000009",
    lot_id: "lot-1",
    description: "Som alto depois das 23h.",
    created_at: "2026-08-30T12:00:00",
  };

  it("locks the lot, prefills from the occurrence and links back to it", async () => {
    renderModal({
      rules: [rule()],
      occurrence: withLot,
      onClose: vi.fn(),
      onSubmit: vi.fn(),
      onPromote: vi.fn(),
    });

    expect(screen.getByTestId("promotion-source")).toHaveTextContent(
      "OCO-2026-000009",
    );
    expect(
      screen.getByTestId("promotion-source").querySelector("a"),
    ).toHaveAttribute("href", expect.stringContaining("occ-1"));

    // The lot is not a choice here -- offering one would invite the 422.
    expect(screen.getByTestId("locked-lot")).toBeInTheDocument();
    expect(screen.queryByLabelText("Lote")).not.toBeInTheDocument();
    await waitFor(() =>
      expect(screen.getByTestId("locked-lot")).toHaveTextContent("A / 101"),
    );

    expect(screen.getByLabelText("Descrição")).toHaveValue(
      "Som alto depois das 23h.",
    );
    expect(screen.getByLabelText("Data do fato")).toHaveValue("2026-08-30");
  });

  it("sends **no** lot_id when the occurrence already has one", async () => {
    const onPromote = vi.fn();
    renderModal({
      rules: [rule()],
      occurrence: withLot,
      onClose: vi.fn(),
      onSubmit: vi.fn(),
      onPromote,
    });

    await waitFor(() =>
      expect(
        Array.from(
          (screen.getByLabelText("Responsável") as HTMLSelectElement).options,
        ).length,
      ).toBe(2),
    );
    fireEvent.change(screen.getByLabelText("Responsável"), {
      target: { value: "res-1" },
    });
    fireEvent.click(screen.getByTestId("submit-new-infraction"));

    expect(onPromote).toHaveBeenCalledWith({
      rule_id: "rule-1",
      responsible_resident_id: "res-1",
      // §7.4's ordinary case: "the caller types nothing", and the server
      // resolves the effective lot from the occurrence.
      lot_id: null,
      description: "Som alto depois das 23h.",
      occurred_on: "2026-08-30",
    });
  });

  it("asks for a lot, with an explanation, when the occurrence has none", async () => {
    const onPromote = vi.fn();
    renderModal({
      rules: [rule()],
      occurrence: { ...withLot, lot_id: null },
      onClose: vi.fn(),
      onSubmit: vi.fn(),
      onPromote,
    });

    expect(screen.queryByTestId("locked-lot")).not.toBeInTheDocument();
    expect(screen.getByTestId("lotless-hint")).toHaveTextContent(
      /área comum/,
    );
    // Nothing is preselected: attributing a common-area report to a unit is a
    // decision the síndico makes, not a default.
    expect(screen.getByLabelText("Lote")).toHaveValue("");
    expect(screen.getByTestId("submit-new-infraction")).toBeDisabled();

    await waitFor(() =>
      expect(
        (screen.getByLabelText("Lote") as HTMLSelectElement).options.length,
      ).toBe(3),
    );
    fireEvent.change(screen.getByLabelText("Lote"), {
      target: { value: "lot-2" },
    });
    await waitFor(() =>
      expect(
        Array.from(
          (screen.getByLabelText("Responsável") as HTMLSelectElement).options,
        ).map((option) => option.text),
      ).toEqual(["Selecione", "João"]),
    );
    fireEvent.change(screen.getByLabelText("Responsável"), {
      target: { value: "res-2" },
    });
    fireEvent.click(screen.getByTestId("submit-new-infraction"));

    expect(onPromote).toHaveBeenCalledWith(
      expect.objectContaining({ lot_id: "lot-2", rule_id: "rule-1" }),
    );
  });
});
