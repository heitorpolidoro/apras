import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type React from "react";
import RoleMembersPanel from "../components/RoleMembersPanel";
import apiClient from "../../../api/client";

/** Membership from the role side (APRAS-48 §6.4). */
vi.mock("../../../api/client", () => ({
  default: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}));

const ROLE_ID = "g-custom";
const OTHER_ROLE = { id: "g-other", name: "Outro" };
const THIS_ROLE = { id: ROLE_ID, name: "Conselho" };

const USERS = [
  {
    id: "u-member",
    email: "ana@test.com",
    full_name: "Ana",
    is_active: true,
    roles: [OTHER_ROLE, THIS_ROLE],
  },
  {
    id: "u-outsider",
    email: "bruno@test.com",
    full_name: "Bruno",
    is_active: true,
    roles: [OTHER_ROLE],
  },
];

const mockedGet = vi.mocked(apiClient.get);
const mockedPatch = vi.mocked(apiClient.patch);

const wrapper = (): React.FC<{ children: React.ReactNode }> => {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
};

beforeEach(() => {
  vi.clearAllMocks();
  mockedGet.mockImplementation(((url: string) =>
    url === "/users/"
      ? Promise.resolve({ data: USERS })
      : Promise.resolve({ data: [] })) as never);
  mockedPatch.mockResolvedValue({ data: {} } as never);
});

const renderPanel = () =>
  render(<RoleMembersPanel roleId={ROLE_ID} />, { wrapper: wrapper() });

describe("RoleMembersPanel", () => {
  it("lists the role's members", async () => {
    renderPanel();

    // Ana is the only member; the list item carries a Remover control.
    expect(
      await screen.findByRole("button", { name: "Remover Ana" }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Remover Bruno" })).toBeNull();
    // Bruno is a member of another role only, so he is offered as a candidate.
    expect(screen.getByRole("option", { name: "Bruno" })).toBeInTheDocument();
    expect(screen.queryByRole("option", { name: "Ana" })).toBeNull();
  });

  it("adds a member through PATCH /users/{id}", async () => {
    renderPanel();
    await screen.findByText("Ana");

    await userEvent.selectOptions(
      screen.getByLabelText("Adicionar membro"),
      "u-outsider",
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Adicionar membro" }),
    );

    await waitFor(() =>
      // The recomputed full list, never a delta: the same call and the same
      // payload shape the user-side modal makes.
      expect(mockedPatch).toHaveBeenCalledWith("/users/u-outsider", {
        role_ids: ["g-other", ROLE_ID],
      }),
    );
  });

  it("removes a member", async () => {
    renderPanel();
    await screen.findByText("Ana");

    await userEvent.click(screen.getByRole("button", { name: "Remover Ana" }));

    await waitFor(() =>
      expect(mockedPatch).toHaveBeenCalledWith("/users/u-member", {
        role_ids: ["g-other"],
      }),
    );
  });

  it("shows the anti-escalation 403 as a friendly message", async () => {
    mockedPatch.mockRejectedValue({
      response: {
        status: 403,
        data: {
          detail: "You cannot grant permissions you do not hold: finance:read",
        },
      },
    } as never);
    renderPanel();
    await screen.findByText("Ana");

    await userEvent.click(screen.getByRole("button", { name: "Remover Ana" }));

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Ver");
    expect(alert.textContent).not.toContain("You cannot grant");
  });

  it("renders the empty state when the role has no member", async () => {
    mockedGet.mockImplementation(((url: string) =>
      url === "/users/"
        ? Promise.resolve({ data: [USERS[1]] })
        : Promise.resolve({ data: [] })) as never);

    renderPanel();

    expect(await screen.findByText("Nenhum membro ainda.")).toBeInTheDocument();
  });
});
