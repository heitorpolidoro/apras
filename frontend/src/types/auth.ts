export const UserRole = {
  ADMINISTRATOR: "ADMINISTRATOR",
  DIRECTOR: "DIRECTOR",
  MANAGER: "MANAGER",
  GUEST: "GUEST",
  RESIDENT: "RESIDENT",
} as const;

export type UserRole = (typeof UserRole)[keyof typeof UserRole];

export interface UserType {
  id: string;
  name: string;
}

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  user_types?: UserType[];
  user_type_ids?: string[] | null;
  cpf?: string;
  phone?: string;
  address?: string;
  block_lot?: string;
}
