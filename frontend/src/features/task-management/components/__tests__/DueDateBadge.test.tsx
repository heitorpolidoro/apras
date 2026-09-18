import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import DueDateBadge from "../DueDateBadge";
import { TaskStatus } from "../../types";

/** A fixed "today" every case is measured against. */
const NOW = new Date(2026, 8, 18, 10, 30);

describe("DueDateBadge", () => {
  it("renders nothing without a due date", () => {
    const { container } = render(
      <DueDateBadge dueDate={null} status={TaskStatus.PENDING} now={NOW} />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("reads a past-due task as relative time with an icon and the word atraso", () => {
    render(
      <DueDateBadge
        dueDate={new Date(2026, 8, 13)}
        status={TaskStatus.PENDING}
        now={NOW}
      />,
    );
    expect(screen.getByText("5 dias em atraso")).toBeInTheDocument();
    expect(screen.getByTestId("due-date-icon")).toBeInTheDocument();
  });

  it("uses the singular wording one day late", () => {
    render(
      <DueDateBadge
        dueDate={new Date(2026, 8, 17)}
        status={TaskStatus.PENDING}
        now={NOW}
      />,
    );
    expect(screen.getByText("1 dia em atraso")).toBeInTheDocument();
  });

  it("reads today and tomorrow in words", () => {
    const { unmount } = render(
      <DueDateBadge
        dueDate={new Date(2026, 8, 18)}
        status={TaskStatus.PENDING}
        now={NOW}
      />,
    );
    expect(screen.getByText("vence hoje")).toBeInTheDocument();
    unmount();

    render(
      <DueDateBadge
        dueDate={new Date(2026, 8, 19)}
        status={TaskStatus.PENDING}
        now={NOW}
      />,
    );
    expect(screen.getByText("vence amanhã")).toBeInTheDocument();
  });

  it("reads a soon date in days, singular and plural", () => {
    const { unmount } = render(
      <DueDateBadge
        dueDate={new Date(2026, 8, 23)}
        status={TaskStatus.PENDING}
        now={NOW}
      />,
    );
    expect(screen.getByText("em 5 dias")).toBeInTheDocument();
    unmount();

    render(
      <DueDateBadge
        dueDate={new Date(2026, 8, 20)}
        status={TaskStatus.PENDING}
        now={NOW}
      />,
    );
    expect(screen.getByText("em 2 dias")).toBeInTheDocument();
  });

  it("keeps the absolute date for a distant deadline", () => {
    render(
      <DueDateBadge
        dueDate={new Date(2026, 9, 30)}
        status={TaskStatus.PENDING}
        now={NOW}
      />,
    );
    expect(screen.getByText("30/10/2026")).toBeInTheDocument();
  });

  it("never reports a completed task as overdue", () => {
    render(
      <DueDateBadge
        dueDate={new Date(2026, 8, 13)}
        status={TaskStatus.COMPLETED}
        now={NOW}
      />,
    );
    expect(screen.queryByText(/atraso/)).not.toBeInTheDocument();
    expect(screen.getByText("13/09/2026")).toBeInTheDocument();
  });

  it("never reports a canceled task as overdue", () => {
    render(
      <DueDateBadge
        dueDate={new Date(2026, 8, 13)}
        status={TaskStatus.CANCELED}
        now={NOW}
      />,
    );
    expect(screen.queryByText(/atraso/)).not.toBeInTheDocument();
  });
});
