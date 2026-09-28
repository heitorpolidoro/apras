import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import App from "../App";
import apiClient from "../api/client";
import { clearActingTenantId, getActingTenantId } from "../features/user-administration/context/tenantState";

/**
 * The public routes carry no application chrome (APRAS-106).
 *
 * `/c/<slug>/obras` is public by decision (APRAS-92 D1) but, until this task,
 * every route was wrapped in `<Navbar />` and `<AppLayoutContent>`. Both are
 * authenticated chrome, so the report was correct in a private window and
 * wrong in a signed-in operator's session: app navigation on a public
 * document, and the document pushed right by the width of a sidebar nobody
 * else can see.
 *
 * This file follows `AppRouting.smoke.test.tsx`'s discipline and not
 * `BrandedEntryPage.test.tsx`'s: the real `App` is mounted — real
 * `BrowserRouter`, real `AuthProvider`/`TenantProvider`/`SidebarProvider`,
 * real page modules — and the **only** mocked module is `src/api/client`.
 * Mocking the router, the auth context or the layout would simulate precisely
 * the integration under test, which is how the app composes layout around a
 * route; APRAS-69 had to be written to undo exactly that mistake once.
 *
 * The two auth states come from one seam and no other: a seeded
 * `localStorage.accessToken` plus a resolving `GET /auth/me`. `isAuthenticated`
 * is never asserted directly — it is asserted by its consequence, the chrome
 * appearing on a non-public route.
 */

const SLUG = "condominio-a";
const REPORT_PATH = `/public/tenants/${SLUG}/projects/report`;
const BRANDING_PATH = `/public/tenants/${SLUG}/branding`;

/** The one report fixture both auth states are served, byte for byte. */
const REPORT_HTML =
  "<html><body><h1>Relatório de Obras</h1><p>Fixture</p></body></html>";

const BRANDING = {
  name: "Condomínio A",
  logo_url: null,
  theme: null,
};

const TENANT_A = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa";
const TENANT_B = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb";

const tenant = (id: string, name: string, slug: string) => ({
  id,
  name,
  slug,
  is_active: true,
  created_at: "2026-01-01T00:00:00Z",
});

/** The condominium behind SLUG, and one the user may actually be a member of. */
const TENANT_OF_SLUG = tenant(TENANT_A, "Condomínio A", SLUG);
const OTHER_TENANT = tenant(TENANT_B, "Condomínio B", "condominio-b");

const membership = (tenantId: string, name: string) => ({
  tenant_id: tenantId,
  name,
  is_active: true,
  is_tenant_admin: false,
});

const userWith = (memberships: ReturnType<typeof membership>[]) => ({
  id: "u-1",
  email: "morador@test.com",
  full_name: "Morador",
  is_active: true,
  roles: [],
  tenants: memberships,
});

