import React, { useMemo, useRef, useState, useSyncExternalStore } from "react";
import { useTranslation } from "react-i18next";
import {
  ArrowUpDown,
  Award,
  FileText,
  Lock,
  Paperclip,
  Pencil,
  Trash2,
  Upload,
} from "lucide-react";
import { Badge } from "../../../components/ui/badge";
import { Button } from "../../../components/ui/button";
import { QUOTE_ATTACHMENT_ACCEPT } from "../../../api/purchases";
import type { PurchaseQuote } from "../../../types/purchase";
import {
  attachmentRejectionKey,
  unionExtraFieldLabels,
} from "../utils/comparison";
import { formatCurrency } from "../utils/formatters";

/**
 * The quotes of one request read side by side (APRAS-63 D7).
 *
 * Suppliers are columns and every fact is a row, so "prazo de entrega" for
 * three suppliers is one line the eye can run along — which the stacked
 * cards this replaces made impossible, each carrying its own `<dl>`.
 *
 * Below `md` the table transposes into one block per supplier with the
 * labels in the left column. **Exactly one** of the two variants is in the
 * DOM at a time, chosen by `matchMedia` through `useSyncExternalStore`
 * rather than by a Tailwind `hidden`/`md:block` pair: rendering both would
 * put every control, every label and every `data-testid` in the document
 * twice, so `getByText` would be ambiguous and "there are two choose
 * buttons" would silently become four. The element carrying each supplier
 * keeps `data-testid="quote-row-${id}"` in both variants, so that count is
 * the number of suppliers whichever one is showing.
 */

/** The `md` breakpoint Tailwind uses, stated once. */
const NARROW_QUERY = "(max-width: 767px)";

const matchMediaOrNull = (): MediaQueryList | null =>
  typeof window !== "undefined" && typeof window.matchMedia === "function"
    ? window.matchMedia(NARROW_QUERY)
    : null;

const subscribeToWidth = (onChange: () => void) => {
  const mql = matchMediaOrNull();
  if (!mql) return () => {};
  mql.addEventListener("change", onChange);
  return () => mql.removeEventListener("change", onChange);
};

/** `false` wherever `matchMedia` is absent (jsdom, SSR): the table is the
 *  default and the phone layout is the special case, never the reverse. */
const isNarrowSnapshot = () => matchMediaOrNull()?.matches ?? false;

/** Ascending ⇄ descending ⇄ the order the backend sent. */
type SortMode = "original" | "asc" | "desc";

const NEXT_SORT: Record<SortMode, SortMode> = {
  original: "asc",
  asc: "desc",
  desc: "original",
};

const SORT_LABEL_KEY: Record<SortMode, string> = {
  original: "purchases.comparison.sortOriginal",
  asc: "purchases.comparison.sortAscending",
  desc: "purchases.comparison.sortDescending",
};

interface QuoteComparisonTableProps {
  quotes: PurchaseQuote[];
  /** `purchases:decide`, and the request is not cancelled. */
  canChoose: boolean;
  /** The request is OPEN — i.e. its quotes are not frozen. */
  quotesEditable: boolean;
  /** `purchases:quote_update`: without it no upload control is rendered. */
  canEditQuotes: boolean;
  onChoose: (quote: PurchaseQuote) => void;
  onEdit: (quote: PurchaseQuote) => void;
  onDelete: (quote: PurchaseQuote) => void;
  onUpload: (quote: PurchaseQuote, file: File) => void;
  onRemoveAttachment: (quote: PurchaseQuote) => void;
}

