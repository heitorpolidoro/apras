import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AttachmentUploader } from "../components/AttachmentUploader";
import { uploadPhoto, deletePhoto } from "../../../api/uploads";
import { useMyPermissions } from "../../../hooks/usePermissionQueries";
import { settledPermissions } from "../../../test/permissionFixtures";

/**
 * The flow, with `api/uploads` mocked wholesale — the wire contract is the
 * other file (`uploadContract.test.tsx`), which mocks only `api/client`.
 *
 * Every case here is **counted**, not eyeballed: a client-side pre-check that
 * refuses a file has to be proved by `uploadPhoto` never being called, because
 * a DOM that shows an error while a request is in flight looks identical.
 */

vi.mock("../../../api/uploads", async () => {
  const actual =
    await vi.importActual<typeof import("../../../api/uploads")>(
      "../../../api/uploads",
    );
  return { ...actual, uploadPhoto: vi.fn(), deletePhoto: vi.fn() };
});

vi.mock("../../../hooks/usePermissionQueries", () => ({
  useMyPermissions: vi.fn(),
  usePermissionCatalogue: vi.fn(() => ({ data: [], isPending: false })),
}));

/** §3.6(a): explicit lists, because the legacy RESIDENT bundle already holds
 *  `uploads:photo_create` and therefore cannot express the denied branch. */
const RESIDENT_WITH_ATTACHMENTS = [
  "infractions:contest",
  "infractions:my_lots_read",
  "uploads:photo_create",
];
const RESIDENT_WITHOUT_ATTACHMENTS = [
  "infractions:contest",
  "infractions:my_lots_read",
];

const asPersona = (permissions: readonly string[]) =>
  vi.mocked(useMyPermissions).mockReturnValue(
    settledPermissions(permissions) as never,
  );

const file = (name: string, type: string, size: number): File => {
  const created = new File(["x"], name, { type });
  Object.defineProperty(created, "size", { value: size });
  return created;
};

const asset = (url: string) => ({ url, id: url, status: "PENDING_APPROVAL" });

type UploaderProps = React.ComponentProps<typeof AttachmentUploader>;

const renderUploader = (props: Partial<UploaderProps> = {}) =>
  render(
    <QueryClientProvider
      client={
        new QueryClient({
          defaultOptions: { queries: { retry: false, gcTime: 0 } },
        })
      }
    >
      <AttachmentUploader
        value={[]}
        onChange={vi.fn()}
        label="Anexos"
        {...props}
      />
    </QueryClientProvider>,
  );

const choose = (files: File[]) =>
  fireEvent.change(screen.getByTestId("attachment-file-input"), {
    target: { files },
  });

