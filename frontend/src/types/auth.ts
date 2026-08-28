export const UserRole = {
  ADMINISTRATOR: "ADMINISTRATOR",
  DIRECTOR: "DIRECTOR",
  MANAGER: "MANAGER",
  GUEST: "GUEST",
  RESIDENT: "RESIDENT",
  PORTEIRO: "PORTEIRO",
} as const;

export type UserRole = (typeof UserRole)[keyof typeof UserRole];

export interface UserType {
  id: string;
  name: string;
  allowed_menus: string[];
  /** Set only for the 5 role-linked types seeded by the APRAS-9 backend
   * migration; undefined/null for regular admin-created types. */
  role?: string | null;
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
}
