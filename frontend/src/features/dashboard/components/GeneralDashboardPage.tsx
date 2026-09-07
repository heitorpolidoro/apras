import React from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "../../user-administration/context/AuthContext";
import { useTenant } from "../../user-administration/context/useTenant";
import { useCanOpenPath } from "../../user-administration/access/useCanAccess";
import {
  CheckSquare,
  ShieldCheck,
  Package,
  BookOpen,
  CalendarDays,
  Megaphone,
  DollarSign,
  FileWarning,
  Building,
  type LucideIcon,
} from "lucide-react";

interface DashboardCardConfig {
  id: string;
  path: string;
  icon: LucideIcon;
  colorClass: string;
  iconBgClass: string;
}

const DASHBOARD_CARDS: DashboardCardConfig[] = [
  {
    id: "tasks",
    path: "/tasks",
    icon: CheckSquare,
    colorClass: "text-blue-500 dark:text-blue-400",
    iconBgClass: "bg-blue-500/10",
  },
  {
    id: "gate",
    path: "/gate",
    icon: ShieldCheck,
    colorClass: "text-emerald-500 dark:text-emerald-400",
    iconBgClass: "bg-emerald-500/10",
  },
  {
    id: "packages",
    path: "/packages",
    icon: Package,
    colorClass: "text-amber-500 dark:text-amber-400",
    iconBgClass: "bg-amber-500/10",
  },
  {
    id: "occurrences",
    path: "/occurrences",
    icon: BookOpen,
    colorClass: "text-indigo-500 dark:text-indigo-400",
    iconBgClass: "bg-indigo-500/10",
  },
  {
    id: "reservations",
    path: "/reservations",
    icon: CalendarDays,
    colorClass: "text-purple-500 dark:text-purple-400",
    iconBgClass: "bg-purple-500/10",
  },
  {
    id: "announcements",
    path: "/announcements",
    icon: Megaphone,
    colorClass: "text-orange-500 dark:text-orange-400",
    iconBgClass: "bg-orange-500/10",
  },
  {
    id: "finance",
    path: "/finance",
    icon: DollarSign,
    colorClass: "text-green-500 dark:text-green-400",
    iconBgClass: "bg-green-500/10",
  },
  {
    id: "infractions",
    path: "/infractions",
    icon: FileWarning,
    colorClass: "text-rose-500 dark:text-rose-400",
    iconBgClass: "bg-rose-500/10",
  },
];

export const GeneralDashboardPage: React.FC = () => {
  const { t } = useTranslation();
  const { user } = useAuth();
  const { actingTenant } = useTenant();
  const canOpen = useCanOpenPath();

  const accessibleCards = DASHBOARD_CARDS.filter((card) => canOpen(card.path));

  const userName = user?.full_name || user?.email || "";

  return (
    <div className="max-w-7xl mx-auto px-4 py-8 space-y-8">
      {/* Welcome Banner */}
      <section
        aria-label={t("dashboard.general.title")}
        className="rounded-2xl border border-border/60 bg-gradient-to-br from-card to-accent/20 p-6 sm:p-8 shadow-sm transition-all"
      >
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div className="space-y-1.5">
            <span className="sr-only">{t("dashboard.general.title")}</span>
            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-foreground">
              {t("dashboard.general.welcome", { name: userName })}
            </h1>
            <p className="text-sm sm:text-base text-muted-foreground">
              {t("dashboard.general.welcomeSubtitle")}
            </p>
            {(user?.is_superuser || (user?.roles && user.roles.length > 0)) && (
              <div className="flex flex-wrap gap-1.5 pt-1">
                {user?.is_superuser && (
                  <span className="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-semibold bg-amber-500/10 text-amber-700 dark:text-amber-400 border border-amber-500/20">
                    {t("common.globalAdmin")}
                  </span>
                )}
                {user?.roles &&
                  user.roles.map((role) => (
                    <span
                      key={role.id}
                      className="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium bg-primary/10 text-primary border border-primary/20"
                    >
                      {role.name.replace(/\s*\(papel\)$/i, "").trim()}
                    </span>
                  ))}
              </div>
            )}
          </div>

          {actingTenant && (
            <div className="inline-flex items-center gap-2.5 px-4 py-2 rounded-xl bg-background/80 border border-border/50 text-sm font-medium text-foreground shadow-xs shrink-0 self-start md:self-auto">
              <Building className="size-4.5 text-primary shrink-0" />
              <span className="font-semibold text-foreground">
                {actingTenant.name}
              </span>
            </div>
          )}
        </div>
      </section>

      {/* Module Shortcuts Grid */}
      <section aria-label={t("dashboard.general.quickAccess")} className="space-y-4">
        <h2 className="text-lg font-bold tracking-tight text-foreground">
          {t("dashboard.general.quickAccess")}
        </h2>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
          {accessibleCards.map((card) => {
            const Icon = card.icon;
            const title = t(`dashboard.general.modules.${card.id}.title`);
            const description = t(
              `dashboard.general.modules.${card.id}.description`,
            );

            return (
              <Link
                key={card.id}
                to={card.path}
                className="group relative flex flex-col justify-between p-5 rounded-xl border border-border/50 bg-card hover:bg-accent/40 hover:border-border hover:shadow-md transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
              >
                <div>
                  <div
                    className={`size-11 rounded-lg flex items-center justify-center mb-4 transition-transform group-hover:scale-105 ${card.iconBgClass} ${card.colorClass}`}
                  >
                    <Icon className="size-5.5" />
                  </div>
                  <h3 className="text-base font-semibold text-foreground group-hover:text-primary transition-colors">
                    {title}
                  </h3>
                  <p className="mt-1.5 text-xs sm:text-sm text-muted-foreground line-clamp-2">
                    {description}
                  </p>
                </div>

                <div className="mt-4 pt-3 border-t border-border/40 flex items-center justify-end text-xs font-medium text-primary opacity-0 group-hover:opacity-100 transition-opacity">
                  <span>{t("dashboard.general.access")} &rarr;</span>
                </div>
              </Link>
            );
          })}
        </div>
      </section>
    </div>
  );
};

export default GeneralDashboardPage;
