import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { RootRedirect } from "../App";
import { useMyPermissions } from "../hooks/usePermissionQueries";

/**
 * IAM F5 (APRAS-49 §10.4): the landings became **data**.
 *
 * `RootRedirect` was a three-way switch on the enum. F4 recorded these
 * redirects as role-shaped and un-expressible in permissions, and it was
 * right: a PORTEIRO holds `tasks:read` and `gate:checkin`, and so do A/D/M,
 * so no predicate over the catalogue separates "pin the gatekeeper to the
 * gate" from "the board can also open the gate". Landing is a *preference*,
 * not authorization — so it lives on the role row and arrives through
 * `GET /permissions/me`.
 *
 * The navigations asserted below are the ones this module always asserted;
 * only the fixture moved from a role value to a `landing_path`.
 */

vi.mock("../hooks/usePermissionQueries", () => ({
  useMyPermissions: vi.fn(),
}));

const withLanding = (landing_path: string | null) => {
  vi.mocked(useMyPermissions).mockReturnValue({
    data: {
      tenant_id: "00000000-0000-0000-0000-000000000001",
      permissions: [],
      landing_path,
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
  });

  it("sends a caller whose landing_path is /welcome there", () => {
    withLanding("/welcome");

    renderRoot();

    expect(screen.getByText("Welcome Page")).toBeInTheDocument();
    expect(screen.queryByText("Dashboard Page")).toBeNull();
  });

  it("sends a caller whose landing_path is /gate there", () => {
    withLanding("/gate");

    renderRoot();

    expect(screen.getByText("Gate Page")).toBeInTheDocument();
    expect(screen.queryByText("Dashboard Page")).toBeNull();
    expect(screen.queryByText("Welcome Page")).toBeNull();
  });

  it("sends everyone else to /dashboard (unchanged behaviour)", () => {
    withLanding(null);

    renderRoot();

    expect(screen.getByText("Dashboard Page")).toBeInTheDocument();
  });

  it("defaults to /dashboard while the query is still settling", () => {
    vi.mocked(useMyPermissions).mockReturnValue({
      data: undefined,
      isPending: true,
      isError: false,
    } as never);

    renderRoot();

    expect(screen.getByText("Dashboard Page")).toBeInTheDocument();
  });

  it("lands a multi-role user on the first landing_path by role name", () => {
    // "First non-null, ordered by role name" is total and deterministic, but
    // it is only *identical* to the retired enum switch for users with one
    // landing-carrying role: a user holding both `Administrador (papel)` and
    // `Porteiro (papel)` lands on `/dashboard`, where the switch — keyed on a
    // single global value — would also have. The backend picks; this asserts
    // the frontend honours whatever it picked, and nothing more.
    withLanding("/dashboard");

    renderRoot();

    expect(screen.getByText("Dashboard Page")).toBeInTheDocument();
    expect(screen.queryByText("Gate Page")).toBeNull();
  });
});
