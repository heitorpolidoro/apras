import React from "react";
import { Link, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth, UserRole } from "../context/AuthContext";
import { useTenant } from "../context/useTenant";
import { useCanShowMenu } from "../access/useCanAccess";
import { NAV_ITEMS, type NavItem } from "../access/routeAccess";
import { cn } from "../../../lib/utils";
import SimulationControls from "./SimulationControls";

const LANGUAGES = [
  { code: "pt", label: "PT" },
  { code: "en", label: "EN" },
];

/**
 * One navigation link, gated by `useCanShowMenu` — the **display** hook, so
 * "view-as" keeps previewing the simulated user's menu (APRAS-48 §2.7).
 *
 * It is a component rather than a loop body so the hook is called once per
 * item at a fixed position, which is what the rules of hooks require.
 */
const NavItemLink: React.FC<{ item: NavItem }> = ({ item }) => {
  const { allowed } = useCanShowMenu(item.access);
  const location = useLocation();
  const { t } = useTranslation();

  if (!allowed) return null;

  return (
    <Link
      to={item.path}
      className={cn(
        "text-sm font-semibold transition-all hover:text-primary relative py-1",
        location.pathname === item.path
          ? "text-primary after:absolute after:bottom-0 after:left-0 after:w-full after:h-0.5 after:bg-primary after:rounded-t-md"
          : "text-muted-foreground",
      )}
    >
      {t(item.labelKey)}
    </Link>
  );
};

const Navbar: React.FC = () => {
  const { user, logout, isAuthenticated } = useAuth();
  const { tenants, actingTenantId, setActingTenant } = useTenant();
  const { t, i18n } = useTranslation();
  const currentLang = i18n.resolvedLanguage ?? i18n.language;

  if (!isAuthenticated) return null;

  return (
    <nav className="flex items-center justify-between px-8 py-4 border-b border-border/40 bg-background/80 backdrop-blur-md sticky top-0 z-40 shadow-sm">
      <Link
        to="/"
        className="text-xl font-black text-primary tracking-tight flex items-center gap-2 hover:opacity-80 transition-opacity"
      >
        <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center">
          <div className="w-4 h-4 rounded-full bg-primary" />
        </div>
        {t("common.appName")}
      </Link>

      <div className="flex items-center gap-8">
        {NAV_ITEMS.map((item) => (
          <NavItemLink key={item.path} item={item} />
        ))}
      </div>

      <div className="flex items-center gap-5">
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
        {user?.role === UserRole.ADMINISTRATOR && <SimulationControls />}
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
          {user?.user_types && user.user_types.length > 0 && (
            <span className="text-xs text-primary/80 font-medium leading-tight">
              {user.user_types.map((ut) => ut.name).join(", ")}
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
    </nav>
  );
};

export default Navbar;
