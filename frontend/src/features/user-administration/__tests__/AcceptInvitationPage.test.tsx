import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import pt from "../../../i18n/locales/pt.json";
import AcceptInvitationPage from "../pages/AcceptInvitationPage";
import * as AuthHook from "../context/AuthContext";
import { acceptInvitation, previewInvitation } from "../../../api/invitations";
import type { InvitationPreview } from "../../../types/invitations";

/**
 * The public acceptance page at `/invite?token=…` (APRAS-72 D5–D7).
 *
 * The rule the whole file exists to pin down: the preview's `account_exists`
 * chooses the **form**, and the accept response **status** chooses the
 * **outcome**. Both crossings are exercised below, because the two calls
 * happen at different moments and can disagree.
 */

vi.mock("../../../api/invitations", () => ({
  issueInvitation: vi.fn(),
  listInvitations: vi.fn(),
  previewInvitation: vi.fn(),
  acceptInvitation: vi.fn(),
}));

const mockedPreview = vi.mocked(previewInvitation);
const mockedAccept = vi.mocked(acceptInvitation);

const t = (key: string): string =>
  key
    .split(".")
    .reduce<unknown>(
      (node, part) => (node as Record<string, unknown>)?.[part],
      pt,
    ) as string;

const TOKEN = "raw-token-value";

const NEW_ACCOUNT: InvitationPreview = {
  email: "ana.souza@example.com",
  tenant_name: "Residencial Aurora",
  tenant_slug: "residencial-aurora",
  invited_by_name: "Heitor Polidoro",
  expires_at: "2026-09-28T12:00:00Z",
  account_exists: false,
};
const EXISTING_ACCOUNT: InvitationPreview = {
  ...NEW_ACCOUNT,
  email: "ja.tenho.conta@example.com",
  account_exists: true,
};

const httpError = (status: number) => ({ response: { status } });

let login: ReturnType<typeof vi.fn>;

const renderPage = (search = `?token=${TOKEN}`) =>
  render(
    <MemoryRouter initialEntries={[`/invite${search}`]}>
      <Routes>
        <Route path="/invite" element={<AcceptInvitationPage />} />
        <Route path="/" element={<div>Painel geral</div>} />
        <Route path="/login" element={<div>Tela de login</div>} />
      </Routes>
    </MemoryRouter>,
  );

const fillNewAccount = async (user: ReturnType<typeof userEvent.setup>) => {
  await user.type(
    screen.getByLabelText(t("acceptInvitation.newAccount.fullNameLabel")),
    "Ana Souza",
  );
  await user.type(
    screen.getByLabelText(t("acceptInvitation.newAccount.cpfLabel")),
    "529.982.247-25",
  );
  await user.type(
    screen.getByLabelText(t("acceptInvitation.newAccount.passwordLabel")),
    "Senha!123",
  );
  await user.type(
    screen.getByLabelText(
      t("acceptInvitation.newAccount.confirmPasswordLabel"),
    ),
    "Senha!123",
  );
};

const submitNewAccount = (user: ReturnType<typeof userEvent.setup>) =>
  user.click(
    screen.getByRole("button", {
      name: t("acceptInvitation.newAccount.submit"),
    }),
  );

/** No credential of any kind reached either storage (D6). */
const expectNoStoredToken = () => {
  expect(localStorage.getItem("accessToken")).toBeNull();
  expect(sessionStorage.getItem("accessToken")).toBeNull();
  expect(sessionStorage.getItem("accessToken")).not.toBe("undefined");
};

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
  sessionStorage.clear();
  // The scrub test writes to the real address bar; reset it so no test
  // inherits another's URL.
  window.history.replaceState({}, "", "/");
  login = vi.fn().mockResolvedValue(undefined);
  vi.spyOn(AuthHook, "useAuth").mockReturnValue({
    user: null,
    isAuthenticated: false,
    isLoading: false,
    login: login as never,
    logout: vi.fn(),
  });
});

