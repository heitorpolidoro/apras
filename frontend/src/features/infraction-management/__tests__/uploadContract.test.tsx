import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { NewInfractionModal } from "../components/NewInfractionModal";
import { ContestationForm } from "../components/ContestationForm";
import { INFRACTION_ENTITY_TYPE } from "../components/AttachmentUploader";
import {
  UPLOAD_ALLOWED_MIME_TYPES,
  UPLOAD_MAX_FILE_SIZE_BYTES,
  UPLOAD_PHOTO_PERMISSION,
} from "../../../api/uploads";
import apiClient from "../../../api/client";
import { useMyPermissions } from "../../../hooks/usePermissionQueries";
import { settledPermissions } from "../../../test/permissionFixtures";
import type { InfractionRule } from "../../../types/infraction";

/**
 * What the infraction forms actually put on the wire, and the constants they
 * put there.
 *
 * `api/uploads` is **deliberately not mocked**: only `api/client` (the axios
 * instance, the last layer before the network) and `hooks/usePermissionQueries`
 * (the persona) are. Every other test in this feature mocks the API module
 * wholesale, which is exactly how APRAS-44 shipped `limit: 200` against a
 * route declaring `le=100` — a 422 before the handler, invisible to a mocked
 * client.
 *
 * **This is one half of a two-sided pin**, the same shape
 * `lotSelectContract.test.tsx` ↔
 * `backend/tests/test_infractions.py::test_the_lots_route_ceiling_matches_the_lot_selects_limit`
 * and `src/i18n/__tests__/index.test.ts` ↔ `backend/tests/test_module_vocabulary.py`
 * already use: neither side can import the other across the language boundary,
 * so each states the constant and names the other. The backend half is
 * `backend/tests/test_uploads.py::test_the_upload_contract_matches_the_infraction_uploader`,
 * which reads `media_service.MAX_FILE_SIZE`/`ALLOWED_MIME_TYPES`,
 * `EntityType.INFRACTION`, `ROUTE_PERMISSIONS[("POST", "/api/v1/uploads/photo")]`
 * and the live route's `dependant`, and fails with this file's name in the
 * message.
 */

vi.mock("../../../api/client", () => ({
  default: { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() },
}));

vi.mock("../../../hooks/usePermissionQueries", () => ({
  useMyPermissions: vi.fn(),
  usePermissionCatalogue: vi.fn(() => ({ data: [], isPending: false })),
}));

// ---------------------------------------------------------------------------
// Half 2 — the constants, declared here and asserted against what production
// exports. A literal compared with an exported constant is not a tautology:
// the constant is what production uses (the `accept=`, the size pre-check, the
// argument of `has()`), the literal is what this file declares to be the
// server's truth, and the twin named above holds the server to it.
// ---------------------------------------------------------------------------

/** `backend/app/services/media_service.py::MAX_FILE_SIZE`. */
const DOCUMENTED_MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024;
/** `backend/app/services/media_service.py::ALLOWED_MIME_TYPES`. */
const DOCUMENTED_MIME_TYPES = ["image/jpeg", "image/png", "image/webp"];
/** `backend/app/models/enums.py::EntityType.INFRACTION`. */
const DOCUMENTED_ENTITY_TYPE = "INFRACTION";
/** `backend/app/api/v1/endpoints/uploads.py`, under the `/api/v1` prefix. */
const DOCUMENTED_UPLOAD_ROUTE = "/uploads/photo";
/** `backend/app/core/permissions.py`, enforced since APRAS-51. */
const DOCUMENTED_UPLOAD_PERMISSION = "uploads:photo_create";

// ---------------------------------------------------------------------------
// Personas (§3.6(a)). Explicit lists and not `permissionsOf("RESIDENT")`: the
// legacy RESIDENT bundle already holds `uploads:photo_create`, so it cannot
// express the denied branch at all.
// ---------------------------------------------------------------------------

const RESIDENT_WITH_ATTACHMENTS = [
  "infractions:contest",
  "infractions:my_lots_read",
  "uploads:photo_create",
];
const RESIDENT_WITHOUT_ATTACHMENTS = [
  "infractions:contest",
  "infractions:my_lots_read",
];
const STAFF_WITH_ATTACHMENTS = [
  "infractions:create",
  "infractions:read",
  "uploads:photo_create",
];
const STAFF_WITHOUT_ATTACHMENTS = ["infractions:create", "infractions:read"];

