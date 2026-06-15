export const UserRole = {
  ADMINISTRATOR: "ADMINISTRATOR",
  DIRECTOR: "DIRECTOR",
  MANAGER: "MANAGER",
  GUEST: "GUEST",
} as const;

export type UserRole = (typeof UserRole)[keyof typeof UserRole];

export interface UserType {
  id: string;
  name: string;
}

export interface User {
  id: string;
  username: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  type?: UserType | null;
  type_id?: string | null;
}
