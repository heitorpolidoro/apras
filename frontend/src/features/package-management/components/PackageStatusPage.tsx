import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { Package as PackageIcon } from "lucide-react";
import { Button } from "../../../components/ui/button";
import { useMarkPackagePickedUp } from "../../visitor-management/hooks/usePackages";
import { useMyPackages } from "../hooks/usePackages";
import { PackageStatus } from "../../../types/package";

export const PackageStatusPage: React.FC = () => {
  const { t } = useTranslation();
  const { lotsWithPackages, isLoading } = useMyPackages();
  const [pickupNotes, setPickupNotes] = useState<Record<string, string>>({});

  const markPickedUpMutation = useMarkPackagePickedUp();

  const handleConfirmPickup = async (packageId: string) => {
    await markPickedUpMutation.mutateAsync({
      id: packageId,
      data: { picked_up_by_notes: pickupNotes[packageId] || undefined },
    });
    setPickupNotes((prev) => ({ ...prev, [packageId]: "" }));
  };

  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl space-y-6">
      <div className="flex items-center gap-3 bg-card p-6 rounded-xl border border-border shadow-sm">
        <div className="p-3 bg-accent text-primary rounded-lg">
          <PackageIcon className="w-6 h-6" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-foreground">
            {t("packages.pageTitle", "Encomendas")}
          </h1>
          <p className="text-sm text-muted-foreground">
            {t("packages.pageSubtitle", "Acompanhe as encomendas recebidas para o seu lote.")}
          </p>
        </div>
      </div>

      {!isLoading && lotsWithPackages.length === 0 && (
        <div className="bg-card p-6 rounded-xl border border-border shadow-sm text-sm text-muted-foreground">
          {t("packages.noLinkedLots", "Você não está vinculado a nenhum lote.")}
        </div>
      )}

      {lotsWithPackages.map(({ lot, packages }) => (
        <div key={lot.id} className="bg-card p-6 rounded-xl border border-border shadow-sm space-y-4">
          <h2 className="text-base font-bold text-foreground">
            {t("lots.block")} {lot.block}, {t("lots.lotNumber")} {lot.lot_number}
          </h2>

          {packages.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              {t("packages.noPackages", "Nenhuma encomenda aguardando retirada.")}
            </p>
          ) : (
            <div className="space-y-3">
              {packages.map((pkg) => (
                <div
                  key={pkg.id}
                  className="flex flex-col gap-2 rounded-lg border border-gray-100 p-3"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="text-sm font-semibold text-foreground flex gap-2">
                        {pkg.description && <span>{pkg.description}</span>}
                        {pkg.carrier && <span>{pkg.carrier}</span>}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {new Date(pkg.received_at).toLocaleString()}
                      </div>
                    </div>
                    <span className="rounded-full bg-muted px-2 py-0.5 text-xs font-semibold text-gray-700">
                      {t(`packages.status.${pkg.status}`, pkg.status)}
                    </span>
                  </div>

                  {pkg.status === PackageStatus.AWAITING_PICKUP && (
                    <div className="flex items-center gap-2">
                      <input
                        type="text"
                        value={pickupNotes[pkg.id] || ""}
                        onChange={(e) =>
                          setPickupNotes((prev) => ({ ...prev, [pkg.id]: e.target.value }))
                        }
                        placeholder={t("packages.pickedUpBy", "Retirado por: ___")}
                        className="flex-1 rounded-md border border-input px-3 py-1.5 text-xs bg-card text-foreground"
                      />
                      <Button
                        size="sm"
                        disabled={markPickedUpMutation.isPending}
                        onClick={() => handleConfirmPickup(pkg.id)}
                        className="gap-1 bg-primary hover:bg-primary/90 text-primary-foreground"
                      >
                        {t("packages.iPickedThisUp", "Já retirei")}
                      </Button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
};
