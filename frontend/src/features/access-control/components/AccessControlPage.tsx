import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { ScanFace, Plus } from "lucide-react";
import { Button } from "../../../components/ui/button";
import { DeviceTable } from "./DeviceTable";
import { RegisterDeviceModal } from "./RegisterDeviceModal";
import { FacialTemplateSyncPanel } from "./FacialTemplateSyncPanel";
import {
  useCreateDevice,
  useDevices,
  useRegenerateDeviceKey,
} from "../hooks/useAccessControl";

export const AccessControlPage: React.FC = () => {
  const { t } = useTranslation();
  const [isModalOpen, setIsModalOpen] = useState(false);

  const { data: devicesData } = useDevices();
  const createDeviceMutation = useCreateDevice();
  const regenerateKeyMutation = useRegenerateDeviceKey();

  const devices = devicesData?.items || [];

  const handleCreateDevice = async (data: { name: string; location?: string }) => {
    await createDeviceMutation.mutateAsync(data);
  };

  const handleRegenerateKey = async (deviceId: string) => {
    const device = await regenerateKeyMutation.mutateAsync(deviceId);
    return device.device_key;
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white flex items-center gap-2">
            <ScanFace className="size-7 text-indigo-600 dark:text-indigo-400" />
            {t("accessControl.title")}
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            {t("accessControl.subtitle")}
          </p>
        </div>
        <Button onClick={() => setIsModalOpen(true)} className="gap-1">
          <Plus className="size-4" />
          {t("accessControl.registerDevice")}
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900 overflow-x-auto">
          <DeviceTable
            devices={devices}
            onRegenerateKey={handleRegenerateKey}
            isRegeneratingKey={regenerateKeyMutation.isPending}
          />
        </div>

        <div className="lg:col-span-1">
          <FacialTemplateSyncPanel />
        </div>
      </div>

      <RegisterDeviceModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSubmit={handleCreateDevice}
        isLoading={createDeviceMutation.isPending}
      />
    </div>
  );
};

export default AccessControlPage;
