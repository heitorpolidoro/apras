import { beforeEach, describe, expect, it, vi } from "vitest";
import apiClient from "../../../api/client";
import {
  QUOTE_ATTACHMENT_ACCEPT,
  QUOTE_ATTACHMENT_ALLOWED_MIME_TYPES,
  QUOTE_ATTACHMENT_MAX_FILE_SIZE_BYTES,
  deleteQuoteAttachment,
  uploadQuoteAttachment,
} from "../../../api/purchases";

/**
 * What the quote-attachment client actually puts on the wire (APRAS-63).
 *
 * `api/purchases` is **deliberately not mocked**: only `api/client`, the
 * axios instance that is the last layer before the network. Every other test
 * in this feature mocks the API module wholesale, which cannot see a wrong
 * path, a missing `multipart/form-data` or a field named anything but
 * `file` — and FastAPI answers all three with a 422 the handler never sees.
 *
 * **This is one half of a two-sided pin**, the shape
 * `uploadContract.test.tsx` and `src/api/tenantProfile.ts` already use. The
 * backend half is
 * `backend/tests/test_purchase_quote_attachment.py::test_the_attachment_contract_matches_the_frontend_client`,
 * which reads `PurchaseService.ATTACHMENT_MAX_FILE_SIZE`,
 * `ATTACHMENT_ALLOWED_MIME_TYPES` and `ROUTE_PERMISSIONS`, and fails with
 * this file's name in the message.
 */

vi.mock("../../../api/client", () => ({
  default: { put: vi.fn(), delete: vi.fn() },
}));

const quote = { id: "quote-1" };

describe("the quote-attachment contract", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(apiClient.put).mockResolvedValue({ data: quote });
    vi.mocked(apiClient.delete).mockResolvedValue({ data: quote });
  });

  it("pins the cap, the accepted set and the derived accept attribute", () => {
    expect(QUOTE_ATTACHMENT_MAX_FILE_SIZE_BYTES).toBe(5 * 1024 * 1024);
    expect([...QUOTE_ATTACHMENT_ALLOWED_MIME_TYPES]).toEqual([
      "application/pdf",
      "image/png",
      "image/jpeg",
    ]);
    expect(QUOTE_ATTACHMENT_ACCEPT).toBe(
      "application/pdf,image/png,image/jpeg",
    );
    // WebP and SVG are outside the set on purpose (D2).
    expect(QUOTE_ATTACHMENT_ACCEPT).not.toContain("webp");
    expect(QUOTE_ATTACHMENT_ACCEPT).not.toContain("svg");
  });

  it("PUTs one multipart `file` to the attachment path", async () => {
    const file = new File(["%PDF-"], "orcamento.pdf", {
      type: "application/pdf",
    });

    const returned = await uploadQuoteAttachment("req-1", "quote-1", file);

    expect(returned).toBe(quote);
    const [path, body, config] = vi.mocked(apiClient.put).mock.calls[0];
    expect(path).toBe("/purchase-requests/req-1/quotes/quote-1/attachment");
    expect(body).toBeInstanceOf(FormData);
    // `append(name, file, file.name)` re-wraps, so identity is not the
    // claim: the field name, the file name and the type are.
    const sent = (body as FormData).get("file") as File;
    expect(sent.name).toBe("orcamento.pdf");
    expect(sent.type).toBe("application/pdf");
    expect(config?.headers?.["Content-Type"]).toBe("multipart/form-data");
  });

  it("DELETEs the same path and returns the quote", async () => {
    const returned = await deleteQuoteAttachment("req-1", "quote-1");

    expect(returned).toBe(quote);
    expect(apiClient.delete).toHaveBeenCalledWith(
      "/purchase-requests/req-1/quotes/quote-1/attachment",
    );
  });
});
