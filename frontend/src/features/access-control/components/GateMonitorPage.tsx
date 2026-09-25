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
        <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2">
          <Radio className="size-7 text-primary" />
          {t("accessControl.gateMonitorTitle")}
        </h1>
        <p className="text-sm text-muted-foreground">
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
              className="flex items-center gap-2 rounded-xl border border-border bg-card px-3 py-2 text-sm"
            >
              <Icon className="size-4 text-primary" />
              <span className="font-semibold text-foreground">{device.name}</span>
              <span className="text-xs text-muted-foreground">
                {t(`accessControl.status${device.status}`)}
              </span>
            </div>
          );
        })}
      </div>

      <div className="rounded-2xl border border-border bg-card p-5 shadow-sm">
        <h2 className="text-base font-bold text-foreground mb-4">
          {t("accessControl.liveFeed")}
        </h2>
        <AccessEventFeed events={events} />
      </div>
    </div>
  );
};

export default GateMonitorPage;