const asPersona = (permissions: readonly string[]) =>
  vi.mocked(useMyPermissions).mockReturnValue(
    settledPermissions(permissions) as never,
  );

const UPLOADED_URL = "/static/uploads/2026/09/prova.png";

const rule: InfractionRule = {
  id: "rule-1",
  article: "art. 12",
  origin: "REGIMENTO_INTERNO",
  description: "Sossego",
  recidivism_window_days: 365,
  is_active: true,
  steps: [],
  created_at: "2026-01-01T00:00:00",
  updated_at: "2026-01-01T00:00:00",
};

const png = (name = "prova.png") =>
  new File(["x"], name, { type: "image/png" });

const withProviders = (node: React.ReactNode) =>
  render(
    <QueryClientProvider
      client={
        new QueryClient({
          defaultOptions: { queries: { retry: false, gcTime: 0 } },
        })
      }
    >
      <MemoryRouter>{node}</MemoryRouter>
    </QueryClientProvider>,
  );

/** The only `post` this file cares about, whatever else the page issues. */
const uploadCalls = () =>
  vi
    .mocked(apiClient.post)
    .mock.calls.filter((call) => call[0] === DOCUMENTED_UPLOAD_ROUTE);

const attach = (file: File) =>
  fireEvent.change(screen.getByTestId("attachment-file-input"), {
    target: { files: [file] },
  });

/**
 * `canSubmit` is `ruleId && residentId && occurredOn && description && lotId`,
 * so reaching the create submit needs a non-empty `rules` prop and both `get`
 * stubs. The precedent (`lotSelectContract.test.tsx`) never submits and so does
 * not carry this.
 */
const fillCreateForm = async () => {
  await waitFor(() =>
    expect(
      (screen.getByLabelText("Responsável") as HTMLSelectElement).options.length,
    ).toBe(2),
  );
  fireEvent.change(screen.getByLabelText("Responsável"), {
    target: { value: "res-1" },
  });
  fireEvent.change(screen.getByLabelText("Data do fato"), {
    target: { value: "2026-09-01" },
  });
  fireEvent.change(screen.getByLabelText("Descrição"), {
    target: { value: "Som alto." },
  });
};

beforeEach(() => {
  vi.clearAllMocks();
  asPersona(STAFF_WITH_ATTACHMENTS);
  vi.mocked(apiClient.get).mockImplementation(((path: string) => {
    if (path === "/lots/") {
      return Promise.resolve({
        data: {
          items: [{ id: "lot-1", block: "A", lot_number: "101" }],
          total: 1,
          skip: 0,
          limit: 100,
        },
      });
    }
    if (path === "/lots/lot-1/residents") {
      return Promise.resolve({
        data: {
          items: [
            { id: "res-1", full_name: "Maria", lot_id: "lot-1", is_active: true },
          ],
          total: 1,
          skip: 0,
          limit: 100,
        },
      });
    }
    return Promise.resolve({ data: { items: [], total: 0, skip: 0, limit: 100 } });
  }) as never);
  vi.mocked(apiClient.post).mockResolvedValue({
    data: { id: "asset-1", url: UPLOADED_URL, status: "PENDING_APPROVAL" },
  } as never);
});

