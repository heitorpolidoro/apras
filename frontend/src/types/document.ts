export interface DocumentFolder {
  id: string;
  name: string;
  description?: string | null;
  parent_id?: string | null;
  allowed_roles: string[];
  document_count: number;
  created_at: string;
  updated_at: string;
}

export interface DocumentFolderTree extends DocumentFolder {
  children: DocumentFolderTree[];
}

export interface AssociationDocument {
  id: string;
  folder_id: string;
  folder_name?: string | null;
  title: string;
  description?: string | null;
  file_url: string;
  file_size_bytes: number;
  mime_type: string;
  version_number: number;
  previous_version_id?: string | null;
  publication_year?: number | null;
  publication_month?: number | null;
  tags: string[];
  uploaded_by_id: string;
  uploader_name?: string | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentDownloadLog {
  id: string;
  document_id: string;
  user_id: string;
  user_name?: string | null;
  downloaded_at: string;
}

export interface DocumentFolderCreatePayload {
  name: string;
  description?: string | null;
  parent_id?: string | null;
  allowed_roles?: string[];
}

export interface DocumentFolderUpdatePayload {
  name?: string | null;
  description?: string | null;
  parent_id?: string | null;
  allowed_roles?: string[] | null;
}

export interface AssociationDocumentCreatePayload {
  folder_id: string;
  title: string;
  description?: string | null;
  file_url: string;
  file_size_bytes: number;
  mime_type?: string;
  publication_year?: number | null;
  publication_month?: number | null;
  tags?: string[] | null;
}

export interface AssociationDocumentVersionCreatePayload {
  title?: string | null;
  description?: string | null;
  file_url: string;
  file_size_bytes: number;
  mime_type?: string;
  tags?: string[] | null;
}

export interface PaginatedDocumentResponse {
  items: AssociationDocument[];
  total: number;
  skip: number;
  limit: number;
}

export interface DocumentFilterParams {
  folder_id?: string;
  tag?: string;
  year?: number;
  month?: number;
  search?: string;
  skip?: number;
  limit?: number;
}
