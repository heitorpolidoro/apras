import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { OccurrenceDetailsView } from "../components/OccurrenceDetailsView";
import * as occurrencesApi from "../../../api/occurrences";
import type { OccurrenceDetail } from "../../../types/occurrence";

/**
 * The **occurrence side** of the bridge (ER-6), which round 2 left unasserted.
 *
 * The infractions side is well covered — promote mode, the endpoint chosen,
 * `?infraction=` opening the detail. This file covers the half that produces
 * those URLs: the `canPromote` gate, both `href`s, and the branch that shows
 * already-promoted infractions to a caller who may *not* promote (a resident
 * reading their own occurrence should still see what came of it).
 */

vi.mock("../../../api/occurrences");

const canShowMenu = vi.fn();
vi.mock("../../user-administration/access/useCanAccess", () => ({
  useEffectivePermissionSet: () => ({ has: () => true }),
  useCanShowMenu: (...args: unknown[]) => canShowMenu(...args),
}));

const occurrence = (overrides: Partial<OccurrenceDetail> = {}) =>
  ({
    id: "occ-1",
    protocol_number: "OCO-2026-000009",
    lot_id: "lot-1",
    lot_summary: "Quadra A, Lote 101",
    reporter_user_id: "u-1",
    reporter_name: "Maria",
    is_anonymous: false,
    is_public: false,
    category: "NOISE",
    title: "Barulho",
    description: "Som alto depois das 23h.",
    photo_urls: [],
    status: "OPEN",
    priority: "MEDIUM",
    assigned_to_id: null,
    resolution_notes: null,
    created_at: "2026-08-30T12:00:00",
    updated_at: "2026-08-30T12:00:00",
    resolved_at: null,
    timeline: [],
    infraction_ids: [],
    ...overrides,
  }) as OccurrenceDetail;

const renderView = () =>
  render(
    <QueryClientProvider
      client={
        new QueryClient({
          defaultOptions: { queries: { retry: false, gcTime: 0 } },
        })
      }
    >
      <MemoryRouter>
        <OccurrenceDetailsView occurrenceId="occ-1" canManage onClose={vi.fn()} />
      </MemoryRouter>
    </QueryClientProvider>,
  );

describe("OccurrenceDetailsView — the infraction bridge", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    canShowMenu.mockReturnValue(true);
    vi.mocked(occurrencesApi.getOccurrenceById).mockResolvedValue(occurrence());
  });

  it("offers 'Promover a infração' pointing at ?occurrence=<id>", async () => {
    const link = await screen.findByTestId("promote-to-infraction", undefined, {
      container: renderView().container,
    });

    expect(link).toHaveAttribute("href", "/infractions?occurrence=occ-1");
    // Gated by the *menu* predicate, so an active simulation sees what the
    // simulated role would see.
    expect(canShowMenu).toHaveBeenCalledWith({
      anyOf: ["infractions:promote"],
    });
  });

  it("hides the promote link without `infractions:promote`", async () => {
    canShowMenu.mockReturnValue(false);

    renderView();

    expect(await screen.findByText("OCO-2026-000009")).toBeInTheDocument();
    expect(
      screen.queryByTestId("promote-to-infraction"),
    ).not.toBeInTheDocument();
    // Nothing to promote and nothing promoted: the whole block is absent.
    expect(
      screen.queryByTestId("occurrence-infractions"),
    ).not.toBeInTheDocument();
  });

  it("links back to each promoted infraction at ?infraction=<id>", async () => {
    vi.mocked(occurrencesApi.getOccurrenceById).mockResolvedValue(
      occurrence({ infraction_ids: ["inf-1", "inf-2"] }),
    );

    renderView();

    expect(await screen.findByTestId("promoted-infraction-inf-1")).toHaveAttribute(
      "href",
      "/infractions?infraction=inf-1",
    );
    expect(screen.getByTestId("promoted-infraction-inf-2")).toHaveAttribute(
      "href",
      "/infractions?infraction=inf-2",
    );
  });

  it("shows the return leg even to a caller who may not promote", async () => {
    // A resident reading their own occurrence holds no `infractions:promote`,
    // and still needs to see what came of it.
    canShowMenu.mockReturnValue(false);
    vi.mocked(occurrencesApi.getOccurrenceById).mockResolvedValue(
      occurrence({ infraction_ids: ["inf-1"] }),
    );

    renderView();

    expect(
      await screen.findByTestId("promoted-infraction-inf-1"),
    ).toBeInTheDocument();
    expect(
      screen.queryByTestId("promote-to-infraction"),
    ).not.toBeInTheDocument();
  });

  it("treats a payload with no `infraction_ids` as none, not as a crash", async () => {
    // The field is additive on the backend and always present, but a cached
    // payload from an older build can still be in flight.
    const legacy = occurrence();
    delete (legacy as { infraction_ids?: string[] }).infraction_ids;
    vi.mocked(occurrencesApi.getOccurrenceById).mockResolvedValue(legacy);

    renderView();

    expect(await screen.findByTestId("promote-to-infraction")).toBeInTheDocument();
    expect(screen.queryByTestId(/^promoted-infraction-/)).not.toBeInTheDocument();
  });
});