describe("AcceptInvitationPage — the preview comes first", () => {
  it("describes the invitation before asking for anything", async () => {
    mockedPreview.mockResolvedValue(NEW_ACCOUNT);
    renderPage();

    const details = await screen.findByTestId("invitation-preview");
    expect(details).toHaveTextContent(NEW_ACCOUNT.email);
    expect(details).toHaveTextContent(NEW_ACCOUNT.tenant_name);
    expect(details).toHaveTextContent(NEW_ACCOUNT.tenant_slug);
    expect(details).toHaveTextContent(NEW_ACCOUNT.invited_by_name);
    expect(details).toHaveTextContent(
      new Date(NEW_ACCOUNT.expires_at).toLocaleDateString("pt"),
    );
    expect(mockedPreview).toHaveBeenCalledWith(TOKEN);
  });

  it("previews exactly once under StrictMode's double effect", async () => {
    mockedPreview.mockResolvedValue(NEW_ACCOUNT);
    render(
      <React.StrictMode>
        <MemoryRouter initialEntries={[`/invite?token=${TOKEN}`]}>
          <Routes>
            <Route path="/invite" element={<AcceptInvitationPage />} />
          </Routes>
        </MemoryRouter>
      </React.StrictMode>,
    );

    await screen.findByTestId("invitation-preview");
    // The route allows five requests a minute; a doubled mount would spend
    // two of them on one page load.
    expect(mockedPreview).toHaveBeenCalledTimes(1);
  });

  it("scrubs the raw token out of the address bar once it has been read", async () => {
    mockedPreview.mockResolvedValue(NEW_ACCOUNT);
    // Seed the real address bar first. `MemoryRouter` never writes to
    // `window.location`, so without this the two token assertions below
    // would pass with the `replaceState` call deleted — they would be
    // asserting jsdom's ambient URL, not the page's behaviour.
    window.history.replaceState({}, "", `/invite?token=${TOKEN}`);
    expect(window.location.href).toContain(TOKEN);

    renderPage();

    await screen.findByTestId("invitation-preview");
    // The token mints a condominium administrator; leaving it in the URL
    // leaves it in history and in every subsequent `Referer`.
    expect(window.location.search).toBe("");
    expect(window.location.href).not.toContain(TOKEN);
    expect(window.location.pathname).toBe("/invite");
    // Scrubbing the bar must not cost the page the token it already holds.
    expect(mockedPreview).toHaveBeenCalledWith(TOKEN);
  });

  it("sends a reload after the scrub back to the e-mail, never to the superuser", async () => {
    // What the invitee hits after leaving the tab to fetch their CPF: the
    // bar now reads `/invite`, so the remount sees no token — but their
    // invitation is alive and their link still works.
    renderPage("");

    const panel = await screen.findByTestId("invitation-missingLink");
    expect(panel).toHaveTextContent(t("acceptInvitation.missingLink.body"));
    // Not the 404 copy: the invitation exists and the link was complete.
    expect(panel).not.toHaveTextContent(t("acceptInvitation.invalid.body"));
    // And above all not "ask the superuser for a new invitation": a re-issue
    // supersedes the valid token still in their mailbox (APRAS-71 D4).
    expect(panel.textContent).not.toMatch(/novo convite|superusu/i);
    expect(panel.textContent).toMatch(/e-mail/i);
    expect(mockedPreview).not.toHaveBeenCalled();
  });

  it("gives the rate-limited or failing preview its own copy, not the generic string twice", async () => {
    // 429 from the 5/minute limiter, or any 5xx: the link is fine, so none
    // of the four D7 states may be claimed.
    mockedPreview.mockRejectedValue(httpError(429));
    renderPage();

    const panel = await screen.findByTestId("invitation-error");
    expect(panel).toHaveTextContent(t("acceptInvitation.error.title"));
    expect(panel).toHaveTextContent(t("acceptInvitation.error.body"));
    expect(t("acceptInvitation.error.title")).not.toBe(
      t("acceptInvitation.error.body"),
    );
    expect(
      screen.queryByText(t("acceptInvitation.invalid.body")),
    ).toBeNull();
    expect(
      screen.queryByLabelText(t("acceptInvitation.newAccount.passwordLabel")),
    ).toBeNull();
  });

  // No parameter and an empty parameter are the same fact, and the page has
  // one predicate for it. `?token=` used to hang forever on the loading
  // message: the effect declined to call (falsy) while the render waited for
  // a terminal state it derived with `=== null`.
  it.each([
    ["no token parameter at all", ""],
    ["a token parameter with an empty value", "?token="],
  ])("renders the missing-link state and calls no API with %s", async (
    _case,
    search,
  ) => {
    renderPage(search);

    expect(
      await screen.findByText(t("acceptInvitation.missingLink.body")),
    ).toBeInTheDocument();
    // Never stuck on the loading message, and never a terminal state whose
    // copy would destroy the invitee's still-valid token.
    expect(screen.queryByText(t("acceptInvitation.loading"))).toBeNull();
    expect(screen.queryByTestId("invitation-invalid")).toBeNull();
    expect(mockedPreview).not.toHaveBeenCalled();
    expect(mockedAccept).not.toHaveBeenCalled();
    expect(
      screen.queryByLabelText(t("acceptInvitation.newAccount.passwordLabel")),
    ).toBeNull();
  });

  it.each([
    [404, "acceptInvitation.invalid.body"],
    [410, "acceptInvitation.expired.body"],
    [409, "acceptInvitation.used.body"],
  ])("renders its own terminal state and no form for a %i preview", async (
    status,
    bodyKey,
  ) => {
    mockedPreview.mockRejectedValue(httpError(status));
    renderPage();

    expect(await screen.findByText(t(bodyKey))).toBeInTheDocument();
    expect(
      screen.queryByLabelText(t("acceptInvitation.newAccount.passwordLabel")),
    ).toBeNull();
    expect(
      screen.queryByRole("button", {
        name: t("acceptInvitation.existingAccount.submit"),
      }),
    ).toBeNull();
  });

  it("links a consumed invitation to the login page", async () => {
    mockedPreview.mockRejectedValue(httpError(409));
    const user = userEvent.setup();
    renderPage();

    await user.click(
      await screen.findByRole("link", { name: t("acceptInvitation.goToLogin") }),
    );
    expect(screen.getByText("Tela de login")).toBeInTheDocument();
  });
});