vi.mock("../api/client", () => ({
  default: {
    // `publicReportUrl` reads the base off the shared client to build the
    // "open for printing" link, so the mock has to carry one.
    defaults: { baseURL: "http://api.test/api/v1" },
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

const mockedGet = vi.mocked(apiClient.get);

interface Session {
  /** `null` means anonymous: no token is seeded and `/auth/me` rejects. */
  user: ReturnType<typeof userWith> | null;
  /** What `GET /tenants` answers. Only read when signed in. */
  tenants: ReturnType<typeof tenant>[];
}

const ANONYMOUS: Session = { user: null, tenants: [] };
const NON_MEMBER: Session = {
  user: userWith([membership(TENANT_B, "Condomínio B")]),
  tenants: [OTHER_TENANT],
};
const MEMBER: Session = {
  user: userWith([membership(TENANT_A, "Condomínio A")]),
  tenants: [TENANT_OF_SLUG],
};

const installClient = (session: Session) => {
  mockedGet.mockReset();
  mockedGet.mockImplementation(((url: string) => {
    if (url === "/auth/me") {
      return session.user === null
        ? Promise.reject(new Error("no session"))
        : Promise.resolve({ data: session.user });
    }
    if (url === "/tenants") return Promise.resolve({ data: session.tenants });
    if (url === "/permissions/me") {
      return Promise.resolve({
        data: {
          tenant_id: getActingTenantId(),
          permissions: [],
          disabled_modules: [],
        },
      });
    }
    if (url === REPORT_PATH) return Promise.resolve({ data: REPORT_HTML });
    if (url === BRANDING_PATH) return Promise.resolve({ data: BRANDING });
    return Promise.resolve({ data: [] });
  }) as never);

  if (session.user !== null) {
    localStorage.setItem("accessToken", "stored-token");
  }
};

const renderAppAt = (path: string) => {
  window.history.pushState({}, "", path);
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>,
  );
};

/** Every element carrying the sidebar offset `AppLayoutContent` applies. */
const offsetElements = (container: HTMLElement) =>
  container.querySelectorAll('[class*="md:ml-64"], [class*="md:ml-20"]');

const expectNoChrome = (container: HTMLElement) => {
  expect(container.querySelector("header")).toBeNull();
  expect(container.querySelector("aside")).toBeNull();
  expect(offsetElements(container).length).toBe(0);
};

describe("public routes render without the app chrome (real App)", () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
    // The acting-tenant mirror is module-level and would otherwise survive
    // from the previous test, handing the next one a resolved tenant it never
    // earned.
    clearActingTenantId();
  });

  it("renders /c/<slug>/obras with no chrome for an anonymous visitor", async () => {
    installClient(ANONYMOUS);

    const { container } = renderAppAt(`/c/${SLUG}/obras`);

    expect(
      await screen.findByTestId("public-obras-report-frame"),
    ).toBeInTheDocument();
    expectNoChrome(container);
    expect(window.location.pathname).toBe(`/c/${SLUG}/obras`);
  });

  it("renders /c/<slug>/obras with no chrome for a signed-in visitor", async () => {
    installClient(MEMBER);

    const { container } = renderAppAt(`/c/${SLUG}/obras`);

    expect(
      await screen.findByTestId("public-obras-report-frame"),
    ).toBeInTheDocument();
    expectNoChrome(container);
    expect(window.location.pathname).toBe(`/c/${SLUG}/obras`);
  });

  it("renders byte-identical markup for /c/<slug>/obras in both auth states", async () => {
    installClient(ANONYMOUS);
    const anonymous = renderAppAt(`/c/${SLUG}/obras`);
    await screen.findByTestId("public-obras-report-frame");
    const anonymousHtml = anonymous.container.innerHTML;
    anonymous.unmount();

    localStorage.clear();
    sessionStorage.clear();
    clearActingTenantId();

    installClient(MEMBER);
    const signedIn = renderAppAt(`/c/${SLUG}/obras`);
    await screen.findByTestId("public-obras-report-frame");
    const signedInHtml = signedIn.container.innerHTML;

    // Guards, without which two empty or failed renders would pass by being
    // equal to each other.
    expect(anonymousHtml.length).toBeGreaterThan(0);
    expect(anonymousHtml).toContain("public-obras-report-frame");
    expect(signedInHtml).toContain("public-obras-report-frame");

    expect(signedInHtml).toBe(anonymousHtml);
  });

  it("still renders the chrome for a signed-in visitor on /welcome", async () => {
    installClient(MEMBER);

    const { container } = renderAppAt("/welcome");

    expect(
      await screen.findByRole("button", { name: "Sair" }),
    ).toBeInTheDocument();
    expect(container.querySelector("header")).not.toBeNull();
    expect(container.querySelector("aside")).not.toBeNull();
    expect(offsetElements(container).length).toBeGreaterThan(0);
  });

  it("renders /c/<slug> with no chrome for an anonymous visitor", async () => {
    installClient(ANONYMOUS);

    const { container } = renderAppAt(`/c/${SLUG}`);

    // The branded sign-in screen itself must still be there.
    expect(await screen.findByLabelText("E-mail")).toBeInTheDocument();
    expect(screen.getByLabelText("Senha")).toBeInTheDocument();
    expect(screen.getByText("Condomínio A")).toBeInTheDocument();
    expectNoChrome(container);
    expect(window.location.pathname).toBe(`/c/${SLUG}`);
  });

  it("renders /c/<slug> with no chrome for a signed-in non-member", async () => {
    installClient(NON_MEMBER);

    const { container } = renderAppAt(`/c/${SLUG}`);

    // The no-access panel, with its own affordances, must still be there.
    expect(
      await screen.findByText("Você não tem acesso a este condomínio"),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Ir para os meus condomínios" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Sair" })).toBeInTheDocument();
    expectNoChrome(container);
    expect(window.location.pathname).toBe(`/c/${SLUG}`);
  });

  it("still redirects a signed-in member from /c/<slug> to /", async () => {
    installClient(MEMBER);

    renderAppAt(`/c/${SLUG}`);

    // Only the redirect is asserted: `/` is a chrome-bearing route, so the
    // header, the aside and the offset class are expected once it settles.
    await waitFor(() => {
      expect(window.location.pathname).toBe("/");
    });
  });
});
