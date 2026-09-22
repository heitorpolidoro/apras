import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  acceptInvitation,
  issueInvitation,
  listInvitations,
  previewInvitation,
} from "../invitations";
import apiClient from "../client";
import type { Invitation, InvitationPreview } from "../../types/invitations";

vi.mock("../client", () => ({
  default: { get: vi.fn(), post: vi.fn() },
}));

const INVITATION: Invitation = {
  id: "inv-1",
  tenant_id: "t-1",
  email: "ana@example.com",
  expires_at: "2026-09-28T12:00:00Z",
  accepted_at: null,
  accepted_user_id: null,
  invited_by_user_id: "u-root",
  created_at: "2026-09-21T12:00:00Z",
};

const PREVIEW: InvitationPreview = {
  email: "ana@example.com",
  tenant_name: "Residencial Aurora",
  tenant_slug: "residencial-aurora",
  invited_by_name: "Heitor Polidoro",
  expires_at: "2026-09-28T12:00:00Z",
  account_exists: false,
};

describe("invitations api client", () => {
  beforeEach(() => vi.clearAllMocks());

  it("issues an invitation on the no-trailing-slash path", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: INVITATION });

    await expect(
      issueInvitation({ tenant_id: "t-1", email: "ana@example.com" }),
    ).resolves.toEqual(INVITATION);
    expect(apiClient.post).toHaveBeenCalledWith("/invitations", {
      tenant_id: "t-1",
      email: "ana@example.com",
    });
  });

  it("lists one condominium's invitations through the tenant_id query param", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: [INVITATION] });

    await expect(listInvitations("t-1")).resolves.toEqual([INVITATION]);
    expect(apiClient.get).toHaveBeenCalledWith("/invitations", {
      params: { tenant_id: "t-1" },
    });
  });

  it("previews with the token in the BODY and never in the URL", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: PREVIEW });

    await expect(previewInvitation("raw-token")).resolves.toEqual(PREVIEW);
    const [url, body] = vi.mocked(apiClient.post).mock.calls[0];
    expect(url).toBe("/invitations/preview");
    expect(body).toEqual({ token: "raw-token" });
    // A token in a query string lands in access logs and browser history.
    expect(url).not.toContain("raw-token");
  });

  it("returns the accept STATUS alongside the body, for both branches", async () => {
    const token = { access_token: "jwt", token_type: "bearer" };
    vi.mocked(apiClient.post).mockResolvedValue({ status: 201, data: token });

    await expect(
      acceptInvitation({
        token: "raw-token",
        full_name: "Ana",
        cpf: "52998224725",
        password: "Senha!123",
      }),
    ).resolves.toEqual({ status: 201, data: token });
    expect(apiClient.post).toHaveBeenCalledWith("/invitations/accept", {
      token: "raw-token",
      full_name: "Ana",
      cpf: "52998224725",
      password: "Senha!123",
    });

    vi.mocked(apiClient.post).mockResolvedValue({ status: 200, data: PREVIEW });
    await expect(acceptInvitation({ token: "raw-token" })).resolves.toEqual({
      status: 200,
      data: PREVIEW,
    });
  });
});
