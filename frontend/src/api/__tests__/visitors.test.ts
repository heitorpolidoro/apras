import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  searchVisitors,
  createVisitor,
  getVisitor,
  updateVisitor,
  getLotAuthorizations,
  createLotAuthorization,
  getAuthorization,
  revokeAuthorization,
  checkInVisitor,
  checkOutVisitor,
  getAccessLogs,
} from "../visitors";
import apiClient from "../client";

vi.mock("../client", () => ({
  default: { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() },
}));

const emptyPage = { items: [], total: 0, skip: 0, limit: 20 };

describe("visitors api client", () => {
  beforeEach(() => vi.clearAllMocks());

  describe("visitor profiles", () => {
    it("searches visitors forwarding q, skip and limit", async () => {
      vi.mocked(apiClient.get).mockResolvedValue({ data: emptyPage });

      await expect(searchVisitors("maria", 20, 10)).resolves.toEqual(emptyPage);

      expect(apiClient.get).toHaveBeenCalledWith("/visitors", {
        params: { q: "maria", skip: 20, limit: 10 },
      });
    });

    it("searches visitors with undefined params when none are given", async () => {
      vi.mocked(apiClient.get).mockResolvedValue({ data: emptyPage });

      await searchVisitors();

      expect(apiClient.get).toHaveBeenCalledWith("/visitors", {
        params: { q: undefined, skip: undefined, limit: undefined },
      });
    });

    it("creates a visitor", async () => {
      vi.mocked(apiClient.post).mockResolvedValue({ data: { id: "v-1" } });

      await expect(
        createVisitor({ full_name: "Maria", cpf: "12345678900" }),
      ).resolves.toEqual({ id: "v-1" });

      expect(apiClient.post).toHaveBeenCalledWith("/visitors", {
        full_name: "Maria",
        cpf: "12345678900",
      });
    });

    it("reads a single visitor by id", async () => {
      vi.mocked(apiClient.get).mockResolvedValue({ data: { id: "v-1" } });

      await expect(getVisitor("v-1")).resolves.toEqual({ id: "v-1" });

      expect(apiClient.get).toHaveBeenCalledWith("/visitors/v-1");
    });

    it("updates a visitor by id", async () => {
      vi.mocked(apiClient.put).mockResolvedValue({ data: { id: "v-1" } });

      await expect(
        updateVisitor("v-1", { phone: "11999999999" }),
      ).resolves.toEqual({ id: "v-1" });

      expect(apiClient.put).toHaveBeenCalledWith("/visitors/v-1", {
        phone: "11999999999",
      });
    });
  });

  describe("authorizations", () => {
    it("lists the authorizations of a lot with the status_filter param", async () => {
      vi.mocked(apiClient.get).mockResolvedValue({ data: emptyPage });

      await expect(
        getLotAuthorizations("l-1", "ACTIVE", 0, 50),
      ).resolves.toEqual(emptyPage);

      expect(apiClient.get).toHaveBeenCalledWith("/lots/l-1/authorizations", {
        params: { status_filter: "ACTIVE", skip: 0, limit: 50 },
      });
    });

    it("lists the authorizations of a lot with undefined params when none are given", async () => {
      vi.mocked(apiClient.get).mockResolvedValue({ data: emptyPage });

      await getLotAuthorizations("l-1");

      expect(apiClient.get).toHaveBeenCalledWith("/lots/l-1/authorizations", {
        params: {
          status_filter: undefined,
          skip: undefined,
          limit: undefined,
        },
      });
    });

    it("creates an authorization under the lot", async () => {
      vi.mocked(apiClient.post).mockResolvedValue({ data: { id: "auth-1" } });

      await expect(
        createLotAuthorization("l-1", {
          visitor_id: "v-1",
          auth_type: "PERMANENT",
          allowed_days: ["MON", "TUE"],
          allowed_shifts: ["FULL_DAY"],
        }),
      ).resolves.toEqual({ id: "auth-1" });

      expect(apiClient.post).toHaveBeenCalledWith("/lots/l-1/authorizations", {
        visitor_id: "v-1",
        auth_type: "PERMANENT",
        allowed_days: ["MON", "TUE"],
        allowed_shifts: ["FULL_DAY"],
      });
    });

    it("reads a single authorization by id", async () => {
      vi.mocked(apiClient.get).mockResolvedValue({ data: { id: "auth-1" } });

      await expect(getAuthorization("auth-1")).resolves.toEqual({
        id: "auth-1",
      });

      expect(apiClient.get).toHaveBeenCalledWith("/authorizations/auth-1");
    });

    it("revokes an authorization sending the reason in the body", async () => {
      vi.mocked(apiClient.put).mockResolvedValue({ data: { id: "auth-1" } });

      await expect(
        revokeAuthorization("auth-1", "Acesso indevido"),
      ).resolves.toEqual({ id: "auth-1" });

      expect(apiClient.put).toHaveBeenCalledWith(
        "/authorizations/auth-1/revoke",
        { reason: "Acesso indevido" },
      );
    });

    it("revokes an authorization with an undefined reason when none is given", async () => {
      vi.mocked(apiClient.put).mockResolvedValue({ data: { id: "auth-1" } });

      await revokeAuthorization("auth-1");

      expect(apiClient.put).toHaveBeenCalledWith(
        "/authorizations/auth-1/revoke",
        { reason: undefined },
      );
    });
  });

  describe("access logs", () => {
    it("checks a visitor in", async () => {
      vi.mocked(apiClient.post).mockResolvedValue({ data: { id: "log-1" } });

      await expect(
        checkInVisitor({
          visitor_id: "v-1",
          lot_id: "l-1",
          authorization_id: "auth-1",
        }),
      ).resolves.toEqual({ id: "log-1" });

      expect(apiClient.post).toHaveBeenCalledWith("/access-logs/check-in", {
        visitor_id: "v-1",
        lot_id: "l-1",
        authorization_id: "auth-1",
      });
    });

    it("checks a visitor out", async () => {
      vi.mocked(apiClient.post).mockResolvedValue({ data: { id: "log-1" } });

      await expect(
        checkOutVisitor({ access_log_id: "log-1", exit_notes: "ok" }),
      ).resolves.toEqual({ id: "log-1" });

      expect(apiClient.post).toHaveBeenCalledWith("/access-logs/check-out", {
        access_log_id: "log-1",
        exit_notes: "ok",
      });
    });

    it("lists access logs forwarding the snake_case filter params", async () => {
      vi.mocked(apiClient.get).mockResolvedValue({ data: emptyPage });

      await expect(
        getAccessLogs({ lot_id: "l-1", visitor_id: "v-1", skip: 0, limit: 25 }),
      ).resolves.toEqual(emptyPage);

      expect(apiClient.get).toHaveBeenCalledWith("/access-logs", {
        params: { lot_id: "l-1", visitor_id: "v-1", skip: 0, limit: 25 },
      });
    });

    it("lists access logs with no params when none are given", async () => {
      vi.mocked(apiClient.get).mockResolvedValue({ data: emptyPage });

      await getAccessLogs();

      expect(apiClient.get).toHaveBeenCalledWith("/access-logs", {
        params: undefined,
      });
    });
  });
});
