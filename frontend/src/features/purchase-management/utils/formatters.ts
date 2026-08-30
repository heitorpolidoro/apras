/** Shared display helpers for the purchase-quotation feature (APRAS-37). */

export const formatCurrency = (value: number | null | undefined): string => {
  if (value === null || value === undefined) return "—";
  return value.toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
  });
};

export const formatDateTime = (value: string | null | undefined): string => {
  if (!value) return "—";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "—";
  return parsed.toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
};
