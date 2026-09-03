import { describe, it, expect } from "vitest";
import { canSeeSimulatedTask, canEditSimulatedTask } from "../simulatedPermissions";
import type { TaskRead } from "../../types";

const baseTask: TaskRead = {
  id: "task-1",
  title: "Task",
  status: "PENDING",
  priority: "MEDIUM",
  category_id: "cat-1",
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
  created_by_id: "creator-1",
  assigned_to_id: null,
  visible_to: [],
};

const MANAGER_TYPE_ID = "type-manager";
const OTHER_TYPE_ID = "type-other";

const role = (id: string) => ({ id, name: id });

/**
 * The permission predicate each retired role value carried, for the four
 * strings these two functions read (IAM F5, APRAS-49 §10.2).
 *
 * The parametrisation is deliberately kept role-shaped: every case below
 * asserts the **same** outcome it asserted when the argument was an enum
 * value, so the rewrite is visibly a re-expression rather than a new set of
 * claims. `tasks:read_all` / `tasks:update_any` are the legacy `{A, D, R, P}`
 * set — everyone but MANAGER — and a GUEST holds none of the four.
 */
const has = (profile: string) => (permission: string) => {
  const bundles: Record<string, string[]> = {
    ADMINISTRATOR: ["tasks:read", "tasks:read_all", "tasks:update", "tasks:update_any"],
    DIRECTOR: ["tasks:read", "tasks:read_all", "tasks:update", "tasks:update_any"],
    MANAGER: ["tasks:read", "tasks:update"],
    GUEST: [],
  };
  return bundles[profile].includes(permission);
};

describe("canSeeSimulatedTask", () => {
  it("GUEST never sees any task, even a public one", () => {
    expect(canSeeSimulatedTask(baseTask, has("GUEST"), [])).toBe(false);
    expect(
      canSeeSimulatedTask({ ...baseTask, visible_to: [role(MANAGER_TYPE_ID)] }, has("GUEST"),
        [MANAGER_TYPE_ID],
      ),
    ).toBe(false);
  });

  it("MANAGER sees a public task (empty visible_to) regardless of Roles", () => {
    expect(canSeeSimulatedTask(baseTask, has("MANAGER"), [])).toBe(true);
  });

  it("MANAGER sees a task targeted to one of their selected Role ids", () => {
    const task = { ...baseTask, visible_to: [role(MANAGER_TYPE_ID)] };
    expect(
      canSeeSimulatedTask(task, has("MANAGER"), [MANAGER_TYPE_ID, OTHER_TYPE_ID]),
    ).toBe(true);
  });

  it("MANAGER sees a task with multiple targets when at least one overlaps", () => {
    const task = {
      ...baseTask,
      visible_to: [role(MANAGER_TYPE_ID), role(OTHER_TYPE_ID)],
    };
    expect(canSeeSimulatedTask(task, has("MANAGER"), [MANAGER_TYPE_ID])).toBe(true);
  });

  it("MANAGER does not see a task targeted to a Role they don't have selected", () => {
    const task = { ...baseTask, visible_to: [role(MANAGER_TYPE_ID)] };
    expect(canSeeSimulatedTask(task, has("MANAGER"), [OTHER_TYPE_ID])).toBe(false);
    expect(canSeeSimulatedTask(task, has("MANAGER"), [])).toBe(false);
  });

  it("MANAGER does not see a task with multiple targets when none overlap", () => {
    const task = {
      ...baseTask,
      visible_to: [role(MANAGER_TYPE_ID), role(OTHER_TYPE_ID)],
    };
    expect(canSeeSimulatedTask(task, has("MANAGER"), ["type-unrelated"])).toBe(
      false,
    );
  });

  it("ADMINISTRATOR sees every task regardless of visibility targeting", () => {
    const task = { ...baseTask, visible_to: [role(OTHER_TYPE_ID)] };
    expect(canSeeSimulatedTask(task, has("ADMINISTRATOR"), [])).toBe(true);
  });

  it("DIRECTOR sees every task regardless of visibility targeting", () => {
    const task = { ...baseTask, visible_to: [role(OTHER_TYPE_ID)] };
    expect(canSeeSimulatedTask(task, has("DIRECTOR"), [])).toBe(true);
  });
});

describe("canEditSimulatedTask", () => {
  it("GUEST can never edit any task", () => {
    expect(canEditSimulatedTask(baseTask, has("GUEST"), [])).toBe(false);
  });

  it("MANAGER can edit an unassigned task", () => {
    expect(canEditSimulatedTask(baseTask, has("MANAGER"), [])).toBe(true);
  });

  it("MANAGER cannot edit a task assigned to anyone — there is no simulated self", () => {
    const task = { ...baseTask, assigned_to_id: "some-user-id" };
    expect(canEditSimulatedTask(task, has("MANAGER"), [])).toBe(false);
  });

  it("ADMINISTRATOR can edit any task, including one assigned to someone else", () => {
    const task = { ...baseTask, assigned_to_id: "some-user-id" };
    expect(canEditSimulatedTask(task, has("ADMINISTRATOR"), [])).toBe(true);
  });

  it("DIRECTOR can edit any task, including one assigned to someone else", () => {
    const task = { ...baseTask, assigned_to_id: "some-user-id" };
    expect(canEditSimulatedTask(task, has("DIRECTOR"), [])).toBe(true);
  });
});
