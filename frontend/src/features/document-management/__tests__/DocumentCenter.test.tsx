import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { DocumentCenterPage } from "../components/DocumentCenterPage";
import { DocumentGridTable } from "../components/DocumentGridTable";
import * as documentsApi from "../../../api/documents";
import type {
  DocumentFolderTree,
  PaginatedDocumentResponse,
} from "../../../types/document";

vi.mock("../../../api/documents");

const mockEffectiveIdentity = vi.fn();
vi.mock("../../user-administration/context/useEffectiveIdentity", () => ({
  useEffectiveIdentity: () => mockEffectiveIdentity(),
}));

const mockFoldersList: DocumentFolderTree[] = [
  {
    id: "folder-1",
    name: "Financeiro",
    description: "Pastas financeiras",
    parent_id: null,
    allowed_roles: ["ADMINISTRATOR", "DIRECTOR", "MANAGER", "RESIDENT"],
    document_count: 2,
    created_at: "2026-08-25T10:00:00Z",
    updated_at: "2026-08-25T10:00:00Z",
    children: [
      {
        id: "folder-2",
        name: "Balancetes 2026",
        description: "Balancetes",
        parent_id: "folder-1",
        allowed_roles: ["ADMINISTRATOR", "DIRECTOR", "MANAGER"],
        document_count: 1,
        created_at: "2026-08-25T10:05:00Z",
        updated_at: "2026-08-25T10:05:00Z",
        children: [],
      },
    ],
  },
];

const mockDocumentsList: PaginatedDocumentResponse = {
  items: [
    {
      id: "doc-1",
      folder_id: "folder-1",
      folder_name: "Financeiro",
      title: "Ata Assembleia Geral 2026",
      description: "Ata da reunião de janeiro",
      file_url: "https://storage.example.com/docs/ata.pdf",
      file_size_bytes: 1048576,
      mime_type: "application/pdf",
      version_number: 1,
      previous_version_id: null,
      publication_year: 2026,
      publication_month: 1,
      tags: ["ata", "assembleia"],
      uploaded_by_id: "user-1",
      uploader_name: "Admin User",
      created_at: "2026-08-25T12:00:00Z",
      updated_at: "2026-08-25T12:00:00Z",
    },
  ],
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

describe("Document Management Feature Suite", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockEffectiveIdentity.mockReturnValue({
      role: "ADMINISTRATOR",
      userTypeIds: [],
      isSimulating: false,
    });
    vi.mocked(documentsApi.getDocumentFolders).mockResolvedValue(mockFoldersList);
    vi.mocked(documentsApi.getDocuments).mockResolvedValue(mockDocumentsList);
  });

  it("renders DocumentCenterPage with folders and documents table", async () => {
    renderWithQuery(<DocumentCenterPage />);

    expect(await screen.findByText("Central de Documentos")).toBeInTheDocument();
    const folderElements = await screen.findAllByText("Financeiro");
    expect(folderElements.length).toBeGreaterThan(0);
    expect(await screen.findByText("Ata Assembleia Geral 2026")).toBeInTheDocument();
  });

  it("filters documents by search query", async () => {
    renderWithQuery(<DocumentCenterPage />);

    const searchInput = await screen.findByPlaceholderText("Buscar por título ou descrição...");
    fireEvent.change(searchInput, { target: { value: "Janeiro" } });

    await waitFor(() => {
      expect(documentsApi.getDocuments).toHaveBeenCalledWith(
        expect.objectContaining({
          search: "Janeiro",
        })
      );
    });
  });

  it("hides action buttons for non-admin/director roles", async () => {
    mockEffectiveIdentity.mockReturnValue({
      role: "RESIDENT",
      userTypeIds: [],
      isSimulating: false,
    });

    renderWithQuery(<DocumentCenterPage />);

    expect(await screen.findByText("Central de Documentos")).toBeInTheDocument();
    expect(screen.queryByText("Nova Pasta")).not.toBeInTheDocument();
    expect(screen.queryByText("Novo Documento")).not.toBeInTheDocument();
  });

  it("opens DocumentUploadModal and uploads new document", async () => {
    vi.mocked(documentsApi.createDocument).mockResolvedValue(mockDocumentsList.items[0]);

    renderWithQuery(<DocumentCenterPage />);

    const newDocBtn = await screen.findByText("Novo Documento");
    fireEvent.click(newDocBtn);

    expect((await screen.findAllByText("Novo Documento")).length).toBeGreaterThan(0);

    const titleInput = screen.getByPlaceholderText("Ex: Balancete Financeiro Jan/2026");
    const urlInput = screen.getByPlaceholderText("https://storage.example.com/arquivo.pdf");

    fireEvent.change(titleInput, { target: { value: "Balancete Fev 2026" } });
    fireEvent.change(urlInput, { target: { value: "https://example.com/bal.pdf" } });

    const submitBtn = screen.getByRole("button", { name: "Salvar Documento" });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(documentsApi.createDocument).toHaveBeenCalledWith(
        expect.objectContaining({
          title: "Balancete Fev 2026",
          file_url: "https://example.com/bal.pdf",
        })
      );
    });
  });

  it("opens FolderFormModal and creates new folder", async () => {
    vi.mocked(documentsApi.createDocumentFolder).mockResolvedValue({
      id: "folder-3",
      name: "Jurídico",
      description: "Documentos jurídicos",
      parent_id: null,
      allowed_roles: ["ADMINISTRATOR", "DIRECTOR"],
      document_count: 0,
      created_at: "2026-08-25T12:00:00Z",
      updated_at: "2026-08-25T12:00:00Z",
    });

    renderWithQuery(<DocumentCenterPage />);

    const newFolderBtn = (await screen.findAllByText("Nova Pasta"))[0];
    fireEvent.click(newFolderBtn);

    expect(screen.getByText("Criar Nova Pasta")).toBeInTheDocument();

    const nameInput = screen.getByPlaceholderText("Ex: Legislação e Atas");
    fireEvent.change(nameInput, { target: { value: "Jurídico" } });

    const createBtn = screen.getByRole("button", { name: "Criar Pasta" });
    fireEvent.click(createBtn);

    await waitFor(() => {
      expect(documentsApi.createDocumentFolder).toHaveBeenCalledWith(
        expect.objectContaining({
          name: "Jurídico",
        })
      );
    });
  });

  it("opens PDFViewerModal on preview button click", async () => {
    renderWithQuery(<DocumentCenterPage />);

    expect(await screen.findByText("Ata Assembleia Geral 2026")).toBeInTheDocument();

    const previewBtn = await screen.findByTitle("Visualizar Inline");
    fireEvent.click(previewBtn);

    expect((await screen.findAllByTitle("Ata Assembleia Geral 2026")).length).toBeGreaterThan(0);
  });

  it("renders DocumentGridTable empty state when no documents", () => {
    renderWithQuery(
      <DocumentGridTable
        documents={[]}
        onPreview={vi.fn()}
        onDownload={vi.fn()}
      />
    );

    expect(screen.getByText("Nenhum documento encontrado")).toBeInTheDocument();
  });
});
