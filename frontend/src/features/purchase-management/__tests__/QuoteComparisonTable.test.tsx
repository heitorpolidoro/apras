import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { QuoteComparisonTable } from "../components/QuoteComparisonTable";
import {
  attachmentRejectionKey,
  unionExtraFieldLabels,
} from "../utils/comparison";
import { QUOTE_ATTACHMENT_MAX_FILE_SIZE_BYTES } from "../../../api/purchases";
import type { PurchaseQuote } from "../../../types/purchase";

const quoteOf = (overrides: Partial<PurchaseQuote>): PurchaseQuote => ({
  id: "q",
  purchase_request_id: "req-1",
  supplier_name: "Fornecedor",
  supplier_contact: null,
  unit_price: 100,
  quantity: 1,
  notes: null,
  extra_fields: [],
  attachment_url: null,
  attachment_filename: null,
  total_price: 100,
  created_by_id: "user-1",
  created_by_name: "Gerente",
  is_selected: false,
  is_lowest_price: false,
  created_at: "2026-09-01T00:00:00Z",
  updated_at: "2026-09-01T00:00:00Z",
  ...overrides,
});

/**
 * Three suppliers, deliberately *not* in total order, so "ordering by total
 * reorders the columns" is a visible change rather than a no-op, and with
 * partially overlapping `extra_fields` so the union and the dash both have
 * something to prove.
 */
const quotes: PurchaseQuote[] = [
  quoteOf({
    id: "luz",
    supplier_name: "Luz & Cia",
    supplier_contact: "(11) 3333-0000",
    unit_price: 289.9,
    quantity: 12,
    total_price: 3478.8,
    notes: "Instalação inclusa",
    extra_fields: [
      { label: "Prazo de entrega", value: "20 dias" },
      { label: "Garantia", value: "36 meses" },
    ],
  }),
  quoteOf({
    id: "eletro",
    supplier_name: "Eletro Norte",
    unit_price: 245,
    quantity: 12,
    total_price: 2940,
    is_lowest_price: true,
    extra_fields: [{ label: "Prazo de entrega", value: "10 dias" }],
  }),
  quoteOf({
    id: "sul",
    supplier_name: "Sul Elétrica",
    unit_price: 300,
    quantity: 12,
    total_price: 3600,
    is_selected: true,
    extra_fields: [{ label: "Frete", value: "Grátis" }],
  }),
];

const handlers = () => ({
  onChoose: vi.fn(),
  onEdit: vi.fn(),
  onDelete: vi.fn(),
  onUpload: vi.fn(),
  onRemoveAttachment: vi.fn(),
});

const renderTable = (
  props: Partial<React.ComponentProps<typeof QuoteComparisonTable>> = {},
) => {
  const spies = handlers();
  render(
    <QuoteComparisonTable
      quotes={quotes}
      canChoose
      quotesEditable
      canEditQuotes
      {...spies}
      {...props}
    />,
  );
  return spies;
};

/** The supplier names in the order the columns are laid out, with the two
 *  badges stripped so the assertion is about order and nothing else. */
const supplierOrder = () =>
  screen
    .getAllByTestId(/quote-row-/)
    .map((element) =>
      (element.textContent ?? "")
        .replace("Menor preço", "")
        .replace("Escolhido", "")
        .trim(),
    );

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("unionExtraFieldLabels", () => {
  it("is the union across quotes, in first-seen order and without repeats", () => {
    expect(unionExtraFieldLabels(quotes)).toEqual([
      "Prazo de entrega",
      "Garantia",
      "Frete",
    ]);
  });

  it("is empty when no quote carries an extra field", () => {
    expect(unionExtraFieldLabels([quoteOf({})])).toEqual([]);
  });
});

