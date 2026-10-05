/**
 * The report's planned-vs-actual physical-progress bar (APRAS-102).
 *
 * Mirrors `_one_bar @ 822` and the four parts the pinned stylesheet gives it:
 * the realized segment, the gap between plan and reality, the planned marker
 * and the two labels. The gap carries the status, and the status is never
 * signalled by colour alone — the plan label carries a text state too.
 */
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { PhysicalProgressPlannedVsActualBar } from "../components/PhysicalProgressPlannedVsActualBar";

/** A curve whose latest past point is the planned percentage each case wants. */
const curveAt = (pct: number) => [{ month: "2020-01", pct }];

/** Any instant after the curves above, so "latest past point" is the last. */
const TODAY = new Date("2026-09-15T12:00:00Z");

describe("PhysicalProgressPlannedVsActualBar", () => {
  it("renders the four parts and the two labels when the obra is behind plan", () => {
    const { container } = render(
      <PhysicalProgressPlannedVsActualBar
        physicalProgressPct={42.5}
        plannedProgressJson={curveAt(64)}
        today={TODAY}
      />,
    );

    const gap = screen.getByTestId("progress-gap");
    expect(gap.className).toContain("bg-destructive/70");
    // Positioned on the **unrounded** figures: the two labels are the only
    // things that go through `formatPercent`. The backend's own stylesheet
    // writes `left:42%;width:22%` because it positions on the `:.0f` figures.
    expect(gap.style.left).toBe("42.5%");
    expect(gap.style.width).toBe("21.5%");

    expect(screen.getByTestId("progress-realized").style.width).toBe("42.5%");
    expect(screen.getByTestId("progress-marker").style.left).toBe("64%");

    // Not by colour alone (WCAG 1.4.1): the below-plan state is also text.
    expect(screen.getByText("abaixo do previsto")).toBeInTheDocument();

    // The labels, rounded half to even: 42.5 prints 42, not 43.
    expect(screen.getByTestId("progress-planned-value").textContent).toBe("64%");
    expect(screen.getByTestId("progress-realized-value").textContent).toBe("42%");
    expect(screen.getByText("previsto")).toBeInTheDocument();
    expect(screen.getByText("realizado")).toBeInTheDocument();

    // The track names both numbers and the state for a screen reader.
    const track = container.querySelector('[role="img"]');
    expect(track?.getAttribute("aria-label")).toContain("abaixo do previsto");
  });

  it("tints the gap with the primary colour and drops the text when ahead", () => {
    render(
      <PhysicalProgressPlannedVsActualBar
        physicalProgressPct={64}
        plannedProgressJson={curveAt(42)}
        today={TODAY}
      />,
    );

    const gap = screen.getByTestId("progress-gap");
    expect(gap.className).toContain("bg-primary/30");
    expect(gap.className).not.toContain("bg-destructive/70");
    expect(gap.style.left).toBe("42%");
    expect(gap.style.width).toBe("22%");
    expect(screen.queryByText("abaixo do previsto")).not.toBeInTheDocument();
  });

  it.each([
    ["null", null],
    ["an empty list", []],
    ["a non-list object", {}],
    ["a malformed point", [{ month: "nope", pct: 1 }]],
  ])("renders the realized segment alone for %s", (_name, payload) => {
    render(
      <PhysicalProgressPlannedVsActualBar
        physicalProgressPct={42.5}
        plannedProgressJson={payload}
        today={TODAY}
      />,
    );

    // "Throws nothing" is not satisfied by rendering nothing: the realized
    // segment must be present, and present with a width.
    const realized = screen.getByTestId("progress-realized");
    expect(realized).toBeInTheDocument();
    expect(realized.style.width).toBe("42.5%");

    expect(screen.getByTestId("progress-planned-value").textContent).toBe("—");
    expect(screen.queryByTestId("progress-gap")).not.toBeInTheDocument();
    expect(screen.queryByTestId("progress-marker")).not.toBeInTheDocument();
    expect(screen.queryByText("abaixo do previsto")).not.toBeInTheDocument();
  });

  it("draws an empty realized segment for an obra that has not started", () => {
    // A brand-new obra measures 0 %, and `0` is falsy: an implementation
    // defaulting it away would read `NaN%` here.
    render(
      <PhysicalProgressPlannedVsActualBar
        physicalProgressPct={0}
        plannedProgressJson={curveAt(10)}
        today={TODAY}
      />,
    );

    expect(screen.getByTestId("progress-realized").style.width).toBe("0%");
    expect(screen.getByTestId("progress-realized-value").textContent).toBe("0%");
    expect(screen.getByTestId("progress-gap").style.width).toBe("10%");
    expect(screen.getByText("abaixo do previsto")).toBeInTheDocument();
  });

  it("draws a marker at zero when the whole curve is still in the future", () => {
    // `0` is not `null`: the plan exists and says nothing is scheduled yet, so
    // the marker is drawn, at zero, and the label reads a number.
    render(
      <PhysicalProgressPlannedVsActualBar
        physicalProgressPct={5}
        plannedProgressJson={[{ month: "2099-01", pct: 90 }]}
        today={TODAY}
      />,
    );

    expect(screen.getByTestId("progress-marker").style.left).toBe("0%");
    expect(screen.getByTestId("progress-planned-value").textContent).toBe("0%");
  });
});
