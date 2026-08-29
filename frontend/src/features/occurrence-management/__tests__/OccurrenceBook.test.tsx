import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { OccurrenceBookPage } from "../components/OccurrenceBookPage";
import { OccurrenceTable } from "../components/OccurrenceTable";
import { OccurrenceDetailsView } from "../components/OccurrenceDetailsView";
import { OccurrenceTimelineLog } from "../components/OccurrenceTimelineLog";
import * as occurrencesApi from "../../../api/occurrences";
import type { OccurrenceDetail, PaginatedOccurrencesResponse } from "../../../types/occurrence";

vi.mock("../../../api/occurrences");
vi.mock("../../user-administration/context/useEffectiveIdentity", () => ({
  useEffectiveIdentity: () => ({
    role: "ADMINISTRATOR",
    userTypeIds: [],
    isSimulating: false,
  }),
}));

const mockOccurrencesList: PaginatedOccurrencesResponse = {
  items: [
    {
      id: "occ-1",
      protocol_number: "OCO-2026-000001",
      lot_id: "lot-1",
      lot_summary: "Quadra A, Lote 10",
      reporter_user_id: "user-1",
      reporter_name: "João Silva",
      is_anonymous: false,
      is_public: true,
      category: "NOISE",
      title: "Som alto à noite",
      description: "Som automotivo na alameda após 22h",
      photo_urls: ["https://example.com/photo1.jpg"],
      status: "OPEN",
      priority: "MEDIUM",
      created_at: "2026-08-25T20:00:00Z",
      updated_at: "2026-08-25T20:00:00Z",
    },
  ],
  total: 1,
  skip: 0,
  limit: 50,
};

const mockOccurrenceDetail: OccurrenceDetail = {
  ...mockOccurrencesList.items[0],
  timeline: [
    {
      id: "line-1",
      occurrence_id: "occ-1",
      actor_id: "user-1",
      actor_name: "João Silva",
      status_from: null,
      status_to: "OPEN",
      note: "Ocorrência registrada no sistema",
      is_internal_only: false,
      created_at: "2026-08-25T20:00:00Z",
    },
    {
      id: "line-2",
      occurrence_id: "occ-1",
      actor_id: "admin-1",
      actor_name: "Administrador",
      status_from: null,
      status_to: null,
      note: "Nota interna de verificação",
      is_internal_only: true,
      created_at: "2026-08-25T20:30:00Z",
    },
  ],
};

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });

const renderWithQuery = (ui: React.ReactNode) => {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>
  );
};

describe("Occurrence Management Feature Suite", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(occurrencesApi.getOccurrences).mockResolvedValue(mockOccurrencesList);
    vi.mocked(occurrencesApi.getOccurrenceById).mockResolvedValue(mockOccurrenceDetail);
  });

  it("renders OccurrenceBookPage with table and filters", async () => {
    renderWithQuery(<OccurrenceBookPage />);

    expect(await screen.findByText("Livro de Ocorrências e Reclamações")).toBeInTheDocument();
    expect(await screen.findByText("OCO-2026-000001")).toBeInTheDocument();
    expect(await screen.findByText("Som alto à noite")).toBeInTheDocument();
  });

  it("opens NewOccurrenceModal and submits new ticket", async () => {
    vi.mocked(occurrencesApi.createOccurrence).mockResolvedValue(mockOccurrencesList.items[0]);

    renderWithQuery(<OccurrenceBookPage />);

    const newBtn = await screen.findByRole("button", { name: "Nova Ocorrência" });
    fireEvent.click(newBtn);

    expect(screen.getByText("Nova Ocorrência / Reclamação")).toBeInTheDocument();

    const titleInput = screen.getByPlaceholderText("Ex: Barulho de som após 22h na quadra B");
    const descInput = screen.getByPlaceholderText("Descreva detalhadamente o ocorrido...");

    fireEvent.change(titleInput, { target: { value: "Manutenção do portão" } });
    fireEvent.change(descInput, { target: { value: "Portão lateral sem trava" } });

    const submitBtn = screen.getByRole("button", { name: "Registrar Ocorrência" });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(occurrencesApi.createOccurrence).toHaveBeenCalledWith(
        expect.objectContaining({
          title: "Manutenção do portão",
          description: "Portão lateral sem trava",
        })
      );
    });
  });

  it("renders OccurrenceTable empty state", () => {
    renderWithQuery(
      <OccurrenceTable occurrences={[]} onSelectOccurrence={vi.fn()} />
    );

    expect(screen.getByText("Nenhuma ocorrência encontrada")).toBeInTheDocument();
  });

  it("opens OccurrenceDetailsView and submits status update", async () => {
    vi.mocked(occurrencesApi.updateOccurrenceStatus).mockResolvedValue({
      ...mockOccurrencesList.items[0],
      status: "RESOLVED",
    });

    renderWithQuery(
      <OccurrenceDetailsView
        occurrenceId="occ-1"
        userRole="ADMINISTRATOR"
        onClose={vi.fn()}
      />
    );

    expect(await screen.findByText("OCO-2026-000001")).toBeInTheDocument();
    expect(screen.getByText("Som automotivo na alameda após 22h")).toBeInTheDocument();

    const statusSelect = screen.getByDisplayValue("Aberto");
    fireEvent.change(statusSelect, { target: { value: "RESOLVED" } });

    const saveBtn = screen.getByRole("button", { name: "Salvar Alterações" });
    fireEvent.click(saveBtn);

    await waitFor(() => {
      expect(occurrencesApi.updateOccurrenceStatus).toHaveBeenCalledWith(
        "occ-1",
        expect.objectContaining({
          status: "RESOLVED",
        })
      );
    });
  });

  it("renders OccurrenceTimelineLog and adds a new timeline note", async () => {
    vi.mocked(occurrencesApi.addTimelineNote).mockResolvedValue({
      id: "line-3",
      occurrence_id: "occ-1",
      actor_id: "admin-1",
      actor_name: "Administrador",
      status_from: null,
      status_to: null,
      note: "Fiscalização enviada ao local",
      is_internal_only: true,
      created_at: "2026-08-25T21:00:00Z",
    });

    renderWithQuery(
      <OccurrenceTimelineLog
        occurrenceId="occ-1"
        timeline={mockOccurrenceDetail.timeline}
        userRole="ADMINISTRATOR"
      />
    );

    expect(screen.getByText("Histórico e Trâmite")).toBeInTheDocument();
    expect(screen.getByText("Nota Interna")).toBeInTheDocument();

    const textInput = screen.getByPlaceholderText("Escreva aqui a observação...");
    fireEvent.change(textInput, { target: { value: "Fiscalização enviada ao local" } });

    const sendBtn = screen.getByRole("button", { name: "Enviar" });
    fireEvent.click(sendBtn);

    await waitFor(() => {
      expect(occurrencesApi.addTimelineNote).toHaveBeenCalledWith(
        "occ-1",
        expect.objectContaining({
          note: "Fiscalização enviada ao local",
        })
      );
    });
  });
});
