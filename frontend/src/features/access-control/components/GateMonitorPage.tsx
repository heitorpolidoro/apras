import React from "react";
import { useTranslation } from "react-i18next";
import { Radio, Wifi, WifiOff, Wrench } from "lucide-react";
import { AccessEventFeed } from "./AccessEventFeed";
import { useAccessEvents, useDevices } from "../hooks/useAccessControl";

const LIVE_POLL_INTERVAL_MS = 5000;

const DEVICE_STATUS_ICON: Record<string, React.ComponentType<{ className?: string }>> = {
  ONLINE: Wifi,
  OFFLINE: WifiOff,
  MAINTENANCE: Wrench,
};

export const GateMonitorPage: React.FC = () => {
  const { t } = useTranslation();
  const { data: devicesData } = useDevices();
  const { data: eventsData } = useAccessEvents({ limit: 50 }, LIVE_POLL_INTERVAL_MS);

  const devices = devicesData?.items || [];
  const events = eventsData?.items || [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white flex items-center gap-2">
          <Radio className="size-7 text-indigo-600 dark:text-indigo-400" />
          {t("accessControl.gateMonitorTitle")}
        </h1>
        <p className="text-sm text-slate-500 dark:text-slate-400">
          {t("accessControl.gateMonitorSubtitle")}
        </p>
      </div>

      {/* Device status strip */}
      <div className="flex flex-wrap gap-3">
        {devices.map((device) => {
          const Icon = DEVICE_STATUS_ICON[device.status] || WifiOff;
          return (
            <div
              key={device.id}
              className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm dark:border-slate-800 dark:bg-slate-900"
            >
              <Icon className="size-4 text-indigo-600 dark:text-indigo-400" />
              <span className="font-semibold text-slate-900 dark:text-white">{device.name}</span>
              <span className="text-xs text-slate-500 dark:text-slate-400">
                {t(`accessControl.status${device.status}`)}
              </span>
            </div>
          );
        })}
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <h2 className="text-base font-bold text-slate-900 dark:text-white mb-4">
          {t("accessControl.liveFeed")}
        </h2>
        <AccessEventFeed events={events} />
      </div>
    </div>
  );
};

export default GateMonitorPage;
