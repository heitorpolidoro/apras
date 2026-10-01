import { describe, it, expect, vi, afterEach } from "vitest";
import {
  listObrasFromReport,
  buildObraPrintDocument,
  openObraPrintWindow,
  PRINT_BREAK_CLASS,
} from "../lib/obraPrintDocument";
import {
  TWO_OBRA_REPORT,
  ONE_OBRA_REPORT,
  NO_OBRA_REPORT,
  NO_KIND_REPORT,
  NO_KICKER_REPORT,
  OBRA_ONE_TITLE,
  OBRA_TWO_TITLE,
  OBRA_ONE_KIND,
  OBRA_TWO_KIND,
  FIXTURE_HEAD_AT_PAGE_COUNT,
} from "./fixtures/obraReportFixture";

/**
 * APRAS-118 — the client-side split of the backend's report into one printable
 * obra. Every assertion here runs against the fixture derived from
 * `backend/tests/data`, so the selectors are the backend's real ones.
 */

const parse = (html: string): Document =>
  new DOMParser().parseFromString(html, "text/html");

afterEach(() => {
  vi.restoreAllMocks();
});

describe("listObrasFromReport", () => {
  it("reads one entry per div.page, titled from the hero", () => {
    expect(listObrasFromReport(TWO_OBRA_REPORT)).toEqual([
      { index: 0, title: OBRA_ONE_TITLE, kind: OBRA_ONE_KIND },
      { index: 1, title: OBRA_TWO_TITLE, kind: OBRA_TWO_KIND },
    ]);
  });

  it("reads the kind from the hero's own kicker, not the masthead's", () => {
    // Each `div.page` carries FOUR `.kicker` elements and the masthead's is
    // first in document order, so a bare `page.querySelector(".kicker")` reads
    // `Obras em foco` for every obra. Asserting the two kinds DIFFER is what
    // catches that: through the masthead they would be identical.
    const [first, second] = listObrasFromReport(TWO_OBRA_REPORT);
    expect(first.kind).not.toBe(second.kind);
    expect(first.kind).toBe(OBRA_ONE_KIND);
    expect(second.kind).toBe(OBRA_TWO_KIND);
    for (const obra of [first, second]) {
      expect(obra.kind).not.toContain("Obras em foco");
      expect(obra.kind).not.toContain("Desenvolvimento");
      expect(obra.kind).not.toContain("Acompanhamento visual");
    }
  });

  it("yields an empty kind when the hero's kicker carries none", () => {
    // `Obra 01` with no `•`: the ordinal is already the row's position, so there
    // is nothing to show beside the title.
    expect(listObrasFromReport(NO_KIND_REPORT)).toEqual([
      { index: 0, title: OBRA_ONE_TITLE, kind: "" },
    ]);
  });

  it("reads a hero that carries no kicker element at all", () => {
    // The companion to the case above, and not a duplicate of it:
    // `NO_KIND_REPORT` has a kicker without the `•`, so the selector finds a
    // node and only the separator is missing. Here the element is absent, so the
    // selector returns null -- the one route to `text`'s own null branch, which
    // every other case in this file reaches with a real node.
    //
    // The title is asserted alongside the empty kind on purpose: it proves the
    // page was parsed and matched, so the `""` is a kind that was looked for and
    // not found, rather than the silence of a page nothing read.
    expect(listObrasFromReport(NO_KICKER_REPORT)).toEqual([
      { index: 0, title: OBRA_ONE_TITLE, kind: "" },
    ]);
  });

  it("returns one entry for a single-obra report and none for an empty one", () => {
    expect(listObrasFromReport(ONE_OBRA_REPORT)).toHaveLength(1);
    expect(listObrasFromReport(NO_OBRA_REPORT)).toHaveLength(0);
  });
});

