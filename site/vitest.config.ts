import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  test: {
    include: ["tests/unit/**/*.{test,spec}.{ts,tsx}"],
    environment: "jsdom",
    globals: true,
    setupFiles: ["./tests/unit/setup.ts"],
    // Redirect @visx/responsive to a lightweight stub so ParentSize renders
    // synchronously with a fixed width in jsdom (ResizeObserver doesn't work there).
    alias: {
      "@visx/responsive": path.resolve(__dirname, "tests/__mocks__/@visx/responsive.tsx"),
    },
    coverage: {
      provider: "v8",
      reporter: ["text", "html"],
      thresholds: { lines: 80, statements: 80, functions: 80, branches: 75 },
    },
  },
});
