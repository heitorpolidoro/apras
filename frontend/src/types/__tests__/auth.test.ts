import { describe, it, expect } from "vitest";
import { UserRole } from "../auth";

describe("UserRole", () => {
  it("includes MANAGER", () => {
    expect(UserRole.MANAGER).toBe("MANAGER");
  });

  it("includes GUEST", () => {
    expect(UserRole.GUEST).toBe("GUEST");
  });

  it("has exactly four roles", () => {
    expect(Object.keys(UserRole)).toHaveLength(4);
  });
});
