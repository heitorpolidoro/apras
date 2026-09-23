import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type React from "react";
import apiClient from "../../../api/client";
import pt from "../../../i18n/locales/pt.json";
import TenantsAdminPage from "../pages/TenantsAdminPage";
import ProtectedRoute from "../components/ProtectedRoute";
import { ROUTE_ACCESS } from "../access/routeAccess";
import * as AuthHook from "../context/AuthContext";
import { useMyPermissions } from "../../../hooks/usePermissionQueries";
import {
  ALL_PERMISSIONS,
  settledPermissions,
} from "../../../test/permissionFixtures";
import type { User } from "../../../types/auth";
import { issueInvitation, listInvitations } from "../../../api/invitations";
import type { Invitation } from "../../../types/invitations";

/**
 * The invitation half of `/admin/tenants` (APRAS-72 D1–D4, D8).
 *
 * The mock boundary is `src/api/invitations`, the module this task adds: the
 * assertions are about the arguments the screen passes it and the states it
 * renders from the answers. `api/client` stays mocked for the tenant list the
 * screen inherits from APRAS-70.
 */

vi.mock("../../../api/client", () => ({
  default: { get: vi.fn(), post: vi.fn(), put: vi.fn(), patch: vi.fn() },
}));

vi.mock("../../../api/invitations", () => ({
  issueInvitation: vi.fn(),
  listInvitations: vi.fn(),
  previewInvitation: vi.fn(),
  acceptInvitation: vi.fn(),
}));

vi.mock("../context/SimulationContext", () => ({
  useSimulation: vi.fn(() => ({
    simulatedRoleIds: [],
    isSimulating: false,
    setSimulatedRoleIds: vi.fn(),
    stopSimulation: vi.fn(),
  })),
}));

vi.mock("../../../hooks/useRoles", () => ({
  useRoles: vi.fn(() => ({ data: [] })),
}));

vi.mock("../../../hooks/usePermissionQueries", () => ({
  useMyPermissions: vi.fn(),
  usePermissionCatalogue: vi.fn(() => ({ data: [], isPending: false })),
}));

const mockedGet = vi.mocked(apiClient.get);
const mockedPost = vi.mocked(apiClient.post);
const mockedIssue = vi.mocked(issueInvitation);
const mockedList = vi.mocked(listInvitations);

const t = (key: string): string =>
  key
    .split(".")
    .reduce<unknown>(
      (node, part) => (node as Record<string, unknown>)?.[part],
      pt,
    ) as string;

const AURORA = {
  id: "t-aurora",
  name: "Edifício Aurora",
  slug: "edificio-aurora",
  is_active: true,
  created_at: "2026-09-20T13:45:09",
};
const AGUAS = {
  id: "t-aguas",
  name: "Parque das Águas",
  slug: "parque-das-aguas",
  is_active: false,
  created_at: "2026-08-12T08:00:00",
};
const SERRA = {
  id: "t-serra",
  name: "Residencial Altos da Serra",
  slug: "residencial-altos-da-serra",
  is_active: true,
  created_at: "2026-07-02T10:15:00",
};
const TENANTS = [AURORA, AGUAS, SERRA];

/**
 * Three invitations, newest first, covering the whole of D3's derivation:
 * one consumed, one past its deadline, one still live. **No fixture carries a
 * `status` field** — `InvitationRead` has none, so a component that read one
 * would render `undefined` here and fail.
 */
