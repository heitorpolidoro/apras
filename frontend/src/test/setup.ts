// The `/vitest` entry point, not the bare one: the bare import augments Jest's
// `expect`, and Vitest 4 happened to pick that up. Vitest 5 does not, so every
// `toBeInTheDocument` and friend became a type error -- 1489 of them across 108
// files -- while the tests themselves still passed, because the matchers were
// registered at runtime either way. `npm run build` runs `tsc`, so only the
// build caught it.
import "@testing-library/jest-dom/vitest";
import { vi } from "vitest";
import pt from "../i18n/locales/pt.json";

// Node.js 22+ ships a partial native localStorage that conflicts with jsdom.
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] ?? null,
    setItem: (key: string, value: string) => {
      store[key] = String(value);
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    },
    get length() {
      return Object.keys(store).length;
    },
    key: (i: number) => Object.keys(store)[i] ?? null,
  };
})();

Object.defineProperty(globalThis, "localStorage", {
  value: localStorageMock,
  writable: true,
});

// Mock simplificado e robusto para react-i18next usando PT como base para os testes
const tMock = (key: string, options?: any) => {
  const keys = key.split(".");
  const ptData = (pt as any).default || pt;
  let value: any = ptData;

  for (const k of keys) {
    value = value?.[k];
  }

  if (typeof value === "string" && options && typeof options === "object") {
    Object.keys(options).forEach((k) => {
      value = value.replace(`{{${k}}}`, options[k]);
    });
  }

  if (value === undefined || value === null) {
    return typeof options === "string" ? options : key;
  }

  return value || key;
};

vi.mock("react-i18next", () => ({
  useTranslation: vi.fn(() => ({
    t: tMock,
    i18n: {
      language: "pt",
      changeLanguage: vi.fn(),
    },
  })),
  initReactI18next: {
    type: "3rdParty",
    init: vi.fn(),
  },
}));
