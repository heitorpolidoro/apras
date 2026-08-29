import React, { useState, useMemo } from "react";
import { useTranslation } from "react-i18next";
import { Plus, Search } from "lucide-react";
import {
  useLots,
  useCreateLot,
  useUpdateLot,
  useDeleteLot,
  useLinkUserLot,
} from "../hooks/useLots";
import { LotTable } from "./LotTable";
import { LotFormModal } from "./LotFormModal";
import { UserLotAssignmentModal } from "./UserLotAssignmentModal";
import { LotDetailsView } from "./LotDetailsView";
import { Button } from "../../../components/ui/button";
import { Input } from "../../../components/ui/input";
import type { Lot, LotCreate, LotUpdate, UserLotLinkCreate } from "../../../types/lot";
import { LotStatus } from "../../../types/lot";
import { UserRole } from "../../../types/auth";
import { useEffectiveIdentity } from "../../user-administration/context/useEffectiveIdentity";

export const LotsPage: React.FC = () => {
  const { t } = useTranslation();
  const identity = useEffectiveIdentity();

  const canManage =
    identity.role === UserRole.ADMINISTRATOR || identity.role === UserRole.DIRECTOR;
  const canDelete = identity.role === UserRole.ADMINISTRATOR;

  const [search, setSearch] = useState("");
  const [selectedBlock, setSelectedBlock] = useState<string>("");
  const [selectedStatus, setSelectedStatus] = useState<string>("");

  const [viewingLotId, setViewingLotId] = useState<string | null>(null);

  // Modals state
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editingLot, setEditingLot] = useState<Lot | null>(null);

  const [isLinkOpen, setIsLinkOpen] = useState(false);
  const [linkingLot, setLinkingLot] = useState<Lot | null>(null);

  const [deletingLot, setDeletingLot] = useState<Lot | null>(null);

  // Queries & Mutations
  const { data, isLoading, isError } = useLots({
    block: selectedBlock || undefined,
    status: (selectedStatus as LotStatus) || undefined,
  });

  const createMutation = useCreateLot();
  const updateMutation = useUpdateLot();
  const deleteMutation = useDeleteLot();
  const linkMutation = useLinkUserLot();

  // Client-side search filter by block or lot_number or address
  const filteredLots = useMemo(() => {
    if (!data?.items) return [];
    if (!search.trim()) return data.items;
    const term = search.toLowerCase();
    return data.items.filter(
      (lot) =>
        lot.block.toLowerCase().includes(term) ||
        lot.lot_number.toLowerCase().includes(term) ||
        (lot.address && lot.address.toLowerCase().includes(term))
    );
  }, [data, search]);

  // Extract unique blocks for filter select
  const uniqueBlocks = useMemo(() => {
    if (!data?.items) return [];
    const blocks = new Set(data.items.map((l) => l.block));
    return Array.from(blocks).sort();
  }, [data]);

  const handleFormSubmit = async (payload: LotCreate | LotUpdate) => {
    if (editingLot) {
      await updateMutation.mutateAsync({ id: editingLot.id, data: payload });
    } else {
      await createMutation.mutateAsync(payload as LotCreate);
    }
  };

  const handleLinkSubmit = async (payload: UserLotLinkCreate) => {
    if (linkingLot) {
      await linkMutation.mutateAsync({ id: linkingLot.id, data: payload });
    }
  };

  const handleConfirmDelete = async () => {
    if (deletingLot) {
      await deleteMutation.mutateAsync(deletingLot.id);
      setDeletingLot(null);
    }
  };

  if (viewingLotId) {
    return (
      <div className="container mx-auto max-w-7xl px-4 py-8">
        <LotDetailsView
          lotId={viewingLotId}
          onBack={() => setViewingLotId(null)}
          onLinkUser={() => {
            const lot = data?.items.find((l) => l.id === viewingLotId);
            if (lot) {
              setLinkingLot(lot);
              setIsLinkOpen(true);
            }
          }}
          canManage={canManage}
        />
        {linkingLot && (
          <UserLotAssignmentModal
            isOpen={isLinkOpen}
            onClose={() => {
              setIsLinkOpen(false);
              setLinkingLot(null);
            }}
            onSubmit={handleLinkSubmit}
            lotBlock={linkingLot.block}
            lotNumber={linkingLot.lot_number}
            isLoading={linkMutation.isPending}
          />
        )}
      </div>
    );
  }

  return (
    <div className="container mx-auto max-w-7xl px-4 py-8 space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
            {t("lots.title")}
          </h1>
        </div>
        {canManage && (
          <Button
            onClick={() => {
              setEditingLot(null);
              setIsFormOpen(true);
            }}
            className="gap-2"
          >
            <Plus className="size-4" />
            {t("lots.newLot")}
          </Button>
        )}
      </div>

      {/* Filter Controls Bar */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-400" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder={t("lots.searchPlaceholder")}
            className="pl-9"
          />
        </div>

        <div className="flex gap-3">
          <select
            value={selectedBlock}
            onChange={(e) => setSelectedBlock(e.target.value)}
            className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:border-blue-500 focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-white"
          >
            <option value="">{t("lots.allBlocks")}</option>
            {uniqueBlocks.map((b) => (
              <option key={b} value={b}>
                {t("lots.block")} {b}
              </option>
            ))}
          </select>

          <select
            value={selectedStatus}
            onChange={(e) => setSelectedStatus(e.target.value)}
            className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:border-blue-500 focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-white"
          >
            <option value="">{t("lots.allStatuses")}</option>
            <option value={LotStatus.VACANT}>{t("lots.statusVacant")}</option>
            <option value={LotStatus.OCCUPIED}>{t("lots.statusOccupied")}</option>
            <option value={LotStatus.UNDER_CONSTRUCTION}>
              {t("lots.statusUnderConstruction")}
            </option>
          </select>
        </div>
      </div>

      {/* Main Lot Table */}
      {isLoading ? (
        <div className="p-8 text-center text-slate-500">{t("lots.loading")}</div>
      ) : isError ? (
        <div className="p-8 text-center text-red-500">Erro ao carregar lotes.</div>
      ) : (
        <LotTable
          lots={filteredLots}
          onViewDetails={(lot) => setViewingLotId(lot.id)}
          onEdit={(lot) => {
            setEditingLot(lot);
            setIsFormOpen(true);
          }}
          onLinkUser={(lot) => {
            setLinkingLot(lot);
            setIsLinkOpen(true);
          }}
          onDelete={(lot) => setDeletingLot(lot)}
          canManage={canManage}
          canDelete={canDelete}
        />
      )}

      {/* Modals */}
      <LotFormModal
        isOpen={isFormOpen}
        onClose={() => {
          setIsFormOpen(false);
          setEditingLot(null);
        }}
        onSubmit={handleFormSubmit}
        initialData={editingLot}
        isLoading={createMutation.isPending || updateMutation.isPending}
      />

      {linkingLot && (
        <UserLotAssignmentModal
          isOpen={isLinkOpen}
          onClose={() => {
            setIsLinkOpen(false);
            setLinkingLot(null);
          }}
          onSubmit={handleLinkSubmit}
          lotBlock={linkingLot.block}
          lotNumber={linkingLot.lot_number}
          isLoading={linkMutation.isPending}
        />
      )}

      {deletingLot && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4 animate-in fade-in duration-200">
          <div className="w-full max-w-sm rounded-xl border border-red-200 bg-white p-6 shadow-xl dark:border-red-900/50 dark:bg-slate-900">
            <h3 className="text-base font-semibold text-red-600 dark:text-red-400">
              {t("lots.delete")}
            </h3>
            <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
              {t("lots.confirmDelete", {
                block: deletingLot.block,
                lot_number: deletingLot.lot_number,
              })}
            </p>
            <div className="mt-5 flex justify-end space-x-3">
              <Button variant="outline" size="sm" onClick={() => setDeletingLot(null)}>
                {t("lots.cancel")}
              </Button>
              <Button variant="destructive" size="sm" onClick={handleConfirmDelete}>
                {t("lots.delete")}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