const ACCEPTED: Invitation = {
  id: "inv-accepted",
  tenant_id: AURORA.id,
  email: "aceito@example.com",
  expires_at: "2026-09-25T10:00:00Z",
  accepted_at: "2026-09-21T09:30:00Z",
  accepted_user_id: "u-1",
  invited_by_user_id: "u-root",
  created_at: "2026-09-20T09:00:00Z",
};
const EXPIRED: Invitation = {
  id: "inv-expired",
  tenant_id: AURORA.id,
  email: "expirado@example.com",
  expires_at: "2026-09-10T10:00:00Z",
  accepted_at: null,
  accepted_user_id: null,
  invited_by_user_id: "u-root",
  created_at: "2026-09-08T09:00:00Z",
};
const PENDING: Invitation = {
  id: "inv-pending",
  tenant_id: AURORA.id,
  email: "pendente@example.com",
  expires_at: "2099-01-01T10:00:00Z",
  accepted_at: null,
  accepted_user_id: null,
  invited_by_user_id: "u-root",
  created_at: "2026-09-21T09:00:00Z",
};
/** Another condominium's, so the column cannot pass by reading row one. */
const AGUAS_ACCEPTED: Invitation = {
  id: "inv-aguas",
  tenant_id: AGUAS.id,
  email: "aguas@example.com",
  expires_at: "2026-09-26T10:00:00Z",
  accepted_at: "2026-09-19T11:00:00Z",
  accepted_user_id: "u-2",
  invited_by_user_id: "u-root",
  created_at: "2026-09-19T09:00:00Z",
};

/** Every invitation in the installation, as the unfiltered call answers. */
const ALL_INVITATIONS = [PENDING, ACCEPTED, AGUAS_ACCEPTED, EXPIRED];

const newClient = () =>
  new QueryClient({ defaultOptions: { queries: { retry: false } } });

const renderPage = (client = newClient()) => {
  const Wrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
  return { client, ...render(<TenantsAdminPage />, { wrapper: Wrapper }) };
};

/**
 * The "invite administrator" button of one condominium's row.
 *
 * Scoped by the row's own test id rather than taken as `findAllByRole(...)[0]`.
 * The `[0]` picked its subject by **render order**, while the assertion twelve
 * lines later names a condominium (`toHaveBeenCalledWith({ tenant_id:
 * AURORA.id })`); the day the page sorts differently, that test goes green
 * while asserting about the wrong tenant. That render-order correctness is the
 * whole justification for this change, and it holds whatever the load harness
 * reports. The row test id already exists in production
 * (`TenantsAdminPage.tsx`, `data-testid={`tenant-row-${tenant.id}`}`), so no
 * component change is needed.
 */
const inviteButtonFor = async (tenantId: string) =>
  within(await screen.findByTestId(`tenant-row-${tenantId}`)).getByRole(
    "button",
    { name: t("invitations.dialog.title") },
  );

const openPanel = async (
  user: ReturnType<typeof userEvent.setup>,
  tenantId: string,
) => {
  await user.click(await screen.findByTestId(`tenant-administrator-${tenantId}`));
  return within(await screen.findByTestId("invitation-panel"));
};

beforeEach(() => {
  vi.clearAllMocks();
  mockedGet.mockReset();
  mockedPost.mockReset();
  mockedIssue.mockReset();
  mockedList.mockReset();
  mockedGet.mockImplementation(((url: string) =>
    url === "/tenants"
      ? Promise.resolve({ data: TENANTS })
      : Promise.resolve({ data: [] })) as never);
  // The route's `tenant_id` is optional: unfiltered returns everything,
  // filtered returns one condominium's. Both shapes are answered here so a
  // component reading the wrong one shows.
  mockedList.mockImplementation((tenantId?: string) =>
    Promise.resolve(
      tenantId === undefined
        ? ALL_INVITATIONS
        : ALL_INVITATIONS.filter(
            (invitation) => invitation.tenant_id === tenantId,
          ),
    ),
  );
  mockedIssue.mockResolvedValue(PENDING);
  vi.mocked(useMyPermissions).mockReturnValue(settledPermissions([]) as never);
});

