import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { RootRedirect } from "../App";
import { useMyPermissions } from "../hooks/usePermissionQueries";
import * as AuthHook from "../features/user-administration/context/AuthContext";

/**
 * APRAS-57: `/` is one page for everybody.
 *
 * The role landing preference is gone — first the enum switch, then the
 * role column that replaced it. `RootRedirect` no longer chooses:
 * it holds a spinner while the permission set settles and then renders the
 * general dashboard, for every authenticated caller. The cases below pin
 * exactly that, including for the two personas that used to be pinned
 * elsewhere (`/gate`, `/welcome`).
 */

vi.mock("../hooks/usePermissionQueries", () => ({
  useMyPermissions: vi.fn(),
}));

const mockAuth = (isSuperuser = false) => {
  vi.spyOn(AuthHook, "useAuth").mockReturnValue({
    user: { id: "u-1", is_superuser: isSuperuser, roles: [] },
    isAuthenticated: true,
    isLoading: false,
    login: vi.fn(),
    logout: vi.fn(),
  } as never);
};

const withPermissions = (permissions: string[] = []) => {
  vi.mocked(useMyPermissions).mockReturnValue({
    data: {
      tenant_id: "00000000-0000-0000-0000-000000000001",
      permissions,
      disabled_modules: [],
    },
    isPending: false,
    isError: false,
  } as never);
};

const renderRoot = () =>
  render(
    <MemoryRouter initialEntries={["/"]}>
      <Routes>
        <Route path="/" element={<RootRedirect />} />
        <Route path="/dashboard" element={<div>Dashboard Page</div>} />
        <Route path="/welcome" element={<div>Welcome Page</div>} />
        <Route path="/gate" element={<div>Gate Page</div>} />
      </Routes>
    </MemoryRouter>,
  );

describe("RootRedirect", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockAuth();
  });

  it("renders the general dashboard for a caller whose role formerly carried /gate", () => {
    // The porteiro persona: the one that used to be bounced to `/gate` by
    // the enum switch and then by the role landing column. No `Navigate` is
    // issued —
    // asserted by the absence of every routed page below, since a
    // redirect would have unmounted `RootRedirect` and rendered one of them.
    withPermissions(["gate:checkin", "tasks:read"]);

    renderRoot();

    expect(screen.getByText("Painel Geral")).toBeInTheDocument();
    expect(screen.queryByText("Gate Page")).toBeNull();
    expect(screen.queryByText("Welcome Page")).toBeNull();
    expect(screen.queryByText("Dashboard Page")).toBeNull();
  });

  it("renders the general dashboard for a caller whose role formerly carried /welcome", () => {
    withPermissions([]);

    renderRoot();

    expect(screen.getByText("Painel Geral")).toBeInTheDocument();
    expect(screen.queryByText("Welcome Page")).toBeNull();
  });

  it("renders General Dashboard directly at / for an ordinary caller", () => {
    withPermissions(["tasks:read"]);

    renderRoot();

    expect(screen.getByText("Painel Geral")).toBeInTheDocument();
    expect(
      screen.getByText("Bem-vindo ao painel central do seu condomínio."),
    ).toBeInTheDocument();
  });

  it("holds a spinner while the query is still settling", () => {
    // **Re-specified by APRAS-39** (code review round 1, finding 3). This
    // case used to assert `/dashboard` — a guess made before the permission
    // set existed. Navigating here unmounts `RootRedirect`, so the component
    // holds the render instead, exactly as `ProtectedRoute` does.
    vi.mocked(useMyPermissions).mockReturnValue({
      data: undefined,
      isPending: true,
      isError: false,
    } as never);

    const { container } = renderRoot();

    expect(container.querySelector(".animate-spin")).not.toBeNull();
    expect(screen.queryByText("Dashboard Page")).toBeNull();
  });

  // APRAS-75: anonymous visitor sees the landing page.
  it("renders the landing page for an anonymous visitor", () => {
    vi.spyOn(AuthHook, "useAuth").mockReturnValue({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      login: vi.fn(),
      logout: vi.fn(),
    } as never);
    withPermissions([]);

    renderRoot();

    expect(screen.getByTestId("landing-capabilities")).toBeInTheDocument();
    expect(screen.getByTestId("landing-previews")).toBeInTheDocument();
    expect(screen.queryByText("Painel Geral")).toBeNull();
  });

  // APRAS-75: while useAuth() itself is loading, show the spinner and not
  // the landing. Distinct from the usePermissionSet() loading case at line 99.
  it("renders a spinner while useAuth is loading (not the landing page)", () => {
    vi.spyOn(AuthHook, "useAuth").mockReturnValue({
      user: null,
      isAuthenticated: false,
      isLoading: true,
      login: vi.fn(),
      logout: vi.fn(),
    } as never);
    withPermissions([]);

    const { container } = renderRoot();

    expect(container.querySelector(".animate-spin")).not.toBeNull();
    expect(screen.queryByTestId("landing-capabilities")).toBeNull();
  });
});
