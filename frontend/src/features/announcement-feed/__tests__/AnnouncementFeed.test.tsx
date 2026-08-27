import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { AnnouncementFeedPage } from "../components/AnnouncementFeedPage";
import { MediaCarousel } from "../components/MediaCarousel";
import { CommentThread } from "../components/CommentThread";
import { AnnouncementCard } from "../components/AnnouncementCard";
import * as announcementsApi from "../../../api/announcements";
import { useAuth } from "../../user-administration/context/AuthContext";
import type {
  Announcement,
  AnnouncementMedia,
  PaginatedAnnouncementsResponse,
} from "../../../types/announcement";

vi.mock("../../../api/announcements");

vi.mock("../../user-administration/context/AuthContext", () => ({
  useAuth: vi.fn(),
  UserRole: {
    ADMINISTRATOR: "ADMINISTRATOR",
    DIRECTOR: "DIRECTOR",
    MANAGER: "MANAGER",
    GUEST: "GUEST",
  },
}));

const mockAuth = (role: string, id = "user-1") =>
  vi.mocked(useAuth).mockReturnValue({
    user: { id, role, full_name: "Test User" },
    isAuthenticated: true,
  } as unknown as ReturnType<typeof useAuth>);

const mockAnnouncement: Announcement = {
  id: "ann-1",
  title: "Assembleia Geral",
  content: "Reunião marcada para dia 10.",
  author_id: "admin-1",
  author_name: "Administrador",
  media: [],
  comment_count: 0,
  is_read: false,
  created_at: "2026-08-27T10:00:00Z",
  updated_at: "2026-08-27T10:00:00Z",
};

const mockFeed: PaginatedAnnouncementsResponse = {
  items: [mockAnnouncement],
  total: 1,
  skip: 0,
  limit: 20,
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

describe("Announcement Feed Suite", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(announcementsApi.getAnnouncements).mockResolvedValue(mockFeed);
    vi.mocked(announcementsApi.getAnnouncementComments).mockResolvedValue([]);
    vi.mocked(announcementsApi.markAnnouncementRead).mockResolvedValue({
      read_at: "2026-08-27T11:00:00Z",
    });
  });

  it("renders the feed with announcement cards", async () => {
    mockAuth("RESIDENT");
    renderWithQuery(<AnnouncementFeedPage />);

    expect(await screen.findByText("Comunicados e Notícias")).toBeInTheDocument();
    expect(await screen.findByText("Assembleia Geral")).toBeInTheDocument();
    expect(screen.getByText("Reunião marcada para dia 10.")).toBeInTheDocument();
  });

  it("shows empty state when there are no announcements", async () => {
    mockAuth("RESIDENT");
    vi.mocked(announcementsApi.getAnnouncements).mockResolvedValue({
      items: [],
      total: 0,
      skip: 0,
      limit: 20,
    });

    renderWithQuery(<AnnouncementFeedPage />);

    expect(
      await screen.findByText("Nenhum comunicado publicado até o momento.")
    ).toBeInTheDocument();
  });

  it("shows 'Novo Comunicado' button only for publishers", async () => {
    mockAuth("ADMINISTRATOR");
    renderWithQuery(<AnnouncementFeedPage />);
    expect(await screen.findByText("Novo Comunicado")).toBeInTheDocument();
  });

  it("hides 'Novo Comunicado' button for residents", async () => {
    mockAuth("RESIDENT");
    renderWithQuery(<AnnouncementFeedPage />);
    await screen.findByText("Assembleia Geral");
    expect(screen.queryByText("Novo Comunicado")).not.toBeInTheDocument();
  });

  it("marks the announcement as read once rendered", async () => {
    mockAuth("RESIDENT");
    renderWithQuery(<AnnouncementFeedPage />);

    await waitFor(() => {
      expect(announcementsApi.markAnnouncementRead).toHaveBeenCalledWith("ann-1");
    });
  });

  it("opens the create modal and submits a new announcement", async () => {
    mockAuth("ADMINISTRATOR");
    vi.mocked(announcementsApi.createAnnouncement).mockResolvedValue({
      ...mockAnnouncement,
      id: "ann-2",
      title: "Novo comunicado",
    });

    renderWithQuery(<AnnouncementFeedPage />);

    const newBtn = await screen.findByText("Novo Comunicado");
    fireEvent.click(newBtn);

    fireEvent.change(screen.getByPlaceholderText("Ex: Assembleia Geral Ordinária"), {
      target: { value: "Novo comunicado" },
    });
    fireEvent.change(screen.getByPlaceholderText("Escreva o comunicado..."), {
      target: { value: "Conteúdo do comunicado" },
    });

    fireEvent.click(screen.getByText("Publicar Comunicado"));

    await waitFor(() => {
      expect(announcementsApi.createAnnouncement).toHaveBeenCalledWith({
        title: "Novo comunicado",
        content: "Conteúdo do comunicado",
      });
    });
  });
});

