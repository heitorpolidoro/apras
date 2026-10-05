/**
 * The two report figures on the internal tracker's detail view (APRAS-102).
 *
 * The page already holds `useProjectDetail`'s payload, so both components take
 * plain numbers and the raw curve as props and issue no request of their own.
 *
 * The budget is stated **once**: the cylinder replaces the green
 * "Acompanhamento Orçamentário" card rather than sitting beside it (operator
 * decision), so this suite asserts the old card is gone as well as that the new
 * one is present — the component itself survives, still exported and still
 * covered by `ProjectsFeature.test.tsx`.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as projectsApi from "../../../api/projects";
import { PERMISSIONS_BY_ROLE } from "../../../test/permissionFixtures";
import type {
  ConstructionProject,
  PaginatedProjects,
  ProjectDetail,
} from "../../../types/project";
import { ConstructionTrackerPage } from "../components/ConstructionTrackerPage";

const hasOf = (profile: string) => (permission: string) =>
  (PERMISSIONS_BY_ROLE[profile] ?? []).includes(permission);

vi.mock("../../../api/projects");

const mockPermissionSet = vi.fn();
vi.mock("../../user-administration/access/useCanAccess", () => ({
  useEffectivePermissionSet: () => mockPermissionSet(),
}));

const mockProject: ConstructionProject = {
  id: "proj-1",
  title: "Reforma da Quadra",
  description: "Pintura epóxi e iluminação",
  contractor_name: "Alfa Construtora",
  total_budget: 480000,
  executed_budget: 204000,
  physical_progress_pct: 42.5,
  start_date: "2026-09-01",
  estimated_completion_date: "2026-12-01",
  actual_completion_date: null,
  status: "IN_PROGRESS",
  cover_photo_url: null,
  created_at: "2026-08-20T10:00:00Z",
  updated_at: "2026-08-20T10:00:00Z",
};

const mockProjectsResponse: PaginatedProjects = {
  items: [mockProject],
  total: 1,
  skip: 0,
  limit: 50,
};

/** The curve is on the **detail** payload only; list items carry no such key. */
const mockProjectDetail: ProjectDetail = {
  ...mockProject,
  milestones: [],
  updates: [],
  planned_progress_json: [
    { month: "2020-01", pct: 8 },
    { month: "2020-02", pct: 31.5 },
    { month: "2020-03", pct: 64 },
  ],
};

const renderPage = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <ConstructionTrackerPage />
    </QueryClientProvider>,
  );
};

const openProjectDetail = async () => {
  fireEvent.click(await screen.findByText("Ver Detalhes"));
  await screen.findByText("Voltar para Lista de Obras");
};

describe("ConstructionTrackerPage report figures", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockPermissionSet.mockReturnValue({ has: hasOf("ADMINISTRATOR") });
    vi.mocked(projectsApi.getProjects).mockResolvedValue(mockProjectsResponse);
    vi.mocked(projectsApi.getProjectDetail).mockResolvedValue(mockProjectDetail);
  });

  it("shows the balance cylinder with the detail payload's figures", async () => {
    renderPage();
    await openProjectDetail();

    expect(screen.getByTestId("cylinder-fill")).toBeInTheDocument();
    expect(screen.getByTestId("cylinder-surface")).toBeInTheDocument();
    // 480000/204000: saldo 276.000,00, 42.5 % executed, 58 % remaining -- the
    // committed report baseline's own obra. Read through the row's own label,
    // because the physical-progress gauge on the same screen also prints
    // `42.5%` and an unscoped query matches both.
    const executedPct = screen
      .getByText("% executado")
      .parentElement?.querySelector("strong");
    expect(executedPct?.textContent).toBe("42.5%");
    expect(screen.getByText("58%")).toBeInTheDocument();
    expect(screen.getByText(/276\.000,00/)).toBeInTheDocument();
  });

  it("shows the planned-vs-actual bar driven by the payload's curve", async () => {
    renderPage();
    await openProjectDetail();

    expect(screen.getByTestId("progress-planned-value").textContent).toBe("64%");
    expect(screen.getByTestId("progress-realized-value").textContent).toBe("42%");
    // 42.5 realized against a 64 plan: behind, so the gap carries the
    // destructive tint and the state is also text.
    expect(screen.getByTestId("progress-gap").className).toContain(
      "bg-destructive/70",
    );
    expect(screen.getByText("abaixo do previsto")).toBeInTheDocument();
  });

  it("states the budget once: the old execution card is gone", async () => {
    renderPage();
    await openProjectDetail();

    expect(screen.getByText("Orçamento da obra")).toBeInTheDocument();
    expect(
      screen.queryByText("Acompanhamento Orçamentário"),
    ).not.toBeInTheDocument();
    expect(screen.queryByTestId("budget-progress-fill")).not.toBeInTheDocument();
  });
});
