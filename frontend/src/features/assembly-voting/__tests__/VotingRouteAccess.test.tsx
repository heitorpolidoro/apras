import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import ProtectedRoute from "../../user-administration/components/ProtectedRoute";
import { useAuth, UserRole } from "../../user-administration/context/AuthContext";
import { useMyPermissions } from "../../../hooks/usePermissionQueries";
import { ROUTE_ACCESS } from "../../user-administration/access/routeAccess";
import {
  PERMISSIONS_BY_ROLE,
  settledPermissions,
} from "../../../test/permissionFixtures";

vi.mock("../../user-administration/context/AuthContext", async () => {
  const actual = await vi.importActual<
    typeof import("../../user-administration/context/AuthContext")
  >("../../user-administration/context/AuthContext");
  return { ...actual, useAuth: vi.fn() };
});

vi.mock("../../user-administration/context/useEffectiveIdentity", () => ({
  useEffectiveIdentity: vi.fn(() => ({ role: UserRole.RESIDENT })),
}));

vi.mock("../../user-administration/context/useMenuAccess", () => ({
  useMenuAccess: vi.fn(() => true),
}));

vi.mock("../../../hooks/usePermissionQueries", () => ({
  useMyPermissions: vi.fn(),
  usePermissionCatalogue: vi.fn(() => ({ data: [], isPending: false })),
}));

/**
 * The roles `{module:"votes"}` resolves to today — the §5.2 delta for
 * `/voting` is "none", so this is the same set the old `requiredRoles` array
 * held, now kept only as the fixture selector for the parametrisation.
 */
const VOTING_ROLES = [
  UserRole.ADMINISTRATOR,
  UserRole.DIRECTOR,
  UserRole.MANAGER,
  UserRole.RESIDENT,
];

const renderVotingRoute = (role: UserRole) => {
  vi.mocked(useAuth).mockReturnValue({
    isAuthenticated: true,
    isLoading: false,
    user: { id: "user-1", role },
  } as never);
  vi.mocked(useMyPermissions).mockReturnValue(
    settledPermissions(PERMISSIONS_BY_ROLE[role]) as never,
  );

  return render(
    <MemoryRouter initialEntries={["/voting"]}>
      <Routes>
        <Route
          path="/voting"
          element={
            <ProtectedRoute requiredAccess={ROUTE_ACCESS["/voting"]}>
              <div>Assembleias e Enquetes</div>
            </ProtectedRoute>
          }
        />
        <Route path="/dashboard" element={<div>Painel</div>} />
      </Routes>
    </MemoryRouter>,
  );
};

describe("/voting route access", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it.each(VOTING_ROLES)("lets %s reach the voting screen", (role) => {
    renderVotingRoute(role);
    expect(screen.getByText("Assembleias e Enquetes")).toBeInTheDocument();
  });

  it.each([UserRole.PORTEIRO, UserRole.GUEST])(
    "keeps %s away from the voting screen",
    (role) => {
      renderVotingRoute(role);
      expect(
        screen.queryByText("Assembleias e Enquetes"),
      ).not.toBeInTheDocument();
      // §2.4: denial is in place, so /dashboard is never reached.
      expect(screen.queryByText("Painel")).not.toBeInTheDocument();
      expect(screen.getByText("Acesso restrito")).toBeInTheDocument();
    },
  );
});
