import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { FeedbackChannelPage } from "../components/FeedbackChannelPage";
import { FeedbackHistoryList } from "../components/FeedbackHistoryList";
import { FeedbackInboxTable } from "../components/FeedbackInboxTable";
import { FeedbackDetailsView } from "../components/FeedbackDetailsView";
import * as feedbackApi from "../../../api/feedback";
import type { Feedback, PaginatedFeedbackResponse } from "../../../types/feedback";

vi.mock("../../../api/feedback");

const mockUseEffectiveIdentity = vi.fn();
vi.mock("../../user-administration/context/useEffectiveIdentity", () => ({
  useEffectiveIdentity: () => mockUseEffectiveIdentity(),
}));

const mockFeedbackItem: Feedback = {
  id: "fb-1",
  reporter_user_id: "user-1",
  reporter_name: "João Silva",
  is_anonymous: false,
  category: "SUGGESTION",
  message: "Poderiam melhorar a iluminação da quadra.",
  status: "PENDING",
  board_response: null,
  responded_by_id: null,
  responded_by_name: null,
  responded_at: null,
  response_seen_by_reporter: false,
  created_at: "2026-08-27T10:00:00Z",
};

const mockAnsweredUnseenItem: Feedback = {
  ...mockFeedbackItem,
  id: "fb-2",
  status: "ANSWERED",
  board_response: "Obrigado pela sugestão, já está em análise.",
  responded_by_id: "admin-1",
  responded_by_name: "Administrador",
  responded_at: "2026-08-27T11:00:00Z",
  response_seen_by_reporter: false,
};

const mockFeedbackList: PaginatedFeedbackResponse = {
  items: [mockFeedbackItem],
  total: 1,
  skip: 0,
  limit: 50,
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

describe("Feedback Management Feature Suite", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(feedbackApi.getFeedbackList).mockResolvedValue(mockFeedbackList);
    vi.mocked(feedbackApi.getFeedbackById).mockResolvedValue(mockFeedbackItem);
  });

  it("renders the submission form and personal history view for non-staff roles", async () => {
    mockUseEffectiveIdentity.mockReturnValue({ role: "GUEST", userTypeIds: [], isSimulating: false });

    renderWithQuery(<FeedbackChannelPage />);

    expect(await screen.findByText("Fale Conosco")).toBeInTheDocument();
    expect(screen.getByText("Enviar Mensagem")).toBeInTheDocument();
    expect(await screen.findByText("Poderiam melhorar a iluminação da quadra.")).toBeInTheDocument();
  });

  it("renders the categorized inbox for ADMINISTRATOR", async () => {
    mockUseEffectiveIdentity.mockReturnValue({ role: "ADMINISTRATOR", userTypeIds: [], isSimulating: false });

    renderWithQuery(<FeedbackChannelPage />);

    expect(await screen.findByText("Filtros")).toBeInTheDocument();
    expect(await screen.findByText("Poderiam melhorar a iluminação da quadra.")).toBeInTheDocument();
    expect(screen.queryByText("Enviar Mensagem")).not.toBeInTheDocument();
  });

  it("renders the categorized inbox for DIRECTOR", async () => {
    mockUseEffectiveIdentity.mockReturnValue({ role: "DIRECTOR", userTypeIds: [], isSimulating: false });

    renderWithQuery(<FeedbackChannelPage />);

    expect(await screen.findByText("Filtros")).toBeInTheDocument();
    expect(screen.queryByText("Enviar Mensagem")).not.toBeInTheDocument();
  });

  it("submits a new feedback message from the contact form", async () => {
    mockUseEffectiveIdentity.mockReturnValue({ role: "RESIDENT", userTypeIds: [], isSimulating: false });
    vi.mocked(feedbackApi.createFeedback).mockResolvedValue(mockFeedbackItem);

    renderWithQuery(<FeedbackChannelPage />);

    const messageInput = await screen.findByPlaceholderText(
      "Escreva sua crítica, sugestão ou elogio..."
    );
    fireEvent.change(messageInput, { target: { value: "Excelente trabalho da portaria!" } });

    const submitBtn = screen.getByRole("button", { name: "Enviar" });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(feedbackApi.createFeedback).toHaveBeenCalledWith(
        expect.objectContaining({ message: "Excelente trabalho da portaria!" })
      );
    });
  });

  it("renders FeedbackHistoryList empty state", () => {
    renderWithQuery(
      <FeedbackHistoryList items={[]} onSelectFeedback={vi.fn()} />
    );

    expect(screen.getByText("Nenhuma mensagem enviada ainda")).toBeInTheDocument();
  });

  it("shows an unread badge for an answered-but-unseen item in the history list", () => {
    renderWithQuery(
      <FeedbackHistoryList items={[mockAnsweredUnseenItem]} onSelectFeedback={vi.fn()} />
    );

    expect(screen.getByText("Novo")).toBeInTheDocument();
  });

  it("does not show an unread badge for a seen answered item", () => {
    renderWithQuery(
      <FeedbackHistoryList
        items={[{ ...mockAnsweredUnseenItem, response_seen_by_reporter: true }]}
        onSelectFeedback={vi.fn()}
      />
    );

    expect(screen.queryByText("Novo")).not.toBeInTheDocument();
  });

  it("renders FeedbackInboxTable empty state", () => {
    renderWithQuery(
      <FeedbackInboxTable items={[]} onSelectFeedback={vi.fn()} />
    );

    expect(screen.getByText("Nenhuma mensagem recebida ainda")).toBeInTheDocument();
  });

  it("fetches individual feedback detail via getFeedbackById when opened, not from the list payload", async () => {
    vi.mocked(feedbackApi.getFeedbackById).mockResolvedValue(mockAnsweredUnseenItem);

    renderWithQuery(
      <FeedbackDetailsView feedbackId="fb-2" canRespond={false} onClose={vi.fn()} />
    );

    await waitFor(() => {
      expect(feedbackApi.getFeedbackById).toHaveBeenCalledWith("fb-2");
    });
    expect(await screen.findByText("Obrigado pela sugestão, já está em análise.")).toBeInTheDocument();
  });

  it("allows staff to respond to a feedback item from the details view", async () => {
    vi.mocked(feedbackApi.getFeedbackById).mockResolvedValue(mockFeedbackItem);
    vi.mocked(feedbackApi.respondToFeedback).mockResolvedValue({
      ...mockFeedbackItem,
      status: "ANSWERED",
      board_response: "Obrigado pelo contato!",
    });

    renderWithQuery(
      <FeedbackDetailsView feedbackId="fb-1" canRespond onClose={vi.fn()} />
    );

    const textarea = await screen.findByPlaceholderText("Escreva a resposta da diretoria...");
    fireEvent.change(textarea, { target: { value: "Obrigado pelo contato!" } });

    const sendBtn = screen.getByRole("button", { name: "Enviar Resposta" });
    fireEvent.click(sendBtn);

    await waitFor(() => {
      expect(feedbackApi.respondToFeedback).toHaveBeenCalledWith(
        "fb-1",
        expect.objectContaining({ board_response: "Obrigado pelo contato!" })
      );
    });
  });

  it("does not show a respond form for non-staff viewers", async () => {
    renderWithQuery(
      <FeedbackDetailsView feedbackId="fb-1" canRespond={false} onClose={vi.fn()} />
    );

    await screen.findByText("Poderiam melhorar a iluminação da quadra.");
    expect(screen.queryByPlaceholderText("Escreva a resposta da diretoria...")).not.toBeInTheDocument();
  });
});
