import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import {
  LOT_SELECT_LIMIT,
  NewInfractionModal,
} from "../components/NewInfractionModal";
import apiClient from "../../../api/client";

/**
 * The test that would have caught round 2's blocking defect (CR3).
 *
 * `api/lots` is **deliberately not mocked** here. Every other test in this
 * feature mocks it wholesale, which is exactly why nobody noticed that
 * `useSelectableLots()` asked for `limit: 200` against a route that declares
 * `le=100`: FastAPI answers 422 before the handler runs, the lot select was
 * empty in production, `canSubmit` was never true, and **no infraction could be
 * registered from the UI at all**.
 *
 * So this file mocks only the axios instance — the last layer before the
 * network — and asserts the parameters the *real* `api/lots` module puts on
 * the wire.
 *
 * **This is one half of a two-sided pin**, the same shape
 * `backend/tests/test_module_vocabulary.py` ↔ `src/i18n/__tests__/index.test.ts`
 * already uses for the module list: neither side can import the other across
 * the language boundary, so each states the constant and names the other. The
 * backend half is
 * `backend/tests/test_infractions.py::test_the_lots_route_ceiling_matches_the_lot_selects_limit`,
 * which reads the live FastAPI route's `le=` bound and fails with this file's
 * name in the message if anyone lowers it.
 */

vi.mock("../../../api/client", () => ({
  default: { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() },
}));

/**
 * `GET /api/v1/lots/` declares `Query(default=100, ge=1, le=100)`. Stated here
 * as a literal and asserted against the live route by the backend half named
 * above — a derivation from the client would compare the client with itself.
 */
const DOCUMENTED_ROUTE_CEILING = 100;

const renderModal = () =>
  render(
    <QueryClientProvider
      client={
        new QueryClient({
          defaultOptions: { queries: { retry: false, gcTime: 0 } },
        })
      }
    >
      <MemoryRouter>
        <NewInfractionModal rules={[]} onClose={vi.fn()} onSubmit={vi.fn()} />
      </MemoryRouter>
    </QueryClientProvider>,
  );

describe("the lot select's contract with GET /api/v1/lots/", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(apiClient.get).mockResolvedValue({
      data: { items: [], total: 0, skip: 0, limit: LOT_SELECT_LIMIT },
    });
  });

  it("requests a limit the route's documented Query bound accepts", () => {
    // The bug, stated as arithmetic: 200 > 100 is a 422, not a big page.
    expect(LOT_SELECT_LIMIT).toBeLessThanOrEqual(DOCUMENTED_ROUTE_CEILING);
    expect(LOT_SELECT_LIMIT).toBeGreaterThan(0);
  });

  it("puts that limit on the wire through the real api/lots module", async () => {
    renderModal();

    await waitFor(() =>
      expect(vi.mocked(apiClient.get)).toHaveBeenCalledWith(
        "/lots/",
        expect.objectContaining({
          params: expect.objectContaining({ limit: LOT_SELECT_LIMIT }),
        }),
      ),
    );
  });

  it("says so when the route has more lots than the select shows", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: {
        items: [{ id: "lot-1", block: "A", lot_number: "101" }],
        total: 137,
        skip: 0,
        limit: LOT_SELECT_LIMIT,
      },
    });

    renderModal();

    // Silently offering the first hundred as if they were all of them is the
    // failure mode a paginated route behind an unpaginated select invites.
    expect(await screen.findByTestId("lots-truncated")).toHaveTextContent("137");
  });

  it("forwards the block filter to the route, so lot 101+ is reachable", async () => {
    // The route's ceiling is 100 and this select is not paginated, so without
    // a search a 300-unit condominium cannot register an infraction against
    // two thirds of its lots. `GET /api/v1/lots/` already accepts `block`;
    // this asserts it actually reaches the wire.
    renderModal();
    await waitFor(() => expect(apiClient.get).toHaveBeenCalled());

    fireEvent.change(screen.getByLabelText("Filtrar lotes por quadra"), {
      target: { value: "C" },
    });

    await waitFor(() =>
      expect(vi.mocked(apiClient.get)).toHaveBeenCalledWith(
        "/lots/",
        expect.objectContaining({
          params: expect.objectContaining({
            block: "C",
            limit: LOT_SELECT_LIMIT,
          }),
        }),
      ),
    );
  });

  it("sends no `block` at all when the filter is blank or whitespace", async () => {
    renderModal();

    await waitFor(() =>
      expect(vi.mocked(apiClient.get)).toHaveBeenCalledWith(
        "/lots/",
        expect.objectContaining({
          params: expect.objectContaining({ block: undefined }),
        }),
      ),
    );

    fireEvent.change(screen.getByLabelText("Filtrar lotes por quadra"), {
      target: { value: "   " },
    });
    await waitFor(() => expect(apiClient.get).toHaveBeenCalled());
    for (const call of vi.mocked(apiClient.get).mock.calls) {
      expect(call[1]).toMatchObject({ params: { block: undefined } });
    }
  });

  it("shows no truncation hint when the page holds everything", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: {
        items: [{ id: "lot-1", block: "A", lot_number: "101" }],
        total: 1,
        skip: 0,
        limit: LOT_SELECT_LIMIT,
      },
    });

    renderModal();

    await waitFor(() => expect(apiClient.get).toHaveBeenCalled());
    expect(screen.queryByTestId("lots-truncated")).not.toBeInTheDocument();
  });
});
