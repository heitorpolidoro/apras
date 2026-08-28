import React, { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import { X, ScanLine } from "lucide-react";
import { Html5Qrcode } from "html5-qrcode";

interface QrScannerModalProps {
  isOpen: boolean;
  onClose: () => void;
  onScanSuccess: (decodedText: string) => void;
}

const SCANNER_ELEMENT_ID = "gatekeeper-qr-scanner";

export const QrScannerModal: React.FC<QrScannerModalProps> = ({
  isOpen,
  onClose,
  onScanSuccess,
}) => {
  const { t } = useTranslation();
  const scannerRef = useRef<Html5Qrcode | null>(null);

  useEffect(() => {
    if (!isOpen) {
      return undefined;
    }

    const scanner = new Html5Qrcode(SCANNER_ELEMENT_ID);
    scannerRef.current = scanner;

    scanner
      .start(
        { facingMode: "environment" },
        { fps: 10, qrbox: 250 },
        (decodedText: string) => onScanSuccess(decodedText),
        undefined
      )
      .catch(() => {
        // Camera access failures leave the gatekeeper without a scan result;
        // they can still fall back to the existing manual search flow.
      });

    return () => {
      scanner
        .stop()
        .then(() => scanner.clear())
        .catch(() => {
          // Scanner may already be stopped (e.g. camera permission denied).
        });
    };
  }, [isOpen, onScanSuccess]);

  if (!isOpen) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4 animate-in fade-in duration-200">
      <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-xl dark:border-slate-800 dark:bg-slate-900">
        <div className="flex items-center justify-between border-b border-slate-100 pb-4 dark:border-slate-800">
          <h3 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <ScanLine className="size-5 text-indigo-600 dark:text-indigo-400" />
            {t("gatekeeper.scanQrTitle")}
          </h3>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
          >
            <X className="size-5" />
          </button>
        </div>

        <div id={SCANNER_ELEMENT_ID} className="mt-4 w-full" />
      </div>
    </div>
  );
};
