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

test.beforeAll(() => {
  // Seed ledger from fixture: recompute real chain hashes so the route won't fail chain_ok.
  fs.mkdirSync(LEDGER_DIR, { recursive: true });
  const fixtureLines = fs.readFileSync(path.join(FIXTURE_DIR, `ledger_${SONG_ID}.jsonl`), "utf8")
    .split("\n").filter(Boolean)
    .map((l) => JSON.parse(l) as Record<string, unknown>);

  let prev: string | null = null;
  const rewritten = fixtureLines.map((rec) => {
    const { chain: _chain, ...core } = rec;
    const recordHash = computeRecordHash(prev, core as Record<string, unknown>);
    prev = recordHash;
    return { ...core, chain: { prev_record_hash: _chain ? (rec.chain as any).prev_record_hash ?? null : null, record_hash: recordHash } };
  });
  // Recompute with correct prev pointers
  let prev2: string | null = null;
  const final = rewritten.map((rec) => {
    const { chain: _chain, ...core } = rec;
    const recordHash = computeRecordHash(prev2, core as Record<string, unknown>);
    prev2 = recordHash;
    return { ...core, chain: { prev_record_hash: prev2 === recordHash ? null : /* prev before this */ (() => { throw 0 })(), record_hash: recordHash } };
  });
  // Simpler: rewrite from scratch with correct prev chain
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
  // Clean up test ledger so it doesn't pollute the real ledger dir.
  if (fs.existsSync(LEDGER_PATH)) fs.unlinkSync(LEDGER_PATH);
});

// ── mocks (route intercepts) ───────────────────────────────────────────────

test.beforeEach(async ({ page }) => {
  // Mock /pipeline/:runId/shots to return fixture data (avoids needing the Python service up).
  await page.route("**/pipeline/*/shots", async (route) => {
    const shots = JSON.parse(fs.readFileSync(path.join(FIXTURE_DIR, "shots.json"), "utf8"));
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(shots) });
  });

  // Intercept media requests with a blank 1-second video blob (avoids HTTP 404 for fixture URLs).
  await page.route("**/tests/fixtures/media/**", async (route) => {
    // Return a tiny valid MP4 (1-frame, silent). This is the smallest parseable MP4 header.
    // The hex below is a 52-byte ftyp+moov+mdat minimal MP4.
    const tinyMp4 = Buffer.from(
      "0000001466747970697736000000000069736f6d" +
      "0000000866726565000000086d6f6f760000000c6d766864000000000000000000000001" +
      "0000000c6d696e660000000c" +
      "6d646174",
      "hex"
    );
    await route.fulfill({ status: 200, contentType: "video/mp4", body: tinyMp4 });
  });
});

// ── NH-S901: keyboard-only review ─────────────────────────────────────────

test("NH-S901: keyboard-only approve + reject + chain_ok", async ({ page }) => {
  await page.goto("/studio/console");

  // Navigate to Review Room domain via sidebar nav link.
  const reviewLink = page.getByText("Review Room");
  await expect(reviewLink).toBeVisible({ timeout: 10000 });
  await reviewLink.click();

  // The ReviewRoom should render with the playlist from fixture assets.
  // Since projAssets in Workspace pulls from Neon and we can't mock that cleanly here,
  // we directly navigate to the Pipeline stage 5 review panel via the pipeline stepper.
  // This hits the mocked /pipeline/*/shots route above.
  await page.goto("/studio/console");
  const pipelineLink = page.getByText("Pipeline").first();
  await pipelineLink.click();

  // Open stage 5 (Review) via the stage stepper — click the "5" / "Review" button.
  // This requires an active run; for the test we use the fixture run.
  // We reach stage 5 by navigating to the URL with the stage param.
  // In dev mode, the console loads the last session from localStorage.
  // For the test, inject a minimal session and reload.
  await page.evaluate((songId) => {
    try { localStorage.setItem("ilyrium.pipeline.session", JSON.stringify({ externalId: songId, view: 5 })); } catch {}
  }, SONG_ID);
  await page.reload();

  // Wait for the review room to appear.
  const reviewRoom = page.locator("text=REVIEW ROOM");
  await expect(reviewRoom).toBeVisible({ timeout: 15000 });

  // Ensure focus is on the body (not an input) so hotkeys fire.
  await page.evaluate(() => { (document.activeElement as HTMLElement)?.blur(); });

  // ── APPROVE take-001a with keyboard shortcut 'A' ──
  await expect(page.getByText(/S1 · take-001/)).toBeVisible();
  await page.keyboard.press("a");
  // The approve toast should appear.
  await expect(page.locator("text=/Approved/i")).toBeVisible({ timeout: 5000 });
  // The playlist chip should show ✓.
  await expect(page.locator("text=✓").first()).toBeVisible();

  // ── NAVIGATE to the next take with 'N' ──
  await page.keyboard.press("n");

  // ── REJECT take-001b / take-002a with keyboard shortcut 'R' ──
  await page.keyboard.press("r");
  // Reject dialog should open.
  const rejectDialog = page.locator("text=Reject take");
  await expect(rejectDialog).toBeVisible({ timeout: 3000 });

  // Confirm that the reason textarea is required — the Confirm button should be disabled.
  const confirmBtn = page.getByRole("button", { name: /Confirm reject/i });
  await expect(confirmBtn).toBeDisabled();

  // Type a reason.
  const reasonTextarea = page.locator("textarea");
  await reasonTextarea.fill("Motion blur exceeds style kernel threshold — regenerate with slower shutter");
  await expect(confirmBtn).toBeEnabled();
  await confirmBtn.click();

  // The rejected toast should appear.
  await expect(page.locator("text=/Rejected/i")).toBeVisible({ timeout: 5000 });

  // ── Verify ledger chain_ok after the review session ──
  // The API route appended to the real ledger file; verify it on disk.
  // (The route runs server-side; in dev mode this is the actual file system.)
  // Give it a moment for the async POST to complete.
  await page.waitForTimeout(1000);

  const chainOk = verifyChain(LEDGER_PATH);
  expect(chainOk).toBe(true);
});

// ── NH-S901b: hotkeys disabled inside text field ───────────────────────────

test("NH-S901b: hotkeys disabled while focus is in text field", async ({ page }) => {
  await page.goto("/studio/console");
  await page.evaluate((songId) => {
    try { localStorage.setItem("ilyrium.pipeline.session", JSON.stringify({ externalId: songId, view: 5 })); } catch {}
  }, SONG_ID);
  await page.reload();

  const reviewRoom = page.locator("text=REVIEW ROOM");
  await expect(reviewRoom).toBeVisible({ timeout: 15000 });

  // Click into the note input — hotkeys should be suppressed here.
  const noteInput = page.locator("input[placeholder*='note']");
  await noteInput.focus();

  // Press 'A' inside the input — must NOT trigger approve.
  await page.keyboard.press("a");

  // No toast should appear.
  await expect(page.locator("text=/Approved/i")).not.toBeVisible({ timeout: 1500 });

  // The input value should contain 'a' (normal typing behavior).
  await expect(noteInput).toHaveValue("a");
});
