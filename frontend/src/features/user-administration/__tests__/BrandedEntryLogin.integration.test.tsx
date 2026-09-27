import React, { useEffect } from "react";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  MemoryRouter,
  Routes,
  Route,
  useLocation,
} from "react-router-dom";
import { RootRedirect } from "../../../App";
import BrandedEntryPage from "../pages/BrandedEntryPage";
import { AuthProvider } from "../context/AuthContext";
import { TenantProvider } from "../context/TenantContext";
import {
  clearActingTenantId,
  getActingTenantId,
} from "../context/tenantState";
import apiClient from "../../../api/client";
import type { Tenant } from "../../../types/auth";

/**
 * The anonymous half of APRAS-69's result 4, end to end (APRAS-74 left it
 * unproven).
 *
 * `BrandedEntryPage.test.tsx` mocks `AuthContext`, `useTenant` and
 * `useNavigate` wholesale, so its login case can only reach
 * `expect(mockLogin).toHaveBeenCalledWith(...)`: every link of the
 * continuation that actually delivers the promise — token accepted →
 * `isAuthenticated` flips → the `["tenants"]` query runs → the readiness gate
 * reopens → `setActingTenant(id)` → `/` — is a mock in that file. This file
 * exercises that chain for real.
 *
 * Harness, in the kind of `src/__tests__/TenantBootstrapOrder.test.tsx`:
 * **only** `src/api/client` is mocked, and its `get`/`post` record
 * `{url, actingTenantId}` — the acting tenant *at the moment the request was
 * issued*, i.e. exactly the value the real Axios interceptor reads off the
 * module-level mirror to build `X-Tenant-Id`. The mocked client builds no
 * header object, so the header contract (result 6) is asserted on that
 * recorded mirror value. Nothing under `src/features/**` is mocked: the real
 * `AuthProvider`, `TenantProvider`, `BrandedEntryPage` and `LoginForm` are
 * under test.
 *
 * Unlike `TenantBootstrapOrder.test.tsx`, which renders the real `App`, this
 * file declares its own two-route `MemoryRouter` table, with `/` served by the
 * **real `RootRedirect`** imported from `src/App.tsx` rather than a sentinel —
 * so the landing destination is the production one and the post-login render
 * is the production render. `RootRedirect` calls `usePermissionSet()`, so the
 * stub must answer `GET /permissions/me`, and `GeneralDashboardPage` below it
 * issues further reads, hence the catch-all default.
 */

const TENANT_MINE = "22222222-2222-2222-2222-222222222222";
const TENANT_OTHER = "11111111-1111-1111-1111-111111111111";

/** The slug in the branded link, identical in all three cases — see case 3. */
const SLUG = "altos-da-serra";
const BRANDING_URL = `/public/tenants/${SLUG}/branding`;

const MINE: Tenant = {
  id: TENANT_MINE,
  name: "Condomínio Altos da Serra",
  slug: SLUG,
  is_active: true,
  created_at: "2026-01-01T00:00:00",
};

const OTHER: Tenant = {
  id: TENANT_OTHER,
  name: "Condomínio Jardim das Flores",
  slug: "jardim-das-flores",
  is_active: true,
  created_at: "2026-01-01T00:00:00",
};

/** Exactly the four keys `PublicTenantBrandingRead` serialises. */
const BRANDING = {
  slug: SLUG,
  name: MINE.name,
  logo_url: null,
  theme: null,
};

const membership = (tenant: Tenant) => ({
  tenant_id: tenant.id,
  name: tenant.name,
  is_active: true,
  is_tenant_admin: false,
});

/**
 * The visitor. `OTHER` comes **first**, which is what
 * `resolveActingTenantId` pre-selects from `/auth/me`; so when the member case
 * ends with the mirror holding `MINE.id`, it is the slug resolution that put
 * it there and nothing else.
 */
const buildUser = (memberships: Tenant[]) => ({
  id: "u-visitor",
  email: "visitor@test.com",
  full_name: "Visitante",
  is_active: true,
  roles: [],
  tenants: memberships.map(membership),
});

vi.mock("../../../api/client", () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

const mockedGet = vi.mocked(apiClient.get);
const mockedPost = vi.mocked(apiClient.post);

interface Call {
  url: string;
  actingTenantId: string | null;
}

let calls: Call[];
/** Every path the router settled on, newest last. */
let locations: string[];

const urls = () => calls.map((call) => call.url);

interface ClientOptions {
  /** Memberships of the caller, in `/auth/me` order. */
  memberships: Tenant[];
  /** Whether the condominium behind the slug exists at all. */
  brandingExists: boolean;
}

const installClient = ({ memberships, brandingExists }: ClientOptions) => {
  mockedGet.mockReset();
  mockedPost.mockReset();

  const record = (url: string) => {
    calls.push({ url, actingTenantId: getActingTenantId() });
  };

  mockedGet.mockImplementation(((url: string) => {
    record(url);

    if (url === BRANDING_URL) {
      return brandingExists
        ? Promise.resolve({ data: BRANDING })
        : Promise.reject({
            response: { status: 404, data: { detail: "Not Found" } },
          });
    }
    if (url === "/auth/me") {
      return Promise.resolve({ data: buildUser(memberships) });
    }
    if (url === "/tenants") {
      return Promise.resolve({ data: memberships });
    }
    if (url === "/permissions/me") {
      return Promise.resolve({
        data: { tenant_id: getActingTenantId(), permissions: [] },
      });
    }
    return Promise.resolve({ data: [] });
  }) as never);

  mockedPost.mockImplementation(((url: string) => {
    record(url);
    if (url.startsWith("/auth/login")) {
      return Promise.resolve({ data: { access_token: "branded-token" } });
    }
    return Promise.resolve({ data: {} });
  }) as never);
};

const LocationRecorder: React.FC = () => {
  const { pathname } = useLocation();
  useEffect(() => {
    locations.push(pathname);
  }, [pathname]);
  return null;
};

const renderBrandedEntry = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      {/* The nesting `App` itself uses: AuthProvider ▸ TenantProvider ▸ router. */}
      <AuthProvider>
        <TenantProvider>
          <MemoryRouter initialEntries={[`/c/${SLUG}`]}>
            <LocationRecorder />
            <Routes>
              <Route path="/c/:slug" element={<BrandedEntryPage />} />
              <Route path="/" element={<RootRedirect />} />
            </Routes>
          </MemoryRouter>
        </TenantProvider>
      </AuthProvider>
    </QueryClientProvider>,
  );
};