describe("TenantsAdminPage — inviting an administrator", () => {
  it("posts { tenant_id, email } from the row action and renders the 201 success state", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(await inviteButtonFor(AURORA.id));
    await user.type(
      screen.getByLabelText(t("invitations.dialog.emailLabel")),
      "ana.souza@example.com",
    );
    await user.click(
      screen.getByRole("button", { name: t("invitations.dialog.submit") }),
    );

    await waitFor(() => expect(mockedIssue).toHaveBeenCalledTimes(1));
    expect(mockedIssue).toHaveBeenCalledWith({
      tenant_id: AURORA.id,
      email: "ana.souza@example.com",
    });
    const success = await screen.findByTestId("invitation-sent");
    expect(success).toHaveTextContent("ana.souza@example.com");
    expect(success).toHaveTextContent(AURORA.name);
  });

  it("sends the optional full name, disables submit while empty and while pending", async () => {
    let resolveIssue: ((value: Invitation) => void) | undefined;
    mockedIssue.mockReturnValue(
      new Promise<Invitation>((resolve) => {
        resolveIssue = resolve;
      }),
    );
    const user = userEvent.setup();
    renderPage();

    await user.click(await inviteButtonFor(AURORA.id));
    const submit = screen.getByRole("button", {
      name: t("invitations.dialog.submit"),
    });
    expect(submit).toBeDisabled();

    await user.type(
      screen.getByLabelText(t("invitations.dialog.emailLabel")),
      "ana@example.com",
    );
    await user.type(
      screen.getByLabelText(t("invitations.dialog.fullNameLabel")),
      "Ana Souza",
    );
    expect(submit).toBeEnabled();
    await user.click(submit);

    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: t("invitations.dialog.submitting") }),
      ).toBeDisabled(),
    );
    expect(mockedIssue).toHaveBeenCalledWith({
      tenant_id: AURORA.id,
      email: "ana@example.com",
      full_name: "Ana Souza",
    });
    resolveIssue?.(PENDING);
    expect(await screen.findByTestId("invitation-sent")).toBeInTheDocument();
  });

  it("renders the translated invalid-email message on 422 and the generic one otherwise", async () => {
    mockedIssue.mockRejectedValue({ response: { status: 422 } });
    const user = userEvent.setup();
    renderPage();

    await user.click(await inviteButtonFor(AURORA.id));
    // Well-formed for the browser's own `type="email"` check and refused by
    // `EmailStr` all the same — the 422 this arm is about is the server's.
    await user.type(
      screen.getByLabelText(t("invitations.dialog.emailLabel")),
      "ana@invalido",
    );
    await user.click(
      screen.getByRole("button", { name: t("invitations.dialog.submit") }),
    );

    expect(
      await screen.findByText(t("invitations.dialog.invalidEmail")),
    ).toBeInTheDocument();

    mockedIssue.mockRejectedValue({ response: { status: 500 } });
    await user.click(
      screen.getByRole("button", { name: t("invitations.dialog.submit") }),
    );
    expect(
      await screen.findByText(t("invitations.dialog.genericError")),
    ).toBeInTheDocument();
  });

  it("closes the dialog without posting when the operator cancels", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(await inviteButtonFor(AURORA.id));
    await user.click(
      screen.getByRole("button", { name: t("invitations.dialog.cancel") }),
    );

    expect(screen.queryByTestId("invite-administrator-dialog")).toBeNull();
    expect(mockedIssue).not.toHaveBeenCalled();
  });

  it("opens the same dialog with the freshly created condominium preselected", async () => {
    const created = {
      id: "t-new",
      name: "Residencial Altos da Serra VI",
      slug: "residencial-altos-da-serra-vi",
      is_active: true,
      created_at: "2026-09-21T09:00:00",
    };
    mockedPost.mockResolvedValue({ data: created } as never);
    const user = userEvent.setup();
    renderPage();

    await user.click(
      await screen.findByRole("button", { name: t("tenantsAdmin.new") }),
    );
    await user.type(
      screen.getByLabelText(t("tenantsAdmin.nameLabel")),
      created.name,
    );
    await user.click(
      screen.getByRole("button", { name: t("tenantsAdmin.submit") }),
    );

    await user.click(
      await screen.findByRole("button", {
        name: t("invitations.dialog.titleFromCreated"),
      }),
    );
    const dialog = within(screen.getByTestId("invite-administrator-dialog"));
    expect(dialog.getByTestId("invite-dialog-tenant")).toHaveTextContent(
      created.name,
    );

    await user.type(
      screen.getByLabelText(t("invitations.dialog.emailLabel")),
      "novo@example.com",
    );
    await user.click(
      screen.getByRole("button", { name: t("invitations.dialog.submit") }),
    );
    await waitFor(() =>
      expect(mockedIssue).toHaveBeenCalledWith({
        tenant_id: created.id,
        email: "novo@example.com",
      }),
    );
  });
});