describe("the infraction uploader's contract with POST /api/v1/uploads/photo", () => {
  it("posts the route, the entity type and NO entity_id when the infraction does not exist yet", async () => {
    withProviders(
      <NewInfractionModal rules={[rule]} onClose={vi.fn()} onSubmit={vi.fn()} />,
    );

    attach(png());

    await waitFor(() => expect(uploadCalls()).toHaveLength(1));
    const [path, body, config] = uploadCalls()[0];
    expect(path).toBe(DOCUMENTED_UPLOAD_ROUTE);
    expect(body).toBeInstanceOf(FormData);
    const form = body as FormData;
    expect(form.get("entity_type")).toBe(DOCUMENTED_ENTITY_TYPE);
    // `has`, not `get`: `uploadPhoto` appends `entity_id` only `if (entityId)`,
    // and `get` on an absent key answers `null` — the assertion would pass by
    // coincidence of the DOM API rather than by construction.
    expect(form.has("entity_id")).toBe(false);
    expect(config).toMatchObject({
      headers: { "Content-Type": "multipart/form-data" },
    });
  });

  it("carries the URL the 201 returned into InfractionCreate.evidence_urls", async () => {
    const onSubmit = vi.fn();
    withProviders(
      <NewInfractionModal rules={[rule]} onClose={vi.fn()} onSubmit={onSubmit} />,
    );

    await fillCreateForm();
    attach(png());
    await screen.findByTestId("attachment-chip");

    fireEvent.click(screen.getByTestId("submit-new-infraction"));

    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({ evidence_urls: [UPLOADED_URL] }),
    );
  });

  it("posts the infraction id as entity_id when contesting, where it exists", async () => {
    asPersona(RESIDENT_WITH_ATTACHMENTS);
    const openDeadline = new Date(Date.now() + 30 * 86400000)
      .toISOString()
      .slice(0, 10);

    withProviders(
      <ContestationForm
        infractionId="inf-1"
        defenseDueOn={openDeadline}
        onSubmit={vi.fn()}
      />,
    );

    attach(png("defesa.png"));

    await waitFor(() => expect(uploadCalls()).toHaveLength(1));
    const form = uploadCalls()[0][1] as FormData;
    expect(form.get("entity_type")).toBe(DOCUMENTED_ENTITY_TYPE);
    expect(form.has("entity_id")).toBe(true);
    expect(form.get("entity_id")).toBe("inf-1");
  });

  it("carries the URL into ContestationCreate.attachment_urls", async () => {
    asPersona(RESIDENT_WITH_ATTACHMENTS);
    const onSubmit = vi.fn();
    const openDeadline = new Date(Date.now() + 30 * 86400000)
      .toISOString()
      .slice(0, 10);

    withProviders(
      <ContestationForm
        infractionId="inf-1"
        defenseDueOn={openDeadline}
        onSubmit={onSubmit}
      />,
    );

    fireEvent.change(screen.getByLabelText("Sua defesa"), {
      target: { value: "Estava viajando." },
    });
    attach(png("defesa.png"));
    await screen.findByTestId("attachment-chip");

    fireEvent.click(screen.getByTestId("submit-contestation"));

    expect(onSubmit).toHaveBeenCalledWith("Estava viajando.", [UPLOADED_URL]);
  });

  it("denies the control on creation without uploads:photo_create, and posts nothing", async () => {
    asPersona(STAFF_WITHOUT_ATTACHMENTS);

    withProviders(
      <NewInfractionModal rules={[rule]} onClose={vi.fn()} onSubmit={vi.fn()} />,
    );

    expect(screen.getByTestId("attachment-unavailable")).toHaveTextContent(
      "Anexos indisponíveis para o seu perfil.",
    );
    expect(screen.queryByTestId("attachment-file-input")).not.toBeInTheDocument();
    await waitFor(() => expect(apiClient.get).toHaveBeenCalled());
    expect(uploadCalls()).toHaveLength(0);
  });

  it("denies the control on contestation, and the text defense still goes through", () => {
    asPersona(RESIDENT_WITHOUT_ATTACHMENTS);
    const onSubmit = vi.fn();
    const openDeadline = new Date(Date.now() + 30 * 86400000)
      .toISOString()
      .slice(0, 10);

    withProviders(
      <ContestationForm
        infractionId="inf-1"
        defenseDueOn={openDeadline}
        onSubmit={onSubmit}
      />,
    );

    expect(screen.getByTestId("attachment-unavailable")).toHaveTextContent(
      "Anexos indisponíveis para o seu perfil.",
    );
    expect(screen.queryByTestId("attachment-file-input")).not.toBeInTheDocument();

    // An attachment permission must not become a permission to contest.
    fireEvent.change(screen.getByLabelText("Sua defesa"), {
      target: { value: "Estava viajando." },
    });
    expect(screen.getByTestId("submit-contestation")).toBeEnabled();
    fireEvent.click(screen.getByTestId("submit-contestation"));

    expect(onSubmit).toHaveBeenCalledWith("Estava viajando.", []);
    expect(uploadCalls()).toHaveLength(0);
  });

  it("shows neither branch while /permissions/me is still pending", () => {
    vi.mocked(useMyPermissions).mockReturnValue({
      data: undefined,
      isPending: true,
      isError: false,
    } as never);

    withProviders(
      <NewInfractionModal rules={[rule]} onClose={vi.fn()} onSubmit={vi.fn()} />,
    );

    expect(screen.getByTestId("attachment-gate-loading")).toBeInTheDocument();
    expect(screen.queryByTestId("attachment-file-input")).not.toBeInTheDocument();
    expect(screen.queryByTestId("attachment-unavailable")).not.toBeInTheDocument();
  });

  it("offers no attachment control in promote mode, permission or not", () => {
    withProviders(
      <NewInfractionModal
        rules={[rule]}
        occurrence={{
          id: "occ-1",
          protocol_number: "OCO-2026-000009",
          lot_id: "lot-1",
          description: "Som alto depois das 23h.",
          created_at: "2026-08-30T12:00:00",
        }}
        onClose={vi.fn()}
        onSubmit={vi.fn()}
        onPromote={vi.fn()}
      />,
    );

    expect(screen.queryByTestId("attachment-uploader")).not.toBeInTheDocument();
    expect(screen.queryByTestId("attachment-gate-loading")).not.toBeInTheDocument();
    expect(screen.queryByTestId("attachment-unavailable")).not.toBeInTheDocument();
  });
});