describe("buildObraPrintDocument", () => {
  it("carries only the chosen obra", () => {
    const built = buildObraPrintDocument(TWO_OBRA_REPORT, 1);

    expect(built).toContain(OBRA_TWO_TITLE);
    expect(built).not.toContain(OBRA_ONE_TITLE);
    expect(parse(built).querySelectorAll("div.page")).toHaveLength(1);
  });

  it("drops the collapsible stage-detail section the report shows on screen", () => {
    // The presence half first: `CSS_BODY`'s second `@media print` block carries
    // `details.all:not([open])>.inner { display:block }`, so the section the
    // screen shows collapsed at 15.0mm prints expanded at 1771mm. Without this
    // half the absence below would pass on a fixture that never had it.
    expect(
      parse(TWO_OBRA_REPORT).querySelectorAll("details.all").length,
    ).toBeGreaterThan(0);

    const built = parse(buildObraPrintDocument(TWO_OBRA_REPORT, 1));
    expect(built.querySelectorAll("details.all")).toHaveLength(0);
  });

  it("does no sheet-size work: no @page is added and none is rewritten", () => {
    const built = buildObraPrintDocument(TWO_OBRA_REPORT, 1);
    const rules = built.match(/@page[^}]*}/g) ?? [];

    // (a) nothing INJECTED — the count is the fixture head's own, counted from
    // the backend's pinned stylesheet rather than written down here.
    expect(rules).toHaveLength(FIXTURE_HEAD_AT_PAGE_COUNT);
    // (b) nothing REWRITTEN. Matched on `size:A4` and deliberately NOT on the
    // absence of `size: 210mm`: a height rewritten in this stylesheet's own
    // space-free house style would slip past that form untouched.
    expect(rules.length).toBeGreaterThan(0);
    for (const rule of rules) {
      expect(rule).toContain("size:A4");
    }
  });

  it("leaves exactly one forced break, on the budget section", () => {
    // Built from index 1 on purpose: index 0 never carried `brk`, so the same
    // assertion at index 0 is the no-op version of this test.
    const built = parse(buildObraPrintDocument(TWO_OBRA_REPORT, 1));

    const budget = built.querySelector(".budget-col")?.closest("section");
    expect(budget).not.toBeNull();

    // Every element the cloned stylesheet or the appended rule would break
    // before: the appended class, a surviving `page brk`, and any adjacent
    // `.page` sibling.
    const broken = Array.from(
      built.querySelectorAll(`.${PRINT_BREAK_CLASS}, .page.brk, .page + .page`),
    );
    expect(broken).toHaveLength(1);
    expect(broken[0]).toBe(budget);

    const page = built.querySelector("div.page");
    expect(page?.classList.contains("brk")).toBe(false);
    expect(page?.classList.contains(PRINT_BREAK_CLASS)).toBe(false);

    // And the stages section is not where the break went.
    const stages = built.querySelector(".grp")?.closest("section");
    expect(stages).not.toBeNull();
    expect(stages).not.toBe(budget);
    expect(stages?.classList.contains(PRINT_BREAK_CLASS)).toBe(false);
  });

  it("carries no script of its own", () => {
    const built = buildObraPrintDocument(TWO_OBRA_REPORT, 1);
    expect(built).not.toContain("<script");
    expect(parse(built).querySelectorAll("script")).toHaveLength(0);
  });

  it("refuses an index the report has no page for", () => {
    expect(() => buildObraPrintDocument(TWO_OBRA_REPORT, 2)).toThrow();
    expect(() => buildObraPrintDocument(NO_OBRA_REPORT, 0)).toThrow();
  });
});

