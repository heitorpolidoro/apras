import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { X, ScanFace } from "lucide-react";
import { Button } from "../../../components/ui/button";

interface RegisterDeviceModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: { name: string; location?: string }) => Promise<void>;
  isLoading?: boolean;
}

export const RegisterDeviceModal: React.FC<RegisterDeviceModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
  isLoading = false,
}) => {
  const { t } = useTranslation();
  const [name, setName] = useState("");
  const [location, setLocation] = useState("");
  const [errorMessage, setErrorMessage] = useState("");

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage("");

    if (!name.trim()) {
      setErrorMessage(t("accessControl.deviceNameRequired"));
      return;
    }

    try {
      await onSubmit({ name: name.trim(), location: location.trim() || undefined });
      setName("");
      setLocation("");
      onClose();
    } catch (err: any) {
      setErrorMessage(err?.response?.data?.detail || t("accessControl.deviceCreateError"));
    }
  };

  return (
    <div
      data-testid="register-device-modal"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4"
    >
      <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-xl dark:border-slate-800 dark:bg-slate-900">
        <div className="flex items-center justify-between border-b border-slate-100 pb-4 dark:border-slate-800">
          <div className="flex items-center gap-2">
            <ScanFace className="size-5 text-indigo-600 dark:text-indigo-400" />
            <h2 className="text-lg font-bold text-slate-900 dark:text-white">
              {t("accessControl.registerDevice")}
            </h2>
          </div>
          <button
            onClick={onClose}
            aria-label={t("accessControl.close")}
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
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
              {t("accessControl.deviceName")} *
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm bg-white dark:border-slate-700 dark:bg-slate-800 text-slate-900 dark:text-white"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
              {t("accessControl.deviceLocation")}
            </label>
            <input
              type="text"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm bg-white dark:border-slate-700 dark:bg-slate-800 text-slate-900 dark:text-white"
            />
          </div>

          <div className="flex justify-end space-x-3 pt-4 border-t border-slate-100 dark:border-slate-800">
            <Button type="button" variant="outline" onClick={onClose} disabled={isLoading}>
              {t("accessControl.cancel")}
            </Button>
            <Button type="submit" disabled={isLoading}>
              {isLoading ? t("accessControl.saving") : t("accessControl.save")}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};