describe("AcceptInvitationPage — account_exists chooses the form", () => {
  it("signs the new account in and lands on / when accept answers 201", async () => {
    mockedPreview.mockResolvedValue(NEW_ACCOUNT);
    mockedAccept.mockResolvedValue({
      status: 201,
      data: { access_token: "jwt-value", token_type: "bearer" },
    });
    const user = userEvent.setup();
    renderPage();

    await screen.findByTestId("invitation-preview");
    await fillNewAccount(user);
    await submitNewAccount(user);

    await waitFor(() => expect(mockedAccept).toHaveBeenCalledTimes(1));
    expect(mockedAccept).toHaveBeenCalledWith({
      token: TOKEN,
      full_name: "Ana Souza",
      cpf: "529.982.247-25",
      password: "Senha!123",
    });
    await waitFor(() =>
      expect(login).toHaveBeenCalledWith("jwt-value", false),
    );
    expect(await screen.findByText("Painel geral")).toBeInTheDocument();
  });

  it("renders no password, full-name or CPF field for an existing account", async () => {
    mockedPreview.mockResolvedValue(EXISTING_ACCOUNT);
    mockedAccept.mockResolvedValue({ status: 200, data: EXISTING_ACCOUNT });
    const user = userEvent.setup();
    renderPage();

    await screen.findByTestId("invitation-preview");
    expect(
      screen.queryByLabelText(t("acceptInvitation.newAccount.passwordLabel")),
    ).toBeNull();
    expect(
      screen.queryByLabelText(t("acceptInvitation.newAccount.fullNameLabel")),
    ).toBeNull();
    expect(
      screen.queryByLabelText(t("acceptInvitation.newAccount.cpfLabel")),
    ).toBeNull();

    await user.click(
      screen.getByRole("button", {
        name: t("acceptInvitation.existingAccount.submit"),
      }),
    );

    await waitFor(() => expect(mockedAccept).toHaveBeenCalledWith({ token: TOKEN }));
    const panel = await screen.findByTestId("invitation-linked");
    expect(panel).toHaveTextContent(EXISTING_ACCOUNT.tenant_name);
    expect(panel.textContent).toMatch(/senha que você já usa/i);
    expect(login).not.toHaveBeenCalled();
    expectNoStoredToken();
    expect(screen.queryByText("Painel geral")).toBeNull();
    expect(
      screen.getByRole("link", { name: t("acceptInvitation.goToLogin") }),
    ).toHaveAttribute("href", "/login");
  });

  it("refuses mismatched passwords before calling accept", async () => {
    mockedPreview.mockResolvedValue(NEW_ACCOUNT);
    const user = userEvent.setup();
    renderPage();

    await screen.findByTestId("invitation-preview");
    await fillNewAccount(user);
    await user.clear(
      screen.getByLabelText(
        t("acceptInvitation.newAccount.confirmPasswordLabel"),
      ),
    );
    await user.type(
      screen.getByLabelText(
        t("acceptInvitation.newAccount.confirmPasswordLabel"),
      ),
      "Outra!456",
    );
    await submitNewAccount(user);

    expect(
      await screen.findByText(
        t("acceptInvitation.newAccount.passwordMismatch"),
      ),
    ).toBeInTheDocument();
    expect(mockedAccept).not.toHaveBeenCalled();
  });
});

