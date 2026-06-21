import { defineConfig } from "vitest/config";

// Minimal config: decide() and its tests are pure TS units (no Next/DOM).
export default defineConfig({
  test: {
    include: ["lib/**/*.test.ts"],
    environment: "node",
  },
});
