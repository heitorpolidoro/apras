import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createDocument,
  createDocumentFolder,
  createDocumentVersion,
  deleteDocument,
  deleteDocumentFolder,
  downloadDocument,
  getDocumentFolders,
  getDocuments,
  updateDocumentFolder,
} from "../../../api/documents";
import type {
  AssociationDocumentCreatePayload,
  AssociationDocumentVersionCreatePayload,
  DocumentFilterParams,
  DocumentFolderCreatePayload,
  DocumentFolderUpdatePayload,
} from "../../../types/document";

export const DOCUMENTS_QUERY_KEY = ["documents"];
export const DOCUMENT_FOLDERS_QUERY_KEY = ["document-folders"];

export function useDocumentFolders() {
  return useQuery({
    queryKey: DOCUMENT_FOLDERS_QUERY_KEY,
    queryFn: () => getDocumentFolders(),
  });
}

export function useCreateFolder() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: DocumentFolderCreatePayload) => createDocumentFolder(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: DOCUMENT_FOLDERS_QUERY_KEY });
    },
  });
}

export function useUpdateFolder() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: DocumentFolderUpdatePayload }) =>
      updateDocumentFolder(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: DOCUMENT_FOLDERS_QUERY_KEY });
      queryClient.invalidateQueries({ queryKey: DOCUMENTS_QUERY_KEY });
    },
  });
}

export function useDeleteFolder() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteDocumentFolder(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: DOCUMENT_FOLDERS_QUERY_KEY });
      queryClient.invalidateQueries({ queryKey: DOCUMENTS_QUERY_KEY });
    },
  });
}

export function useDocuments(params?: DocumentFilterParams) {
  return useQuery({
    queryKey: [...DOCUMENTS_QUERY_KEY, params],
    queryFn: () => getDocuments(params),
  });
}

export function useUploadDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: AssociationDocumentCreatePayload) => createDocument(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: DOCUMENTS_QUERY_KEY });
      queryClient.invalidateQueries({ queryKey: DOCUMENT_FOLDERS_QUERY_KEY });
    },
  });
}

export function useCreateDocumentVersion() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: AssociationDocumentVersionCreatePayload }) =>
      createDocumentVersion(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: DOCUMENTS_QUERY_KEY });
    },
  });
}

export function useDownloadDocument() {
  return useMutation({
    mutationFn: (id: string) => downloadDocument(id),
  });
}

export function useDeleteDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteDocument(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: DOCUMENTS_QUERY_KEY });
      queryClient.invalidateQueries({ queryKey: DOCUMENT_FOLDERS_QUERY_KEY });
    },
  });
}
