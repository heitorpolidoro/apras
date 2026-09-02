import { describe, it, expect } from "vitest";
import { useTranslation } from "react-i18next";
import {
  CANNOT_GRANT_PREFIX,
  SUPERUSER_ONLY_PREFIX,
  friendlyPermissionError,
} from "../utils/permissionErrors";

const { t } = useTranslation();

const apiError = (detail: unknown, status = 403) => ({
  response: { status, data: { detail } },
});

describe("friendlyPermissionError", () => {
  it("localises the anti-escalation 403 by permission label", () => {
    const message = friendlyPermissionError(
      apiError(`${CANNOT_GRANT_PREFIX}finance:read, votes:cast`),
      t,
    );

    expect(message).toContain("Ver");
    expect(message).toContain("Votar");
    expect(message).not.toContain(CANNOT_GRANT_PREFIX);
  });

  it("localises the superuser-only 403 by permission label", () => {
    const message = friendlyPermissionError(
      apiError(`${SUPERUSER_ONLY_PREFIX}tenants:create`),
      t,
    );

    expect(message).toContain("Criar");
    expect(message).not.toContain(SUPERUSER_ONLY_PREFIX);
  });

  it("maps the duplicate-name 409 to groups.errors.nameTaken", () => {
    const message = friendlyPermissionError(
      apiError("A user type with this name already exists", 409),
      t,
    );

    expect(message).toBe("Já existe um grupo com esse nome.");
  });

  it("falls back to parseApiError for any other detail", () => {
    expect(friendlyPermissionError(apiError("Role-linked user types cannot be deleted"), t)).toBe(
      "Role-linked user types cannot be deleted",
    );
    expect(
      friendlyPermissionError(apiError([{ msg: "field required" }], 422), t),
    ).toContain("field required");
  });

  it("falls back to the generic message when there is no detail at all", () => {
    expect(friendlyPermissionError(new Error("network down"), t)).toBe(
      "Não foi possível concluir a operação.",
    );
  });
});
