export type FeedbackCategory =
  | 'CRITICISM'
  | 'SUGGESTION'
  | 'COMPLIMENT'
  | 'OTHER';

export type FeedbackStatus = 'PENDING' | 'ANSWERED';

export interface Feedback {
  id: string;
  reporter_user_id?: string | null;
  reporter_name?: string | null;
  is_anonymous: boolean;
  category: FeedbackCategory;
  message: string;
  status: FeedbackStatus;
  board_response?: string | null;
  responded_by_id?: string | null;
  responded_by_name?: string | null;
  responded_at?: string | null;
  response_seen_by_reporter: boolean;
  created_at: string;
}

export interface FeedbackCreatePayload {
  category: FeedbackCategory;
  message: string;
  is_anonymous?: boolean;
}

export interface FeedbackRespondPayload {
  board_response: string;
}

export interface PaginatedFeedbackResponse {
  items: Feedback[];
  total: number;
  skip: number;
  limit: number;
}

export interface FeedbackFilterParams {
  category?: FeedbackCategory;
  status?: FeedbackStatus;
  skip?: number;
  limit?: number;
}
