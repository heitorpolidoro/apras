import { describe, it, expect, expectTypeOf } from "vitest";
import type { Role, User } from "../auth";

/**
 * The enum's obituary.
 *
 * This module used to assert that `UserRole` had six members. IAM F5
 * (APRAS-49 §10.1) deleted the const and the type, so the successor
 * statement is about the shape that replaced them: a user's power is a list
 * of `Role`s, and neither `User` nor `Role` carries a role *value* any more.
 *
 * `expectTypeOf` rather than a runtime check on purpose — there is no
 * runtime object left to count, and a compile-time assertion is what stops
 * the field being quietly re-added.
 */
describe("the auth types after the enum", () => {
  it("User carries roles, not a role", () => {
    expectTypeOf<User>().toHaveProperty("roles");
    expectTypeOf<User>().not.toHaveProperty("role");
  });

  it("User carries the caller's own is_superuser, for /auth/me only", () => {
    expectTypeOf<User>().toHaveProperty("is_superuser");
  });

  it("Role carries a bundle and a landing preference, not a role value", () => {
    expectTypeOf<Role>().toHaveProperty("permissions");
    expectTypeOf<Role>().toHaveProperty("landing_path");
    expectTypeOf<Role>().not.toHaveProperty("role");
    expectTypeOf<Role>().not.toHaveProperty("allowed_menus");
  });

  it("a Role is identified by id and name and nothing else", () => {
    const role: Role = { id: "r1", name: "Diretor (papel)" };
    expect(role.name).toBe("Diretor (papel)");
    expect(role.permissions).toBeUndefined();
  });
});
