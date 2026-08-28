import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { X, CheckCircle, ShieldAlert, User, Building, Car, FileText } from "lucide-react";
import { Button } from "../../../components/ui/button";
import type { Visitor } from "../../../types/visitor";

interface GatekeeperEntryModalProps {
  isOpen: boolean;
  onClose: () => void;
  visitor: Visitor | null;
  lotId: string;
  authorizationId?: string | null;
  isValidAccess?: boolean;
  onConfirmCheckIn: (notes: string, authorizationId?: string | null) => Promise<void>;
  isLoading?: boolean;
}

export const GatekeeperEntryModal: React.FC<GatekeeperEntryModalProps> = ({
  isOpen,
  onClose,
  visitor,
  authorizationId,
  isValidAccess = true,
  onConfirmCheckIn,
  isLoading = false,
}) => {
  const { t } = useTranslation();
  const [entryNotes, setEntryNotes] = useState("");
  const [errorMsg, setErrorMsg] = useState("");

  if (!isOpen || !visitor) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg("");

    try {
      await onConfirmCheckIn(entryNotes, authorizationId);
      setEntryNotes("");
      onClose();
    } catch (err: any) {
      setErrorMsg(err?.response?.data?.detail || "Check-in failed");
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4 animate-in fade-in duration-200">
      <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-xl dark:border-slate-800 dark:bg-slate-900">
        <div className="flex items-center justify-between border-b border-slate-100 pb-4 dark:border-slate-800">
          <h3 className="text-lg font-bold text-slate-900 dark:text-white">
            {t("gatekeeper.confirmCheckIn")}
          </h3>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
          >
            <X className="size-5" />
          </button>
        </div>

        {/* Validation Status Banner */}
        <div
          className={`mt-4 flex items-center gap-3 rounded-xl p-3 text-sm font-medium ${
            isValidAccess
              ? "bg-emerald-50 text-emerald-800 dark:bg-emerald-950/50 dark:text-emerald-300"
              : "bg-red-50 text-red-800 dark:bg-red-950/50 dark:text-red-300"
          }`}
        >
          {isValidAccess ? (
            <CheckCircle className="size-5 text-emerald-600 dark:text-emerald-400 shrink-0" />
          ) : (
            <ShieldAlert className="size-5 text-red-600 dark:text-red-400 shrink-0" />
          )}
          <div>
            <div>{isValidAccess ? t("gatekeeper.validAccess") : t("gatekeeper.invalidAccess")}</div>
          </div>
        </div>

        {errorMsg && (
          <div className="mt-3 rounded-lg bg-red-50 p-3 text-xs text-red-700 dark:bg-red-950/50 dark:text-red-400">
            {errorMsg}
          </div>
        )}

        {/* Visitor Profile Details */}
        <div className="mt-4 space-y-3 rounded-xl bg-slate-50 p-4 text-sm dark:bg-slate-800/50">
          <div className="flex items-center gap-2 font-semibold text-slate-900 dark:text-white">
            <User className="size-4 text-slate-400" />
            {visitor.full_name}
          </div>
          {visitor.cpf && (
            <div className="text-xs text-slate-500 dark:text-slate-400 pl-6">
              CPF: {visitor.cpf}
            </div>
          )}
          {visitor.company_name && (
            <div className="flex items-center gap-2 text-slate-600 dark:text-slate-300 text-xs">
              <Building className="size-3.5 text-slate-400" />
              {visitor.company_name}
            </div>
          )}
          {visitor.vehicle_plate && (
            <div className="flex items-center gap-2 text-slate-600 dark:text-slate-300 text-xs">
              <Car className="size-3.5 text-slate-400" />
              {visitor.vehicle_plate} {visitor.vehicle_model ? `(${visitor.vehicle_model})` : ""}
            </div>
          )}
        </div>

        <form onSubmit={handleSubmit} className="mt-4 space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1">
              {t("gatekeeper.entryNotes")}
            </label>
            <div className="relative">
              <FileText className="absolute left-3 top-2.5 size-4 text-slate-400" />
              <input
                type="text"
                value={entryNotes}
                onChange={(e) => setEntryNotes(e.target.value)}
                placeholder="Ex: Entrega, Crachá #12, Mala de ferramentas..."
                className="w-full rounded-lg border border-slate-300 pl-9 pr-3 py-2 text-sm bg-white text-slate-900 dark:border-slate-700 dark:bg-slate-800 dark:text-white"
              />
            </div>
          </div>

          <div className="flex justify-end space-x-3 pt-2">
            <Button type="button" variant="outline" onClick={onClose} disabled={isLoading}>
              {t("authorizations.cancel")}
            </Button>
            <Button type="submit" disabled={isLoading || !isValidAccess} className="bg-emerald-600 hover:bg-emerald-700 text-white">
              {isLoading ? t("residents.saving") : t("gatekeeper.checkIn")}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};
