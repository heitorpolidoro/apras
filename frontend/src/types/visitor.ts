export type AuthorizationType = 'SINGLE' | 'PERMANENT';
export type AuthorizationStatus = 'ACTIVE' | 'EXPIRED' | 'REVOKED';
export type DayOfWeek = 'MON' | 'TUE' | 'WED' | 'THU' | 'FRI' | 'SAT' | 'SUN';
export type ShiftType = 'MORNING' | 'AFTERNOON' | 'NIGHT' | 'FULL_DAY';

export interface Visitor {
  id: string;
  full_name: string;
  cpf?: string | null;
  rg?: string | null;
  phone?: string | null;
  company_name?: string | null;
  vehicle_plate?: string | null;
  vehicle_model?: string | null;
  notes?: string | null;
  created_at: string;
  updated_at: string;
}

export interface VisitorCreate {
  full_name: string;
  cpf?: string | null;
  rg?: string | null;
  phone?: string | null;
  company_name?: string | null;
  vehicle_plate?: string | null;
  vehicle_model?: string | null;
  notes?: string | null;
}

export interface VisitorUpdate {
  full_name?: string;
  cpf?: string | null;
  rg?: string | null;
  phone?: string | null;
  company_name?: string | null;
  vehicle_plate?: string | null;
  vehicle_model?: string | null;
  notes?: string | null;
}

export interface PaginatedVisitorRead {
  items: Visitor[];
  total: number;
  skip: number;
  limit: number;
}

export interface VisitorAuthorization {
  id: string;
  visitor_id: string;
  lot_id: string;
  authorizer_user_id: string;
  auth_type: AuthorizationType;
  allowed_days_json: string;
  allowed_shifts_json: string;
  allowed_days: DayOfWeek[];
  allowed_shifts: ShiftType[];
  valid_from?: string | null;
  valid_until?: string | null;
  status: AuthorizationStatus;
  notes?: string | null;
  created_at: string;
  updated_at: string;
  visitor?: Visitor | null;
}

export interface VisitorAuthorizationCreate {
  visitor_id: string;
  auth_type?: AuthorizationType;
  allowed_days?: DayOfWeek[];
  allowed_shifts?: ShiftType[];
  valid_from?: string | null;
  valid_until?: string | null;
  notes?: string | null;
}

export interface VisitorAuthorizationRevoke {
  reason?: string | null;
}

export interface PaginatedAuthorizationRead {
  items: VisitorAuthorization[];
  total: number;
  skip: number;
  limit: number;
}

export interface AccessLog {
  id: string;
  authorization_id?: string | null;
  visitor_id: string;
  lot_id: string;
  entry_time: string;
  exit_time?: string | null;
  gatekeeper_user_id?: string | null;
  entry_notes?: string | null;
  exit_notes?: string | null;
  visitor?: Visitor | null;
}

export interface AccessLogCheckIn {
  visitor_id: string;
  lot_id: string;
  authorization_id?: string | null;
  entry_notes?: string | null;
}

export interface AccessLogCheckOut {
  access_log_id?: string | null;
  visitor_id?: string | null;
  exit_notes?: string | null;
}

export interface PaginatedAccessLogRead {
  items: AccessLog[];
  total: number;
  skip: number;
  limit: number;
}