describe("attachmentRejectionKey", () => {
  it("refuses a type outside the accepted set", () => {
    const file = new File(["x"], "planilha.xlsx", {
      type: "application/vnd.ms-excel",
    });
    expect(attachmentRejectionKey(file)).toBe("purchases.attachment.invalidType");
  });

  it("refuses an accepted type above the 5 MiB cap", () => {
    const file = new File(["x"], "grande.pdf", { type: "application/pdf" });
    Object.defineProperty(file, "size", {
      value: QUOTE_ATTACHMENT_MAX_FILE_SIZE_BYTES + 1,
    });
    expect(attachmentRejectionKey(file)).toBe("purchases.attachment.tooLarge");
  });

  it("accepts a small PDF, PNG and JPEG", () => {
    for (const type of ["application/pdf", "image/png", "image/jpeg"]) {
      expect(attachmentRejectionKey(new File(["x"], "f", { type }))).toBeNull();
    }
  });
});

describe("QuoteComparisonTable", () => {
  it("renders one column per supplier and one row per union label", () => {
    renderTable();

    expect(screen.getAllByTestId(/quote-row-/)).toHaveLength(3);
    for (const label of ["Prazo de entrega", "Garantia", "Frete"]) {
      expect(screen.getByText(label)).toBeInTheDocument();
    }
    expect(screen.getByText("20 dias")).toBeInTheDocument();
    expect(screen.getByText("10 dias")).toBeInTheDocument();
  });

  it("renders an explicit dash, never a blank, where a supplier filled nothing", () => {
    renderTable();

    // Eletro Norte and Sul Elétrica have no "Garantia"; Luz & Cia does.
    // Two quotes have no contact and two have no notes, and every quote is
    // missing at least one extra label.
    const dashes = screen.getAllByTitle("Não informado por este fornecedor");
    expect(dashes.length).toBeGreaterThan(0);
    for (const dash of dashes) {
      expect(dash).toHaveTextContent("—");
    }
  });

  it("marks the lowest total and the chosen quote with their badges", () => {
    renderTable();

    const lowest = screen.getByTestId("quote-row-eletro");
    expect(within(lowest).getByText("Menor preço")).toBeInTheDocument();
    expect(
      within(screen.getByTestId("quote-row-sul")).getByText("Escolhido"),
    ).toBeInTheDocument();
    expect(
      within(screen.getByTestId("quote-row-luz")).queryByText("Menor preço"),
    ).toBeNull();
  });

  it("orders the columns by total and restores the source order on the third click", () => {
    renderTable();

    expect(supplierOrder()).toEqual([
      "Luz & Cia",
      "Eletro Norte",
      "Sul Elétrica",
    ]);

    const toggle = screen.getByTitle("Ordenar por total");
    fireEvent.click(toggle);
    expect(supplierOrder()).toEqual([
      "Eletro Norte",
      "Luz & Cia",
      "Sul Elétrica",
    ]);

    fireEvent.click(toggle);
    expect(supplierOrder()).toEqual([
      "Sul Elétrica",
      "Luz & Cia",
      "Eletro Norte",
    ]);

    fireEvent.click(toggle);
    expect(supplierOrder()).toEqual([
      "Luz & Cia",
      "Eletro Norte",
      "Sul Elétrica",
    ]);
  });

  it("uploads an accepted file and issues no request for a refused one", () => {
    const spies = renderTable();
    const input = screen.getByTestId("attachment-input-eletro");

    const refused = new File(["x"], "planilha.xlsx", { type: "text/plain" });
    fireEvent.change(input, { target: { files: [refused] } });

    expect(spies.onUpload).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toHaveTextContent(
      "planilha.xlsx não foi enviado.",
    );
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Formato não aceito. Envie PDF, PNG ou JPEG com até 5 MB.",
    );

    const tooBig = new File(["x"], "enorme.pdf", { type: "application/pdf" });
    Object.defineProperty(tooBig, "size", {
      value: QUOTE_ATTACHMENT_MAX_FILE_SIZE_BYTES + 1,
    });
    fireEvent.change(input, { target: { files: [tooBig] } });
    expect(spies.onUpload).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Arquivo acima de 5 MB. Envie PDF, PNG ou JPEG com até 5 MB.",
    );

    const accepted = new File(["%PDF-"], "orcamento.pdf", {
      type: "application/pdf",
    });
    fireEvent.change(input, { target: { files: [accepted] } });
    expect(spies.onUpload).toHaveBeenCalledWith(
      expect.objectContaining({ id: "eletro" }),
      accepted,
    );
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("ignores a picker that was dismissed without choosing a file", () => {
    const spies = renderTable();
    fireEvent.change(screen.getByTestId("attachment-input-eletro"), {
      target: { files: [] },
    });
    expect(spies.onUpload).not.toHaveBeenCalled();
  });

  it("links a stored document and offers replace and remove to an editor", () => {
    const spies = renderTable({
      quotes: [
        quoteOf({
          id: "eletro",
          supplier_name: "Eletro Norte",
          attachment_url: "/static/uploads/2026/09/abc.pdf",
          attachment_filename: "orcamento-eletro-norte.pdf",
        }),
      ],
    });

    const link = screen.getByRole("link", {
      name: /orcamento-eletro-norte\.pdf/,
    });
    expect(link).toHaveAttribute("href", "/static/uploads/2026/09/abc.pdf");
    expect(link).toHaveAttribute("target", "_blank");

    fireEvent.click(screen.getByTitle("Remover"));
    expect(spies.onRemoveAttachment).toHaveBeenCalledWith(
      expect.objectContaining({ id: "eletro" }),
    );
    expect(screen.getByTitle("Substituir")).toBeInTheDocument();
  });

  it("shows the link but no upload control once the quotes are frozen", () => {
    renderTable({
      quotesEditable: false,
      quotes: [
        quoteOf({
          id: "eletro",
          attachment_url: "/static/uploads/2026/09/abc.pdf",
          attachment_filename: "orcamento.pdf",
        }),
      ],
    });

    expect(
      screen.getByRole("link", { name: /orcamento\.pdf/ }),
    ).toBeInTheDocument();
    expect(screen.queryByTitle("Anexar documento")).toBeNull();
    expect(screen.queryByTitle("Substituir")).toBeNull();
    expect(screen.queryByTitle("Remover")).toBeNull();
    expect(screen.getByText("somente leitura")).toBeInTheDocument();
  });

  it("renders no upload control for a caller without purchases:quote_update", () => {
    renderTable({ canEditQuotes: false });

    expect(screen.queryByTitle("Anexar documento")).toBeNull();
    expect(screen.queryAllByTestId(/attachment-input-/)).toHaveLength(0);
  });

  it("renders no choose control when the caller may not decide", () => {
    renderTable({ canChoose: false });
    expect(screen.queryAllByTitle("Escolher este Orçamento")).toHaveLength(0);
    // …and still shows the comparison itself.
    expect(screen.getAllByTestId(/quote-row-/)).toHaveLength(3);
  });

  it("wires choose, edit and delete to their handlers", () => {
    const spies = renderTable();

    fireEvent.click(screen.getAllByTitle("Escolher este Orçamento")[0]);
    fireEvent.click(screen.getAllByTitle("Editar Orçamento")[0]);
    fireEvent.click(screen.getAllByTitle("Excluir Orçamento")[0]);

    expect(spies.onChoose).toHaveBeenCalledWith(
      expect.objectContaining({ id: "luz" }),
    );
    expect(spies.onEdit).toHaveBeenCalledWith(
      expect.objectContaining({ id: "luz" }),
    );
    expect(spies.onDelete).toHaveBeenCalledWith(
      expect.objectContaining({ id: "luz" }),
    );
  });

  it("transposes into one block per supplier below the md breakpoint", () => {
    const listeners: Array<() => void> = [];
    vi.stubGlobal(
      "matchMedia",
      vi.fn(() => ({
        matches: true,
        addEventListener: (_: string, cb: () => void) => listeners.push(cb),
        removeEventListener: vi.fn(),
      })),
    );

    renderTable();

    // Still one element per supplier, so the `quote-row-` assertions keep
    // meaning — but there is no table any more.
    expect(screen.getAllByTestId(/quote-row-/)).toHaveLength(3);
    expect(document.querySelector("table")).toBeNull();
    expect(
      within(screen.getByTestId("quote-row-luz")).getByText("Garantia"),
    ).toBeInTheDocument();
  });
});