describe("AcceptInvitationPage — the accept STATUS chooses the outcome", () => {
  it("account_exists false receiving 200 lands on the terminal panel, signed out", async () => {
    mockedPreview.mockResolvedValue(NEW_ACCOUNT);
    // The invitee signed up at /signup between the preview and the accept:
    // the backend found an account and returned an `InvitationPreview` with
    // no `access_token` at all.
    mockedAccept.mockResolvedValue({
      status: 200,
      data: { ...NEW_ACCOUNT, account_exists: true },
    });
    const user = userEvent.setup();
    renderPage();

    await screen.findByTestId("invitation-preview");
    await fillNewAccount(user);
    await submitNewAccount(user);

    expect(await screen.findByTestId("invitation-linked")).toHaveTextContent(
      NEW_ACCOUNT.tenant_name,
    );
    expect(login).not.toHaveBeenCalled();
    expectNoStoredToken();
    expect(screen.queryByText("Painel geral")).toBeNull();
  });

  it("account_exists true receiving 201 signs the person in and navigates to /", async () => {
    mockedPreview.mockResolvedValue(EXISTING_ACCOUNT);
    mockedAccept.mockResolvedValue({
      status: 201,
      data: { access_token: "jwt-value", token_type: "bearer" },
    });
    const user = userEvent.setup();
    renderPage();

    await screen.findByTestId("invitation-preview");
    await user.click(
      screen.getByRole("button", {
        name: t("acceptInvitation.existingAccount.submit"),
      }),
    );

    await waitFor(() => expect(login).toHaveBeenCalledWith("jwt-value", false));
    expect(await screen.findByText("Painel geral")).toBeInTheDocument();
    expect(screen.queryByTestId("invitation-linked")).toBeNull();
  });
});

