import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { QuoteComparisonTable } from "../components/QuoteComparisonTable";
import {
  attachmentRejectionKey,
  buildComparisonGrid,
  unionExtraFieldLabels,
} from "../utils/comparison";
import { QUOTE_ATTACHMENT_MAX_FILE_SIZE_BYTES } from "../../../api/purchases";
import type {
  PurchaseQuote,
  PurchaseQuoteItem,
  PurchaseRequestItem,
} from "../../../types/purchase";

/** The request's enumeration: the grid's rows, in `position` order. */
const requestItems: PurchaseRequestItem[] = [
  { id: "ri-lamp", description: "Luminárias LED", quantity: 12, position: 0 },
  { id: "ri-work", description: "Mão de obra", quantity: 1, position: 1 },
];

const lineOf = (
  overrides: Partial<PurchaseQuoteItem> & { id: string },
): PurchaseQuoteItem => ({
  request_item_id: null,
  model: null,
  unit_price: 100,
  description: "Item",
  quantity: 1,
  position: 0,
  line_total: 100,
  ...overrides,
});

const quoteOf = (overrides: Partial<PurchaseQuote>): PurchaseQuote => ({
  id: "q",
  purchase_request_id: "req-1",
  supplier_name: "Fornecedor",
  supplier_contact: null,
  items: [],
  quoted_item_count: 0,
  is_complete: true,
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
    items: [
      lineOf({
        id: "luz-lamp",
        request_item_id: "ri-lamp",
        model: "Philips BY698P",
        unit_price: 289.9,
        description: "Luminárias LED",
        quantity: 12,
        position: 0,
        line_total: 3478.8,
      }),
    ],
    quoted_item_count: 1,
    is_complete: false,
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
    items: [
      lineOf({
        id: "eletro-lamp",
        request_item_id: "ri-lamp",
        unit_price: 245,
        description: "Luminárias LED",
        quantity: 12,
        position: 0,
        line_total: 2940,
      }),
      lineOf({
        id: "eletro-work",
        request_item_id: "ri-work",
        unit_price: 0.01,
        description: "Mão de obra",
        quantity: 1,
        position: 1,
        line_total: 0.01,
      }),
      lineOf({
        id: "eletro-extra",
        request_item_id: null,
        description: "Descarte das antigas",
        quantity: 1,
        unit_price: 150,
        position: 2,
        line_total: 150,
      }),
    ],
    quoted_item_count: 2,
    is_complete: true,
    total_price: 2940,
    is_lowest_price: true,
    extra_fields: [{ label: "Prazo de entrega", value: "10 dias" }],
  }),
  quoteOf({
    id: "sul",
    supplier_name: "Sul Elétrica",
    items: [
      lineOf({
        id: "sul-lamp",
        request_item_id: "ri-lamp",
        unit_price: 300,
        description: "Luminárias LED",
        quantity: 12,
        position: 0,
        line_total: 3600,
      }),
    ],
    quoted_item_count: 1,
    is_complete: false,
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
      requestItems={requestItems}
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
        // APRAS-73: the header also carries the coverage of an
        // incomplete quote, which this assertion is not about.
        .replace(/Cobertura: \d+ de \d+ itens/, "")
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

describe("buildComparisonGrid", () => {
  it("puts the request lines first in position order, then the extras", () => {
    const rows = buildComparisonGrid(requestItems, quotes);

    expect(rows.map((row) => row.key)).toEqual([
      "ri-lamp",
      "ri-work",
      "eletro-extra",
    ]);
    expect(rows.map((row) => row.isExtra)).toEqual([false, false, true]);
    expect(rows[0].description).toBe("Luminárias LED");
    expect(rows[0].quantity).toBe(12);
  });

  it("leaves the cell undefined where a supplier priced nothing", () => {
    const rows = buildComparisonGrid(requestItems, quotes);

    // Every supplier priced the lamps; only Eletro Norte priced the labour.
    expect(Object.keys(rows[0].cells).sort()).toEqual(["eletro", "luz", "sul"]);
    expect(rows[1].cells.eletro?.id).toBe("eletro-work");
    expect(rows[1].cells.luz).toBeUndefined();
    expect(rows[1].cells.sul).toBeUndefined();
    // An extra line is filled only in the column of the quote that added it.
    expect(Object.keys(rows[2].cells)).toEqual(["eletro"]);
  });

  it("sorts the request lines by position, not by arrival", () => {
    const rows = buildComparisonGrid([...requestItems].reverse(), quotes);

    expect(rows.map((row) => row.key)).toEqual([
      "ri-lamp",
      "ri-work",
      "eletro-extra",
    ]);
  });

  it("is empty for a request with no lines and quotes with no extras", () => {
    expect(buildComparisonGrid([], [quoteOf({})])).toEqual([]);
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

  it("renders the items grid: one row per request line, extras beneath", () => {
    renderTable();

    expect(screen.getByText("12 × Luminárias LED")).toBeInTheDocument();
    expect(screen.getByText("1 × Mão de obra")).toBeInTheDocument();
    expect(screen.getByText("1 × Descarte das antigas")).toBeInTheDocument();
    expect(screen.getByText("Extra")).toBeInTheDocument();
    // D9 deleted the `Unitário × qtd.` row together with the single price.
    expect(screen.queryByText("Unitário × qtd.")).toBeNull();
  });

  it("renders `Não cotado` with data-quoted=false where a supplier skipped a line", () => {
    renderTable();

    const skipped = screen.getByTestId("grid-cell-ri-work-luz");
    expect(skipped).toHaveAttribute("data-quoted", "false");
    expect(skipped).toHaveTextContent("Não cotado");

    const priced = screen.getByTestId("grid-cell-ri-work-eletro");
    expect(priced).toHaveAttribute("data-quoted", "true");
    expect(priced).not.toHaveTextContent("Não cotado");
  });

  it("leaves an extra line's other columns empty rather than `Não cotado`", () => {
    renderTable();

    const foreign = screen.getByTestId("grid-cell-eletro-extra-luz");
    expect(foreign).toHaveAttribute("data-quoted", "false");
    expect(foreign).toHaveTextContent("");
  });

  it("renders no model element at all in a cell whose model is null", () => {
    renderTable();

    expect(
      within(screen.getByTestId("grid-cell-ri-lamp-luz")).getByText(
        "Philips BY698P",
      ),
    ).toBeInTheDocument();
    const withoutModel = screen.getByTestId("grid-cell-ri-lamp-eletro");
    expect(withoutModel).not.toHaveTextContent("—");
    expect(withoutModel.querySelectorAll("div")).toHaveLength(3);
  });

  it("shows the coverage of every incomplete quote and of no complete one", () => {
    renderTable();

    expect(screen.getByTestId("quote-coverage-luz")).toHaveTextContent(
      "Cobertura: 1 de 2 itens",
    );
    expect(screen.getByTestId("quote-coverage-sul")).toHaveTextContent(
      "Cobertura: 1 de 2 itens",
    );
    expect(screen.queryByTestId("quote-coverage-eletro")).toBeNull();
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

    // The same lines, once per card, with the per-card `Itens (N)` heading
    // and the skipped line still spelled out.
    const card = within(screen.getByTestId("quote-row-luz"));
    expect(card.getByText("Itens (3)")).toBeInTheDocument();
    expect(card.getByText("12 × Luminárias LED")).toBeInTheDocument();
    expect(card.getByTestId("grid-cell-ri-work-luz")).toHaveTextContent(
      "Não cotado",
    );
    expect(card.getByText("Cobertura: 1 de 2 itens")).toBeInTheDocument();
  });
});
