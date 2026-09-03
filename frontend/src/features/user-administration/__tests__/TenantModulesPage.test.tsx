import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type React from "react";
import apiClient from "../../../api/client";
import pt from "../../../i18n/locales/pt.json";
import TenantModulesPage from "../pages/TenantModulesPage";

/** The suite's `t` resolves against `pt.json` (`src/test/setup.ts`), so the
 *  assertions below name the key and read the same string the component
 *  renders — no literal is duplicated and a copy change cannot rot them. */
const t = (key: string): string =>
  key
    .split(".")
    .reduce<unknown>(
      (node, part) => (node as Record<string, unknown>)?.[part],
      pt,
    ) as string;

/**
 * The superuser screen (APRAS-39 §10.3): a condominium `<select>` plus a
 * checkbox list of the 27 modules grouped by the companion clusters, with
 * the four core ones rendered checked-and-disabled. Optimistic updates are
 * deliberately not used — the `PUT` response body *is* the new state.
 */

vi.mock("../../../api/client", () => ({
  default: { get: vi.fn(), post: vi.fn(), put: vi.fn(), patch: vi.fn() },
}));

const mockedGet = vi.mocked(apiClient.get);
const mockedPut = vi.mocked(apiClient.put);

const MODULES = [
  "access_control",
  "announcements",
  "assemblies",
  "assets",
  "authorizations",
  "billing",
  "categories",
  "documents",
  "feedback",
  "finance",
  "gate",
  "inventory",
  "lots",
  "occurrences",
  "packages",
  "projects",
  "purchases",
  "reservations",
  "residents",
  "roles",
  "spaces",
  "tasks",
  "tenants",
  "uploads",
  "users",
  "visitors",
  "votes",
];

const CORE = ["tenants", "users", "roles", "billing"];

const TENANTS = [
  { id: "t-1", name: "Condomínio A", is_active: true },
  { id: "t-2", name: "Condomínio B", is_active: true },
];

const modulesBody = (tenantId: string, disabled: string[] = []) => ({
  tenant_id: tenantId,
  modules: MODULES.map((module) => ({
    module,
    is_core: CORE.includes(module),
    is_active: !disabled.includes(module),
  })),
});

const renderPage = () => {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const Wrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
  return render(<TenantModulesPage />, { wrapper: Wrapper });
};

beforeEach(() => {
  vi.clearAllMocks();
  mockedGet.mockReset();
  mockedPut.mockReset();
  mockedGet.mockImplementation(((url: string) => {
    if (url === "/tenants") return Promise.resolve({ data: TENANTS });
    if (url === "/tenants/t-1/modules") {
      return Promise.resolve({ data: modulesBody("t-1") });
    }
    if (url === "/tenants/t-2/modules") {
      return Promise.resolve({ data: modulesBody("t-2", ["assets"]) });
    }
    return Promise.resolve({ data: [] });
  }) as never);
});

