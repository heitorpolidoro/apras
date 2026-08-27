export type AnnouncementMediaType = "IMAGE" | "PDF";

export interface AnnouncementMedia {
  id: string;
  announcement_id: string;
  media_type: AnnouncementMediaType;
  url: string;
  mime_type: string;
  file_size_bytes: number;
  order_index: number;
  created_at: string;
}

export interface AnnouncementComment {
  id: string;
  announcement_id: string;
  user_id: string;
  author_name?: string | null;
  content: string;
  created_at: string;
}

export interface AnnouncementReadReceipt {
  user_id: string;
  user_name?: string | null;
  read_at: string;
}

export interface Announcement {
  id: string;
  title: string;
  content: string;
  author_id: string;
  author_name?: string | null;
  media: AnnouncementMedia[];
  comment_count: number;
  is_read: boolean;
  created_at: string;
  updated_at: string;
}

export interface AnnouncementDetail extends Announcement {
  comments: AnnouncementComment[];
}

export interface AnnouncementCreatePayload {
  title: string;
  content: string;
}

export interface AnnouncementUpdatePayload {
  title?: string;
  content?: string;
}

export interface CommentCreatePayload {
  content: string;
}

export interface PaginatedAnnouncementsResponse {
  items: Announcement[];
  total: number;
  skip: number;
  limit: number;
}

export interface MarkReadResponse {
  read_at: string;
}
