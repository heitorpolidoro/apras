import React, { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Search, LogIn, Users, Building2, History, ScanLine } from "lucide-react";
import { Button } from "../../../components/ui/button";
import { useLots } from "../../lot-management/hooks/useLots";
import {
  useAccessLogs,
  useAuthorization,
  useCheckIn,
  useCheckOut,
  useVisitors,
} from "../hooks/useVisitors";
import { GatekeeperEntryModal } from "./GatekeeperEntryModal";
import { QrScannerModal } from "./QrScannerModal";
import { AccessLogTimeline } from "./AccessLogTimeline";
import type { AccessLog, Visitor } from "../../../types/visitor";

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export const GatekeeperDashboard: React.FC = () => {
  const { t } = useTranslation();
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedLotId, setSelectedLotId] = useState("");
  const [selectedVisitor, setSelectedVisitor] = useState<Visitor | null>(null);
  const [isEntryModalOpen, setIsEntryModalOpen] = useState(false);
  const [isScannerOpen, setIsScannerOpen] = useState(false);
  const [scannedAuthorizationId, setScannedAuthorizationId] = useState<string | null>(null);
  const [scanError, setScanError] = useState<string | null>(null);

  const { data: visitorsData } = useVisitors(searchTerm);
  const { data: logsData } = useAccessLogs();
  const { data: lotsData } = useLots();

  const checkInMutation = useCheckIn();
  const checkOutMutation = useCheckOut();

  const { data: scannedAuth, isError: isScannedAuthError } = useAuthorization(
    scannedAuthorizationId ?? undefined
  );

  const logs = logsData?.items || [];
  const activeLogs = logs.filter((l) => !l.exit_time);
  const lots = lotsData?.items || [];

  // A scanned authorization is more specific/authoritative than whatever is
  // currently selected in the manual lot dropdown, so it always overwrites it.
  useEffect(() => {
    if (scannedAuth) {
      setSelectedLotId(scannedAuth.lot_id);
      setSelectedVisitor(scannedAuth.visitor ?? null);
      setIsEntryModalOpen(true);
    }
  }, [scannedAuth]);

  useEffect(() => {
    if (scannedAuthorizationId && isScannedAuthError) {
      setScanError(t("gatekeeper.scanNotFound"));
      setScannedAuthorizationId(null);
    }
  }, [isScannedAuthError, scannedAuthorizationId, t]);

  const handleSelectVisitorForCheckIn = (visitor: Visitor) => {
    setSelectedVisitor(visitor);
    setIsEntryModalOpen(true);
  };

  const handleScanSuccess = (decodedText: string) => {
    setIsScannerOpen(false);
    const trimmed = decodedText.trim();
    if (!UUID_PATTERN.test(trimmed)) {
      setScanError(t("gatekeeper.scanInvalidQr"));
      return;
    }
    setScanError(null);
    setScannedAuthorizationId(trimmed);
  };

  const handleCloseEntryModal = () => {
    setIsEntryModalOpen(false);
    setSelectedVisitor(null);
    setScannedAuthorizationId(null);
  };

  const handleConfirmCheckIn = async (entryNotes: string, authorizationId?: string | null) => {
    if (selectedVisitor && selectedLotId) {
      await checkInMutation.mutateAsync({
        visitor_id: selectedVisitor.id,
        lot_id: selectedLotId,
        entry_notes: entryNotes || undefined,
        authorization_id: authorizationId || undefined,
      });
    }
  };

  const handleCheckOut = async (log: AccessLog) => {
    await checkOutMutation.mutateAsync({
      access_log_id: log.id,
    });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white flex items-center gap-2">
            <Building2 className="size-7 text-indigo-600 dark:text-indigo-400" />
            {t("gatekeeper.title")}
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            {t("gatekeeper.subtitle")}
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button variant="outline" onClick={() => setIsScannerOpen(true)} className="gap-2">
            <ScanLine className="size-4" />
            {t("gatekeeper.scanQr")}
          </Button>

          {/* Active Visitors Counter */}
          <div className="flex items-center gap-3 rounded-2xl bg-indigo-50 px-4 py-3 border border-indigo-100 dark:bg-indigo-950/40 dark:border-indigo-900/50">
            <Users className="size-6 text-indigo-600 dark:text-indigo-400" />
            <div>
              <div className="text-2xl font-black text-indigo-700 dark:text-indigo-300 leading-none">
                {activeLogs.length}
              </div>
              <div className="text-xs font-semibold text-indigo-600/80 dark:text-indigo-400">
                {t("gatekeeper.activeVisitorsCount")}
              </div>
            </div>
          </div>
        </div>
      </div>

      {scanError && (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900/50 dark:bg-red-950/50 dark:text-red-400">
          {scanError}
        </div>
      )}

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Search & Terminal */}
        <div className="lg:col-span-1 space-y-4">
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900 space-y-4">
            <h2 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <Search className="size-4 text-indigo-600" />
              {t("gatekeeper.searchVisitor")}
            </h2>

            {/* Target Lot Selector */}
            <div>
              <label className="block text-xs font-semibold text-slate-500 dark:text-slate-400 mb-1">
                {t("authorizations.lotSelect")} *
              </label>
              <select
                value={selectedLotId}
                onChange={(e) => setSelectedLotId(e.target.value)}
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm bg-white dark:border-slate-700 dark:bg-slate-800 text-slate-900 dark:text-white"
              >
                <option value="">-- {t("authorizations.lotSelect")} --</option>
                {lots.map((lot) => (
                  <option key={lot.id} value={lot.id}>
                    {t("lots.block")} {lot.block}, {t("lots.lotNumber")} {lot.lot_number}
                  </option>
                ))}
              </select>
            </div>

            {/* Search Input */}
            <div className="relative">
              <Search className="absolute left-3 top-2.5 size-4 text-slate-400" />
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder={t("visitors.searchPlaceholder")}
                className="w-full rounded-md border border-slate-300 pl-9 pr-3 py-2 text-sm bg-white text-slate-900 dark:border-slate-700 dark:bg-slate-800 dark:text-white"
              />
            </div>

            {/* Search Results List */}
            <div className="max-h-80 overflow-y-auto divide-y divide-slate-100 dark:divide-slate-800/80">
              {visitorsData?.items.map((visitor) => (
                <div
                  key={visitor.id}
                  className="flex items-center justify-between p-3 hover:bg-slate-50 dark:hover:bg-slate-800/50 rounded-lg transition-colors"
                >
                  <div>
                    <div className="font-semibold text-slate-900 dark:text-white text-sm">
                      {visitor.full_name}
                    </div>
                    <div className="text-xs text-slate-500 dark:text-slate-400">
                      {visitor.company_name || visitor.vehicle_plate || visitor.cpf || "Sem dados adicionais"}
                    </div>
                  </div>

                  <Button
                    size="sm"
                    disabled={!selectedLotId || checkInMutation.isPending}
                    onClick={() => handleSelectVisitorForCheckIn(visitor)}
                    className="gap-1 bg-emerald-600 hover:bg-emerald-700 text-white"
                  >
                    <LogIn className="size-3.5" />
                    {t("gatekeeper.checkIn")}
                  </Button>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right Column: Timeline & On-Site Feed */}
        <div className="lg:col-span-2 space-y-4">
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
            <h2 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2 mb-4">
              <History className="size-5 text-indigo-600 dark:text-indigo-400" />
              {t("accessLogs.title")}
            </h2>

            <AccessLogTimeline
              logs={logs}
              onCheckOut={handleCheckOut}
              canCheckOut={true}
            />
          </div>
        </div>
      </div>

      {/* QR Scanner Modal */}
      <QrScannerModal
        isOpen={isScannerOpen}
        onClose={() => setIsScannerOpen(false)}
        onScanSuccess={handleScanSuccess}
      />

      {/* Entry Modal */}
      <GatekeeperEntryModal
        isOpen={isEntryModalOpen}
        onClose={handleCloseEntryModal}
        visitor={selectedVisitor}
        lotId={selectedLotId}
        authorizationId={scannedAuthorizationId}
        onConfirmCheckIn={handleConfirmCheckIn}
        isLoading={checkInMutation.isPending}
      />
    </div>
  );
};
