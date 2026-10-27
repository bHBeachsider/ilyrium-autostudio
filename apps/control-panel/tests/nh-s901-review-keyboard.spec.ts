/**
 * NH-S901 — Keyboard-only review room
 *
 * Covers: approve (A key) + reject with required reason (R key + reason input),
 * take navigation (N / P), and ledger chain_ok verification after the session.
 *
 * Uses fixtures only — never touches production Neon (Decision B).
 * Requires: pnpm add -D @playwright/test && npx playwright install chromium
 */
import { test, expect } from "@playwright/test";
import * as path from "path";
import * as fs from "fs";
import * as crypto from "crypto";

// ── helpers matching review/route.ts ──────────────────────────────────────

function canonicalJSON(obj: unknown): string {
  if (obj === null || obj === undefined) return "null";
  if (typeof obj === "boolean" || typeof obj === "number") return JSON.stringify(obj);
  if (typeof obj === "string") return JSON.stringify(obj);
  if (Array.isArray(obj)) return "[" + obj.map(canonicalJSON).join(",") + "]";
  if (typeof obj === "object") {
    const keys = Object.keys(obj as object).sort();
    return "{" + keys.map((k) => JSON.stringify(k) + ":" + canonicalJSON((obj as Record<string, unknown>)[k])).join(",") + "}";
  }
  return JSON.stringify(obj);
}

function sha256(data: string): string {
  return "sha256:" + crypto.createHash("sha256").update(data, "utf8").digest("hex");
}

function snapshotHash(record: Record<string, unknown>): string {
  const { chain: _chain, ...core } = record;
  return sha256(canonicalJSON(core));
}

function computeRecordHash(prevHash: string | null, record: Record<string, unknown>): string {
  return sha256((prevHash ?? "") + snapshotHash(record));
}

function verifyChain(ledgerPath: string): boolean {
  const lines = fs.readFileSync(ledgerPath, "utf8").split("\n").filter(Boolean);
  let prev: string | null = null;
  for (const line of lines) {
    const rec = JSON.parse(line) as Record<string, unknown>;
    const chain = rec.chain as { prev_record_hash?: string | null; record_hash?: string } | undefined;
    const expected = computeRecordHash(prev, rec);
    if (chain?.record_hash !== expected) return false;
    prev = chain?.record_hash ?? null;
  }
  return true;
}

// ── fixtures ──────────────────────────────────────────────────────────────

const FIXTURE_DIR = path.join(__dirname, "fixtures");
const LEDGER_DIR = path.join(__dirname, "..", "..", "..", "ilyrium-shots", "ledger");
const SONG_ID = "nh-s901-test";
const LEDGER_PATH = path.join(LEDGER_DIR, `${SONG_ID}.jsonl`);

// Fixture adopt/state response — what the pipeline service returns when adopting a project.
const ADOPT_RESPONSE = {
  run_id: "nh-s901-fixture",
  state: {
    campaign_id: SONG_ID,
    stage: 5,
    status: "awaiting_approval",
    stages: {},
  },
};

test.beforeAll(() => {
  // Seed the test ledger from the fixture, recomputing real chain hashes.
  fs.mkdirSync(LEDGER_DIR, { recursive: true });
  const fixtureLines = fs.readFileSync(path.join(FIXTURE_DIR, `ledger_${SONG_ID}.jsonl`), "utf8")
    .split("\n").filter(Boolean)
    .map((l) => JSON.parse(l) as Record<string, unknown>);

  let prevH: string | null = null;
  const clean = fixtureLines.map((rec) => {
    const { chain: _c, ...core } = rec;
    const rh = computeRecordHash(prevH, core);
    const entry = { ...core, chain: { prev_record_hash: prevH, record_hash: rh } };
    prevH = rh;
    return JSON.stringify(entry);
  });
  fs.writeFileSync(LEDGER_PATH, clean.join("\n") + "\n", "utf8");
});

test.afterAll(() => {
  if (fs.existsSync(LEDGER_PATH)) fs.unlinkSync(LEDGER_PATH);
});

// ── mocks ─────────────────────────────────────────────────────────────────

const SHOTS_FIXTURE = JSON.stringify(
  JSON.parse(fs.readFileSync(path.join(FIXTURE_DIR, "shots.json"), "utf8"))
);

// Tiny valid MP4 (ftyp + empty mdat) — browsers won't play it but won't crash either.
const TINY_MP4 = Buffer.from(
  "0000001c667479706d703432000000006d703432" +
  "6d703431000000086d646174",
  "hex"
);

