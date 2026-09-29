import React, { useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Spinner } from "../../../components/ui/spinner";
import { fetchPublicProjectsReport } from "../../../api/publicProjects";
import ObraPrintDialog from "./ObraPrintDialog";
import {
  listObrasFromReport,
  openObraPrintWindow,
} from "../lib/obraPrintDocument";

/**
 * `/c/<slug>/obras` — the condominium's obras report, to a visitor who is not
 * signed in (APRAS-92, D1/D2).
 *
 * The **backend** owns the document and this page owns the URL: they are
 * different deployments (`frontend/vercel.json` rewrites every path to
 * `index.html`, and the API is a separate function behind `VITE_API_URL`), so
 * the backend cannot serve a path on this origin. The fetched HTML is therefore
 * displayed in a full-viewport `iframe` with `srcDoc` and `sandbox=""` — the
 * same treatment `AssemblyMinutesView` gives server-rendered minutes, and the
 * reason it is sandboxed is that the document is a whole page with its own
 * `<style>`, which would otherwise leak into the app's own stylesheet.
 *
 * Beside it, the print control. It used to be a plain `<a target="_blank">` to
 * the API URL, which put the backend host in front of a resident; since
 * APRAS-118 it is a button opening `ObraPrintDialog`, and choosing an obra
 * opens a top-level blob document built from the HTML this page already holds
 * — no second request, no backend origin, one obra per sheet set. The iframe
 * and its `sandbox=""` are untouched: a sandboxed iframe cannot print itself,
 * which is why the printed document is top level and not this frame.
 *
 * A failed read — a 404 for an unknown *or* inactive condominium, or a
 * transport failure — renders a short "unavailable" panel. Never a blank
 * screen, and never a redirect to `/login`: the visitor has no account to sign
 * into and telling them to get one would be the wrong answer.
 *
 * The route sits outside `ProtectedRoute` and gets no `ROUTE_ACCESS`,
 * `NAV_ITEMS` or `NAV_GROUPS` entry, exactly like `/c/:slug`.
 */
const PublicObrasReportPage: React.FC = () => {
  const { slug = "" } = useParams<{ slug: string }>();
  const { t } = useTranslation();

  const [reportHtml, setReportHtml] = useState<string | null>(null);
  const [isPending, setIsPending] = useState(true);
  const [hasFailed, setHasFailed] = useState(false);
  // The slug the fetch below was issued for, so React 19's double-invoked
  // development effects do not issue it twice.
  const requestedSlug = useRef<string | null>(null);
  const [isPrintDialogOpen, setIsPrintDialogOpen] = useState(false);

  // Parsed from the HTML already in state: the report holds every obra as one
  // `div.page`, so the list costs no request.
  const obras = useMemo(
    () => (reportHtml === null ? [] : listObrasFromReport(reportHtml)),
    [reportHtml],
  );

  useEffect(() => {
    if (requestedSlug.current === slug) return;
    requestedSlug.current = slug;
    setIsPending(true);
    setHasFailed(false);
    void fetchPublicProjectsReport(slug)
      .then((html) => {
        setReportHtml(html);
      })
      .catch(() => {
        setReportHtml(null);
        setHasFailed(true);
      })
      .finally(() => {
        setIsPending(false);
      });
  }, [slug]);

  if (isPending) return <Spinner />;

  if (hasFailed || reportHtml === null) {
    return (
      <div className="flex flex-col items-center justify-center gap-2 min-h-[50vh] p-8 text-center">
        <p className="text-lg font-semibold text-foreground">
          {t("projects.publicReport.unavailable")}
        </p>
        <p className="text-sm text-muted-foreground max-w-md">
          {t("projects.publicReport.unavailableMessage")}
        </p>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col bg-muted/30">
      <div className="flex items-center justify-between gap-4 px-4 py-2">
        <h1 className="text-sm font-semibold text-foreground">
          {t("projects.publicReport.title")}
        </h1>
        <button
          type="button"
          onClick={() => setIsPrintDialogOpen(true)}
          className="rounded-md border border-border px-3 py-1.5 text-sm font-medium text-foreground hover:bg-muted/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          {t("projects.publicReport.openForPrinting")}
        </button>
      </div>
      <ObraPrintDialog
        open={isPrintDialogOpen}
        obras={obras}
        onClose={() => setIsPrintDialogOpen(false)}
        onSelect={(index) => {
          openObraPrintWindow(reportHtml, index);
        }}
      />
      <iframe
        title={t("projects.publicReport.title")}
        data-testid="public-obras-report-frame"
        sandbox=""
        srcDoc={reportHtml}
        className="flex-1 w-full min-h-[85vh] border-0 bg-card"
      />
    </div>
  );
};

export default PublicObrasReportPage;
