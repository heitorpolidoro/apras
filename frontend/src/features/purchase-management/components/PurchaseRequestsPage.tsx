import React, { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  Ban,
  CheckCircle2,
  Eye,
  FileText,
  Pencil,
  Plus,
  Search,
  Trash2,
  Wallet,
} from "lucide-react";
import { AlertModal } from "../../../components/ui/alert-modal";
import { Badge } from "../../../components/ui/badge";
import { Button } from "../../../components/ui/button";
import { Input } from "../../../components/ui/input";
import { UserRole } from "../../../types/auth";
import type {
  PurchaseFilterParams,
  PurchaseRequest,
  PurchaseRequestFormData,
} from "../../../types/purchase";
import { PurchaseRequestStatus } from "../../../types/purchase";
import { useEffectiveIdentity } from "../../user-administration/context/useEffectiveIdentity";
import {
  useCancelPurchaseRequest,
  useCreatePurchaseRequest,
  useDeletePurchaseRequest,
  usePurchaseRequests,
  usePurchaseSummary,
  useUpdatePurchaseRequest,
} from "../hooks/usePurchaseRequests";
import { formatCurrency, formatDateTime } from "../utils/formatters";
import { PurchaseRequestDetailModal } from "./PurchaseRequestDetailModal";
import { PurchaseRequestFormModal } from "./PurchaseRequestFormModal";

type FilterTab = "all" | "open" | "decided" | "cancelled";

const TAB_STATUS: Record<FilterTab, PurchaseRequestStatus | undefined> = {
  all: undefined,
  open: PurchaseRequestStatus.OPEN,
  decided: PurchaseRequestStatus.DECIDED,
  cancelled: PurchaseRequestStatus.CANCELLED,
};

const STATUS_BADGE_VARIANT: Record<
  PurchaseRequestStatus,
  "pending" | "completed" | "canceled"
> = {
  [PurchaseRequestStatus.OPEN]: "pending",
  [PurchaseRequestStatus.DECIDED]: "completed",
  [PurchaseRequestStatus.CANCELLED]: "canceled",
};