export const QuoteComparisonTable: React.FC<QuoteComparisonTableProps> = ({
  quotes,
  canChoose,
  quotesEditable,
  canEditQuotes,
  onChoose,
  onEdit,
  onDelete,
  onUpload,
  onRemoveAttachment,
}) => {
  const { t } = useTranslation();
  const [sortMode, setSortMode] = useState<SortMode>("original");
  const [rejected, setRejected] = useState<string | null>(null);
  const isNarrow = useSyncExternalStore(subscribeToWidth, isNarrowSnapshot);
  const pickers = useRef<Record<string, HTMLInputElement | null>>({});

  const labels = useMemo(() => unionExtraFieldLabels(quotes), [quotes]);

  const ordered = useMemo(() => {
    if (sortMode === "original") return quotes;
    const copy = [...quotes];
    copy.sort((a, b) =>
      sortMode === "asc"
        ? a.total_price - b.total_price
        : b.total_price - a.total_price,
    );
    return copy;
  }, [quotes, sortMode]);

  const canUpload = quotesEditable && canEditQuotes;

  const handlePicked = (
    quote: PurchaseQuote,
    event: React.ChangeEvent<HTMLInputElement>,
  ) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    const reason = attachmentRejectionKey(file);
    if (reason) {
      setRejected(
        `${t("purchases.attachment.rejected", { filename: file.name })} ${t(reason)}`,
      );
      return;
    }
    setRejected(null);
    onUpload(quote, file);
  };

  /** A value the supplier did not fill is an explicit dash, never a blank:
   *  an empty cell reads as a zero. */
  const cell = (value: string | null | undefined) =>
    value && value.trim() !== "" ? (
      <span>{value}</span>
    ) : (
      <span
        className="text-gray-400"
        title={t("purchases.comparison.notProvided", "Não informado")}
      >
        —
      </span>
    );

  const badges = (quote: PurchaseQuote) => (
    <>
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
    </>
  );

  const attachmentLink = (quote: PurchaseQuote) =>
    quote.attachment_url ? (
      <a
        href={quote.attachment_url}
        target="_blank"
        rel="noopener noreferrer"
        title={t("purchases.attachment.open", "Abrir o documento do fornecedor")}
        className="inline-flex items-center gap-1 text-sky-700 hover:underline break-all"
      >
        <FileText className="w-4 h-4 shrink-0" />
        {quote.attachment_filename}
      </a>
    ) : null;

  const attachmentControls = (quote: PurchaseQuote) => (
    <div className="flex flex-wrap items-center gap-1">
      {attachmentLink(quote) ?? (!canUpload ? cell(null) : null)}
      {!quotesEditable && quote.attachment_url && (
        <span className="inline-flex items-center gap-1 text-[11px] text-gray-400">
          <Lock className="w-3 h-3" />
          {t("purchases.attachment.readOnly", "somente leitura")}
        </span>
      )}
      {canUpload && (
        <>
          <input
            type="file"
            className="hidden"
            accept={QUOTE_ATTACHMENT_ACCEPT}
            data-testid={`attachment-input-${quote.id}`}
            aria-label={t("purchases.attachment.upload", "Anexar documento")}
            ref={(element) => {
              pickers.current[quote.id] = element;
            }}
            onChange={(event) => handlePicked(quote, event)}
          />
          <Button
            variant="ghost"
            size="sm"
            title={
              quote.attachment_url
                ? t("purchases.attachment.replace", "Substituir")
                : t("purchases.attachment.upload", "Anexar documento")
            }
            onClick={() => pickers.current[quote.id]?.click()}
          >
            {quote.attachment_url ? (
              <Upload className="w-4 h-4" />
            ) : (
              <Paperclip className="w-4 h-4" />
            )}
          </Button>
          {quote.attachment_url && (
            <Button
              variant="ghost"
              size="sm"
              title={t("purchases.attachment.remove", "Remover")}
              onClick={() => onRemoveAttachment(quote)}
            >
              <Trash2 className="w-4 h-4 text-red-500" />
            </Button>
          )}
        </>
      )}
    </div>
  );

  const actions = (quote: PurchaseQuote) => (
    <div className="flex items-center gap-1">
      {canChoose && (
        <Button
          variant="ghost"
          size="sm"
          title={t("purchases.actions.chooseQuote", "Escolher este Orçamento")}
          onClick={() => onChoose(quote)}
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
            onClick={() => onEdit(quote)}
          >
            <Pencil className="w-4 h-4" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            title={t("purchases.actions.deleteQuote", "Excluir Orçamento")}
            onClick={() => onDelete(quote)}
          >
            <Trash2 className="w-4 h-4 text-red-500" />
          </Button>
        </>
      )}
    </div>
  );

  const fixedRows: Array<{
    key: string;
    label: string;
    render: (quote: PurchaseQuote) => React.ReactNode;
  }> = [
    {
      key: "total",
      label: t("purchases.comparison.total", "Total"),
      render: (quote) => (
        <span
          className={`text-base font-bold ${
            quote.is_lowest_price ? "text-emerald-700" : "text-gray-900"
          }`}
        >
          {formatCurrency(quote.total_price)}
        </span>
      ),
    },
    {
      key: "unit",
      label: t("purchases.comparison.unitTimesQuantity", "Unitário × qtd."),
      render: (quote) => (
        <span>
          {formatCurrency(quote.unit_price)} × {quote.quantity}
        </span>
      ),
    },
    {
      key: "contact",
      label: t("purchases.comparison.contact", "Contato"),
      render: (quote) => cell(quote.supplier_contact),
    },
    {
      key: "notes",
      label: t("purchases.comparison.notes", "Observações"),
      render: (quote) => cell(quote.notes),
    },
    {
      key: "attachment",
      label: t("purchases.comparison.attachment", "Documento"),
      render: (quote) => attachmentControls(quote),
    },
  ];

  const valueOf = (quote: PurchaseQuote, label: string) =>
    quote.extra_fields.find((field) => field.label === label)?.value;

  return (
    <div className="space-y-3" data-testid="quote-comparison">
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs text-gray-500">
          {t("purchases.attachment.hint", "PDF, PNG ou JPEG · até 5 MB")}
        </span>
        <Button
          variant="outline"
          size="sm"
          onClick={() => setSortMode(NEXT_SORT[sortMode])}
          title={t("purchases.comparison.sortToggle", "Ordenar por total")}
        >
          <ArrowUpDown className="w-3.5 h-3.5 mr-1" />
          {t(SORT_LABEL_KEY[sortMode])}
        </Button>
      </div>

      {rejected && (
        <p
          role="alert"
          className="rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-700"
        >
          {rejected}
        </p>
      )}

      {/* Wide: suppliers across, facts down. */}
      {!isNarrow && (
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-left">
          <thead>
            <tr>
              <th className="w-44 border-b border-gray-200 p-2 text-xs font-semibold uppercase text-gray-500">
                {t("purchases.comparison.field", "Campo")}
              </th>
              {ordered.map((quote) => (
                <th
                  key={quote.id}
                  data-testid={`quote-row-${quote.id}`}
                  className={`border-b border-gray-200 p-2 align-top ${
                    quote.is_lowest_price ? "bg-emerald-50/60" : ""
                  }`}
                >
                  <div className="flex flex-wrap items-center gap-1 font-semibold text-gray-900">
                    {quote.supplier_name}
                    {badges(quote)}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {fixedRows.map((row) => (
              <tr key={row.key} className="border-b border-gray-100">
                <td className="p-2 text-xs font-semibold text-gray-600">
                  {row.label}
                </td>
                {ordered.map((quote) => (
                  <td
                    key={quote.id}
                    className={`p-2 text-sm ${
                      quote.is_lowest_price ? "bg-emerald-50/40" : ""
                    }`}
                  >
                    {row.render(quote)}
                  </td>
                ))}
              </tr>
            ))}

            {labels.length > 0 && (
              <tr>
                <td
                  colSpan={ordered.length + 1}
                  className="pt-4 pb-1 text-[11px] font-semibold uppercase text-gray-400"
                >
                  {t("purchases.comparison.extraFields", "Campos extras")}
                </td>
              </tr>
            )}
            {labels.map((label) => (
              <tr key={label} className="border-b border-gray-100">
                <td className="p-2 text-xs font-semibold text-gray-600">
                  {label}
                </td>
                {ordered.map((quote) => (
                  <td
                    key={quote.id}
                    className={`p-2 text-sm ${
                      quote.is_lowest_price ? "bg-emerald-50/40" : ""
                    }`}
                  >
                    {cell(valueOf(quote, label))}
                  </td>
                ))}
              </tr>
            ))}

            <tr>
              <td className="p-2 text-xs font-semibold text-gray-600">
                {t("purchases.comparison.actions", "Ações")}
              </td>
              {ordered.map((quote) => (
                <td key={quote.id} className="p-2">
                  {actions(quote)}
                </td>
              ))}
            </tr>
          </tbody>
        </table>
      </div>
      )}

      {/* Phone: one block per supplier, the same labels down the left. */}
      {isNarrow && (
      <div className="space-y-3">
        {ordered.map((quote) => (
          <div
            key={quote.id}
            data-testid={`quote-row-${quote.id}`}
            className={`rounded-lg border p-3 ${
              quote.is_lowest_price
                ? "border-emerald-300 bg-emerald-50/40"
                : "border-gray-200"
            }`}
          >
            <div className="flex flex-wrap items-center gap-1 text-sm font-semibold text-gray-900">
              {quote.supplier_name}
              {badges(quote)}
            </div>
            <dl className="mt-2 space-y-1">
              {fixedRows.map((row) => (
                <div
                  key={row.key}
                  className="flex justify-between gap-3 text-xs"
                >
                  <dt className="text-gray-500">{row.label}</dt>
                  <dd className="text-right text-gray-800">
                    {row.render(quote)}
                  </dd>
                </div>
              ))}
              {labels.map((label) => (
                <div key={label} className="flex justify-between gap-3 text-xs">
                  <dt className="text-gray-500">{label}</dt>
                  <dd className="text-right text-gray-800">
                    {cell(valueOf(quote, label))}
                  </dd>
                </div>
              ))}
            </dl>
            <div className="mt-2">{actions(quote)}</div>
          </div>
        ))}
      </div>
      )}
    </div>
  );
};

export default QuoteComparisonTable;