describe("TenantsAdminPage — the per-tenant invitation panel", () => {
  it("fills the whole column with ONE unfiltered call, never one per row", async () => {
    const user = userEvent.setup();
    renderPage();

    // Three rows on screen, one list call: the unfiltered one the page makes
    // for the whole table. The count is what rules out a per-row request —
    // it would be three here, and would grow with the table.
    await screen.findByTestId(`tenant-row-${SERRA.id}`);
    await waitFor(() => expect(mockedList).toHaveBeenCalledTimes(1));
    expect(mockedList).toHaveBeenCalledWith();
    expect(mockedList).not.toHaveBeenCalledWith(AURORA.id);

    // The panel adds exactly one filtered call, for the condominium opened.
    await openPanel(user, AURORA.id);
    await waitFor(() => expect(mockedList).toHaveBeenCalledTimes(2));
    expect(mockedList).toHaveBeenLastCalledWith(AURORA.id);
  });

  it("derives three distinct badges from accepted_at and expires_at alone", async () => {
    const user = userEvent.setup();
    renderPage();
    const panel = await openPanel(user, AURORA.id);

    const accepted = within(
      await screen.findByTestId(`invitation-row-${ACCEPTED.id}`),
    );
    const expired = within(screen.getByTestId(`invitation-row-${EXPIRED.id}`));
    const pending = within(screen.getByTestId(`invitation-row-${PENDING.id}`));

    expect(
      accepted.getByText(t("invitations.status.accepted")),
    ).toBeInTheDocument();
    expect(
      expired.getByText(t("invitations.status.expired")),
    ).toBeInTheDocument();
    expect(
      pending.getByText(t("invitations.status.pending")),
    ).toBeInTheDocument();

    // Distinct, not merely present: no row carries another row's label.
    expect(accepted.queryByText(t("invitations.status.pending"))).toBeNull();
    expect(expired.queryByText(t("invitations.status.accepted"))).toBeNull();
    expect(pending.queryByText(t("invitations.status.expired"))).toBeNull();

    // The three badges render three different classes, so they are also
    // visually distinct and not three copies of one neutral chip.
    const chip = (scope: ReturnType<typeof within>, key: string) =>
      scope.getByText(t(key)).className;
    expect(
      new Set([
        chip(accepted, "invitations.status.accepted"),
        chip(expired, "invitations.status.expired"),
        chip(pending, "invitations.status.pending"),
      ]).size,
    ).toBe(3);

    // Emails and the two dates are on the row; the panel names its tenant.
    expect(panel.getByText(PENDING.email)).toBeInTheDocument();
    expect(
      pending.getByText(new Date(PENDING.created_at).toLocaleDateString("pt")),
    ).toBeInTheDocument();
    expect(
      pending.getByText(new Date(PENDING.expires_at).toLocaleDateString("pt")),
    ).toBeInTheDocument();
  });

  it("resends a pending or expired invitation and offers no resend on an accepted one", async () => {
    const user = userEvent.setup();
    const { client } = renderPage();
    const invalidate = vi.spyOn(client, "invalidateQueries");
    await openPanel(user, AURORA.id);

    const accepted = within(
      await screen.findByTestId(`invitation-row-${ACCEPTED.id}`),
    );
    expect(
      accepted.queryByRole("button", { name: t("invitations.panel.resend") }),
    ).toBeNull();

    const expired = within(screen.getByTestId(`invitation-row-${EXPIRED.id}`));
    expect(
      expired.getByRole("button", { name: t("invitations.panel.resend") }),
    ).toBeInTheDocument();

    const pending = within(screen.getByTestId(`invitation-row-${PENDING.id}`));
    await user.click(
      pending.getByRole("button", { name: t("invitations.panel.resend") }),
    );

    await waitFor(() =>
      expect(mockedIssue).toHaveBeenCalledWith({
        tenant_id: PENDING.tenant_id,
        email: PENDING.email,
      }),
    );
    await waitFor(() =>
      expect(invalidate).toHaveBeenCalledWith({ queryKey: ["invitations"] }),
    );
  });

  it("labels the action as resending while the re-issue is in flight", async () => {
    mockedIssue.mockReturnValue(new Promise<Invitation>(() => {}));
    const user = userEvent.setup();
    renderPage();
    await openPanel(user, AURORA.id);

    const pending = within(
      await screen.findByTestId(`invitation-row-${PENDING.id}`),
    );
    await user.click(
      pending.getByRole("button", { name: t("invitations.panel.resend") }),
    );

    expect(
      await screen.findByRole("button", {
        name: t("invitations.panel.resending"),
      }),
    ).toBeDisabled();
  });

  it("draws no revoke control anywhere in the panel", async () => {
    const user = userEvent.setup();
    renderPage();
    const panel = await openPanel(user, AURORA.id);
    await screen.findByTestId(`invitation-row-${PENDING.id}`);

    // D4: there is no `revoked_at` column and no route, so no control may
    // suggest one exists. Matched case-insensitively across both locales.
    expect(panel.queryByText(/revogar|revoke|cancelar convite/i)).toBeNull();
  });

  it("shows the loading, error and empty states of the panel", async () => {
    let resolveList: ((value: Invitation[]) => void) | undefined;
    mockedList.mockReturnValue(
      new Promise<Invitation[]>((resolve) => {
        resolveList = resolve;
      }),
    );
    const user = userEvent.setup();
    const { unmount } = renderPage();
    let panel = await openPanel(user, AURORA.id);
    expect(panel.getByText(t("invitations.panel.loading"))).toBeInTheDocument();
    resolveList?.([]);
    expect(
      await screen.findByText(t("invitations.panel.empty")),
    ).toBeInTheDocument();
    unmount();

    mockedList.mockRejectedValue(new Error("500"));
    renderPage();
    panel = await openPanel(user, AURORA.id);
    expect(
      await screen.findByText(t("invitations.panel.loadError")),
    ).toBeInTheDocument();
  });

  it("closes the panel and stops listing", async () => {
    const user = userEvent.setup();
    renderPage();
    const panel = await openPanel(user, AURORA.id);
    await screen.findByTestId(`invitation-row-${PENDING.id}`);

    await user.click(
      panel.getByRole("button", { name: t("invitations.panel.close") }),
    );
    expect(screen.queryByTestId("invitation-panel")).toBeNull();
  });

  it("states each condominium's newest invitation on first load, with no panel opened", async () => {
    renderPage();

    // No panel is ever opened in this test: the column is correct from the
    // one list call the page makes.
    await waitFor(() =>
      expect(
        screen.getByTestId(`tenant-administrator-${AURORA.id}`),
      ).toHaveTextContent(t("invitations.status.pending")),
    );
    // The newest is the first entry the endpoint returns for that
    // condominium, not the first entry of the payload.
    expect(
      screen.getByTestId(`tenant-administrator-${AGUAS.id}`),
    ).toHaveTextContent(t("invitations.status.accepted"));

    // The em dash means exactly one thing: the list came back and this
    // condominium has none.
    expect(
      screen.getByTestId(`tenant-administrator-${SERRA.id}`),
    ).toHaveTextContent(t("tenantsAdmin.administratorPlaceholder"));
    expect(screen.queryByTestId("invitation-panel")).toBeNull();
  });

  it("says the column failed instead of going silently blank, and still opens the panel", async () => {
    const user = userEvent.setup();
    // The unfiltered call fails; the panel's filtered call still works, so
    // the click-through is a real recovery and not a second dead end.
    mockedList.mockImplementation((tenantId?: string) =>
      tenantId === undefined
        ? Promise.reject(new Error("500"))
        : Promise.resolve(
            ALL_INVITATIONS.filter(
              (invitation) => invitation.tenant_id === tenantId,
            ),
          ),
    );
    renderPage();

    const cell = await screen.findByTestId(`tenant-administrator-${AURORA.id}`);
    // (a) No em dash: that would say "no invitation", which is not known.
    await waitFor(() =>
      expect(cell).toHaveTextContent(t("invitations.column.loadError")),
    );
    expect(cell).not.toHaveTextContent(
      t("tenantsAdmin.administratorPlaceholder"),
    );
    // (b) Something visible, not an empty box, and it explains itself.
    expect(cell.textContent?.trim()).not.toBe("");
    expect(
      within(cell).getByTitle(t("invitations.panel.loadError")),
    ).toBeInTheDocument();
    // Every row says so, not just the first.
    expect(
      screen.getByTestId(`tenant-administrator-${SERRA.id}`),
    ).toHaveTextContent(t("invitations.column.loadError"));

    // (c) The cell still opens the panel, which is where the retry lives.
    await user.click(cell);
    expect(
      within(await screen.findByTestId("invitation-panel")).getByText(
        PENDING.email,
      ),
    ).toBeInTheDocument();
  });

  it("claims nothing — no em dash — while the invitation list is still in flight", async () => {
    let resolveList: ((value: Invitation[]) => void) | undefined;
    mockedList.mockReturnValue(
      new Promise<Invitation[]>((resolve) => {
        resolveList = resolve;
      }),
    );
    renderPage();

    // An em dash here would tell a superuser that SERRA *and* AURORA have no
    // administrator invited, and the natural response is a duplicate invite.
    const aurora = await screen.findByTestId(
      `tenant-administrator-${AURORA.id}`,
    );
    expect(aurora).toHaveTextContent("");
    expect(aurora).not.toHaveTextContent(
      t("tenantsAdmin.administratorPlaceholder"),
    );
    // The cell is still reachable and still names what it opens.
    expect(aurora).toHaveAccessibleName(
      `Ver os convites de ${AURORA.name}`,
    );

    resolveList?.(ALL_INVITATIONS);
    await waitFor(() =>
      expect(aurora).toHaveTextContent(t("invitations.status.pending")),
    );
  });
});