describe("TenantModulesPage", () => {
  it("renders all 27 modules, with the core ones checked and disabled", async () => {
    renderPage();

    await waitFor(() =>
      expect(screen.getByLabelText(t("modules.names.finance"))).toBeInTheDocument(),
    );

    for (const module of MODULES) {
      const box = screen.getByLabelText(t(`modules.names.${module}`));
      expect(box).toBeInTheDocument();
      expect(box).toBeChecked();
      expect((box as HTMLInputElement).disabled).toBe(CORE.includes(module));
    }
    // Grouped by the companion clusters of §2.3, which is presentation and
    // not machinery: turning one companion off without the other is legal.
    expect(screen.getByText(t("modules.groups.finance"))).toBeInTheDocument();
    expect(screen.getByText(t("modules.groups.access"))).toBeInTheDocument();
  });

  it("PUTs the derived disabled_modules when a module is unchecked and saved", async () => {
    mockedPut.mockResolvedValue({ data: modulesBody("t-1", ["finance"]) } as never);
    const user = userEvent.setup();
    renderPage();

    await waitFor(() =>
      expect(screen.getByLabelText(t("modules.names.finance"))).toBeInTheDocument(),
    );
    await user.click(screen.getByLabelText(t("modules.names.finance")));
    await user.click(screen.getByRole("button", { name: t("modules.save") }));

    await waitFor(() =>
      expect(mockedPut).toHaveBeenCalledWith("/tenants/t-1/modules", {
        disabled_modules: ["finance"],
      }),
    );
    expect(await screen.findByText(t("modules.saved"))).toBeInTheDocument();
  });

  it("shows an error state when the save is refused", async () => {
    mockedPut.mockRejectedValue(new Error("400") as never);
    const user = userEvent.setup();
    renderPage();

    await waitFor(() =>
      expect(screen.getByLabelText(t("modules.names.finance"))).toBeInTheDocument(),
    );
    await user.click(screen.getByLabelText(t("modules.names.finance")));
    await user.click(screen.getByRole("button", { name: t("modules.save") }));

    expect(await screen.findByText(t("modules.saveError"))).toBeInTheDocument();
  });

  it("refetches when the condominium select changes", async () => {
    const user = userEvent.setup();
    renderPage();

    await waitFor(() =>
      expect(screen.getByLabelText(t("modules.names.assets"))).toBeChecked(),
    );

    await user.selectOptions(screen.getByLabelText(t("modules.tenantLabel")), "t-2");

    await waitFor(() =>
      expect(screen.getByLabelText(t("modules.names.assets"))).not.toBeChecked(),
    );
    expect(mockedGet).toHaveBeenCalledWith("/tenants/t-2/modules");
  });

  it("renders a module the clusters do not name, instead of hiding it", async () => {
    // The backend derives `MODULES` from the catalogue so "a module a future
    // task adds is toggleable the day its first permission exists". The §2.3
    // clusters are presentation and are hand-written, so a 27th module would
    // otherwise be invisible to the operator with no test turning red. It
    // falls into a trailing "other" group and stays fully operable.
    const withExtra = {
      tenant_id: "t-1",
      modules: [
        ...modulesBody("t-1").modules,
        { module: "telemetry", is_core: false, is_active: true },
      ],
    };
    mockedGet.mockImplementation(((url: string) => {
      if (url === "/tenants") return Promise.resolve({ data: TENANTS });
      return Promise.resolve({ data: withExtra });
    }) as never);
    mockedPut.mockResolvedValue({ data: withExtra } as never);
    const user = userEvent.setup();
    renderPage();

    const box = await screen.findByLabelText("modules.names.telemetry");
    expect(box).toBeInTheDocument();
    expect(box).toBeChecked();
    expect(screen.getByText(t("modules.groups.other"))).toBeInTheDocument();

    await user.click(box);
    await user.click(screen.getByRole("button", { name: t("modules.save") }));

    await waitFor(() =>
      expect(mockedPut).toHaveBeenCalledWith("/tenants/t-1/modules", {
        disabled_modules: ["telemetry"],
      }),
    );
  });

  it("does not send a core module even if the row claims it is inactive", async () => {
    // Defence in depth against a hand-edited row: the checkbox is disabled,
    // and the derived payload is computed from the toggleable set only.
    mockedGet.mockImplementation(((url: string) => {
      if (url === "/tenants") return Promise.resolve({ data: TENANTS });
      return Promise.resolve({ data: modulesBody("t-1", ["users"]) });
    }) as never);
    mockedPut.mockResolvedValue({ data: modulesBody("t-1") } as never);
    const user = userEvent.setup();
    renderPage();

    await waitFor(() =>
      expect(screen.getByLabelText(t("modules.names.users"))).toBeInTheDocument(),
    );
    await user.click(screen.getByRole("button", { name: t("modules.save") }));

    await waitFor(() =>
      expect(mockedPut).toHaveBeenCalledWith("/tenants/t-1/modules", {
        disabled_modules: [],
      }),
    );
  });
});
