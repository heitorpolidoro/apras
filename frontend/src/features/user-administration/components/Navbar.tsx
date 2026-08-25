import React from "react";
import { Link, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth, UserRole } from "../context/AuthContext";
import { useEffectiveIdentity } from "../context/useEffectiveIdentity";
import { cn } from "../../../lib/utils";
import SimulationControls from "./SimulationControls";

const LANGUAGES = [
  { code: "pt", label: "PT" },
  { code: "en", label: "EN" },
];

const Navbar: React.FC = () => {
  const { user, logout, isAuthenticated } = useAuth();
  const { role: effectiveRole } = useEffectiveIdentity();
  const location = useLocation();
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
        <Link
          to="/dashboard"
          className={cn(
            "text-sm font-semibold transition-all hover:text-primary relative py-1",
            location.pathname === "/dashboard"
              ? "text-primary after:absolute after:bottom-0 after:left-0 after:w-full after:h-0.5 after:bg-primary after:rounded-t-md"
              : "text-muted-foreground",
          )}
        >
          {t("nav.tasks")}
        </Link>

        <Link
          to="/categories"
          className={cn(
            "text-sm font-semibold transition-all hover:text-primary relative py-1",
            location.pathname === "/categories"
              ? "text-primary after:absolute after:bottom-0 after:left-0 after:w-full after:h-0.5 after:bg-primary after:rounded-t-md"
              : "text-muted-foreground",
          )}
        >
          {t("nav.categories")}
        </Link>

        {effectiveRole !== UserRole.GUEST && (
          <Link
            to="/lots"
            className={cn(
              "text-sm font-semibold transition-all hover:text-primary relative py-1",
              location.pathname === "/lots"
                ? "text-primary after:absolute after:bottom-0 after:left-0 after:w-full after:h-0.5 after:bg-primary after:rounded-t-md"
                : "text-muted-foreground",
            )}
          >
            {t("nav.lots")}
          </Link>
        )}

        {effectiveRole !== UserRole.GUEST && (
          <Link
            to="/authorizations"
            className={cn(
              "text-sm font-semibold transition-all hover:text-primary relative py-1",
              location.pathname === "/authorizations"
                ? "text-primary after:absolute after:bottom-0 after:left-0 after:w-full after:h-0.5 after:bg-primary after:rounded-t-md"
                : "text-muted-foreground",
            )}
          >
            {t("nav.authorizations")}
          </Link>
        )}

        {(effectiveRole === UserRole.ADMINISTRATOR ||
          effectiveRole === UserRole.DIRECTOR ||
          effectiveRole === UserRole.MANAGER) && (
          <Link
            to="/gate"
            className={cn(
              "text-sm font-semibold transition-all hover:text-primary relative py-1",
              location.pathname === "/gate"
                ? "text-primary after:absolute after:bottom-0 after:left-0 after:w-full after:h-0.5 after:bg-primary after:rounded-t-md"
                : "text-muted-foreground",
            )}
          >
            {t("nav.gate")}
          </Link>
        )}

        <Link
          to="/occurrences"
          className={cn(
            "text-sm font-semibold transition-all hover:text-primary relative py-1",
            location.pathname === "/occurrences"
              ? "text-primary after:absolute after:bottom-0 after:left-0 after:w-full after:h-0.5 after:bg-primary after:rounded-t-md"
              : "text-muted-foreground",
          )}
        >
          {t("nav.occurrences", "Ocorrências")}
        </Link>

        <Link
          to="/documents"
          className={cn(
            "text-sm font-semibold transition-all hover:text-primary relative py-1",
            location.pathname === "/documents"
              ? "text-primary after:absolute after:bottom-0 after:left-0 after:w-full after:h-0.5 after:bg-primary after:rounded-t-md"
              : "text-muted-foreground",
          )}
        >
          {t("nav.documents", "Documentos")}
        </Link>

        {effectiveRole === UserRole.ADMINISTRATOR && (
          <Link
            to="/admin/users"
            className={cn(
              "text-sm font-semibold transition-all hover:text-primary relative py-1",
              location.pathname === "/admin/users"
                ? "text-primary after:absolute after:bottom-0 after:left-0 after:w-full after:h-0.5 after:bg-primary after:rounded-t-md"
                : "text-muted-foreground",
            )}
          >
            {t("nav.administration")}
          </Link>
        )}

      </div>

      <div className="flex items-center gap-5">
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