test.beforeEach(async ({ page }) => {
  // Inject the pipeline session into localStorage before the page loads.
  await page.addInitScript((payload: string) => {
    try { localStorage.setItem("ilyrium.pipeline.session", payload); } catch {}
  }, JSON.stringify({ externalId: SONG_ID, view: 5 }));

  // Mock pipeline list (GET /pipeline).
  await page.route("**/pipeline", async (route) => {
    if (route.request().method() === "GET") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ runs: [{ run_id: "nh-s901-fixture", state: ADOPT_RESPONSE.state }] }),
      });
    } else {
      await route.continue();
    }
  });

  // Mock pipeline adopt (POST /pipeline/adopt).
  await page.route("**/pipeline/adopt", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(ADOPT_RESPONSE),
    });
  });

  // Mock shots endpoint (GET /pipeline/:runId/shots).
  await page.route("**/pipeline/*/shots", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: SHOTS_FIXTURE });
  });

  // Mock any other pipeline service calls that Pipeline.tsx might fire.
  await page.route("**/pipeline/**", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: "{}" });
  });

  // Serve fixture media as a tiny MP4 (avoids 404s that block video element creation).
  await page.route("**/tests/fixtures/media/**", async (route) => {
    await route.fulfill({ status: 200, contentType: "video/mp4", body: TINY_MP4 });
  });
});

// ── NH-S901: keyboard-only review ─────────────────────────────────────────

test("NH-S901: keyboard-only approve + reject + chain_ok", async ({ page }) => {
  await page.goto("/studio/console");

  // The Pipeline component calls adopt() on load (from the injected localStorage session),
  // which our mock returns run_id + state with stage=5, so ReviewPanel mounts.
  const reviewRoom = page.locator("text=REVIEW ROOM");
  await expect(reviewRoom).toBeVisible({ timeout: 20000 });

  // The playlist should show the first take. Label format: "S{scene} · {take_id[0:6]} · {model}"
  // fixture take-001a → "S1 · take-0 · fal/wan-i2v"
  const firstTakeEntry = page.locator("text=/S1 · take-0/").first();
  await expect(firstTakeEntry).toBeVisible({ timeout: 5000 });

  // Ensure focus is not trapped in a text input before firing hotkeys.
  await page.evaluate(() => { (document.activeElement as HTMLElement)?.blur(); document.body.focus(); });

  // ── APPROVE take-001a with keyboard shortcut 'A' ──
  await page.keyboard.press("a");
  // Toast confirms approval.
  await expect(page.locator("text=/Approved/i")).toBeVisible({ timeout: 8000 });
  // Playlist chip should show ✓.
  await expect(page.locator(".text-good, [style*='#57c97a']").first()).toBeVisible();

  // ── Navigate to the next take with 'N' ──
  await page.keyboard.press("n");
  // Give the transition time to settle.
  await page.waitForTimeout(300);

  // ── REJECT the second take with keyboard shortcut 'R' ──
  await page.keyboard.press("r");
  const rejectDialog = page.locator("text=Reject take");
  await expect(rejectDialog).toBeVisible({ timeout: 3000 });

  // Confirm the reason textarea is required — button starts disabled.
  const confirmBtn = page.getByRole("button", { name: /Confirm reject/i });
  await expect(confirmBtn).toBeDisabled();

  // Type a reason into the textarea.
  const reasonTextarea = page.locator("textarea");
  await reasonTextarea.fill("Motion blur exceeds style kernel threshold — regenerate with slower shutter");
  await expect(confirmBtn).toBeEnabled();
  await confirmBtn.click();

  // Rejected toast should appear.
  await expect(page.locator("text=/Rejected/i")).toBeVisible({ timeout: 8000 });

  // ── Verify ledger chain_ok after the review session ──
  // The API route (Next.js server-side) appended records to the ledger file.
  // Wait for the async POSTs to complete (toasts confirm they did above).
  await page.waitForTimeout(1500);

  const chainOk = verifyChain(LEDGER_PATH);
  expect(chainOk).toBe(true);
});

// ── NH-S901b: hotkeys disabled inside text field ───────────────────────────

test("NH-S901b: hotkeys disabled while focus is in text field", async ({ page }) => {
  await page.goto("/studio/console");

  const reviewRoom = page.locator("text=REVIEW ROOM");
  await expect(reviewRoom).toBeVisible({ timeout: 20000 });

  // Click into the note input — hotkeys should be suppressed here.
  const noteInput = page.locator("input[placeholder*='note']");
  await expect(noteInput).toBeVisible({ timeout: 5000 });
  await noteInput.focus();

  // Press 'A' inside the input — must NOT trigger the approve action.
  await page.keyboard.press("a");

  // No approve toast should appear.
  await expect(page.locator("text=/Approved/i")).not.toBeVisible({ timeout: 1500 });

  // The input value should contain 'a' (normal typing behaviour).
  await expect(noteInput).toHaveValue("a");
});
