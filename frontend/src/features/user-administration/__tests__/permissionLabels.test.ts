import { describe, it, expect } from "vitest";
import { useTranslation } from "react-i18next";
import {
  actionLabel,
  moduleLabel,
  permissionLabel,
  sortModules,
} from "../utils/permissionLabels";

// The global setup mocks `react-i18next` with a real pt.json lookup that
// returns the raw key when it misses, which is exactly the resolution ladder
// these functions have to survive.
const { t } = useTranslation();

describe("permissionLabels", () => {
  it("prefers an override", () => {
    const overriding = ((key: string, options?: unknown) =>
      key === "permissions.overrides.finance.read"
        ? "Ver o caixa"
        : t(key, options as never)) as typeof t;

    expect(permissionLabel("finance:read", overriding)).toBe("Ver o caixa");
  });

  it("falls back to the action label", () => {
    expect(permissionLabel("finance:read", t)).toBe("Ver");
    expect(actionLabel("transaction_create", t)).toBe("Criar lançamento");
  });

  it("humanizes an unknown action", () => {
    // A permission a future slice adds must render legibly, never as a raw key.
    expect(permissionLabel("finance:brand_new_thing", t)).toBe(
      "Brand new thing",
    );
    expect(moduleLabel("brand_new_module", t)).toBe("Brand new module");
  });

  it("never returns the raw key for a catalogue action", () => {
    for (const permission of [
      "finance:read",
      "access_control:device_regenerate_key",
      "votes:cast",
      "user_types:delete",
    ]) {
      const label = permissionLabel(permission, t);
      expect(label).not.toContain("permissions.");
      expect(label).not.toBe(permission);
    }
  });

  it("sorts unknown modules last and keeps the display order otherwise", () => {
    expect(sortModules(["zzz_unknown", "users", "tasks"])).toEqual([
      "tasks",
      "users",
      "zzz_unknown",
    ]);
  });
});
