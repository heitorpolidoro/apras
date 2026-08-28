export type ReservationStatus = "PENDING" | "CONFIRMED" | "CANCELLED" | "REJECTED";

export interface ReservableSpaceRead {
  id: string;
  name: string;
  description?: string | null;
  capacity?: number | null;
  requires_approval: boolean;
  is_active: boolean;
  created_at: string;
}

export interface ReservableSpaceCreatePayload {
  name: string;
  description?: string | null;
  capacity?: number | null;
  requires_approval?: boolean;
}

export interface ReservableSpaceUpdatePayload {
  name?: string;
  description?: string | null;
  capacity?: number | null;
  requires_approval?: boolean;
  is_active?: boolean;
}

export interface SpaceReservationRead {
  id: string;
  space_id: string;
  space_name?: string | null;
  reserved_by_id?: string | null;
  reserved_by_name?: string | null;
  lot_id?: string | null;
  start_time: string;
  end_time: string;
  status: ReservationStatus;
  notes?: string | null;
  decided_by_id?: string | null;
  decided_at?: string | null;
  cancelled_at?: string | null;
  created_at: string;
}

export interface SpaceReservationCreatePayload {
  space_id: string;
  lot_id?: string | null;
  start_time: string;
  end_time: string;
  notes?: string | null;
}

export interface SpaceReservationListParams {
  space_id?: string;
  mine?: boolean;
}
