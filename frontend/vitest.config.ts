import { defineConfig, mergeConfig } from "vitest/config";
import viteConfig from "./vite.config";

export default mergeConfig(
  viteConfig,
  defineConfig({
    // `backend/tests/data/contrast_fixtures.json` is read with `?raw` by
    // `src/lib/__tests__/contrast.test.ts` (APRAS-68 D-D): it is the contract
    // the Python and the TypeScript contrast functions are both pinned
    // against, and neither language may import the other. Vite denies a file
    // outside the project root by default, so the one directory the fixture
    // lives in is allowed — deliberately that directory and not `../backend`.
    server: {
      fs: {
        allow: [".", "../backend/tests/data"],
      },
    },
    test: {
      globals: true,
      environment: "jsdom",
      environmentOptions: {
        jsdom: {
          url: "http://localhost:3000/",
        },
      },
      setupFiles: "./src/test/setup.ts",
      coverage: {
        provider: "v8",
        reporter: ["text", "lcov", "json-summary"],
        include: ["src/**/*"],
        exclude: [
          "src/main.tsx",
          "src/vite-env.d.ts",
          "src/test/**",
          "**/*.test.tsx",
          "**/*.test.ts",
        ],
        // Ratcheted by APRAS-36 to lock in the coverage gained there.
        // Measured on that run: 88.26 lines / 83.37 functions /
        // 79.16 branches / 87.41 statements.
        thresholds: {
          lines: 80,
          functions: 78,
          branches: 76,
          statements: 80,
        },
      },
    },
  }),
);
