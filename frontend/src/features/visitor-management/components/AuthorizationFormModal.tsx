import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { X, UserPlus, ShieldCheck } from "lucide-react";
import { Button } from "../../../components/ui/button";
import { useCreateVisitor, useVisitors } from "../hooks/useVisitors";
import type {
  AuthorizationType,
  DayOfWeek,
  ShiftType,
  VisitorAuthorizationCreate,
} from "../../../types/visitor";

interface AuthorizationFormModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: VisitorAuthorizationCreate) => Promise<void>;
  lotId: string;
  isLoading?: boolean;
}

const ALL_DAYS: DayOfWeek[] = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"];
const ALL_SHIFTS: ShiftType[] = ["MORNING", "AFTERNOON", "NIGHT", "FULL_DAY"];

export const AuthorizationFormModal: React.FC<AuthorizationFormModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
  isLoading = false,
}) => {
  const { t } = useTranslation();
  const { data: visitorsData } = useVisitors();
  const createVisitorMutation = useCreateVisitor();

  const [selectedVisitorId, setSelectedVisitorId] = useState<string>("");
  const [isCreatingVisitor, setIsCreatingVisitor] = useState(false);

  // New Visitor Form State
  const [fullName, setFullName] = useState("");
  const [cpf, setCpf] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [vehiclePlate, setVehiclePlate] = useState("");

  // Authorization Form State
  const [authType, setAuthType] = useState<AuthorizationType>("SINGLE");
  const [allowedDays, setAllowedDays] = useState<DayOfWeek[]>([...ALL_DAYS]);
  const [allowedShifts, setAllowedShifts] = useState<ShiftType[]>(["FULL_DAY"]);
  const [validFrom, setValidFrom] = useState("");
  const [validUntil, setValidUntil] = useState("");
  const [notes, setNotes] = useState("");
  const [errorMessage, setErrorMessage] = useState("");

  if (!isOpen) return null;

  const handleToggleDay = (day: DayOfWeek) => {
    setAllowedDays((prev) =>
      prev.includes(day) ? prev.filter((d) => d !== day) : [...prev, day]
    );
  };

  const handleToggleShift = (shift: ShiftType) => {
    setAllowedShifts((prev) =>
      prev.includes(shift) ? prev.filter((s) => s !== shift) : [...prev, shift]
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage("");

    let targetVisitorId = selectedVisitorId;

    if (isCreatingVisitor) {
      if (!fullName.trim()) {
        setErrorMessage(t("residents.validationNameRequired"));
        return;
      }
      try {
        const newVisitor = await createVisitorMutation.mutateAsync({
          full_name: fullName.trim(),
          cpf: cpf.trim() || undefined,
          company_name: companyName.trim() || undefined,
          vehicle_plate: vehiclePlate.trim() || undefined,
        });
        targetVisitorId = newVisitor.id;
      } catch (err: any) {
        setErrorMessage(err?.response?.data?.detail || "Error creating visitor profile");
        return;
      }
    }

    if (!targetVisitorId) {
      setErrorMessage(t("visitors.selectVisitor"));
      return;
    }

    try {
      await onSubmit({
        visitor_id: targetVisitorId,
        auth_type: authType,
        allowed_days: allowedDays,
        allowed_shifts: allowedShifts,
        valid_from: validFrom ? new Date(validFrom).toISOString() : null,
        valid_until: validUntil ? new Date(validUntil).toISOString() : null,
        notes: notes.trim() || null,
      });
      onClose();
    } catch (err: any) {
      setErrorMessage(err?.response?.data?.detail || "Error creating authorization");
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4 animate-in fade-in duration-200">
      <div className="w-full max-w-xl max-h-[90vh] overflow-y-auto rounded-2xl border border-slate-200 bg-white p-6 shadow-xl dark:border-slate-800 dark:bg-slate-900">
        <div className="flex items-center justify-between border-b border-slate-100 pb-4 dark:border-slate-800">
          <div className="flex items-center gap-2">
            <ShieldCheck className="size-5 text-indigo-600 dark:text-indigo-400" />
            <h2 className="text-lg font-bold text-slate-900 dark:text-white">
              {t("authorizations.newAuth")}
            </h2>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
          >
            <X className="size-5" />
          </button>
        </div>

        {errorMessage && (
          <div className="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700 dark:border-red-900/50 dark:bg-red-950/50 dark:text-red-400">
            {errorMessage}
          </div>
        )}

        <form onSubmit={handleSubmit} className="mt-4 space-y-4">
          {/* Visitor Selector / Creator Toggle */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm font-medium text-slate-700 dark:text-slate-300">
                {t("authorizations.visitorSelect")} *
              </label>
              <button
                type="button"
                onClick={() => setIsCreatingVisitor(!isCreatingVisitor)}
                className="text-xs font-semibold text-indigo-600 hover:underline dark:text-indigo-400 flex items-center gap-1"
              >
                <UserPlus className="size-3.5" />
                {isCreatingVisitor ? t("authorizations.visitorSelect") : t("visitors.newVisitor")}
              </button>
            </div>

            {isCreatingVisitor ? (
              <div className="space-y-3 rounded-xl border border-indigo-100 bg-indigo-50/50 p-4 dark:border-indigo-900/50 dark:bg-indigo-950/20">
                <div>
                  <input
                    type="text"
                    placeholder={t("visitors.fullName") + " *"}
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm bg-white dark:border-slate-700 dark:bg-slate-800 text-slate-900 dark:text-white"
                  />
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <input
                    type="text"
                    placeholder={t("visitors.cpf")}
                    value={cpf}
                    onChange={(e) => setCpf(e.target.value)}
                    className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm bg-white dark:border-slate-700 dark:bg-slate-800 text-slate-900 dark:text-white"
                  />
                  <input
                    type="text"
                    placeholder={t("visitors.companyName")}
                    value={companyName}
                    onChange={(e) => setCompanyName(e.target.value)}
                    className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm bg-white dark:border-slate-700 dark:bg-slate-800 text-slate-900 dark:text-white"
                  />
                </div>
                <div>
                  <input
                    type="text"
                    placeholder={t("visitors.vehiclePlate")}
                    value={vehiclePlate}
                    onChange={(e) => setVehiclePlate(e.target.value)}
                    className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm bg-white dark:border-slate-700 dark:bg-slate-800 text-slate-900 dark:text-white"
                  />
                </div>
              </div>
            ) : (
              <select
                value={selectedVisitorId}
                onChange={(e) => setSelectedVisitorId(e.target.value)}
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm bg-white dark:border-slate-700 dark:bg-slate-800 text-slate-900 dark:text-white"
              >
                <option value="">-- {t("visitors.selectVisitor")} --</option>
                {visitorsData?.items.map((v) => (
                  <option key={v.id} value={v.id}>
                    {v.full_name} {v.cpf ? `(${v.cpf})` : ""} {v.company_name ? `- ${v.company_name}` : ""}
                  </option>
                ))}
              </select>
            )}
          </div>

          {/* Authorization Type Toggle */}
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
              {t("authorizations.authType")}
            </label>
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => setAuthType("SINGLE")}
                className={`rounded-lg border p-3 text-center text-sm font-medium transition-all ${
                  authType === "SINGLE"
                    ? "border-indigo-600 bg-indigo-50 text-indigo-700 dark:border-indigo-500 dark:bg-indigo-950/50 dark:text-indigo-300"
                    : "border-slate-200 bg-white text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300"
                }`}
              >
                {t("authorizations.single")}
              </button>
              <button
                type="button"
                onClick={() => setAuthType("PERMANENT")}
                className={`rounded-lg border p-3 text-center text-sm font-medium transition-all ${
                  authType === "PERMANENT"
                    ? "border-indigo-600 bg-indigo-50 text-indigo-700 dark:border-indigo-500 dark:bg-indigo-950/50 dark:text-indigo-300"
                    : "border-slate-200 bg-white text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300"
                }`}
              >
                {t("authorizations.permanent")}
              </button>
            </div>
          </div>

          {/* Allowed Days */}
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
              {t("authorizations.allowedDays")}
            </label>
            <div className="flex flex-wrap gap-2">
              {ALL_DAYS.map((day) => {
                const isSelected = allowedDays.includes(day);
                return (
                  <button
                    key={day}
                    type="button"
                    onClick={() => handleToggleDay(day)}
                    className={`rounded-md px-3 py-1.5 text-xs font-semibold transition-all ${
                      isSelected
                        ? "bg-indigo-600 text-white dark:bg-indigo-500"
                        : "bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-400"
                    }`}
                  >
                    {t(`authorizations.day${day}` as any)}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Allowed Shifts */}
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
              {t("authorizations.allowedShifts")}
            </label>
            <div className="grid grid-cols-2 gap-2">
              {ALL_SHIFTS.map((shift) => {
                const isSelected = allowedShifts.includes(shift);
                return (
                  <button
                    key={shift}
                    type="button"
                    onClick={() => handleToggleShift(shift)}
                    className={`rounded-md px-3 py-2 text-xs font-semibold transition-all ${
                      isSelected
                        ? "bg-indigo-600 text-white dark:bg-indigo-500"
                        : "bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-400"
                    }`}
                  >
                    {shift === "MORNING"
                      ? t("authorizations.shiftMorning")
                      : shift === "AFTERNOON"
                      ? t("authorizations.shiftAfternoon")
                      : shift === "NIGHT"
                      ? t("authorizations.shiftNight")
                      : t("authorizations.shiftFullDay")}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Validity Range */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                {t("authorizations.validFrom")}
              </label>
              <input
                type="datetime-local"
                value={validFrom}
                onChange={(e) => setValidFrom(e.target.value)}
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm bg-white dark:border-slate-700 dark:bg-slate-800 text-slate-900 dark:text-white"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                {t("authorizations.validUntil")}
              </label>
              <input
                type="datetime-local"
                value={validUntil}
                onChange={(e) => setValidUntil(e.target.value)}
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm bg-white dark:border-slate-700 dark:bg-slate-800 text-slate-900 dark:text-white"
              />
            </div>
          </div>

          {/* Notes */}
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
              {t("visitors.notes")}
            </label>
            <textarea
              rows={2}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm bg-white dark:border-slate-700 dark:bg-slate-800 text-slate-900 dark:text-white"
            />
          </div>

          <div className="flex justify-end space-x-3 pt-4 border-t border-slate-100 dark:border-slate-800">
            <Button type="button" variant="outline" onClick={onClose} disabled={isLoading}>
              {t("authorizations.cancel")}
            </Button>
            <Button type="submit" disabled={isLoading}>
              {isLoading ? t("residents.saving") : t("authorizations.save")}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};