describe("AttachmentUploader", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    asPersona(RESIDENT_WITH_ATTACHMENTS);
  });

  it("uploads every chosen file in order and reports the URLs once", async () => {
    const onChange = vi.fn();
    vi.mocked(uploadPhoto)
      .mockResolvedValueOnce(asset("/static/uploads/2026/09/a.png") as never)
      .mockResolvedValueOnce(asset("/static/uploads/2026/09/b.png") as never);

    renderUploader({ onChange, entityId: "inf-1" });
    choose([
      file("a.png", "image/png", 1024),
      file("b.png", "image/png", 2048),
    ]);

    await waitFor(() => expect(onChange).toHaveBeenCalled());
    expect(vi.mocked(uploadPhoto)).toHaveBeenCalledTimes(2);
    expect(onChange).toHaveBeenCalledWith([
      "/static/uploads/2026/09/a.png",
      "/static/uploads/2026/09/b.png",
    ]);
  });

  it("renders one chip per URL already attached", () => {
    renderUploader({ value: ["/static/uploads/2026/09/a.png"] });

    expect(screen.getAllByTestId("attachment-chip")).toHaveLength(1);
    expect(screen.getByAltText("Anexo 1")).toHaveAttribute(
      "src",
      "/static/uploads/2026/09/a.png",
    );
  });

  it("refuses a file over the endpoint's limit without calling the endpoint", async () => {
    renderUploader();
    choose([file("huge.png", "image/png", 6 * 1024 * 1024)]);

    expect(await screen.findByTestId("attachment-error")).toHaveTextContent(
      /huge\.png/,
    );
    // Measured, not inferred: the pre-check exists to save the round trip.
    expect(vi.mocked(uploadPhoto).mock.calls).toHaveLength(0);
  });

  it("refuses a MIME type outside ALLOWED_MIME_TYPES without calling the endpoint", async () => {
    renderUploader();
    choose([file("laudo.pdf", "application/pdf", 1024)]);

    expect(await screen.findByTestId("attachment-error")).toHaveTextContent(
      /laudo\.pdf/,
    );
    expect(vi.mocked(uploadPhoto).mock.calls).toHaveLength(0);
  });

  it("renders the server's 400 size refusal verbatim", async () => {
    vi.mocked(uploadPhoto).mockRejectedValue({
      response: {
        status: 400,
        data: { detail: "Arquivo excede o limite máximo permitido de 5MB." },
      },
    });

    renderUploader();
    choose([file("ok.png", "image/png", 1024)]);

    expect(await screen.findByTestId("attachment-error")).toHaveTextContent(
      "Arquivo excede o limite máximo permitido de 5MB.",
    );
  });

  it("renders the server's 400 format refusal verbatim", async () => {
    // The corrupted-bytes door: MIME is right, Pillow still refuses. A client
    // pre-check cannot cover this, which is why the refusal is rendered.
    vi.mocked(uploadPhoto).mockRejectedValue({
      response: {
        status: 400,
        data: {
          detail:
            "Formato de imagem inválido. Formatos aceitos: JPEG, PNG, WebP.",
        },
      },
    });

    renderUploader();
    choose([file("corrupt.png", "image/png", 1024)]);

    expect(await screen.findByTestId("attachment-error")).toHaveTextContent(
      "Formato de imagem inválido. Formatos aceitos: JPEG, PNG, WebP.",
    );
  });

  it("renders the 403 of a permission revoked between load and click, and creates no chip", async () => {
    const onChange = vi.fn();
    vi.mocked(uploadPhoto).mockRejectedValue({
      response: {
        status: 403,
        data: { detail: "The user doesn't have enough privileges" },
      },
    });

    renderUploader({ onChange });
    choose([file("ok.png", "image/png", 1024)]);

    expect(await screen.findByTestId("attachment-error")).toHaveTextContent(
      "The user doesn't have enough privileges",
    );
    expect(onChange).not.toHaveBeenCalled();
    expect(screen.queryByTestId("attachment-chip")).not.toBeInTheDocument();
  });

  it("shows the denied branch, and nothing clickable, without the permission", () => {
    asPersona(RESIDENT_WITHOUT_ATTACHMENTS);

    renderUploader();

    expect(screen.getByTestId("attachment-unavailable")).toHaveTextContent(
      "Anexos indisponíveis para o seu perfil.",
    );
    expect(screen.queryByTestId("attachment-file-input")).not.toBeInTheDocument();
    expect(vi.mocked(uploadPhoto).mock.calls).toHaveLength(0);
  });

  it("shows the loading placeholder and neither branch while /permissions/me is pending", () => {
    vi.mocked(useMyPermissions).mockReturnValue({
      data: undefined,
      isPending: true,
      isError: false,
    } as never);

    renderUploader();

    expect(screen.getByTestId("attachment-gate-loading")).toBeInTheDocument();
    expect(screen.queryByTestId("attachment-file-input")).not.toBeInTheDocument();
    expect(screen.queryByTestId("attachment-unavailable")).not.toBeInTheDocument();
  });

  it("removes a chip from the list without deleting the stored asset", () => {
    const onChange = vi.fn();
    renderUploader({
      value: ["/static/uploads/a.png", "/static/uploads/b.png"],
      onChange,
    });

    fireEvent.click(screen.getAllByTestId("attachment-remove")[0]);

    expect(onChange).toHaveBeenCalledWith(["/static/uploads/b.png"]);
    // `DELETE /uploads/photos/{id}` needs `uploads:delete`, which the resident
    // contesting may not hold: calling it would 403 on the happy path.
    expect(vi.mocked(deletePhoto).mock.calls).toHaveLength(0);
  });

  it("disables the input while the form is submitting", () => {
    renderUploader({ disabled: true });

    expect(screen.getByTestId("attachment-file-input")).toBeDisabled();
  });

  it("announces the file in flight and re-enables the input afterwards", async () => {
    let resolveUpload: (value: unknown) => void = () => {};
    vi.mocked(uploadPhoto).mockReturnValue(
      new Promise((resolve) => {
        resolveUpload = resolve;
      }) as never,
    );

    renderUploader();
    choose([file("slow.png", "image/png", 1024)]);

    expect(await screen.findByTestId("attachment-uploading")).toHaveTextContent(
      /slow\.png/,
    );
    expect(screen.getByTestId("attachment-file-input")).toBeDisabled();

    resolveUpload(asset("/static/uploads/slow.png"));

    await waitFor(() =>
      expect(screen.getByTestId("attachment-file-input")).toBeEnabled(),
    );
  });

  it("derives the hint from the exported constants rather than a typed sentence", () => {
    renderUploader();

    const hint = screen.getByTestId("attachment-hint");
    expect(hint).toHaveTextContent("JPEG");
    expect(hint).toHaveTextContent("PNG");
    expect(hint).toHaveTextContent("WEBP");
    expect(hint).toHaveTextContent("5 MB");
  });
});