export const PurchaseRequestsPage: React.FC = () => {
  const { t } = useTranslation();
  const { role } = useEffectiveIdentity();

  const canDecide =
    role === UserRole.ADMINISTRATOR || role === UserRole.DIRECTOR;

  const [activeTab, setActiveTab] = useState<FilterTab>("all");
  const [searchQuery, setSearchQuery] = useState<string>("");

  const [isFormOpen, setIsFormOpen] = useState<boolean>(false);
  const [editingRequest, setEditingRequest] = useState<PurchaseRequest | null>(
    null,
  );
  const [detailRequestId, setDetailRequestId] = useState<string | null>(null);
  const [requestToDelete, setRequestToDelete] = useState<PurchaseRequest | null>(
    null,
  );
  const [requestToCancel, setRequestToCancel] = useState<PurchaseRequest | null>(
    null,
  );
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const filterParams = useMemo<PurchaseFilterParams>(() => {
    const params: PurchaseFilterParams = {};
    if (searchQuery.trim()) params.search = searchQuery.trim();
    const status = TAB_STATUS[activeTab];
    if (status) params.status = status;
    return params;
  }, [activeTab, searchQuery]);

  const { data: listData, isLoading } = usePurchaseRequests(filterParams);
  const { data: summary } = usePurchaseSummary();

  const createMutation = useCreatePurchaseRequest();
  const updateMutation = useUpdatePurchaseRequest();
  const deleteMutation = useDeletePurchaseRequest();
  const cancelMutation = useCancelPurchaseRequest();

  const handleFormSubmit = async (data: PurchaseRequestFormData) => {
    if (editingRequest) {
      await updateMutation.mutateAsync({ id: editingRequest.id, data });
    } else {
      await createMutation.mutateAsync(data);
    }
  };

  const handleConfirmDelete = async () => {
    if (!requestToDelete) return;
    try {
      await deleteMutation.mutateAsync(requestToDelete.id);
      setRequestToDelete(null);
    } catch (err: unknown) {
      setRequestToDelete(null);
      setErrorMessage(
        err instanceof Error
          ? err.message
          : t("common.genericError", "Erro ao excluir o pedido."),
      );
    }
  };

  const handleConfirmCancel = async () => {
    if (!requestToCancel) return;
    try {
      await cancelMutation.mutateAsync(requestToCancel.id);
      setRequestToCancel(null);
    } catch (err: unknown) {
      setRequestToCancel(null);
      setErrorMessage(
        err instanceof Error
          ? err.message
          : t("common.genericError", "Erro ao cancelar o pedido."),
      );
    }
  };

  const summaryCards = [
    {
      key: "open",
      icon: FileText,
      label: t("purchases.summary.open", "Pedidos Abertos"),
      value: summary?.open_count ?? 0,
    },
    {
      key: "decided",
      icon: CheckCircle2,
      label: t("purchases.summary.decided", "Pedidos Decididos"),
      value: summary?.decided_count ?? 0,
    },
    {
      key: "cancelled",
      icon: Ban,
      label: t("purchases.summary.cancelled", "Pedidos Cancelados"),
      value: summary?.cancelled_count ?? 0,
    },
    {
      key: "totalSelected",
      icon: Wallet,
      label: t("purchases.summary.totalSelected", "Valor Escolhido"),
      value: formatCurrency(summary?.total_selected_value ?? 0),
    },
  ];

  const tabs: FilterTab[] = ["all", "open", "decided", "cancelled"];

  return (
    <div className="p-8 max-w-7xl mx-auto">
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-black text-gray-900">
            {t("purchases.pageTitle", "Cotações de Compra")}
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            {t(
              "purchases.pageSubtitle",
              "Pedidos de compra, orçamentos de fornecedores e a escolha justificada.",
            )}
          </p>
        </div>
        <Button
          onClick={() => {
            setEditingRequest(null);
            setIsFormOpen(true);
          }}
        >
          <Plus className="w-4 h-4 mr-1" />
          {t("purchases.actions.newRequest", "Novo Pedido")}
        </Button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {summaryCards.map((card) => {
          const Icon = card.icon;
          return (
            <div
              key={card.key}
              data-testid={`purchase-summary-${card.key}`}
              className="rounded-xl border border-gray-200 bg-white p-4 flex items-center gap-3"
            >
              <Icon className="w-5 h-5 text-primary" />
              <div>
                <p className="text-xs text-gray-500 uppercase font-semibold">
                  {card.label}
                </p>
                <p className="text-xl font-bold text-gray-900">{card.value}</p>
              </div>
            </div>
          );
        })}
      </div>

      <div className="flex flex-wrap items-center gap-2 mb-4">
        {tabs.map((tab) => (
          <button
            key={tab}
            type="button"
            onClick={() => setActiveTab(tab)}
            className={
              activeTab === tab
                ? "px-3 py-1.5 rounded-md text-sm font-semibold bg-primary text-primary-foreground"
                : "px-3 py-1.5 rounded-md text-sm font-semibold text-gray-600 hover:bg-gray-100"
            }
          >
            {t(`purchases.tabs.${tab}`, tab)}
          </button>
        ))}
      </div>

      <div className="relative mb-4">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
        <Input
          className="pl-9"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder={t(
            "purchases.searchPlaceholder",
            "Buscar por título ou descrição...",
          )}
        />
      </div>

      {isLoading && !listData ? (
        <p className="text-sm text-gray-500">{t("purchases.loading", "Carregando...")}</p>
      ) : listData && listData.items.length === 0 ? (
        <p className="text-sm text-gray-500">
          {t("purchases.noRequestsFound", "Nenhum pedido de compra encontrado.")}
        </p>
      ) : (
        <div className="space-y-3">
          {listData?.items.map((request) => (
            <div
              key={request.id}
              data-testid={`purchase-request-row-${request.id}`}
              className="rounded-xl border border-gray-200 bg-white p-4 flex items-start justify-between gap-4"
            >
              <div className="min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-semibold text-gray-900">
                    {request.title}
                  </span>
                  <Badge variant={STATUS_BADGE_VARIANT[request.status]}>
                    {t(`purchases.status.${request.status}`, request.status)}
                  </Badge>
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  {t("purchases.requestedBy", "Aberto por")}:{" "}
                  {request.requested_by_name ?? "—"} •{" "}
                  {formatDateTime(request.created_at)}
                </p>
                <p className="text-xs text-gray-600 mt-1">
                  {request.quote_count} {t("purchases.quoteCount", "orçamentos")}
                  {request.lowest_quote_total !== null && (
                    <>
                      {" • "}
                      {t("purchases.lowestTotal", "Menor orçamento")}:{" "}
                      {formatCurrency(request.lowest_quote_total)}
                    </>
                  )}
                  {request.selected_quote_total !== null && (
                    <>
                      {" • "}
                      {t("purchases.selectedTotal", "Orçamento escolhido")}:{" "}
                      {formatCurrency(request.selected_quote_total)}
                    </>
                  )}
                </p>
              </div>

              <div className="flex items-center gap-1 shrink-0">
                <Button
                  variant="ghost"
                  size="sm"
                  title={t("purchases.actions.openDetail", "Ver Orçamentos")}
                  onClick={() => setDetailRequestId(request.id)}
                >
                  <Eye className="w-4 h-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  title={t("purchases.actions.edit", "Editar")}
                  onClick={() => {
                    setEditingRequest(request);
                    setIsFormOpen(true);
                  }}
                >
                  <Pencil className="w-4 h-4" />
                </Button>
                {canDecide && request.status === PurchaseRequestStatus.OPEN && (
                  <Button
                    variant="ghost"
                    size="sm"
                    title={t("purchases.actions.cancelRequest", "Cancelar Pedido")}
                    onClick={() => setRequestToCancel(request)}
                  >
                    <Ban className="w-4 h-4 text-amber-600" />
                  </Button>
                )}
                <Button
                  variant="ghost"
                  size="sm"
                  title={t("purchases.actions.delete", "Excluir")}
                  onClick={() => setRequestToDelete(request)}
                >
                  <Trash2 className="w-4 h-4 text-red-500" />
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}

      <PurchaseRequestFormModal
        key={`request-form-${isFormOpen}-${editingRequest?.id ?? "new"}`}
        isOpen={isFormOpen}
        onClose={() => {
          setIsFormOpen(false);
          setEditingRequest(null);
        }}
        request={editingRequest}
        onSubmit={handleFormSubmit}
        isLoading={createMutation.isPending || updateMutation.isPending}
      />

      <PurchaseRequestDetailModal
        isOpen={!!detailRequestId}
        onClose={() => setDetailRequestId(null)}
        requestId={detailRequestId}
      />

      {requestToDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-md w-full p-6 space-y-4">
            <h3 className="text-lg font-bold text-gray-900">
              {t("purchases.deleteConfirmTitle", "Excluir Pedido de Compra")}
            </h3>
            <p className="text-sm text-gray-600">
              {t(
                "purchases.deleteConfirmMessage",
                "Tem certeza de que deseja excluir o pedido '{{title}}'? Os orçamentos e as justificativas registradas também serão removidos.",
                { title: requestToDelete.title },
              )}
            </p>
            <div className="flex justify-end gap-3 pt-2">
              <Button
                variant="outline"
                onClick={() => setRequestToDelete(null)}
                disabled={deleteMutation.isPending}
              >
                {t("purchases.actions.cancel", "Cancelar")}
              </Button>
              <Button
                variant="destructive"
                onClick={handleConfirmDelete}
                disabled={deleteMutation.isPending}
              >
                {t("common.confirm", "Confirmar")}
              </Button>
            </div>
          </div>
        </div>
      )}

      {requestToCancel && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-md w-full p-6 space-y-4">
            <h3 className="text-lg font-bold text-gray-900">
              {t("purchases.cancelConfirmTitle", "Cancelar Pedido de Compra")}
            </h3>
            <p className="text-sm text-gray-600">
              {t(
                "purchases.cancelConfirmMessage",
                "Tem certeza de que deseja cancelar o pedido '{{title}}'? Não será possível reabri-lo.",
                { title: requestToCancel.title },
              )}
            </p>
            <div className="flex justify-end gap-3 pt-2">
              <Button
                variant="outline"
                onClick={() => setRequestToCancel(null)}
                disabled={cancelMutation.isPending}
              >
                {t("purchases.actions.cancel", "Cancelar")}
              </Button>
              <Button
                variant="destructive"
                onClick={handleConfirmCancel}
                disabled={cancelMutation.isPending}
              >
                {t("common.confirm", "Confirmar")}
              </Button>
            </div>
          </div>
        </div>
      )}

      <AlertModal
        open={!!errorMessage}
        onClose={() => setErrorMessage(null)}
        variant="destructive"
        title={t("common.error", "Erro")}
        message={errorMessage ?? ""}
      />
    </div>
  );
};

export default PurchaseRequestsPage;
