import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { AlertTriangle, X } from "lucide-react";
import { Button } from "../../../components/ui/button";
import { Textarea } from "../../../components/ui/textarea";
import type { DecisionFormData, PurchaseQuote } from "../../../types/purchase";
import { computeGap } from "../utils/comparison";
import { formatCurrency } from "../utils/formatters";

/** Minimum length the backend enforces on `justification` (APRAS-37). */
export const MIN_JUSTIFICATION_LENGTH = 10;

/**
 * The parent remounts this modal with a `key` derived from the quote being
 * decided, so the form starts empty on every open. That is why there is no
 * reset `useEffect` here: resetting state from an effect causes a cascading
 * render (react-hooks/set-state-in-effect) for no benefit.
 */
interface SelectQuoteModalProps {
  isOpen: boolean;
  onClose: () => void;
  quote: PurchaseQuote | null;
  /**
   * The quote carrying the lowest total, or `null` when none is known.
   * Since APRAS-73 D10 the backend only ever marks a **complete** quote
   * `is_lowest_price`, so this inherits the restriction with no change here.
   */
  lowestQuote?: PurchaseQuote | null;
  /** How many lines the request enumerates, for the coverage sentence. */
  requestItemCount?: number;
  onSubmit: (data: DecisionFormData) => Promise<void>;
  isLoading?: boolean;
}

export const SelectQuoteModal: React.FC<SelectQuoteModalProps> = ({
  isOpen,
  onClose,
  quote,
  lowestQuote = null,
  requestItemCount = 0,
  onSubmit,
  isLoading,
}) => {
  const { t } = useTranslation();
  const [justification, setJustification] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  if (!isOpen || !quote) return null;

  const trimmed = justification.trim();
  const isTooShort = trimmed.length < MIN_JUSTIFICATION_LENGTH;
  // D10: the two panels are mutually exclusive. `computeGap` already returns
  // `null` for an incomplete quote, so `isIncomplete` never has to be
  // subtracted from `gap` a second time here.
  const isIncomplete = quote.is_complete === false;
  const gap = computeGap(quote, lowestQuote);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isTooShort) return;
    try {
      setError(null);
      await onSubmit({ quote_id: quote.id, justification: trimmed });
      onClose();
    } catch (err: unknown) {
      setError(
        err instanceof Error
          ? err.message
          : t("common.genericError", "Erro ao registrar a escolha."),
      );
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="bg-card rounded-xl shadow-xl max-w-lg w-full overflow-hidden">
        <div className="flex items-center justify-between p-6 border-b border-border">
          <h2 className="text-xl font-bold text-foreground">
            {t("purchases.decision.title", "Escolher Orçamento")}
          </h2>
          <Button variant="ghost" size="sm" onClick={onClose} aria-label="close">
            <X className="w-5 h-5" />
          </Button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4" data-testid="decision-form">
          {error && (
            <div className="bg-red-50 text-red-700 text-sm p-3 rounded-lg border border-red-200">
              {error}
            </div>
          )}

          <div className="rounded-lg border border-border bg-muted p-4">
            <p className="text-sm font-semibold text-foreground">
              {quote.supplier_name}
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              {t("purchases.items.coverage", {
                quoted: quote.quoted_item_count,
                total: requestItemCount,
                defaultValue: "Cobertura: {{quoted}} de {{total}} itens",
              })}{" "}
              ·{" "}
              <span className="font-semibold text-foreground">
                {formatCurrency(quote.total_price)}
              </span>
            </p>
          </div>

          {isIncomplete && (
            <div
              data-testid="decision-coverage-warning"
              className="rounded-lg border border-amber-200 bg-amber-50 p-4"
            >
              <div className="flex items-start gap-2">
                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
                <div className="text-xs text-amber-900">
                  <p className="font-semibold">
                    {t("purchases.decision.coverageTitle", {
                      quoted: quote.quoted_item_count,
                      total: requestItemCount,
                      defaultValue:
                        "Este orçamento cobre {{quoted}} de {{total}} itens.",
                    })}
                  </p>
                  <p className="mt-1">
                    {t(
                      "purchases.decision.coverageBody",
                      "Ele não atende o pedido inteiro, então não há comparação de preço com os orçamentos completos.",
                    )}
                  </p>
                </div>
              </div>
            </div>
          )}

          {gap && lowestQuote && (
            <div
              data-testid="decision-gap"
              className="rounded-lg border border-amber-200 bg-amber-50 p-4"
            >
              <div className="flex items-start gap-2">
                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
                <div className="text-xs text-amber-900">
                  <p className="font-semibold">
                    {t(
                      "purchases.decision.gapTitle",
                      "Este não é o menor orçamento.",
                    )}
                  </p>
                  <p className="mt-1">
                    {t("purchases.decision.gapBody", {
                      supplier: lowestQuote.supplier_name,
                      lowest: formatCurrency(lowestQuote.total_price),
                      difference: formatCurrency(gap.difference),
                      percent: gap.percent.toFixed(1),
                    })}
                  </p>
                  <p className="mt-1 text-amber-700">
                    {t(
                      "purchases.decision.gapHint",
                      "Explique abaixo o que justifica a diferença.",
                    )}
                  </p>
                </div>
              </div>
            </div>
          )}

          <div>
            <label
              htmlFor="decision-justification"
              className="block text-xs font-semibold text-gray-700 uppercase mb-1"
            >
              {t("purchases.decision.justification", "Justificativa da escolha *")}
            </label>
            <Textarea
              id="decision-justification"
              rows={4}
              value={justification}
              onChange={(e) => setJustification(e.target.value)}
              placeholder={t(
                "purchases.decision.justificationPlaceholder",
                "Explique por que este orçamento foi escolhido...",
              )}
            />
            {isTooShort && (
              <p className="mt-1 text-xs text-amber-600">
                {t(
                  "purchases.decision.justificationHint",
                  "A justificativa precisa ter ao menos 10 caracteres.",
                )}
              </p>
            )}
          </div>

          <div className="flex items-center justify-end gap-3 pt-4 border-t border-border">
            <Button type="button" variant="outline" onClick={onClose} disabled={isLoading}>
              {t("purchases.actions.cancel", "Cancelar")}
            </Button>
            <Button type="submit" disabled={isTooShort || isLoading}>
              {t("purchases.decision.confirm", "Confirmar Escolha")}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default SelectQuoteModal;
