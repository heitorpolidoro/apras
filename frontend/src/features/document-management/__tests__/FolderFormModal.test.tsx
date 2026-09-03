import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { FolderFormModal } from "../components/FolderFormModal";
import { useRoles } from "../../../hooks/useRoles";
import type { DocumentFolderTree } from "../../../types/document";

/**
 * The folder ACL editor after IAM F5 (APRAS-49 §6).
 *
 * `DocumentFolder.allowed_roles_json` stored a JSON list of `UserRole`
 * **strings** — the one place the enum leaked into user data. It is a list of
 * role **ids** now, and the column was renamed to `allowed_role_ids_json` so
 * that a reader which was not updated fails loudly instead of silently
 * matching nothing.
 *
 * Two consequences show up in this component, and both are asserted below:
 *
 * * the checkbox list comes from `useRoles()` instead of a hard-coded
 *   `ALL_ROLES` constant, so a folder can be scoped to **any** role rather
 *   than only the six legacy ones — a straight improvement the enum made
 *   impossible;
 * * the default is `[]` rather than the four-value literal, because
 *   `DocumentFolderCreate.allowed_role_ids` is now **required**: neither the
 *   Python-side default nor the column's `server_default` can name four role
 *   ids, since a `server_default` is a constant expression and role ids
 *   differ per tenant and per install.
 */

vi.mock("../../../hooks/useRoles", () => ({ useRoles: vi.fn() }));

const ROLES = [
  { id: "role-director", name: "Diretor (papel)" },
  { id: "role-manager", name: "Gerente (papel)" },
  { id: "role-council", name: "Conselho Fiscal" },
];

const FOLDERS: DocumentFolderTree[] = [
  {
    id: "folder-1",
    name: "Financeiro",
    description: null,
    parent_id: null,
    allowed_role_ids: [],
    document_count: 0,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    children: [
      {
        id: "folder-2",
        name: "Balancetes",
        description: null,
        parent_id: "folder-1",
        allowed_role_ids: [],
        document_count: 0,
        created_at: "2026-01-01T00:00:00Z",
        updated_at: "2026-01-01T00:00:00Z",
        children: [],
      },
    ],
  },
];

const onSubmit = vi.fn().mockResolvedValue(undefined);
const onClose = vi.fn();

const renderModal = (props: Partial<React.ComponentProps<typeof FolderFormModal>> = {}) =>
  render(
    <FolderFormModal
      isOpen
      onClose={onClose}
      folders={FOLDERS}
      onSubmit={onSubmit}
      {...props}
    />,
  );

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(useRoles).mockReturnValue({ data: ROLES } as never);
});

describe("FolderFormModal", () => {
  it("renders nothing while closed", () => {
    const { container } = renderModal({ isOpen: false });
    expect(container.firstChild).toBeNull();
  });

  it("lists every role of the tenant, including non-legacy ones", () => {
    renderModal();

    for (const role of ROLES) {
      expect(screen.getByText(role.name)).toBeInTheDocument();
    }
    // `Conselho Fiscal` never had a `UserRole` value, so before F5 no folder
    // could name it at all.
    expect(screen.getByText("Conselho Fiscal")).toBeInTheDocument();
  });

  it("tolerates an unloaded role list", () => {
    vi.mocked(useRoles).mockReturnValue({ data: undefined } as never);

    renderModal();

    expect(screen.queryByText("Diretor (papel)")).toBeNull();
  });

  it("starts a new folder with an empty ACL and submits the ids ticked", async () => {
    renderModal();

    const checkboxes = screen.getAllByRole("checkbox") as HTMLInputElement[];
    expect(checkboxes.every((box) => !box.checked)).toBe(true);

    fireEvent.change(screen.getByPlaceholderText(/Legisla/i), {
      target: { value: "Prestação de contas" },
    });
    fireEvent.click(checkboxes[2]);
    fireEvent.submit(screen.getByRole("button", { name: /Criar Pasta/i }));

    await waitFor(() => expect(onSubmit).toHaveBeenCalled());
    expect(onSubmit.mock.calls[0][0]).toMatchObject({
      name: "Prestação de contas",
      allowed_role_ids: ["role-council"],
    });
    expect(onClose).toHaveBeenCalled();
  });

  it("toggles a role off again", async () => {
    renderModal();

    const checkboxes = screen.getAllByRole("checkbox") as HTMLInputElement[];
    fireEvent.click(checkboxes[0]);
    fireEvent.click(checkboxes[1]);
    fireEvent.click(checkboxes[0]);
    fireEvent.submit(screen.getByRole("button", { name: /Criar Pasta/i }));

    await waitFor(() => expect(onSubmit).toHaveBeenCalled());
    expect(onSubmit.mock.calls[0][0].allowed_role_ids).toEqual(["role-manager"]);
  });

  it("pre-fills the stored ACL in edit mode, and excludes the folder itself as a parent", () => {
    renderModal({
      initialData: {
        ...FOLDERS[0],
        allowed_role_ids: ["role-director", "role-manager"],
        description: "Documentos financeiros",
      },
    });

    const checkboxes = screen.getAllByRole("checkbox") as HTMLInputElement[];
    expect(checkboxes[0].checked).toBe(true);
    expect(checkboxes[1].checked).toBe(true);
    expect(checkboxes[2].checked).toBe(false);
    expect(screen.getByRole("button", { name: /Salvar/i })).toBeInTheDocument();
    // A folder may not become its own parent — nor its own descendant's
    // child, which is why the whole subtree drops out of the list and not
    // just the folder itself. Only the root placeholder is left here.
    const options = screen.getAllByRole("option").map((node) => node.textContent);
    expect(options.some((label) => label?.includes("Financeiro"))).toBe(false);
    expect(options.some((label) => label?.includes("Balancetes"))).toBe(false);
    expect(options).toHaveLength(1);
  });

  it("falls back to an empty ACL when the stored one is missing", () => {
    renderModal({
      initialData: {
        ...FOLDERS[0],
        allowed_role_ids: undefined as never,
      },
    });

    const checkboxes = screen.getAllByRole("checkbox") as HTMLInputElement[];
    expect(checkboxes.every((box) => !box.checked)).toBe(true);
  });

  it("honours an initialParentId when creating a subfolder", async () => {
    renderModal({ initialParentId: "folder-1" });

    fireEvent.change(screen.getByPlaceholderText(/Legisla/i), {
      target: { value: "Sub" },
    });
    fireEvent.submit(screen.getByRole("button", { name: /Criar Pasta/i }));

    await waitFor(() => expect(onSubmit).toHaveBeenCalled());
    expect(onSubmit.mock.calls[0][0].parent_id).toBe("folder-1");
  });

  it("sends a null parent_id when none is chosen", async () => {
    renderModal();

    fireEvent.change(screen.getByPlaceholderText(/Legisla/i), {
      target: { value: "Raiz" },
    });
    fireEvent.submit(screen.getByRole("button", { name: /Criar Pasta/i }));

    await waitFor(() => expect(onSubmit).toHaveBeenCalled());
    expect(onSubmit.mock.calls[0][0].parent_id).toBeNull();
  });

  it("closes without submitting when cancelled", () => {
    renderModal();

    fireEvent.click(screen.getByRole("button", { name: /Cancelar/i }));

    expect(onClose).toHaveBeenCalled();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("disables the submit button while a save is in flight", () => {
    renderModal({ isLoading: true });

    expect(screen.getByRole("button", { name: /Criar Pasta/i })).toBeDisabled();
  });
});