describe("Announcement Feed publisher actions", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(announcementsApi.getAnnouncements).mockResolvedValue(mockFeed);
    vi.mocked(announcementsApi.getAnnouncementComments).mockResolvedValue([]);
    vi.mocked(announcementsApi.markAnnouncementRead).mockResolvedValue({
      read_at: "2026-08-27T11:00:00Z",
    });
  });

  it("deletes an announcement when the publisher clicks delete", async () => {
    mockAuth("ADMINISTRATOR");
    vi.mocked(announcementsApi.deleteAnnouncement).mockResolvedValue(undefined);

    renderWithQuery(<AnnouncementFeedPage />);

    const deleteBtn = await screen.findByLabelText("Excluir comunicado");
    fireEvent.click(deleteBtn);

    await waitFor(() => {
      expect(announcementsApi.deleteAnnouncement).toHaveBeenCalledWith("ann-1");
    });
  });

  it("opens the edit modal pre-filled and submits an update", async () => {
    mockAuth("DIRECTOR");
    vi.mocked(announcementsApi.updateAnnouncement).mockResolvedValue(mockAnnouncement);

    renderWithQuery(<AnnouncementFeedPage />);

    const editBtn = await screen.findByLabelText("Editar comunicado");
    fireEvent.click(editBtn);

    const titleInput = screen.getByDisplayValue("Assembleia Geral") as HTMLInputElement;
    expect(titleInput).toBeInTheDocument();

    fireEvent.change(titleInput, { target: { value: "Assembleia Geral - Editada" } });
    fireEvent.click(screen.getByText("Salvar Alterações"));

    await waitFor(() => {
      expect(announcementsApi.updateAnnouncement).toHaveBeenCalledWith("ann-1", {
        title: "Assembleia Geral - Editada",
        content: "Reunião marcada para dia 10.",
      });
    });
  });
});

