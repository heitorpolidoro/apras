import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { PackageStatusPage } from "../components/PackageStatusPage";
import * as packageHooks from "../hooks/usePackages";
import * as visitorPackageHooks from "../../visitor-management/hooks/usePackages";

vi.mock("../hooks/usePackages");
vi.mock("../../visitor-management/hooks/usePackages");

const createTestQueryClient = () =>
  new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });

const renderComponent = () => {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <PackageStatusPage />
    </QueryClientProvider>
  );
};

describe("PackageStatusPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(visitorPackageHooks.useMarkPackagePickedUp).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    } as any);
  });

  it("renders packages grouped by the resident's own linked lot(s)", () => {
    vi.mocked(packageHooks.useMyPackages).mockReturnValue({
      isLoading: false,
      lotsWithPackages: [
        {
          lot: { id: "lot-1", block: "A", lot_number: "101" },
          packages: [
            {
              id: "pkg-1",
              lot_id: "lot-1",
              description: "Caixa",
              carrier: "Correios",
              received_at: "2026-08-27T10:00:00Z",
              status: "AWAITING_PICKUP",
            },
          ],
          isLoading: false,
        },
      ],
    } as any);

    renderComponent();

    expect(screen.getByText(/Quadra/)).toBeInTheDocument();
    expect(screen.getByText("Caixa")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Já retirei" })).toBeInTheDocument();
  });

  it("clicking 'Já retirei' on an AWAITING_PICKUP package calls the pickup mutation", async () => {
    const mutateAsync = vi.fn().mockResolvedValue({ id: "pkg-1", status: "PICKED_UP" });
    vi.mocked(visitorPackageHooks.useMarkPackagePickedUp).mockReturnValue({
      mutateAsync,
      isPending: false,
    } as any);
    vi.mocked(packageHooks.useMyPackages).mockReturnValue({
      isLoading: false,
      lotsWithPackages: [
        {
          lot: { id: "lot-1", block: "A", lot_number: "101" },
          packages: [
            {
              id: "pkg-1",
              lot_id: "lot-1",
              description: "Caixa",
              carrier: "Correios",
              received_at: "2026-08-27T10:00:00Z",
              status: "AWAITING_PICKUP",
            },
          ],
          isLoading: false,
        },
      ],
    } as any);

    renderComponent();

    fireEvent.click(screen.getByRole("button", { name: "Já retirei" }));

    await waitFor(() => {
      expect(mutateAsync).toHaveBeenCalledWith({
        id: "pkg-1",
        data: { picked_up_by_notes: undefined },
      });
    });
  });

  it("shows an empty-state message (not an error) for a resident with zero linked lots", () => {
    vi.mocked(packageHooks.useMyPackages).mockReturnValue({
      isLoading: false,
      lotsWithPackages: [],
    } as any);

    renderComponent();

    expect(
      screen.getByText("Você não está vinculado a nenhum lote.")
    ).toBeInTheDocument();
  });
});
