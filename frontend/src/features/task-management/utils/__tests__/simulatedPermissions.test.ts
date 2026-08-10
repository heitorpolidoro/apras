import { describe, it, expect } from "vitest";
import { canSeeSimulatedTask, canEditSimulatedTask } from "../simulatedPermissions";
import { UserRole } from "../../../../types/auth";
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
  visible_to_id: null,
};

const MANAGER_TYPE_ID = "type-manager";
const OTHER_TYPE_ID = "type-other";

describe("canSeeSimulatedTask", () => {
  it("GUEST never sees any task, even a public one", () => {
    expect(canSeeSimulatedTask(baseTask, UserRole.GUEST, [])).toBe(false);
    expect(
      canSeeSimulatedTask(
        { ...baseTask, visible_to_id: MANAGER_TYPE_ID },
        UserRole.GUEST,
        [MANAGER_TYPE_ID],
      ),
    ).toBe(false);
  });

  it("MANAGER sees a public task (visible_to_id null) regardless of UserTypes", () => {
    expect(canSeeSimulatedTask(baseTask, UserRole.MANAGER, [])).toBe(true);
  });

  it("MANAGER sees a task targeted to one of their selected UserType ids", () => {
    const task = { ...baseTask, visible_to_id: MANAGER_TYPE_ID };
    expect(
      canSeeSimulatedTask(task, UserRole.MANAGER, [MANAGER_TYPE_ID, OTHER_TYPE_ID]),
    ).toBe(true);
  });

  it("MANAGER does not see a task targeted to a UserType they don't have selected", () => {
    const task = { ...baseTask, visible_to_id: MANAGER_TYPE_ID };
    expect(canSeeSimulatedTask(task, UserRole.MANAGER, [OTHER_TYPE_ID])).toBe(false);
    expect(canSeeSimulatedTask(task, UserRole.MANAGER, [])).toBe(false);
  });

  it("ADMINISTRATOR sees every task regardless of visibility targeting", () => {
    const task = { ...baseTask, visible_to_id: OTHER_TYPE_ID };
    expect(canSeeSimulatedTask(task, UserRole.ADMINISTRATOR, [])).toBe(true);
  });

  it("DIRECTOR sees every task regardless of visibility targeting", () => {
    const task = { ...baseTask, visible_to_id: OTHER_TYPE_ID };
    expect(canSeeSimulatedTask(task, UserRole.DIRECTOR, [])).toBe(true);
  });
});

describe("canEditSimulatedTask", () => {
  it("GUEST can never edit any task", () => {
    expect(canEditSimulatedTask(baseTask, UserRole.GUEST, [])).toBe(false);
  });

  it("MANAGER can edit an unassigned task", () => {
    expect(canEditSimulatedTask(baseTask, UserRole.MANAGER, [])).toBe(true);
  });

  it("MANAGER cannot edit a task assigned to anyone — there is no simulated self", () => {
    const task = { ...baseTask, assigned_to_id: "some-user-id" };
    expect(canEditSimulatedTask(task, UserRole.MANAGER, [])).toBe(false);
  });

  it("ADMINISTRATOR can edit any task, including one assigned to someone else", () => {
    const task = { ...baseTask, assigned_to_id: "some-user-id" };
    expect(canEditSimulatedTask(task, UserRole.ADMINISTRATOR, [])).toBe(true);
  });

  it("DIRECTOR can edit any task, including one assigned to someone else", () => {
    const task = { ...baseTask, assigned_to_id: "some-user-id" };
    expect(canEditSimulatedTask(task, UserRole.DIRECTOR, [])).toBe(true);
  });
});
