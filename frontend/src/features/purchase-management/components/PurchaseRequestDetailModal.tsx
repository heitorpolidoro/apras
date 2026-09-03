import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { Award, CheckCircle2, Pencil, Plus, Trash2, X } from "lucide-react";
import { Badge } from "../../../components/ui/badge";
import { Button } from "../../../components/ui/button";
import type {
  DecisionFormData,
  PurchaseQuote,
  QuoteFormData,
} from "../../../types/purchase";
import { PurchaseRequestStatus } from "../../../types/purchase";
import { useEffectivePermissionSet } from "../../user-administration/access/useCanAccess";
import { useAddQuote, useDeleteQuote, usePurchaseRequest, useSelectQuote, useUpdateQuote,  } from "../hooks/usePurchaseRequests";
import { formatCurrency, formatDateTime } from "../utils/formatters";
import { QuoteFormModal } from "./QuoteFormModal";
import { SelectQuoteModal } from "./SelectQuoteModal";

interface PurchaseRequestDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  requestId: string | null;
}

export const PurchaseRequestDetailModal: React.FC<
  PurchaseRequestDetailModalProps
> = ({ isOpen, onClose, requestId }) => {
  const { t } = useTranslation();
  const { has } = useEffectivePermissionSet();

  const [isQuoteFormOpen, setIsQuoteFormOpen] = useState<boolean>(false);
  const [editingQuote, setEditingQuote] = useState<PurchaseQuote | null>(null);
  const [decidingQuote, setDecidingQuote] = useState<PurchaseQuote | null>(null);

  const { data: detail, isLoading } = usePurchaseRequest(
    isOpen ? requestId : null,
  );
  const addQuoteMutation = useAddQuote();
  const updateQuoteMutation = useUpdateQuote();
  const deleteQuoteMutation = useDeleteQuote();
  const selectQuoteMutation = useSelectQuote();

  if (!isOpen || !requestId) return null;

  const canDecide =
    has("purchases:decide");
  const isOpenRequest = detail?.status === PurchaseRequestStatus.OPEN;
  const quotesEditable = !!detail && isOpenRequest;

  const handleQuoteSubmit = async (data: QuoteFormData) => {
    if (editingQuote) {
      await updateQuoteMutation.mutateAsync({
        requestId,
        quoteId: editingQuote.id,
        data,
      });
    } else {
      await addQuoteMutation.mutateAsync({ requestId, data });
    }
  };

  const handleDecisionSubmit = async (data: DecisionFormData) => {
    await selectQuoteMutation.mutateAsync({ requestId, data });
  };

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/50 p-4">
      <div className="bg-white rounded-xl shadow-xl max-w-4xl w-full max-h-[92vh] overflow-y-auto">
        <div className="flex items-start justify-between p-6 border-b border-gray-200">
          <div>
            <h2 className="text-xl font-bold text-gray-900">
              {detail?.title ?? t("purchases.detail.title", "Pedido de Compra")}
            </h2>
            {detail && (
              <p className="text-xs text-gray-500 mt-1">
                {t("purchases.requestedBy", "Aberto por")}:{" "}
                {detail.requested_by_name ?? "—"} •{" "}
                {formatDateTime(detail.created_at)}
              </p>
            )}
          </div>
          <div className="flex items-center gap-2">
            {detail && (
              <Badge
                variant={
                  detail.status === PurchaseRequestStatus.DECIDED
                    ? "completed"
                    : detail.status === PurchaseRequestStatus.CANCELLED
                      ? "canceled"
                      : "pending"
                }
              >
                {t(`purchases.status.${detail.status}`, detail.status)}
              </Badge>
            )}
            <Button variant="ghost" size="sm" onClick={onClose} aria-label="close">
              <X className="w-5 h-5" />
            </Button>
          </div>
        </div>

        {isLoading && !detail && (
          <div className="p-6 text-sm text-gray-500">
            {t("purchases.loading", "Carregando...")}
          </div>
        )}

        {detail && (
          <div className="p-6 space-y-6">
            {detail.description && (
              <section>
                <h3 className="text-xs font-semibold text-gray-700 uppercase mb-1">
                  {t("purchases.detail.description", "Descrição")}
                </h3>
                <p className="text-sm text-gray-800 whitespace-pre-line">
                  {detail.description}
                </p>
              </section>
            )}

            {detail.general_notes && (
              <section className="rounded-lg bg-amber-50 border border-amber-200 p-4">
                <h3 className="text-xs font-semibold text-amber-800 uppercase mb-1">
                  {t("purchases.detail.generalNotes", "Anotações gerais")}
                </h3>
                <p className="text-sm text-amber-900 whitespace-pre-line">
                  {detail.general_notes}
                </p>
              </section>
            )}

            <section>
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-bold text-gray-900">
                  {t("purchases.detail.quotes", "Orçamentos")} ({detail.quotes.length})
                </h3>
                {quotesEditable && (
                  <Button
                    size="sm"
                    onClick={() => {
                      setEditingQuote(null);
                      setIsQuoteFormOpen(true);
                    }}
                  >
                    <Plus className="w-4 h-4 mr-1" />
                    {t("purchases.actions.addQuote", "Novo Orçamento")}
                  </Button>
                )}
              </div>

              {!quotesEditable && (
                <p className="text-xs text-gray-500 mb-3">
                  {t(
                    "purchases.quote.frozen",
                    "Os orçamentos deste pedido estão congelados.",
                  )}
                </p>
              )}

              {detail.quotes.length === 0 ? (
                <p className="text-sm text-gray-500">
                  {t("purchases.quote.noQuotes", "Nenhum orçamento registrado neste pedido.")}
                </p>
              ) : (
                <div className="space-y-3">
                  {detail.quotes.map((quote) => (
                    <div
                      key={quote.id}
                      data-testid={`quote-row-${quote.id}`}
                      className="rounded-lg border border-gray-200 p-4"
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div className="min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="font-semibold text-gray-900">
                              {quote.supplier_name}
                            </span>
                            {quote.is_lowest_price && (
                              <Badge variant="active">
                                {t("purchases.quote.lowestBadge", "Menor preço")}
                              </Badge>
                            )}
                            {quote.is_selected && (
                              <Badge variant="completed">
                                {t("purchases.quote.selectedBadge", "Escolhido")}
                              </Badge>
                            )}
                          </div>
                          {quote.supplier_contact && (
                            <p className="text-xs text-gray-500 mt-0.5">
                              {quote.supplier_contact}
                            </p>
                          )}
                          <p className="text-xs text-gray-600 mt-1">
                            {quote.quantity} × {formatCurrency(quote.unit_price)}
                          </p>
                          {quote.notes && (
                            <p className="text-xs text-gray-600 mt-1">{quote.notes}</p>
                          )}
                          {quote.extra_fields.length > 0 && (
                            <dl className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1">
                              {quote.extra_fields.map((field, index) => (
                                <div key={`${quote.id}-${index}`} className="text-xs">
                                  <dt className="font-semibold text-gray-700">
                                    {field.label}
                                  </dt>
                                  <dd className="text-gray-600">{field.value}</dd>
                                </div>
                              ))}
                            </dl>
                          )}
                        </div>

                        <div className="flex flex-col items-end gap-2 shrink-0">
                          <span className="text-lg font-bold text-gray-900">
                            {formatCurrency(quote.total_price)}
                          </span>
                          <div className="flex items-center gap-1">
                            {canDecide &&
                              detail.status !== PurchaseRequestStatus.CANCELLED && (
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  title={t(
                                    "purchases.actions.chooseQuote",
                                    "Escolher este Orçamento",
                                  )}
                                  onClick={() => setDecidingQuote(quote)}
                                >
                                  <Award className="w-4 h-4 text-emerald-600" />
                                </Button>
                              )}
                            {quotesEditable && (
                              <>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  title={t("purchases.actions.editQuote", "Editar Orçamento")}
                                  onClick={() => {
                                    setEditingQuote(quote);
                                    setIsQuoteFormOpen(true);
                                  }}
                                >
                                  <Pencil className="w-4 h-4" />
                                </Button>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  title={t(
                                    "purchases.actions.deleteQuote",
                                    "Excluir Orçamento",
                                  )}
                                  onClick={() =>
                                    deleteQuoteMutation.mutate({
                                      requestId,
                                      quoteId: quote.id,
                                    })
                                  }
                                >
                                  <Trash2 className="w-4 h-4 text-red-500" />
                                </Button>
                              </>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </section>

            <section className="border-t border-gray-200 pt-4">
              <h3 className="text-sm font-bold text-gray-900 mb-2">
                {t("purchases.decision.panelTitle", "Decisão registrada")}
              </h3>

              {!detail.current_decision ? (
                <p className="text-sm text-gray-500">
                  {t("purchases.decision.noDecision", "Nenhum orçamento escolhido até agora.")}
                </p>
              ) : (
                <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4">
                  <div className="flex items-center gap-2 mb-1">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                    <span className="text-sm font-semibold text-emerald-900">
                      {detail.current_decision.quote_supplier_name} •{" "}
                      {formatCurrency(detail.current_decision.quote_total_price)}
                    </span>
                    <Badge variant="completed">
                      {t("purchases.decision.current", "Atual")}
                    </Badge>
                  </div>
                  <p className="text-sm text-emerald-900">
                    {detail.current_decision.justification}
                  </p>
                  <p className="text-xs text-emerald-700 mt-2">
                    {t("purchases.decision.decidedBy", "Decidido por")}:{" "}
                    {detail.current_decision.decided_by_name ?? "—"} •{" "}
                    {formatDateTime(detail.current_decision.decided_at)}
                  </p>
                </div>
              )}

              {detail.decisions.filter((d) => !d.is_current).length > 0 && (
                <div className="mt-4">
                  <h4 className="text-xs font-semibold text-gray-700 uppercase mb-2">
                    {t("purchases.decision.supersededTitle", "Decisões anteriores")}
                  </h4>
                  <div className="space-y-2">
                    {detail.decisions
                      .filter((decision) => !decision.is_current)
                      .map((decision) => (
                        <div
                          key={decision.id}
                          data-testid={`decision-row-${decision.id}`}
                          className="rounded-lg border border-gray-200 bg-gray-50 p-3"
                        >
                          <div className="flex items-center gap-2 mb-1">
                            <span className="text-xs font-semibold text-gray-700">
                              {decision.quote_supplier_name} •{" "}
                              {formatCurrency(decision.quote_total_price)}
                            </span>
                            <Badge variant="secondary">
                              {t("purchases.decision.superseded", "Substituída")}
                            </Badge>
                          </div>
                          <p className="text-sm text-gray-700">
                            {decision.justification}
                          </p>
                          <p className="text-xs text-gray-500 mt-1">
                            {t("purchases.decision.decidedBy", "Decidido por")}:{" "}
                            {decision.decided_by_name ?? "—"} •{" "}
                            {formatDateTime(decision.decided_at)}
                          </p>
                        </div>
                      ))}
                  </div>
                </div>
              )}
            </section>
          </div>
        )}

        <div className="flex justify-end p-6 border-t border-gray-200">
          <Button variant="outline" onClick={onClose}>
            {t("purchases.actions.close", "Fechar")}
          </Button>
        </div>
      </div>

      <QuoteFormModal
        key={`quote-form-${isQuoteFormOpen}-${editingQuote?.id ?? "new"}`}
        isOpen={isQuoteFormOpen}
        onClose={() => {
          setIsQuoteFormOpen(false);
          setEditingQuote(null);
        }}
        quote={editingQuote}
        onSubmit={handleQuoteSubmit}
        isLoading={addQuoteMutation.isPending || updateQuoteMutation.isPending}
      />

      <SelectQuoteModal
        key={`decision-${decidingQuote?.id ?? "none"}`}
        isOpen={!!decidingQuote}
        onClose={() => setDecidingQuote(null)}
        quote={decidingQuote}
        onSubmit={handleDecisionSubmit}
        isLoading={selectQuoteMutation.isPending}
      />
    </div>
  );
};

export default PurchaseRequestDetailModal;
