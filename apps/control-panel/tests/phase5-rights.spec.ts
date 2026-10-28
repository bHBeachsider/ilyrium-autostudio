/**
 * Phase 5 — Rights & C2PA integration tests (ILY-205 Task 30)
 *
 * Verifies:
 *  - Every NH-S901 take shows a C2PA rights chip in the playlist
 *  - shot-003 (no takes) shows a "No takes" rights-gap badge in RightsPanel
 *  - Master export button is disabled while any shot has a gap
 *
 * Uses fixtures only — never touches production Neon (Decision B).
 */
import { test, expect } from "@playwright/test";
import * as path from "path";
import * as fs from "fs";

const FIXTURE_DIR = path.join(__dirname, "fixtures");

// Read fixture once at module level.
const SHOTS_FIXTURE = JSON.stringify(
  JSON.parse(fs.readFileSync(path.join(FIXTURE_DIR, "shots.json"), "utf8"))
);

// Tiny MP4 so video elements don't 404.
const TINY_MP4 = Buffer.from(
  "0000001c667479706d703432000000006d703432" +
  "6d703431000000086d646174",
  "hex"
);

const SONG_ID = "nh-s901-test";

const ADOPT_RESPONSE = {
  run_id: "nh-s901-fixture",
  state: {
    campaign_id: SONG_ID,
    stage: 5,
    status: "awaiting_approval",
    stages: {},
  },
};

test.beforeEach(async ({ page }) => {
  // Inject pipeline session so Workspace renders the review domain.
  await page.addInitScript((payload: string) => {
    try { localStorage.setItem("ilyrium.pipeline.session", payload); } catch {}
  }, JSON.stringify({ externalId: SONG_ID, view: 5 }));

  // Mock pipeline service endpoints.
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

  await page.route("**/pipeline/adopt", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(ADOPT_RESPONSE) });
  });

  // shots endpoint returns our fixture (3 shots, including shot-003 with no takes).
  await page.route("**/pipeline/*/shots", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: SHOTS_FIXTURE });
  });

  // Catch-all for other pipeline calls.
  await page.route("**/pipeline/**", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: "{}" });
  });

  // Serve tiny MP4 for fixture media.
  await page.route("**/tests/fixtures/media/**", async (route) => {
    await route.fulfill({ status: 200, contentType: "video/mp4", body: TINY_MP4 });
  });
});

// ── ILY-205-P5-01: C2PA chips appear on all takes in the Review Room ──────────

test("ILY-205-P5-01: C2PA chips visible for all takes in Review Room", async ({ page }) => {
  await page.goto("/studio/console");

  // Wait for Review Room to render (stage=5 from localStorage drives review domain).
  const reviewRoom = page.locator("text=REVIEW ROOM");
  await expect(reviewRoom).toBeVisible({ timeout: 20000 });

  // Playlist should be populated. Fixture has 3 takes (001a, 001b, 002a).
  // Each take with a c2pa_status should show a C2PA chip.
  // take-001a: c2pa_status=valid → "C2PA ✓"
  // take-001b: c2pa_status=missing → "C2PA ?"
  // take-002a: c2pa_status=valid → "C2PA ✓"
  const validChips = page.locator("[data-c2pa='valid']");
  const missingChips = page.locator("[data-c2pa='missing']");

  // At least 2 valid chips (001a and 002a) and 1 missing chip (001b).
  await expect(validChips.first()).toBeVisible({ timeout: 8000 });
  await expect(missingChips.first()).toBeVisible({ timeout: 5000 });

  // Count of valid chips should be >= 2.
  const validCount = await validChips.count();
  expect(validCount).toBeGreaterThanOrEqual(2);
});

// ── ILY-205-P5-02: Source & Licence panel shows C2PA status ──────────────────

test("ILY-205-P5-02: Source & Licence panel shows model and C2PA status", async ({ page }) => {
  await page.goto("/studio/console");

  const reviewRoom = page.locator("text=REVIEW ROOM");
  await expect(reviewRoom).toBeVisible({ timeout: 20000 });

  // Open the Source & Licence collapsible in the Inspector.
  const licenceToggle = page.getByRole("button", { name: /Source & Licence/i });
  await expect(licenceToggle).toBeVisible({ timeout: 5000 });
  await licenceToggle.click();

  // After opening, C2PA status should be visible in the panel.
  // First take (001a) has c2pa_status=valid and model="fal/wan-i2v".
  const c2paInPanel = page.locator("[data-c2pa]").filter({ hasText: /C2PA/ }).first();
  await expect(c2paInPanel).toBeVisible({ timeout: 3000 });

  // Model name should also appear.
  await expect(page.locator("text=fal/wan-i2v")).toBeVisible({ timeout: 3000 });
});

// ── ILY-205-P5-03: RightsPanel blocked badge + export gate ───────────────────

test("ILY-205-P5-03: shot-003 shows rights gap and master export is disabled", async ({ page }) => {
  await page.goto("/studio/console");

  // Navigate to the analytics domain which hosts RightsPanel.
  // The analytics nav item is in the left rail.
  const analyticsNav = page.locator("button, [role='button']").filter({ hasText: /Control Plane|analytics/i }).first();
  await expect(analyticsNav).toBeVisible({ timeout: 15000 });
  await analyticsNav.click();

  // Wait for RightsPanel header.
  const rightsHeader = page.locator("text=Rights & Deliver");
  await expect(rightsHeader).toBeVisible({ timeout: 10000 });

  // shot-003 has no takes → "No takes" / rights-gap badge.
  const noTakesBadge = page.locator("[data-rights='no-takes']");
  await expect(noTakesBadge).toBeVisible({ timeout: 5000 });

  // shot-001 has a take with c2pa_status=missing → also a rights gap.
  const gapBadge = page.locator("[data-rights='gap']");
  await expect(gapBadge).toBeVisible({ timeout: 5000 });

  // Export button must be disabled.
  const exportBtn = page.locator("button[data-deliver-blocked='true']");
  await expect(exportBtn).toBeVisible({ timeout: 3000 });
  await expect(exportBtn).toBeDisabled();

  // The "blocked" warning text should be visible.
  await expect(page.locator("text=/blocked — /i")).toBeVisible({ timeout: 3000 });
});

// ── ILY-205-P5-04: filter toggle hides cleared shots ─────────────────────────

test("ILY-205-P5-04: blocked-only filter shows only shots with rights gaps", async ({ page }) => {
  await page.goto("/studio/console");

  const analyticsNav = page.locator("button, [role='button']").filter({ hasText: /Control Plane|analytics/i }).first();
  await expect(analyticsNav).toBeVisible({ timeout: 15000 });
  await analyticsNav.click();

  const rightsHeader = page.locator("text=Rights & Deliver");
  await expect(rightsHeader).toBeVisible({ timeout: 10000 });

  // Enable "blocked only" filter.
  const blockedOnlyCheckbox = page.locator("input[aria-label='Show blocked only']");
  await expect(blockedOnlyCheckbox).toBeVisible({ timeout: 3000 });
  await blockedOnlyCheckbox.check();

  // shot-002 is clear (one take with valid C2PA) → must NOT be visible after filter.
  // shot-001 has a missing take and shot-003 has no takes → both should stay visible.
  const clearedBadge = page.locator("[data-rights='clear']");
  await expect(clearedBadge).not.toBeVisible({ timeout: 3000 });

  const gapBadge = page.locator("[data-rights='gap']");
  await expect(gapBadge).toBeVisible({ timeout: 3000 });
});