describe("/admin/tenants invitation controls behind the superuser gate", () => {
  const mockAuth = (user: Partial<User>) => {
    vi.spyOn(AuthHook, "useAuth").mockReturnValue({
      user: user as User,
      isAuthenticated: true,
      isLoading: false,
      login: vi.fn() as never,
      logout: vi.fn(),
    });
  };

  const renderRoute = () =>
    render(
      <QueryClientProvider client={newClient()}>
        <MemoryRouter initialEntries={["/admin/tenants"]}>
          <Routes>
            <Route
              path="/admin/tenants"
              element={
                <ProtectedRoute requiredAccess={ROUTE_ACCESS["/admin/tenants"]}>
                  <TenantsAdminPage />
                </ProtectedRoute>
              }
            />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    );

  it("renders RestrictedAccessMessage and neither invitation control for a non-superuser", async () => {
    mockAuth({ id: "u-tenant-admin", is_superuser: false, tenants: [] });
    vi.mocked(useMyPermissions).mockReturnValue(
      settledPermissions(ALL_PERMISSIONS) as never,
    );

    renderRoute();

    expect(await screen.findByText("Acesso restrito")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: t("invitations.dialog.title") }),
    ).toBeNull();
    expect(screen.queryByTestId("invitation-panel")).toBeNull();
    expect(mockedList).not.toHaveBeenCalled();
    expect(mockedIssue).not.toHaveBeenCalled();
  });
});
