import React from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "../context/AuthContext";
import { usePermissionSet } from "../access/useCanAccess";
import { useTenant } from "../context/useTenant";
import { useSidebar } from "../context/useSidebar";
import { useSimulation } from "../context/SimulationContext";
import { useRoles } from "../../../hooks/useRoles";
import { cn } from "../../../lib/utils";
import SimulationControls from "./SimulationControls";
import Sidebar from "./Sidebar";
import { Menu } from "lucide-react";

const LANGUAGES = [
  { code: "pt", label: "PT" },
  { code: "en", label: "EN" },
];

const cleanRoleName = (name: string): string =>
  name.replace(/\s*\(papel\)$/i, "").trim();

const Navbar: React.FC = () => {
  const { user, logout, isAuthenticated } = useAuth();
  const canSimulate = usePermissionSet().has("roles:update");
  const { tenants, actingTenantId, setActingTenant } = useTenant();
  const { isCollapsed, toggleMobile } = useSidebar();
  const { isSimulating, simulatedRoleIds } = useSimulation();
  const { data: roles } = useRoles();
  const { t, i18n } = useTranslation();
  const currentLang = i18n.resolvedLanguage ?? i18n.language;

  if (!isAuthenticated) return null;

  const simulatedRoleNames = (roles ?? [])
    .filter((role) => simulatedRoleIds.includes(role.id))
    .map((role) => cleanRoleName(role.name))
    .join(", ");

  let roleSubtitle: string | null = null;
  if (isSimulating) {
    roleSubtitle = t("simulation.simulatingAs", {
      roles: simulatedRoleNames || t("simulation.noRoles"),
    });
  } else if (user?.is_superuser) {
    const localRoles = (user.roles ?? [])
      .map((ut) => cleanRoleName(ut.name))
      .filter(
        (name) =>
          name.toLowerCase() !== "administrador" &&
          name.toLowerCase() !== "administrator",
      );
    if (localRoles.length > 0) {
      roleSubtitle = `${t("common.globalAdmin")} (${localRoles.join(", ")})`;
    } else {
      roleSubtitle = t("common.globalAdmin");
    }
  } else if (user?.roles && user.roles.length > 0) {
    roleSubtitle = user.roles.map((ut) => cleanRoleName(ut.name)).join(", ");
  }

  return (
    <>
      <Sidebar />
      <header
        className={cn(
          "sticky top-0 z-20 flex items-center justify-between px-4 sm:px-6 py-3 border-b border-border/40 bg-background/80 backdrop-blur-md shadow-sm transition-all duration-300 ease-in-out",
          isCollapsed ? "md:ml-20" : "md:ml-64",
        )}
      >
        <div className="flex items-center gap-3">
          {/* Mobile hamburger menu toggle */}
          <button
            type="button"
            onClick={toggleMobile}
            aria-label={t("nav.openMenu")}
            title={t("nav.openMenu")}
            className="md:hidden p-2 rounded-md text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
          >
            <Menu className="size-5" />
          </button>

          {/* Logo on mobile */}
          <Link
            to="/"
            aria-label={t("common.appName")}
            className="md:hidden flex items-center gap-2 hover:opacity-80 transition-opacity"
          >
            <div className="size-7 rounded-lg bg-primary/10 flex items-center justify-center">
              <div className="size-3.5 rounded-full bg-primary" />
            </div>
          </Link>
        </div>

        <div className="flex items-center gap-3 sm:gap-5">
          {/* The switcher renders only when there is something to switch
              between. With exactly one option that tenant is already the
              pre-selection, and with zero options the Navbar renders nothing at
              all — no placeholder, no message — because the zero-option state is
              also the state of every bare Navbar/ProtectedRoute test and of the
              routing smoke test, where any new text would be a regression.
              A native <select>, not Radix, for a stable combobox surface in
              jsdom. */}
          {tenants.length >= 2 && (
            <select
              aria-label={t("tenant.switcherLabel")}
              value={actingTenantId ?? ""}
              onChange={(event) => {
                setActingTenant(event.target.value);
              }}
              className="text-sm font-semibold bg-background border border-border/50 rounded-md px-2 py-1.5 text-foreground"
            >
              {tenants.map((tenant) => (
                <option key={tenant.id} value={tenant.id}>
                  {tenant.name}
                </option>
              ))}
            </select>
          )}
          {/* TRANSITIONAL (IAM F4 -> F5): "view-as" is an operator tool, not an
              authorization gate, and F3 exposes no `is_superuser` on
              `/auth/me` to replace this comparison with. */}
          {/* IAM F5 (APRAS-49 §10.2): `roles:update` is the legacy {A} set
              exactly. It reads the REAL set (`usePermissionSet`), never the
              effective one, so the control that ends a simulation can never
              be hidden by the simulation. */}
          {canSimulate && <SimulationControls />}
          <div className="flex items-center gap-1 border border-border/50 rounded-md overflow-hidden">
            {LANGUAGES.map((lang) => (
              <button
                key={lang.code}
                onClick={() => i18n.changeLanguage(lang.code)}
                className={cn(
                  "px-2.5 py-1 text-xs font-semibold transition-all",
                  currentLang.startsWith(lang.code)
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:text-foreground",
                )}
              >
                {lang.label}
              </button>
            ))}
          </div>
          <div className="hidden sm:flex flex-col items-end">
            <span className="text-sm font-semibold text-foreground leading-tight">
              {user?.full_name}
            </span>
            {roleSubtitle && (
              <span
                className={cn(
                  "text-xs font-medium leading-tight",
                  isSimulating
                    ? "text-amber-600 dark:text-amber-400 font-semibold"
                    : user?.is_superuser
                      ? "text-primary font-semibold"
                      : "text-muted-foreground",
                )}
              >
                {roleSubtitle}
              </span>
            )}
          </div>
          <div className="h-8 w-[1px] bg-border/50 hidden sm:block" />
          <button
            onClick={logout}
            className="text-sm font-semibold text-muted-foreground hover:text-destructive hover:bg-destructive/10 px-3 py-1.5 rounded-md transition-all"
          >
            {t("common.logout")}
          </button>
        </div>
      </header>
    </>
  );
};

export default Navbar;
