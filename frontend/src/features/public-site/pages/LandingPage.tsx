import { useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  ClipboardList,
  ShieldCheck,
  AlertCircle,
  HardHat,
  Wallet,
  FileText,
} from "lucide-react";

/**
 * Public landing page served at `/` for anonymous visitors.
 *
 * APRAS-75: anonymous visitors see this page; authenticated visitors
 * are served GeneralDashboardPage via the same route (branch in RootRedirect).
 * No redirect is issued; the CTA links to /login.
 */
const LandingPage: React.FC = () => {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState<
    "tasks" | "access" | "infractions" | "finance"
  >("tasks");

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-4 border-b border-border">
        <span className="text-xl font-bold tracking-tight">{t("landing.brand")}</span>
        <Link
          to="/login"
          className="text-sm font-medium text-primary hover:underline"
        >
          {t("landing.loginButton")}
        </Link>
      </header>

      {/* Hero */}
      <section className="flex flex-col items-center text-center px-6 py-16 md:py-24 gap-6">
        <span className="inline-block rounded-full bg-primary/10 text-primary text-xs font-semibold px-4 py-1">
          {t("landing.hero.badge")}
        </span>
        <h1 className="text-3xl md:text-5xl font-bold max-w-3xl leading-tight">
          {t("landing.hero.title")}
        </h1>
        <p className="text-muted-foreground max-w-2xl text-base md:text-lg">
          {t("landing.hero.subtitle")}
        </p>
        <div className="flex gap-4 flex-col sm:flex-row">
          <Link
            to="/login"
            className="inline-flex items-center justify-center rounded-md bg-primary text-primary-foreground px-6 py-3 text-sm font-semibold hover:opacity-90 transition-opacity"
          >
            {t("landing.hero.cta")}
          </Link>
          <a
            href="#landing-previews"
            className="inline-flex items-center justify-center rounded-md border border-border px-6 py-3 text-sm font-semibold hover:bg-accent transition-colors"
          >
            {t("landing.hero.secondaryCta")}
          </a>
        </div>
      </section>

      {/* Interactive UI Previews */}
      <section
        id="landing-previews"
        data-testid="landing-previews"
        className="px-6 py-12 md:py-16 bg-muted/30"
      >
        <div className="max-w-5xl mx-auto flex flex-col gap-8">
          <div className="text-center flex flex-col gap-3">
            <span className="inline-block rounded-full bg-primary/10 text-primary text-xs font-semibold px-4 py-1 self-center">
              {t("landing.previews.badge")}
            </span>
            <h2 className="text-2xl md:text-3xl font-bold">
              {t("landing.previews.title")}
            </h2>
            <p className="text-muted-foreground max-w-xl mx-auto">
              {t("landing.previews.subtitle")}
            </p>
          </div>

          {/* Tab navigation */}
          <div className="flex gap-2 overflow-x-auto pb-1" role="tablist">
            {(
              [
                { key: "tasks", label: t("landing.previews.tabTasks") },
                { key: "access", label: t("landing.previews.tabAccess") },
                { key: "infractions", label: t("landing.previews.tabInfractions") },
                { key: "finance", label: t("landing.previews.tabFinance") },
              ] as const
            ).map(({ key, label }) => (
              <button
                key={key}
                role="tab"
                aria-selected={activeTab === key}
                onClick={() => setActiveTab(key)}
                className={`whitespace-nowrap rounded-md px-4 py-2 text-sm font-medium transition-colors ${
                  activeTab === key
                    ? "bg-primary text-primary-foreground"
                    : "border border-border hover:bg-accent"
                }`}
              >
                {label}
              </button>
            ))}
          </div>

          {/* Preview panels */}
          <div className="rounded-xl border border-border bg-background p-6 shadow-sm">
            {activeTab === "tasks" && (
              <div className="flex flex-col gap-3">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-sm">
                    {t("landing.previews.tasks.cardTitle")}
                  </span>
                  <span className="rounded-full bg-[var(--status-in-progress-bg)] text-[var(--status-in-progress-fg)] text-xs px-2 py-0.5">
                    {t("landing.previews.tasks.status")}
                  </span>
                </div>
                <span className="rounded-full bg-[var(--priority-high-bg)] text-[var(--priority-high-fg)] text-xs px-2 py-0.5 self-start">
                  {t("landing.previews.tasks.priority")}
                </span>
                <p className="text-muted-foreground text-sm">
                  {t("landing.previews.tasks.dueDate")}
                </p>
                <p className="text-muted-foreground text-xs border-t border-border pt-2">
                  {t("landing.previews.tasks.audit")}
                </p>
              </div>
            )}
            {activeTab === "access" && (
              <div className="flex flex-col gap-3">
                <span className="font-semibold text-sm">
                  {t("landing.previews.access.cardTitle")}
                </span>
                <p className="text-sm">{t("landing.previews.access.visitor")}</p>
                <p className="text-muted-foreground text-sm">
                  {t("landing.previews.access.unit")}
                </p>
                <span className="rounded-full bg-[var(--status-completed-bg)] text-[var(--status-completed-fg)] text-xs px-2 py-0.5 self-start">
                  {t("landing.previews.access.status")}
                </span>
                <p className="text-muted-foreground text-xs">
                  {t("landing.previews.access.time")}
                </p>
              </div>
            )}
            {activeTab === "infractions" && (
              <div className="flex flex-col gap-3">
                <span className="font-semibold text-sm">
                  {t("landing.previews.infractions.cardTitle")}
                </span>
                <p className="text-muted-foreground text-sm">
                  {t("landing.previews.infractions.unit")}
                </p>
                <span className="rounded-full bg-[var(--status-pending-bg)] text-[var(--status-pending-fg)] text-xs px-2 py-0.5 self-start">
                  {t("landing.previews.infractions.status")}
                </span>
                <p className="text-muted-foreground text-sm">
                  {t("landing.previews.infractions.deadline")}
                </p>
                <p className="text-muted-foreground text-xs border-t border-border pt-2">
                  {t("landing.previews.infractions.evidence")}
                </p>
              </div>
            )}
            {activeTab === "finance" && (
              <div className="flex flex-col gap-3">
                <span className="font-semibold text-sm">
                  {t("landing.previews.finance.cardTitle")}
                </span>
                <p className="text-sm">{t("landing.previews.finance.progress")}</p>
                <p className="text-muted-foreground text-sm">
                  {t("landing.previews.finance.budget")}
                </p>
                <p className="text-muted-foreground text-xs border-t border-border pt-2">
                  {t("landing.previews.finance.milestone")}
                </p>
              </div>
            )}
          </div>
        </div>
      </section>

      {/* Capability blocks — exactly 6 <h2> inside this section */}
      <section
        data-testid="landing-capabilities"
        className="px-6 py-12 md:py-16"
      >
        <div className="max-w-5xl mx-auto grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {/* 1 */}
          <div className="flex flex-col gap-3 rounded-xl border border-border p-6">
            <ClipboardList className="h-6 w-6 text-primary" />
            <h2 className="font-semibold text-base">
              {t("landing.capabilities.tasks.title")}
            </h2>
            <p className="text-muted-foreground text-sm">
              {t("landing.capabilities.tasks.description")}
            </p>
          </div>
          {/* 2 */}
          <div className="flex flex-col gap-3 rounded-xl border border-border p-6">
            <ShieldCheck className="h-6 w-6 text-primary" />
            <h2 className="font-semibold text-base">
              {t("landing.capabilities.access.title")}
            </h2>
            <p className="text-muted-foreground text-sm">
              {t("landing.capabilities.access.description")}
            </p>
          </div>
          {/* 3 */}
          <div className="flex flex-col gap-3 rounded-xl border border-border p-6">
            <AlertCircle className="h-6 w-6 text-primary" />
            <h2 className="font-semibold text-base">
              {t("landing.capabilities.infractions.title")}
            </h2>
            <p className="text-muted-foreground text-sm">
              {t("landing.capabilities.infractions.description")}
            </p>
          </div>
          {/* 4 */}
          <div className="flex flex-col gap-3 rounded-xl border border-border p-6">
            <HardHat className="h-6 w-6 text-primary" />
            <h2 className="font-semibold text-base">
              {t("landing.capabilities.finance.title")}
            </h2>
            <p className="text-muted-foreground text-sm">
              {t("landing.capabilities.finance.description")}
            </p>
          </div>
          {/* 5 */}
          <div className="flex flex-col gap-3 rounded-xl border border-border p-6">
            <Wallet className="h-6 w-6 text-primary" />
            <h2 className="font-semibold text-base">
              {t("landing.capabilities.purchases.title")}
            </h2>
            <p className="text-muted-foreground text-sm">
              {t("landing.capabilities.purchases.description")}
            </p>
          </div>
          {/* 6 */}
          <div className="flex flex-col gap-3 rounded-xl border border-border p-6">
            <FileText className="h-6 w-6 text-primary" />
            <h2 className="font-semibold text-base">
              {t("landing.capabilities.documents.title")}
            </h2>
            <p className="text-muted-foreground text-sm">
              {t("landing.capabilities.documents.description")}
            </p>
          </div>
        </div>
      </section>

      {/* Repeat CTA band — h2 deliberately OUTSIDE landing-capabilities */}
      <section className="px-6 py-12 md:py-16 bg-muted/30 flex flex-col items-center gap-6 text-center">
        <h2 className="text-2xl md:text-3xl font-bold max-w-xl">
          {t("landing.ctaBand.title")}
        </h2>
        <Link
          to="/login"
          className="inline-flex items-center justify-center rounded-md bg-primary text-primary-foreground px-8 py-3 text-sm font-semibold hover:opacity-90 transition-opacity"
        >
          {t("landing.ctaBand.cta")}
        </Link>
      </section>

      {/* Footer */}
      <footer className="px-6 py-8 border-t border-border text-center text-muted-foreground text-sm">
        {t("landing.footer.text")}
      </footer>
    </div>
  );
};

export default LandingPage;
