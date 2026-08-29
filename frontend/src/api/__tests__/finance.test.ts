import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  getCategories,
  createCategory,
  updateCategory,
  getBudgetLines,
  createBudgetLine,
  updateBudgetLine,
  deleteBudgetLine,
  getTransactions,
  getTransactionById,
  createTransaction,
  updateTransaction,
  deleteTransaction,
  uploadInvoice,
  deleteInvoice,
  getCashBalance,
  getStatement,
  getBudgetVsActual,
  getCategoryTransactions,
} from "../finance";
import apiClient from "../client";

vi.mock("../client", () => ({
  default: { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() },
}));

describe("finance api client", () => {
  beforeEach(() => vi.clearAllMocks());

  describe("categories", () => {
    it("lists categories forwarding the filter params", async () => {
      vi.mocked(apiClient.get).mockResolvedValue({ data: [{ id: "c-1" }] });

      await expect(
        getCategories({ type: "EXPENSE", include_inactive: true }),
      ).resolves.toEqual([{ id: "c-1" }]);

      expect(apiClient.get).toHaveBeenCalledWith("/finance/categories", {
        params: { type: "EXPENSE", include_inactive: true },
      });
    });

    it("lists categories with no params when none are given", async () => {
      vi.mocked(apiClient.get).mockResolvedValue({ data: [] });

      await expect(getCategories()).resolves.toEqual([]);

      expect(apiClient.get).toHaveBeenCalledWith("/finance/categories", {
        params: undefined,
      });
    });

    it("creates a category", async () => {
      vi.mocked(apiClient.post).mockResolvedValue({ data: { id: "c-1" } });

      await expect(
        createCategory({ name: "Manutenção", type: "EXPENSE" }),
      ).resolves.toEqual({ id: "c-1" });

      expect(apiClient.post).toHaveBeenCalledWith("/finance/categories", {
        name: "Manutenção",
        type: "EXPENSE",
      });
    });

    it("updates a category by id", async () => {
      vi.mocked(apiClient.put).mockResolvedValue({ data: { id: "c-1" } });

      await expect(
        updateCategory("c-1", { name: "Obras", is_active: false }),
      ).resolves.toEqual({ id: "c-1" });

      expect(apiClient.put).toHaveBeenCalledWith("/finance/categories/c-1", {
        name: "Obras",
        is_active: false,
      });
    });
  });

  describe("budget lines", () => {
    it("lists budget lines for a fiscal year", async () => {
      vi.mocked(apiClient.get).mockResolvedValue({ data: [{ id: "b-1" }] });

      await expect(getBudgetLines(2026)).resolves.toEqual([{ id: "b-1" }]);

      expect(apiClient.get).toHaveBeenCalledWith("/finance/budget-lines", {
        params: { fiscal_year: 2026 },
      });
    });

    it("creates a budget line", async () => {
      vi.mocked(apiClient.post).mockResolvedValue({ data: { id: "b-1" } });

      await expect(
        createBudgetLine({
          category_id: "c-1",
          fiscal_year: 2026,
          planned_amount: 1500,
          notes: "orçado",
        }),
      ).resolves.toEqual({ id: "b-1" });

      expect(apiClient.post).toHaveBeenCalledWith("/finance/budget-lines", {
        category_id: "c-1",
        fiscal_year: 2026,
        planned_amount: 1500,
        notes: "orçado",
      });
    });

    it("updates a budget line by id", async () => {
      vi.mocked(apiClient.put).mockResolvedValue({ data: { id: "b-1" } });

      await expect(
        updateBudgetLine("b-1", { planned_amount: 2000 }),
      ).resolves.toEqual({ id: "b-1" });

      expect(apiClient.put).toHaveBeenCalledWith("/finance/budget-lines/b-1", {
        planned_amount: 2000,
      });
    });

    it("deletes a budget line by id", async () => {
      vi.mocked(apiClient.delete).mockResolvedValue({ data: undefined });

      await expect(deleteBudgetLine("b-1")).resolves.toBeUndefined();

      expect(apiClient.delete).toHaveBeenCalledWith("/finance/budget-lines/b-1");
    });
  });

  describe("transactions", () => {
    it("lists transactions forwarding every snake_case filter param", async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        data: { items: [], total: 0, skip: 0, limit: 20 },
      });

      await expect(
        getTransactions({
          type: "INCOME",
          category_id: "c-1",
          start_date: "2026-01-01",
          end_date: "2026-12-31",
          skip: 20,
          limit: 10,
        }),
      ).resolves.toEqual({ items: [], total: 0, skip: 0, limit: 20 });

      expect(apiClient.get).toHaveBeenCalledWith("/finance/transactions", {
        params: {
          type: "INCOME",
          category_id: "c-1",
          start_date: "2026-01-01",
          end_date: "2026-12-31",
          skip: 20,
          limit: 10,
        },
      });
    });

    it("lists transactions with no params when none are given", async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        data: { items: [], total: 0, skip: 0, limit: 20 },
      });

      await getTransactions();

      expect(apiClient.get).toHaveBeenCalledWith("/finance/transactions", {
        params: undefined,
      });
    });

    it("reads a single transaction by id", async () => {
      vi.mocked(apiClient.get).mockResolvedValue({ data: { id: "t-1" } });

      await expect(getTransactionById("t-1")).resolves.toEqual({ id: "t-1" });

      expect(apiClient.get).toHaveBeenCalledWith("/finance/transactions/t-1");
    });

    it("creates a transaction", async () => {
      vi.mocked(apiClient.post).mockResolvedValue({ data: { id: "t-1" } });

      await expect(
        createTransaction({
          type: "EXPENSE",
          category_id: "c-1",
          description: "Bomba d'água",
          amount: 350.5,
          transaction_date: "2026-03-02",
          payment_method: "PIX",
        }),
      ).resolves.toEqual({ id: "t-1" });

      expect(apiClient.post).toHaveBeenCalledWith("/finance/transactions", {
        type: "EXPENSE",
        category_id: "c-1",
        description: "Bomba d'água",
        amount: 350.5,
        transaction_date: "2026-03-02",
        payment_method: "PIX",
      });
    });

    it("updates a transaction by id", async () => {
      vi.mocked(apiClient.put).mockResolvedValue({ data: { id: "t-1" } });

      await expect(
        updateTransaction("t-1", { amount: 400 }),
      ).resolves.toEqual({ id: "t-1" });

      expect(apiClient.put).toHaveBeenCalledWith("/finance/transactions/t-1", {
        amount: 400,
      });
    });

    it("deletes a transaction by id", async () => {
      vi.mocked(apiClient.delete).mockResolvedValue({ data: undefined });

      await expect(deleteTransaction("t-1")).resolves.toBeUndefined();

      expect(apiClient.delete).toHaveBeenCalledWith("/finance/transactions/t-1");
    });

    it("uploads an invoice as multipart form data under the 'file' field", async () => {
      vi.mocked(apiClient.post).mockResolvedValue({ data: { id: "t-1" } });
      const file = new File(["nota"], "nota.pdf", { type: "application/pdf" });

      await expect(uploadInvoice("t-1", file)).resolves.toEqual({ id: "t-1" });

      const [path, body, config] = vi.mocked(apiClient.post).mock.calls[0];
      expect(path).toBe("/finance/transactions/t-1/invoice");
      expect(body).toBeInstanceOf(FormData);
      expect((body as FormData).get("file")).toBe(file);
      expect(config).toEqual({
        headers: { "Content-Type": "multipart/form-data" },
      });
    });

    it("deletes the invoice of a transaction", async () => {
      vi.mocked(apiClient.delete).mockResolvedValue({ data: undefined });

      await expect(deleteInvoice("t-1")).resolves.toBeUndefined();

      expect(apiClient.delete).toHaveBeenCalledWith(
        "/finance/transactions/t-1/invoice",
      );
    });
  });

  describe("reporting", () => {
    it("reads the cash balance at a given date", async () => {
      vi.mocked(apiClient.get).mockResolvedValue({ data: { balance: 10 } });

      await expect(getCashBalance("2026-06-30")).resolves.toEqual({
        balance: 10,
      });

      expect(apiClient.get).toHaveBeenCalledWith("/finance/balance", {
        params: { as_of: "2026-06-30" },
      });
    });

    it("omits the as_of param when no date is given", async () => {
      vi.mocked(apiClient.get).mockResolvedValue({ data: { balance: 10 } });

      await getCashBalance();

      expect(apiClient.get).toHaveBeenCalledWith("/finance/balance", {
        params: undefined,
      });
    });

    it("reads the statement for a date range", async () => {
      vi.mocked(apiClient.get).mockResolvedValue({ data: { entries: [] } });

      await expect(
        getStatement("2026-01-01", "2026-06-30"),
      ).resolves.toEqual({ entries: [] });

      expect(apiClient.get).toHaveBeenCalledWith("/finance/statement", {
        params: { start_date: "2026-01-01", end_date: "2026-06-30" },
      });
    });

    it("reads budget vs actual for a fiscal year", async () => {
      vi.mocked(apiClient.get).mockResolvedValue({ data: { rows: [] } });

      await expect(getBudgetVsActual(2026)).resolves.toEqual({ rows: [] });

      expect(apiClient.get).toHaveBeenCalledWith("/finance/budget-vs-actual", {
        params: { fiscal_year: 2026 },
      });
    });

    it("reads the transactions behind a budget-vs-actual category row", async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        data: { items: [], total: 0, skip: 0, limit: 50 },
      });

      await expect(
        getCategoryTransactions("c-1", 2026, { skip: 50, limit: 50 }),
      ).resolves.toEqual({ items: [], total: 0, skip: 0, limit: 50 });

      expect(apiClient.get).toHaveBeenCalledWith(
        "/finance/budget-vs-actual/c-1/transactions",
        { params: { fiscal_year: 2026, skip: 50, limit: 50 } },
      );
    });

    it("reads category transactions with only the fiscal year when no paging is given", async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        data: { items: [], total: 0, skip: 0, limit: 50 },
      });

      await getCategoryTransactions("c-1", 2026);

      expect(apiClient.get).toHaveBeenCalledWith(
        "/finance/budget-vs-actual/c-1/transactions",
        { params: { fiscal_year: 2026 } },
      );
    });
  });
});
