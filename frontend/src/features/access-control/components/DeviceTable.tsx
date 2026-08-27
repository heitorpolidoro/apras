import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { KeyRound, Wifi, WifiOff, Wrench } from "lucide-react";
import { Button } from "../../../components/ui/button";
import type { AccessDevice } from "../../../types/accessControl";

interface DeviceTableProps {
  devices: AccessDevice[];
  onRegenerateKey: (deviceId: string) => Promise<string | void>;
  isRegeneratingKey?: boolean;
}

const StatusBadge: React.FC<{ status: AccessDevice["status"] }> = ({ status }) => {
  const { t } = useTranslation();
  const config = {
    ONLINE: {
      icon: Wifi,
      classes: "bg-emerald-100 text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-400",
    },
    OFFLINE: {
      icon: WifiOff,
      classes: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400",
    },
    MAINTENANCE: {
      icon: Wrench,
      classes: "bg-amber-100 text-amber-700 dark:bg-amber-950/50 dark:text-amber-400",
    },
  }[status];

  const Icon = config.icon;

  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-semibold ${config.classes}`}
    >
      <Icon className="size-3.5" />
      {t(`accessControl.status${status}`)}
    </span>
  );
};

export const DeviceTable: React.FC<DeviceTableProps> = ({
  devices,
  onRegenerateKey,
  isRegeneratingKey = false,
}) => {
  const { t } = useTranslation();
  const [revealedKey, setRevealedKey] = useState<{ deviceId: string; key: string } | null>(null);

  const handleRegenerate = async (deviceId: string) => {
    const newKey = await onRegenerateKey(deviceId);
    if (newKey) {
      setRevealedKey({ deviceId, key: newKey });
    }
  };

  if (devices.length === 0) {
    return (
      <p className="p-6 text-center text-sm text-slate-500 dark:text-slate-400">
        {t("accessControl.noDevices")}
      </p>
    );
  }

  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="border-b border-slate-100 text-left text-xs font-semibold uppercase text-slate-500 dark:border-slate-800 dark:text-slate-400">
          <th className="py-2 pr-4">{t("accessControl.deviceName")}</th>
          <th className="py-2 pr-4">{t("accessControl.deviceLocation")}</th>
          <th className="py-2 pr-4">{t("accessControl.deviceStatus")}</th>
          <th className="py-2 pr-4">{t("accessControl.lastSeen")}</th>
          <th className="py-2 pr-4">{t("accessControl.actions")}</th>
        </tr>
      </thead>
      <tbody className="divide-y divide-slate-100 dark:divide-slate-800/80">
        {devices.map((device) => (
          <tr key={device.id}>
            <td className="py-3 pr-4 font-semibold text-slate-900 dark:text-white">
              {device.name}
            </td>
            <td className="py-3 pr-4 text-slate-500 dark:text-slate-400">
              {device.location || "-"}
            </td>
            <td className="py-3 pr-4">
              <StatusBadge status={device.status} />
            </td>
            <td className="py-3 pr-4 text-slate-500 dark:text-slate-400">
              {device.last_seen_at ? new Date(device.last_seen_at).toLocaleString() : "-"}
            </td>
            <td className="py-3 pr-4">
              <Button
                size="sm"
                variant="outline"
                disabled={isRegeneratingKey}
                onClick={() => handleRegenerate(device.id)}
                className="gap-1"
              >
                <KeyRound className="size-3.5" />
                {t("accessControl.regenerateKey")}
              </Button>
              {revealedKey?.deviceId === device.id && (
                <div className="mt-2 rounded-md border border-indigo-200 bg-indigo-50 p-2 text-xs font-mono text-indigo-700 dark:border-indigo-900/50 dark:bg-indigo-950/40 dark:text-indigo-300 break-all">
                  {revealedKey.key}
                </div>
              )}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
};