describe("MediaCarousel", () => {
  it("renders an image inline", () => {
    const media: AnnouncementMedia[] = [
      {
        id: "m1",
        announcement_id: "ann-1",
        media_type: "IMAGE",
        url: "/static/uploads/2026/08/photo.jpg",
        mime_type: "image/jpeg",
        file_size_bytes: 1000,
        order_index: 0,
        created_at: "2026-08-27T10:00:00Z",
      },
    ];
    render(<MediaCarousel media={media} />);
    expect(screen.getByAltText("Anexo do comunicado")).toBeInTheDocument();
  });

  it("renders a PDF as an openable link", () => {
    const media: AnnouncementMedia[] = [
      {
        id: "m2",
        announcement_id: "ann-1",
        media_type: "PDF",
        url: "/static/uploads/2026/08/doc.pdf",
        mime_type: "application/pdf",
        file_size_bytes: 2000,
        order_index: 0,
        created_at: "2026-08-27T10:00:00Z",
      },
    ];
    render(<MediaCarousel media={media} />);
    const link = screen.getByTestId("pdf-attachment-link");
    expect(link).toHaveAttribute("href", "/static/uploads/2026/08/doc.pdf");
    expect(link).toHaveAttribute("target", "_blank");
  });

  it("renders nothing when there is no media", () => {
    const { container } = render(<MediaCarousel media={[]} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("navigates to the next and previous items, wrapping at the boundaries", () => {
    const media: AnnouncementMedia[] = [
      {
        id: "m1",
        announcement_id: "ann-1",
        media_type: "IMAGE",
        url: "/static/uploads/2026/08/photo-1.jpg",
        mime_type: "image/jpeg",
        file_size_bytes: 1000,
        order_index: 0,
        created_at: "2026-08-27T10:00:00Z",
      },
      {
        id: "m2",
        announcement_id: "ann-1",
        media_type: "IMAGE",
        url: "/static/uploads/2026/08/photo-2.jpg",
        mime_type: "image/jpeg",
        file_size_bytes: 1000,
        order_index: 1,
        created_at: "2026-08-27T10:00:00Z",
      },
      {
        id: "m3",
        announcement_id: "ann-1",
        media_type: "IMAGE",
        url: "/static/uploads/2026/08/photo-3.jpg",
        mime_type: "image/jpeg",
        file_size_bytes: 1000,
        order_index: 2,
        created_at: "2026-08-27T10:00:00Z",
      },
    ];

    render(<MediaCarousel media={media} />);

    const image = () => screen.getByAltText("Anexo do comunicado");
    expect(image()).toHaveAttribute("src", "/static/uploads/2026/08/photo-1.jpg");

    const nextBtn = screen.getByLabelText("Próximo");
    const prevBtn = screen.getByLabelText("Anterior");

    fireEvent.click(nextBtn);
    expect(image()).toHaveAttribute("src", "/static/uploads/2026/08/photo-2.jpg");

    fireEvent.click(nextBtn);
    expect(image()).toHaveAttribute("src", "/static/uploads/2026/08/photo-3.jpg");

    // wraps around back to the first item
    fireEvent.click(nextBtn);
    expect(image()).toHaveAttribute("src", "/static/uploads/2026/08/photo-1.jpg");

    // wraps backward to the last item
    fireEvent.click(prevBtn);
    expect(image()).toHaveAttribute("src", "/static/uploads/2026/08/photo-3.jpg");

    fireEvent.click(prevBtn);
    expect(image()).toHaveAttribute("src", "/static/uploads/2026/08/photo-2.jpg");
  });
});

describe("CommentThread", () => {
  it("hides the comment input for GUEST role", () => {
    mockAuth("GUEST");
    renderWithQuery(<CommentThread announcementId="ann-1" comments={[]} />);
    expect(
      screen.queryByPlaceholderText("Escreva um comentário...")
    ).not.toBeInTheDocument();
  });

  it("shows the comment input for RESIDENT role", () => {
    mockAuth("RESIDENT");
    renderWithQuery(<CommentThread announcementId="ann-1" comments={[]} />);
    expect(screen.getByPlaceholderText("Escreva um comentário...")).toBeInTheDocument();
  });

  it("only allows the comment author or a publisher to delete", () => {
    mockAuth("RESIDENT", "user-1");
    renderWithQuery(
      <CommentThread
        announcementId="ann-1"
        comments={[
          {
            id: "c1",
            announcement_id: "ann-1",
            user_id: "user-1",
            author_name: "Author",
            content: "My comment",
            created_at: "2026-08-27T10:00:00Z",
          },
          {
            id: "c2",
            announcement_id: "ann-1",
            user_id: "someone-else",
            author_name: "Other",
            content: "Another comment",
            created_at: "2026-08-27T10:05:00Z",
          },
        ]}
      />
    );

    expect(screen.getAllByLabelText("Excluir comentário")).toHaveLength(1);
  });

  it("submits a new comment through the input form", async () => {
    mockAuth("RESIDENT", "user-1");
    vi.mocked(announcementsApi.addAnnouncementComment).mockResolvedValue({
      id: "c3",
      announcement_id: "ann-1",
      user_id: "user-1",
      author_name: "Test User",
      content: "Nova mensagem",
      created_at: "2026-08-27T12:00:00Z",
    });

    renderWithQuery(<CommentThread announcementId="ann-1" comments={[]} />);

    fireEvent.change(screen.getByPlaceholderText("Escreva um comentário..."), {
      target: { value: "Nova mensagem" },
    });
    fireEvent.click(screen.getByLabelText("Enviar comentário"));

    await waitFor(() => {
      expect(announcementsApi.addAnnouncementComment).toHaveBeenCalledWith("ann-1", {
        content: "Nova mensagem",
      });
    });
  });

  it("deletes a comment when the author clicks the delete icon", async () => {
    mockAuth("RESIDENT", "user-1");
    vi.mocked(announcementsApi.deleteAnnouncementComment).mockResolvedValue(undefined);

    renderWithQuery(
      <CommentThread
        announcementId="ann-1"
        comments={[
          {
            id: "c1",
            announcement_id: "ann-1",
            user_id: "user-1",
            author_name: "Author",
            content: "My comment",
            created_at: "2026-08-27T10:00:00Z",
          },
        ]}
      />
    );

    fireEvent.click(screen.getByLabelText("Excluir comentário"));

    await waitFor(() => {
      expect(announcementsApi.deleteAnnouncementComment).toHaveBeenCalledWith("c1");
    });
  });
});

describe("AnnouncementCard", () => {
  it("shows edit/delete controls only for publishers", async () => {
    mockAuth("ADMINISTRATOR");
    vi.mocked(announcementsApi.getAnnouncementComments).mockResolvedValue([]);

    renderWithQuery(<AnnouncementCard announcement={mockAnnouncement} onEdit={vi.fn()} />);

    expect(await screen.findByLabelText("Editar comunicado")).toBeInTheDocument();
    expect(screen.getByLabelText("Excluir comunicado")).toBeInTheDocument();
  });

  it("hides edit/delete controls for residents", async () => {
    mockAuth("RESIDENT");
    renderWithQuery(<AnnouncementCard announcement={mockAnnouncement} onEdit={vi.fn()} />);

    await screen.findByText("Assembleia Geral");
    expect(screen.queryByLabelText("Editar comunicado")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Excluir comunicado")).not.toBeInTheDocument();
  });
});
