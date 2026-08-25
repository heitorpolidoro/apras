import apiClient from "./client";
import type {
  AssociationDocument,
  AssociationDocumentCreatePayload,
  AssociationDocumentVersionCreatePayload,
  DocumentFilterParams,
  DocumentFolder,
  DocumentFolderCreatePayload,
  DocumentFolderTree,
  DocumentFolderUpdatePayload,
  PaginatedDocumentResponse,
} from "../types/document";

export const getDocumentFolders = async (): Promise<DocumentFolderTree[]> => {
  const response = await apiClient.get<DocumentFolderTree[]>("/documents/folders");
  return response.data;
};

export const createDocumentFolder = async (
  data: DocumentFolderCreatePayload
): Promise<DocumentFolder> => {
  const response = await apiClient.post<DocumentFolder>("/documents/folders", data);
  return response.data;
};

export const updateDocumentFolder = async (
  id: string,
  data: DocumentFolderUpdatePayload
): Promise<DocumentFolder> => {
  const response = await apiClient.put<DocumentFolder>(`/documents/folders/${id}`, data);
  return response.data;
};

export const deleteDocumentFolder = async (id: string): Promise<void> => {
  await apiClient.delete(`/documents/folders/${id}`);
};

export const getDocuments = async (
  params?: DocumentFilterParams
): Promise<PaginatedDocumentResponse> => {
  const response = await apiClient.get<PaginatedDocumentResponse>("/documents", {
    params,
  });
  return response.data;
};

export const createDocument = async (
  data: AssociationDocumentCreatePayload
): Promise<AssociationDocument> => {
  const response = await apiClient.post<AssociationDocument>("/documents", data);
  return response.data;
};

export const createDocumentVersion = async (
  id: string,
  data: AssociationDocumentVersionCreatePayload
): Promise<AssociationDocument> => {
  const response = await apiClient.post<AssociationDocument>(
    `/documents/${id}/versions`,
    data
  );
  return response.data;
};

export const downloadDocument = async (id: string): Promise<{ file_url: string }> => {
  const response = await apiClient.post<{ file_url: string }>(`/documents/${id}/download`);
  return response.data;
};

export const deleteDocument = async (id: string): Promise<void> => {
  await apiClient.delete(`/documents/${id}`);
};
