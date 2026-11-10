import { defineConfig, devices } from "@playwright/test";
import * as os from "os";
import * as path from "path";

// Dedicated port, and never reuse a running server: attaching to another checkout's
// dev server on :3000 would run the specs against (and write ledger files into) that checkout.
const PORT = Number(process.env.PW_PORT ?? 3217);
const BASE_URL = `http://localhost:${PORT}`;

// Tests must never write to ilyrium-shots/ledger (the real append-only audit ledger).
// Set on process.env so the spec workers read the same directory the dev server writes to.
// Keyed by port so concurrent runs from two checkouts (different PW_PORT) do not share a file.
process.env.LEDGER_DIR = path.join(os.tmpdir(), `ilyrium-pw-ledger-${PORT}`);

// Fixtures only, never Neon (ILY-205 Decision B): the console page renders from this
// file instead of querying the database.
const CONSOLE_FIXTURE = path.join(__dirname, "tests", "fixtures", "console.json");

export default defineConfig({
  testDir: "./tests",
  testMatch: "**/*.spec.ts",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: [["html", { open: "never" }], ["line"]],
  use: {
    baseURL: BASE_URL,
    trace: "on-first-retry",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: {
    command: `pnpm exec next dev -p ${PORT}`,
    url: BASE_URL,
    reuseExistingServer: false,
    timeout: 120000,
    env: {
      LEDGER_DIR: process.env.LEDGER_DIR,
      ILYRIUM_CONSOLE_FIXTURE: CONSOLE_FIXTURE,
      // Empty on purpose: blanks any DATABASE_URL inherited from the shell. next.config.js
      // skips its .env override when ILYRIUM_CONSOLE_FIXTURE is set, and Next's own .env
      // loading does not replace a variable that is already defined.
      DATABASE_URL: "",
    },
  },
});
