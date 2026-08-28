import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { Search, LogIn, Users, Building2, History, Package as PackageIcon } from "lucide-react";
import { Button } from "../../../components/ui/button";
import { useLots } from "../../lot-management/hooks/useLots";
import {
  useAccessLogs,
  useCheckIn,
  useCheckOut,
  useVisitors,
} from "../hooks/useVisitors";
import {
  useCreatePackage,
  useMarkPackagePickedUp,
  usePackageQueue,
} from "../hooks/usePackages";
import { GatekeeperEntryModal } from "./GatekeeperEntryModal";
import { AccessLogTimeline } from "./AccessLogTimeline";
import type { AccessLog, Visitor } from "../../../types/visitor";

export const GatekeeperDashboard: React.FC = () => {
  const { t } = useTranslation();
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedLotId, setSelectedLotId] = useState("");
  const [selectedVisitor, setSelectedVisitor] = useState<Visitor | null>(null);
  const [isEntryModalOpen, setIsEntryModalOpen] = useState(false);

  const [packageDescription, setPackageDescription] = useState("");
  const [packageCarrier, setPackageCarrier] = useState("");
  const [pickupNotes, setPickupNotes] = useState<Record<string, string>>({});

  const { data: visitorsData } = useVisitors(searchTerm);
  const { data: logsData } = useAccessLogs();
  const { data: lotsData } = useLots();
  const { data: packageQueueData } = usePackageQueue();

  const checkInMutation = useCheckIn();
  const checkOutMutation = useCheckOut();
  const createPackageMutation = useCreatePackage();
  const markPickedUpMutation = useMarkPackagePickedUp();

  const logs = logsData?.items || [];
  const activeLogs = logs.filter((l) => !l.exit_time);
  const lots = lotsData?.items || [];
  const packageQueue = packageQueueData?.items || [];

  const handleSelectVisitorForCheckIn = (visitor: Visitor) => {
    setSelectedVisitor(visitor);
    setIsEntryModalOpen(true);
  };

  const handleConfirmCheckIn = async (entryNotes: string) => {
    if (selectedVisitor && selectedLotId) {
      await checkInMutation.mutateAsync({
        visitor_id: selectedVisitor.id,
        lot_id: selectedLotId,
        entry_notes: entryNotes || undefined,
      });
      setSelectedVisitor(null);
      setIsEntryModalOpen(false);
    }
  };

  const handleCheckOut = async (log: AccessLog) => {
    await checkOutMutation.mutateAsync({
      access_log_id: log.id,
    });
  };

  const handleLogPackageArrival = async () => {
    if (!selectedLotId) return;
    await createPackageMutation.mutateAsync({
      lot_id: selectedLotId,
      description: packageDescription || undefined,
      carrier: packageCarrier || undefined,
    });
    setPackageDescription("");
    setPackageCarrier("");
  };

  const handleConfirmPickup = async (packageId: string) => {
    await markPickedUpMutation.mutateAsync({
      id: packageId,
      data: { picked_up_by_notes: pickupNotes[packageId] || undefined },
    });
    setPickupNotes((prev) => ({ ...prev, [packageId]: "" }));
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

      {/* Encomendas Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Log Arrival Form */}
        <div className="lg:col-span-1 space-y-4">
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900 space-y-4">
            <h2 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <PackageIcon className="size-4 text-indigo-600" />
              {t("packages.title", "Encomendas")}
            </h2>

            <div>
              <input
                type="text"
                value={packageDescription}
                onChange={(e) => setPackageDescription(e.target.value)}
                placeholder={t("packages.description", "Descrição")}
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm bg-white dark:border-slate-700 dark:bg-slate-800 text-slate-900 dark:text-white"
              />
            </div>

            <div>
              <input
                type="text"
                value={packageCarrier}
                onChange={(e) => setPackageCarrier(e.target.value)}
                placeholder={t("packages.carrier", "Transportadora")}
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm bg-white dark:border-slate-700 dark:bg-slate-800 text-slate-900 dark:text-white"
              />
            </div>

            <Button
              disabled={!selectedLotId || createPackageMutation.isPending}
              onClick={handleLogPackageArrival}
              className="w-full gap-1 bg-indigo-600 hover:bg-indigo-700 text-white"
            >
              <PackageIcon className="size-3.5" />
              {t("packages.logArrival", "Registrar Encomenda")}
            </Button>
          </div>
        </div>

        {/* Right Column: Awaiting Pickup Queue */}
        <div className="lg:col-span-2 space-y-4">
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
            <h2 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2 mb-4">
              <PackageIcon className="size-5 text-indigo-600 dark:text-indigo-400" />
              {t("packages.awaitingPickup", "Encomendas Aguardando Retirada")}
            </h2>

            {packageQueue.length === 0 ? (
              <p className="text-sm text-slate-500 dark:text-slate-400">
                {t("packages.noPackages", "Nenhuma encomenda aguardando retirada.")}
              </p>
            ) : (
              <div className="space-y-3 max-h-96 overflow-y-auto">
                {packageQueue.map((pkg) => (
                  <div
                    key={pkg.id}
                    className="flex flex-col gap-2 rounded-xl border border-slate-100 p-3 dark:border-slate-800/80"
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="font-semibold text-slate-900 dark:text-white text-sm">
                          {pkg.lot_summary
                            ? `${t("lots.block")} ${pkg.lot_summary.block}, ${t("lots.lotNumber")} ${pkg.lot_summary.lot_number}`
                            : ""}
                        </div>
                        <div className="text-xs text-slate-500 dark:text-slate-400 flex gap-2">
                          {pkg.description && <span>{pkg.description}</span>}
                          {pkg.carrier && <span>{pkg.carrier}</span>}
                        </div>
                        <div className="text-xs text-slate-400 dark:text-slate-500">
                          {new Date(pkg.received_at).toLocaleString()}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <input
                        type="text"
                        value={pickupNotes[pkg.id] || ""}
                        onChange={(e) =>
                          setPickupNotes((prev) => ({ ...prev, [pkg.id]: e.target.value }))
                        }
                        placeholder={t("packages.pickedUpBy", "Retirado por: ___")}
                        className="flex-1 rounded-md border border-slate-300 px-3 py-1.5 text-xs bg-white dark:border-slate-700 dark:bg-slate-800 text-slate-900 dark:text-white"
                      />
                      <Button
                        size="sm"
                        disabled={markPickedUpMutation.isPending}
                        onClick={() => handleConfirmPickup(pkg.id)}
                        className="gap-1 bg-emerald-600 hover:bg-emerald-700 text-white"
                      >
                        {t("packages.confirmPickup", "Confirmar Retirada")}
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Entry Modal */}
      <GatekeeperEntryModal
        isOpen={isEntryModalOpen}
        onClose={() => setIsEntryModalOpen(false)}
        visitor={selectedVisitor}
        lotId={selectedLotId}
        onConfirmCheckIn={handleConfirmCheckIn}
        isLoading={checkInMutation.isPending}
      />
    </div>
  );
};
