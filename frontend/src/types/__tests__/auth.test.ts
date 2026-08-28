import { describe, it, expect } from "vitest";
import { UserRole } from "../auth";

describe("UserRole", () => {
  it("includes MANAGER", () => {
    expect(UserRole.MANAGER).toBe("MANAGER");
  });

  it("includes GUEST", () => {
    expect(UserRole.GUEST).toBe("GUEST");
  });

  it("includes RESIDENT", () => {
    expect(UserRole.RESIDENT).toBe("RESIDENT");
  });

  it("includes PORTEIRO", () => {
    expect(UserRole.PORTEIRO).toBe("PORTEIRO");
  });

  it("has exactly six roles", () => {
    expect(Object.keys(UserRole)).toHaveLength(6);
  });
});
