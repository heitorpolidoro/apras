import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { FileText, FileX2 } from "lucide-react";
import { useCategoryTransactions } from "../../../hooks/useFinance";
import { InvoicePreviewModal } from "./InvoicePreviewModal";

interface CategoryTransactionDrilldownProps {
  categoryId: string;
  fiscalYear: number;
}

const formatCurrency = (value: number): string =>
  value.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

export const CategoryTransactionDrilldown: React.FC<
  CategoryTransactionDrilldownProps
> = ({ categoryId, fiscalYear }) => {
  const { t } = useTranslation();
  const { data, isLoading } = useCategoryTransactions(categoryId, fiscalYear);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  if (isLoading) {
    return (
      <p className="text-sm text-slate-500 dark:text-slate-400 py-3">
        {t("common.loading", "Carregando...")}
      </p>
    );
  }

  const transactions = data?.items ?? [];

  if (transactions.length === 0) {
    return (
      <p className="text-sm text-slate-500 dark:text-slate-400 py-3">
        {t("finance.drilldown.empty", "Nenhuma transação neste período.")}
      </p>
    );
  }

  return (
    <>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
            <th className="py-1.5">{t("finance.drilldown.date", "Data")}</th>
            <th className="py-1.5">
              {t("finance.drilldown.description", "Descrição")}
            </th>
            <th className="py-1.5 text-right">
              {t("finance.drilldown.amount", "Valor")}
            </th>
            <th className="py-1.5 text-center">
              {t("finance.drilldown.invoice", "Nota Fiscal")}
            </th>
          </tr>
        </thead>
        <tbody>
          {transactions.map((txn) => (
            <tr key={txn.id} className="border-t border-slate-100 dark:border-slate-800">
              <td className="py-1.5">{txn.transaction_date}</td>
              <td className="py-1.5">{txn.description}</td>
              <td className="py-1.5 text-right">{formatCurrency(txn.amount)}</td>
              <td className="py-1.5 text-center">
                {txn.invoice_file_url ? (
                  <button
                    type="button"
                    aria-label={t("finance.drilldown.viewInvoice", "Ver nota fiscal")}
                    onClick={() => setPreviewUrl(txn.invoice_file_url as string)}
                    className="inline-flex items-center justify-center p-1.5 rounded-md text-indigo-600 hover:bg-indigo-50 dark:hover:bg-indigo-950 transition-colors"
                  >
                    <FileText className="h-4 w-4" />
                  </button>
                ) : (
                  <span
                    title={t(
                      "finance.drilldown.noInvoice",
                      "Nenhuma nota fiscal anexada"
                    )}
                    className="inline-flex items-center justify-center p-1.5 text-slate-300 dark:text-slate-700"
                  >
                    <FileX2 className="h-4 w-4" />
                  </span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <InvoicePreviewModal
        isOpen={Boolean(previewUrl)}
        onClose={() => setPreviewUrl(null)}
        invoiceUrl={previewUrl}
      />
    </>
  );
};