/** Fills the branded `LoginForm` and submits it. */
const signIn = async () => {
  const user = userEvent.setup();
  await user.type(
    await screen.findByLabelText("E-mail"),
    "visitor@test.com",
  );
  await user.type(screen.getByLabelText("Senha"), "secret");
  await user.click(screen.getByRole("button", { name: "Entrar" }));
};

describe("anonymous login at /c/<slug> (real providers)", () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
    // The mirror is module-level and would otherwise survive the previous
    // test, handing this one a resolved tenant it never earned.
    clearActingTenantId();
    calls = [];
    locations = [];
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("lands an anonymous member inside that condominium at /", async () => {
    installClient({ memberships: [OTHER, MINE], brandingExists: true });

    renderBrandedEntry();

    // The branded screen: the condominium's own name above the shared form.
    expect(await screen.findByText(MINE.name)).toBeInTheDocument();
    expect(getActingTenantId()).toBeNull();

    await signIn();

    // The continuation, all the way through: the production dashboard.
    expect(
      await screen.findByText("Bem-vindo ao painel central do seu condomínio."),
    ).toBeInTheDocument();
    expect(locations.at(-1)).toBe("/");

    // The pre-selection from `/auth/me` is OTHER (first membership); the slug
    // resolution is what moves the mirror to MINE.
    expect(getActingTenantId()).toBe(TENANT_MINE);

    // Result 6, held *across* the login and not only from a signed-in start:
    // every request issued after the membership list arrived carries the
    // resolved id — the value the real interceptor sends as `X-Tenant-Id`.
    const afterMemberships = calls.slice(
      calls.findIndex((call) => call.url === "/tenants") + 1,
    );
    expect(afterMemberships.length).toBeGreaterThan(0);
    expect(afterMemberships[0].actingTenantId).toBe(TENANT_MINE);
    for (const call of afterMemberships) {
      expect(call.actingTenantId).toBe(TENANT_MINE);
    }
    expect(urls()).toContain("/permissions/me");
  });

  it("shows the no-access panel to an anonymous non-member, with no navigation", async () => {
    installClient({ memberships: [OTHER], brandingExists: true });

    renderBrandedEntry();

    await signIn();

    expect(
      await screen.findByText("Você não tem acesso a este condomínio"),
    ).toBeInTheDocument();
    await waitFor(() => {
      expect(getActingTenantId()).toBe(TENANT_OTHER);
    });

    // Never a 404, and never a redirect: the only path the router ever held.
    expect(new Set(locations)).toEqual(new Set([`/c/${SLUG}`]));
    expect(screen.queryByText(/404/)).toBeNull();
    expect(
      screen.queryByText("Bem-vindo ao painel central do seu condomínio."),
    ).toBeNull();
  });

  it("renders an unknown slug and a non-member condominium identically after login", async () => {
    /**
     * Result 5, as this task can honestly test it: **structural
     * indistinguishability after authentication**. Not a timing claim — there
     * is no wall-clock assertion anywhere in this file, and none would mean
     * anything in jsdom.
     *
     * The slug string is held **identical** across the two branches and only
     * the server's answer to the branding read varies (200 vs 404), which is
     * what makes the URL-list equality an assertion about the post-login
     * surface rather than an artifact of two different paths. Before login the
     * two branches are plainly distinguishable by design — a known slug
     * renders branded, an unknown one falls back unbranded — and that oracle
     * was accepted knowingly under APRAS-74's D3. What is asserted here is
     * that the post-authentication no-access panel adds no *second* oracle.
     */
    const runToSettledPanel = async (brandingExists: boolean) => {
      localStorage.clear();
      sessionStorage.clear();
      clearActingTenantId();
      calls = [];
      locations = [];
      installClient({ memberships: [OTHER], brandingExists });

      const { container } = renderBrandedEntry();
      await signIn();

      // Settled: the panel is up *and* the login continuation has finished —
      // the membership list arrived and the acting tenant was resolved from
      // it. Measured here, never before.
      await screen.findByText("Você não tem acesso a este condomínio");
      await waitFor(() => {
        expect(getActingTenantId()).toBe(TENANT_OTHER);
      });
      await waitFor(() => {
        expect(urls()).toContain("/tenants");
      });

      const settled = { html: container.innerHTML, urls: urls() };
      cleanup();
      return settled;
    };

    const nonMember = await runToSettledPanel(true);
    const unknownSlug = await runToSettledPanel(false);

    expect(unknownSlug.html).toBe(nonMember.html);
    expect(unknownSlug.urls).toEqual(nonMember.urls);
  });
});