describe("openObraPrintWindow", () => {
  /**
   * The fake opened window. `document` is present but carries **no `fonts`** —
   * the implementation awaits `w.document.fonts.ready` where available, and a
   * stub that supplied a ready-resolving `fonts` would exercise the happy path
   * while leaving the guard untested; one that supplied nothing at all would
   * throw inside the implementation instead of asserting. Omitting `fonts` on a
   * present `document` is what runs the guard.
   */
  const fakeWindow = () => {
    const listeners: Record<string, (() => void)[]> = {};
    return {
      document: {},
      print: vi.fn(),
      addEventListener: vi.fn((event: string, handler: () => void) => {
        (listeners[event] ??= []).push(handler);
      }),
      fire: (event: string) => {
        for (const handler of listeners[event] ?? []) handler();
      },
    };
  };

  it("opens a top-level blob document and lets the OPENER print it", async () => {
    const opened = fakeWindow();
    const createObjectURL = vi
      .spyOn(URL, "createObjectURL")
      .mockReturnValue("blob:print-one-obra");
    const open = vi
      .spyOn(window, "open")
      .mockReturnValue(opened as unknown as Window);

    openObraPrintWindow(TWO_OBRA_REPORT, 1);

    expect(createObjectURL).toHaveBeenCalledTimes(1);
    const blob = createObjectURL.mock.calls[0][0] as Blob;
    expect(blob.type).toBe("text/html");
    expect(await blob.text()).toContain(OBRA_TWO_TITLE);
    expect(await blob.text()).not.toContain(OBRA_ONE_TITLE);
    expect(open).toHaveBeenCalledWith("blob:print-one-obra", "_blank");

    // Not before load: the document is script-free, so nothing else could
    // print it, and printing an unloaded window prints nothing.
    expect(opened.print).not.toHaveBeenCalled();
    opened.fire("load");
    await vi.waitFor(() => {
      expect(opened.print).toHaveBeenCalledTimes(1);
    });
  });

  it("returns null when the popup is blocked, without throwing", () => {
    vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:blocked");
    vi.spyOn(window, "open").mockReturnValue(null);

    expect(openObraPrintWindow(ONE_OBRA_REPORT, 0)).toBeNull();
  });

  it("waits for the new window's webfonts when it has them", async () => {
    // The companion to the test above, whose stub omits `document.fonts` to
    // exercise the guard. This one supplies a `fonts` whose `ready` is still
    // pending, and asserts nothing prints until it settles — the reason the wait
    // is there at all is that printing before DM Sans swaps in prints the
    // fallback face.
    let settle: () => void = () => undefined;
    const ready = new Promise<void>((resolve) => {
      settle = resolve;
    });
    const opened = fakeWindow() as ReturnType<typeof fakeWindow> & {
      document: { fonts?: { ready: Promise<void> } };
    };
    opened.document.fonts = { ready };

    vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:with-fonts");
    vi.spyOn(window, "open").mockReturnValue(opened as unknown as Window);

    openObraPrintWindow(ONE_OBRA_REPORT, 0);
    opened.fire("load");

    await Promise.resolve();
    expect(opened.print).not.toHaveBeenCalled();

    settle();
    await vi.waitFor(() => {
      expect(opened.print).toHaveBeenCalledTimes(1);
    });
  });

  it("swallows a print() that throws because the window was closed", async () => {
    // `print()` throws on a window the user closed while the fonts were still
    // settling, and that rejects the chain inside the load listener. The
    // `.catch` on it is therefore reachable code, not a linter concession.
    //
    // The assertion is a real one, not the absence of a crash: an unhandled
    // rejection is captured from `process` and asserted empty. Relying on
    // Vitest's own unhandled-error report would be the shape this project keeps
    // shipping -- a test that passes while its subject throws, red only because
    // something outside the test noticed.
    const rejections: unknown[] = [];
    const record = (reason: unknown) => rejections.push(reason);
    process.on("unhandledRejection", record);

    try {
      const opened = fakeWindow();
      const closed = new Error("window closed");
      opened.print.mockImplementation(() => {
        throw closed;
      });
      vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:closed-window");
      vi.spyOn(window, "open").mockReturnValue(opened as unknown as Window);

      const handle = openObraPrintWindow(ONE_OBRA_REPORT, 0);
      expect(handle).toBe(opened as unknown as Window);

      opened.fire("load");

      // Positive anchor first: the chain did reach `print()` and it did throw.
      // Without this, the emptiness below would also hold for a chain that
      // never ran at all.
      await vi.waitFor(() => {
        expect(opened.print).toHaveBeenCalledTimes(1);
      });
      expect(opened.print.mock.results[0]).toEqual({
        type: "throw",
        value: closed,
      });

      // A macrotask, because Node decides a rejection is unhandled only after
      // the microtask queue has drained.
      await new Promise((resolve) => setTimeout(resolve, 0));
      expect(rejections).toEqual([]);
    } finally {
      process.off("unhandledRejection", record);
    }
  });
});
