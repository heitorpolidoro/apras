import { describe, it, expect } from "vitest";
import {
  normalizeText,
  matchesSearch,
  dueDateInfo,
  isOverdue,
} from "../taskUtils";
import { TaskStatus, TaskPriority } from "../../types";
import type { TaskRead } from "../../types";

const baseTask: TaskRead = {
  id: "1",
  title: "Manutenção do elevador",
  description: "Contrato anual preventivo",
  status: TaskStatus.PENDING,
  priority: TaskPriority.MEDIUM,
  created_at: "2026-09-01T00:00:00Z",
  updated_at: "2026-09-01T00:00:00Z",
  created_by_id: "user-1",
  category_id: "cat-1",
  visible_to: [],
};

/** A fixed "today" every due-date case is measured against. */
const NOW = new Date(2026, 8, 18, 10, 30);

describe("normalizeText", () => {
  it("lower-cases and strips diacritics", () => {
    expect(normalizeText("Manutenção")).toBe("manutencao");
    expect(normalizeText("ÁÉÍÓÚ Ç ÃÕ")).toBe("aeiou c ao");
  });

  it("returns an empty string for null and undefined", () => {
    expect(normalizeText(null)).toBe("");
    expect(normalizeText(undefined)).toBe("");
  });
});

describe("matchesSearch", () => {
  it("matches an accent-insensitive title fragment", () => {
    expect(matchesSearch(baseTask, "manutencao")).toBe(true);
    expect(matchesSearch(baseTask, "MANUTENCAO")).toBe(true);
  });

  it("matches on the description alone", () => {
    expect(matchesSearch(baseTask, "preventivo")).toBe(true);
  });

  it("keeps everything for a blank or whitespace-only search", () => {
    expect(matchesSearch(baseTask, "")).toBe(true);
    expect(matchesSearch(baseTask, "   ")).toBe(true);
    expect(matchesSearch(baseTask, undefined)).toBe(true);
  });

  it("rejects a fragment present in neither field", () => {
    expect(matchesSearch(baseTask, "piscina")).toBe(false);
  });

  it("tolerates a task with no description", () => {
    expect(matchesSearch({ ...baseTask, description: null }, "elevador")).toBe(
      true,
    );
    expect(matchesSearch({ ...baseTask, description: null }, "contrato")).toBe(
      false,
    );
  });
});

describe("dueDateInfo", () => {
  it("returns null when there is no due date", () => {
    expect(dueDateInfo(null, TaskStatus.PENDING, NOW)).toBeNull();
    expect(dueDateInfo(undefined, TaskStatus.PENDING, NOW)).toBeNull();
  });

  it("classifies a past date as overdue with the whole-day distance", () => {
    expect(dueDateInfo(new Date(2026, 8, 13), TaskStatus.PENDING, NOW)).toEqual(
      { state: "overdue", days: 5 },
    );
  });

  it("classifies today, tomorrow, soon and future", () => {
    expect(dueDateInfo(new Date(2026, 8, 18), TaskStatus.PENDING, NOW)).toEqual(
      { state: "today", days: 0 },
    );
    expect(dueDateInfo(new Date(2026, 8, 19), TaskStatus.PENDING, NOW)).toEqual(
      { state: "tomorrow", days: 1 },
    );
    expect(dueDateInfo(new Date(2026, 8, 23), TaskStatus.PENDING, NOW)).toEqual(
      { state: "soon", days: 5 },
    );
    expect(dueDateInfo(new Date(2026, 9, 18), TaskStatus.PENDING, NOW)).toEqual(
      { state: "future", days: 30 },
    );
  });

  it("treats the seventh day as soon and the eighth as future", () => {
    expect(dueDateInfo(new Date(2026, 8, 25), TaskStatus.PENDING, NOW)).toEqual(
      { state: "soon", days: 7 },
    );
    expect(dueDateInfo(new Date(2026, 8, 26), TaskStatus.PENDING, NOW)).toEqual(
      { state: "future", days: 8 },
    );
  });

  it("never reports a COMPLETED or CANCELED task as overdue", () => {
    expect(
      dueDateInfo(new Date(2026, 8, 13), TaskStatus.COMPLETED, NOW),
    ).toEqual({ state: "future", days: 5 });
    expect(
      dueDateInfo(new Date(2026, 8, 13), TaskStatus.CANCELED, NOW),
    ).toEqual({ state: "future", days: 5 });
  });

  it("accepts an ISO string due date", () => {
    expect(
      dueDateInfo("2026-09-13T00:00:00", TaskStatus.PENDING, NOW),
    ).toEqual({ state: "overdue", days: 5 });
  });
});

describe("isOverdue", () => {
  it("is true for a past-due open task", () => {
    expect(
      isOverdue({ ...baseTask, due_date: new Date(2026, 8, 13) }, NOW),
    ).toBe(true);
  });

  it("is false for a past-due completed task", () => {
    expect(
      isOverdue(
        {
          ...baseTask,
          status: TaskStatus.COMPLETED,
          due_date: new Date(2026, 8, 13),
        },
        NOW,
      ),
    ).toBe(false);
  });

  it("is false without a due date and for a future one", () => {
    expect(isOverdue(baseTask, NOW)).toBe(false);
    expect(
      isOverdue({ ...baseTask, due_date: new Date(2026, 8, 30) }, NOW),
    ).toBe(false);
  });
});
