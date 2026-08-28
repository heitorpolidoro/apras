import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import React from "react";
import { AuthorizationQrModal } from "../components/AuthorizationQrModal";
import apiClient from "../../../api/client";

vi.mock("../../../api/client", () => ({
  default: {
    get: vi.fn(),
  },
}));

const mockAuthorization = {
  id: "auth-1",
  visitor_id: "vis-1",
  lot_id: "lot-1",
  authorizer_user_id: "user-1",
  auth_type: "SINGLE",
  allowed_days_json: "[]",
  allowed_shifts_json: "[]",
  allowed_days: [],
  allowed_shifts: [],
  status: "ACTIVE",
  created_at: "2026-08-25T10:00:00Z",
  updated_at: "2026-08-25T10:00:00Z",
} as any;

describe("AuthorizationQrModal", () => {
  const originalCreateObjectURL = URL.createObjectURL;
  const originalRevokeObjectURL = URL.revokeObjectURL;

  beforeEach(() => {
    vi.clearAllMocks();
    URL.createObjectURL = vi.fn(() => "blob:mock-object-url");
    URL.revokeObjectURL = vi.fn();
  });

  afterEach(() => {
    URL.createObjectURL = originalCreateObjectURL;
    URL.revokeObjectURL = originalRevokeObjectURL;
  });

  it("returns null when no authorization is provided", () => {
    const { container } = render(
      <AuthorizationQrModal authorization={null} onClose={vi.fn()} />
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("fetches the qr code as a blob via apiClient and renders it as an object URL", async () => {
    const mockBlob = new Blob(["fake-png-bytes"], { type: "image/png" });
    vi.mocked(apiClient.get).mockResolvedValue({ data: mockBlob });

    render(<AuthorizationQrModal authorization={mockAuthorization} onClose={vi.fn()} />);

    await waitFor(() => {
      expect(apiClient.get).toHaveBeenCalledWith("/authorizations/auth-1/qr-code", {
        responseType: "blob",
      });
    });

    const img = await screen.findByRole("img");
    expect(img).toHaveAttribute("src", "blob:mock-object-url");
    expect(img.getAttribute("src")).not.toContain("/authorizations/auth-1/qr-code");
  });

  it("revokes the object URL when the modal is closed", async () => {
    const mockBlob = new Blob(["fake-png-bytes"], { type: "image/png" });
    vi.mocked(apiClient.get).mockResolvedValue({ data: mockBlob });
    const onClose = vi.fn();

    const { rerender } = render(
      <AuthorizationQrModal authorization={mockAuthorization} onClose={onClose} />
    );

    await screen.findByRole("img");

    rerender(<AuthorizationQrModal authorization={null} onClose={onClose} />);

    await waitFor(() => {
      expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:mock-object-url");
    });
  });

  it("shows an error message when the fetch fails", async () => {
    vi.mocked(apiClient.get).mockRejectedValue(new Error("network error"));

    render(<AuthorizationQrModal authorization={mockAuthorization} onClose={vi.fn()} />);

    expect(await screen.findByText("Erro ao carregar o QR Code.")).toBeInTheDocument();
  });
});
