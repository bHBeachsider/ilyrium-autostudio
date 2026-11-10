/**
 * NH-S901 — Keyboard-only review room
 *
 * Covers: approve (A key) + reject with required reason (R key + reason input),
 * take navigation (N / P), and ledger chain_ok verification after the session.
 *
 * Uses fixtures only — never touches production Neon (Decision B): the console page renders
 * from tests/fixtures/console.json and the ledger lives in a temp dir (see playwright.config.ts).
 * Run: pnpm run test:e2e   (first time: pnpm exec playwright install chromium)
 */
import { test, expect } from "@playwright/test";
import { mockPipelineService } from "./helpers/mockService";
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
// The temp dir playwright.config.ts hands to the dev server - never the real ilyrium-shots/ledger.
const LEDGER_DIR = process.env.LEDGER_DIR ?? "";
if (!LEDGER_DIR || /ilyrium-shots/.test(LEDGER_DIR)) {
  throw new Error("LEDGER_DIR must be a temp dir set by playwright.config.ts");
}
const SONG_ID = "nh-s901-test";
const LEDGER_PATH = path.join(LEDGER_DIR, `${SONG_ID}.jsonl`);
const SEEDED_RECORDS = fs.readFileSync(path.join(FIXTURE_DIR, `ledger_${SONG_ID}.jsonl`), "utf8")
  .split("\n").filter(Boolean).length;

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

  // The pipeline service is served from the contract fixtures (tests/helpers/mockService.ts).
  // Two endpoints are overridden for this spec: adopt lands on the review stage, and shots
  // use the target shape (shot_id, song_id, c2pa_status) that the tracked service does not
  // return yet - see the notes on that entry in fixtures/service/contract.json.
  await mockPipelineService(page, {
    overrides: {
      "POST /pipeline/adopt": ADOPT_RESPONSE,
      "GET /pipeline/{run_id}/shots": JSON.parse(SHOTS_FIXTURE),
    },
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
  // The toast text is only shown when the review route answered ok (ledger appended).
  await expect(page.getByText("Approved — ledger updated")).toBeVisible({ timeout: 8000 });

  // Auto-advance (on by default) moves to the next take ~600 ms after a decision.
  // Wait for it, so the keys below act on a known take: take-001b, which has no decision yet.
  const approvedOverlay = page.getByText("✓ APPROVED", { exact: true });
  await expect(approvedOverlay).toBeHidden({ timeout: 5000 });

  // ── Take navigation: 'P' goes back to the approved take, 'N' forward again ──
  await page.keyboard.press("p");
  await expect(approvedOverlay).toBeVisible({ timeout: 3000 });
  await page.keyboard.press("n");
  await expect(approvedOverlay).toBeHidden({ timeout: 3000 });

  // ── REJECT the second take with keyboard shortcut 'R' ──
  await page.keyboard.press("r");
  const rejectDialog = page.locator("text=Reject take");
  await expect(rejectDialog).toBeVisible({ timeout: 3000 });

  // The hotkey must not leak into the autofocused reason field (an "r" there would
  // satisfy "reason required" without the reviewer typing one).
  const reasonTextarea = page.getByPlaceholder(/Reason for rejection/);
  await expect(reasonTextarea).toHaveValue("");

  // Confirm the reason textarea is required — button starts disabled.
  const confirmBtn = page.getByRole("button", { name: /Confirm reject/i });
  await expect(confirmBtn).toBeDisabled();

  // Type a reason into the textarea.
  await reasonTextarea.fill("Motion blur exceeds style kernel threshold — regenerate with slower shutter");
  await expect(confirmBtn).toBeEnabled();
  await confirmBtn.click();

  // Rejected toast should appear.
  await expect(page.getByText("Rejected — reason recorded")).toBeVisible({ timeout: 8000 });

  // ── Verify ledger chain_ok after the review session ──
  // The API route (Next.js server-side) appended records to the ledger file.
  // Wait for the async POSTs to complete (toasts confirm they did above).
  await page.waitForTimeout(1500);

  const chainOk = verifyChain(LEDGER_PATH);
  expect(chainOk).toBe(true);

  // Both decisions were appended (never rewritten) after the 2 seeded fixture records.
  const records = fs.readFileSync(LEDGER_PATH, "utf8").split("\n").filter(Boolean).map((l) => JSON.parse(l));
  expect(records.length).toBe(SEEDED_RECORDS + 2);
  expect(records.slice(-2).map((r) => r.approval?.state)).toEqual(["approved", "rejected"]);
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

  // No approve toast and no approved overlay should appear.
  await page.waitForTimeout(1500);
  await expect(page.getByText(/Approved — ledger updated|Approved \(no ledger/)).toHaveCount(0);
  await expect(page.getByText("✓ APPROVED", { exact: true })).toHaveCount(0);

  // The input value should contain 'a' (normal typing behaviour).
  await expect(noteInput).toHaveValue("a");
});
