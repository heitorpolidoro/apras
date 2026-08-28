import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import ProtectedRoute from "../../user-administration/components/ProtectedRoute";
import { useAuth, UserRole } from "../../user-administration/context/AuthContext";

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

  return render(
    <MemoryRouter initialEntries={["/voting"]}>
      <Routes>
        <Route
          path="/voting"
          element={
            <ProtectedRoute requiredRoles={VOTING_ROLES}>
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
      expect(screen.getByText("Painel")).toBeInTheDocument();
    },
  );
});