describe("the five server facts, pinned from this side", () => {
  it("declares media_service.MAX_FILE_SIZE", () => {
    expect(
      UPLOAD_MAX_FILE_SIZE_BYTES,
      "backend/app/services/media_service.py::MAX_FILE_SIZE and " +
        "frontend/src/api/uploads.ts disagree. The backend twin is " +
        "backend/tests/test_uploads.py::test_the_upload_contract_matches_the_infraction_uploader.",
    ).toBe(DOCUMENTED_MAX_FILE_SIZE_BYTES);
  });

  it("declares media_service.ALLOWED_MIME_TYPES", () => {
    expect(
      new Set(UPLOAD_ALLOWED_MIME_TYPES),
      "backend/app/services/media_service.py::ALLOWED_MIME_TYPES and " +
        "frontend/src/api/uploads.ts disagree. The backend twin is " +
        "backend/tests/test_uploads.py::test_the_upload_contract_matches_the_infraction_uploader.",
    ).toEqual(new Set(DOCUMENTED_MIME_TYPES));
  });

  it("declares EntityType.INFRACTION", () => {
    expect(
      INFRACTION_ENTITY_TYPE,
      "backend/app/models/enums.py::EntityType.INFRACTION and " +
        "AttachmentUploader.tsx disagree; a value outside the server enum is a " +
        "FastAPI 422 raised before the handler. Backend twin: " +
        "backend/tests/test_uploads.py::test_the_upload_contract_matches_the_infraction_uploader.",
    ).toBe(DOCUMENTED_ENTITY_TYPE);
  });

  it("declares the route the client posts to", async () => {
    withProviders(
      <NewInfractionModal rules={[rule]} onClose={vi.fn()} onSubmit={vi.fn()} />,
    );
    attach(png());

    await waitFor(() =>
      expect(
        vi.mocked(apiClient.post).mock.calls.map((call) => call[0]),
        "backend/app/api/v1/endpoints/uploads.py moved POST /photo. Backend " +
          "twin: backend/tests/test_uploads.py::" +
          "test_the_upload_contract_matches_the_infraction_uploader.",
      ).toContain(DOCUMENTED_UPLOAD_ROUTE),
    );
  });

  it("declares the permission the route demands and the gate consults", () => {
    expect(
      UPLOAD_PHOTO_PERMISSION,
      "backend/app/core/permissions.py maps POST /api/v1/uploads/photo to a " +
        "different permission than frontend/src/api/uploads.ts consults; " +
        "APRAS-51 made it a runtime guard. Backend twin: " +
        "backend/tests/test_uploads.py::test_the_upload_contract_matches_the_infraction_uploader.",
    ).toBe(DOCUMENTED_UPLOAD_PERMISSION);
  });
});