describe("AcceptInvitationPage — the two meanings of 409 on accept", () => {
  it("keeps the form and blames the CPF when the follow-up preview still answers 200", async () => {
    mockedPreview.mockResolvedValue(NEW_ACCOUNT);
    mockedAccept.mockRejectedValue(httpError(409));
    const user = userEvent.setup();
    renderPage();

    await screen.findByTestId("invitation-preview");
    await fillNewAccount(user);
    await submitNewAccount(user);

    expect(
      await screen.findByText(t("acceptInvitation.newAccount.cpfConflict")),
    ).toBeInTheDocument();
    // The token is alive: the conflict was the CPF, so the form stays open
    // with every typed value kept.
    expect(mockedPreview).toHaveBeenCalledTimes(2);
    expect(
      screen.getByLabelText(t("acceptInvitation.newAccount.fullNameLabel")),
    ).toHaveValue("Ana Souza");
    expect(
      screen.getByLabelText(t("acceptInvitation.newAccount.cpfLabel")),
    ).toHaveValue("529.982.247-25");
    expect(screen.queryByTestId("invitation-used")).toBeNull();
  });

  it("switches to the already-used state when the follow-up preview answers 409", async () => {
    mockedPreview
      .mockResolvedValueOnce(NEW_ACCOUNT)
      .mockRejectedValueOnce(httpError(409));
    mockedAccept.mockRejectedValue(httpError(409));
    const user = userEvent.setup();
    renderPage();

    await screen.findByTestId("invitation-preview");
    await fillNewAccount(user);
    await submitNewAccount(user);

    expect(await screen.findByTestId("invitation-used")).toHaveTextContent(
      t("acceptInvitation.used.body"),
    );
    expect(
      screen.queryByLabelText(t("acceptInvitation.newAccount.passwordLabel")),
    ).toBeNull();
  });

  it("switches to the expired state when accept answers 410", async () => {
    mockedPreview.mockResolvedValue(NEW_ACCOUNT);
    mockedAccept.mockRejectedValue(httpError(410));
    const user = userEvent.setup();
    renderPage();

    await screen.findByTestId("invitation-preview");
    await fillNewAccount(user);
    await submitNewAccount(user);

    expect(await screen.findByTestId("invitation-expired")).toHaveTextContent(
      t("acceptInvitation.expired.body"),
    );
    // A single preview: only the 409 path pays for the extra request (D7).
    expect(mockedPreview).toHaveBeenCalledTimes(1);
  });

  it("renders the generic message on the existing-account branch too", async () => {
    mockedPreview.mockResolvedValue(EXISTING_ACCOUNT);
    mockedAccept.mockRejectedValue(httpError(500));
    const user = userEvent.setup();
    renderPage();

    await screen.findByTestId("invitation-preview");
    await user.click(
      screen.getByRole("button", {
        name: t("acceptInvitation.existingAccount.submit"),
      }),
    );

    expect(
      await screen.findByText(t("acceptInvitation.genericError")),
    ).toBeInTheDocument();
    // Still the confirmation, never a password field.
    expect(
      screen.getByRole("button", {
        name: t("acceptInvitation.existingAccount.submit"),
      }),
    ).toBeInTheDocument();
    expect(
      screen.queryByLabelText(t("acceptInvitation.newAccount.passwordLabel")),
    ).toBeNull();
  });

  it("renders the generic message under the form for any other accept failure", async () => {
    mockedPreview.mockResolvedValue(NEW_ACCOUNT);
    mockedAccept.mockRejectedValue(httpError(500));
    const user = userEvent.setup();
    renderPage();

    await screen.findByTestId("invitation-preview");
    await fillNewAccount(user);
    await submitNewAccount(user);

    expect(
      await screen.findByText(t("acceptInvitation.genericError")),
    ).toBeInTheDocument();
    expect(
      screen.getByLabelText(t("acceptInvitation.newAccount.passwordLabel")),
    ).toBeInTheDocument();
  });
});
