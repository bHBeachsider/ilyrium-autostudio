/**
 * Console routing and key registry (ILY-206 Phase 1, tasks 11 and 13).
 *
 * Fixtures only: the page props come from fixtures/console.json and the pipeline service
 * from fixtures/service/contract.json, as in contract-smoke.spec.ts. The default 'ready'
 * adopt fixture polls and snaps the visible stage, so every test that walks stages adopts
 * with status awaiting_approval.
 */
import { test, expect, type Page } from "@playwright/test";
import * as fs from "fs";
import * as path from "path";
import { mockPipelineService, contract, FIXTURE_IDS, type MockService } from "./helpers/mockService";
import { PAGES } from "../app/studio/console/pages";
import { BINDINGS, cheatSheetRows } from "../app/studio/console/keys/registry";

const adoptFixture = contract.endpoints.find((e) => e.method === "POST" && e.path === "/pipeline/adopt")!
  .response as { run_id: string; state: Record<string, unknown> };
const adoptAt = (stage: number) => ({ ...adoptFixture, state: { ...adoptFixture.state, stage, status: "awaiting_approval" } });

// Target-shape shots (shot_id, song_id, c2pa_status): the review room gets ledger-writing takes.
const SHOTS = JSON.parse(fs.readFileSync(path.join(__dirname, "fixtures", "shots.json"), "utf8"));
const TINY_MP4 = Buffer.from("0000001c667479706d703432000000006d7034326d703431000000086d646174", "hex");

const nav = (page: Page) => page.getByRole("navigation").first();
const navButton = (page: Page, label: RegExp) => nav(page).getByRole("button", { name: label });
const countCalls = (svc: MockService, key: string) => svc.calls.filter((c) => c === key).length;

async function expectCall(svc: MockService, key: string, after = 0) {
  await expect
    .poll(() => svc.calls.slice(after).includes(key), { message: `waiting for ${key}`, timeout: 15000 })
    .toBe(true);
}

/** Opens the fixture project at `view`, as a returning user would, with a non-polling adopt. */
async function seedRun(page: Page, view: number, opts: { shots?: boolean } = {}) {
  await page.addInitScript((payload: string) => {
    try { localStorage.setItem("ilyrium.pipeline.session", payload); } catch {}
  }, JSON.stringify({ externalId: FIXTURE_IDS.campaign_id, view }));
  const overrides: Record<string, unknown> = { "POST /pipeline/adopt": adoptAt(view) };
  if (opts.shots) overrides["GET /pipeline/{run_id}/shots"] = SHOTS;
  const svc = await mockPipelineService(page, { overrides });
  await page.route("**/tests/fixtures/media/**", (route) =>
    route.fulfill({ status: 200, contentType: "video/mp4", body: TINY_MP4 }));
  return svc;
}

/** React and Next report hydration and Activity problems as console errors. */
function watchErrors(page: Page) {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("console", (m) => {
    if (m.type() === "error" && /hydrat|did not match|Activity|Warning:/i.test(m.text())) errors.push(m.text());
  });
  return errors;
}

// The review room's own toolbar, not the rail label (getByText is a case-insensitive substring).
const reviewToolbar = (page: Page) => page.getByText(/REVIEW ROOM · \d+ take/);

const blur = (page: Page) => page.evaluate(() => { (document.activeElement as HTMLElement)?.blur(); document.body.focus(); });

test("1. every slug loads by URL and survives a reload", async ({ page }) => {
  const errors = watchErrors(page);
  const svc = await mockPipelineService(page);
  // Each legacy page and what proves it rendered. `mark` is the call-log length taken just
  // before this load, so a service call counted here came from the page that just loaded.
  const proof: Record<string, (mark: number) => Promise<void>> = {
    // "New project from a director prompt" exists only inside Run (not in the shell), and
    // Run's mount effect lists runs: both only happen if Run really rendered.
    "run": async (mark) => {
      await expect(page.getByText("New project from a director prompt")).toBeVisible();
      await expectCall(svc, "GET /pipeline", mark);
    },
    "legacy-review": async () => { await expect(page.getByText(/REVIEW ROOM · \d+ take|No takes in the review queue/)).toBeVisible(); },
    "chat": async (mark) => {
      await expectCall(svc, "GET /box/status", mark);
    },
    "script": async () => { await expect(page.getByText(/ — Script$/).first()).toBeVisible(); },
    "legacy-generation": async () => { await expect(page.getByRole("heading", { name: /^Asset Generation/ })).toBeVisible(); },
    "legacy-assembly": async () => { await expect(page.getByRole("heading", { name: /^Timeline & Assembly/ })).toBeVisible(); },
    "analytics": async () => { await expect(page.getByText("Rights & Deliver")).toBeVisible(); },
  };
  for (const p of PAGES) {
    for (const load of ["goto", "reload"] as const) {
      // A blank page first, so nothing still polling from the previous page lands in the call log.
      if (p.kind === "placeholder" && load === "goto") await page.goto("about:blank");
      const mark = svc.calls.length;
      if (load === "goto") await page.goto(`/studio/console/${p.slug}`); else await page.reload();
      await expect(page).toHaveURL(new RegExp(`/studio/console/${p.slug}$`));
      await expect(nav(page).getByRole("button", { name: /^Pipeline/ })).toBeVisible();
      await expect(page.getByText("Page not found")).toHaveCount(0);
      if (p.kind === "placeholder") {
        await expect(page.locator(`[data-page="${p.slug}"]`)).toBeVisible();
        await expect(page.getByText(`Built in Phase ${p.phase}`)).toBeVisible();
        expect(svc.calls.slice(mark), `${p.slug} must make no service call`).toEqual([]);
      } else {
        await proof[p.slug](mark);
      }
    }
  }
  expect(svc.unmatched).toEqual([]);
  expect(svc.escaped).toEqual([]);
  expect(errors).toEqual([]);
});

test("2. / and /studio/console redirect to run with a 307", async ({ page, request }) => {
  await mockPipelineService(page);
  for (const from of ["/", "/studio/console"]) {
    const res = await request.get(from, { maxRedirects: 0 });
    expect(res.status(), from).toBe(307);
    expect(res.headers()["location"], from).toMatch(/\/studio\/console\/run$/);
    await page.goto(from);
    await expect(page).toHaveURL(/\/studio\/console\/run$/);
  }
});

test("3. an unknown slug shows the not-found page inside the shell", async ({ page, request }) => {
  await mockPipelineService(page);
  const res = await page.goto("/studio/console/bogus");
  // The shell stays: the rail is there and the not-found content is in the main area.
  await expect(navButton(page, /^Pipeline/)).toBeVisible();
  await expect(page.getByText("Page not found")).toBeVisible();
  // loading.tsx streams a fallback first, which pins the status to 200 with a noindex tag
  // (recorded in ILY-206-DECISIONS.md). Assert the 404 only if the response really is one.
  if (res!.status() !== 404) await expect(page.locator('meta[name="robots"][content="noindex"]').first()).toBeAttached();
  // A URL that matches no route is the root 404.
  expect((await request.get("/studio/console/run/extra")).status()).toBe(404);
});

test("4. run state survives leaving Run, with no re-adopt and a refetch on return", async ({ page }) => {
  const errors = watchErrors(page);
  const svc = await seedRun(page, 3);
  await page.goto("/studio/console/run");
  await expect(page.getByRole("heading", { name: "3. Storyboard" })).toBeVisible({ timeout: 20000 });
  // next dev runs mount effects twice (StrictMode), so a mount adopts once or twice. What
  // matters is that leaving and returning adds none.
  const adopts = countCalls(svc, "POST /pipeline/adopt");
  expect(adopts).toBeGreaterThanOrEqual(1);
  expect(adopts).toBeLessThanOrEqual(2);

  await navButton(page, /^Studio Control Plane/).click();
  await expect(page).toHaveURL(/\/analytics$/);
  await expect(page.getByText("Rights & Deliver")).toBeVisible();
  await expect(page.getByRole("heading", { name: "3. Storyboard" })).toBeHidden();

  const mark = svc.calls.length;
  await navButton(page, /^Pipeline/).click();
  await expect(page).toHaveURL(/\/run$/);
  // No re-adopt and no nav click needed: the stage is still the one we left.
  await expect(page.getByRole("heading", { name: "3. Storyboard" })).toBeVisible();
  await expectCall(svc, "GET /pipeline", mark);
  expect(countCalls(svc, "POST /pipeline/adopt")).toBe(adopts);
  expect(errors).toEqual([]);
});

test("4b. the stepper hands off to Run once, and later reveals do not adopt again", async ({ page }) => {
  const svc = await mockPipelineService(page, { overrides: { "POST /pipeline/adopt": adoptAt(5) } });
  await page.route("**/tests/fixtures/media/**", (route) => route.fulfill({ status: 200, contentType: "video/mp4", body: TINY_MP4 }));
  await page.goto("/studio/console/analytics");    // Run is mounted hidden: no service call yet
  await expect(page.getByText("Rights & Deliver")).toBeVisible();
  expect(countCalls(svc, "POST /pipeline/adopt")).toBe(0);

  await page.getByTitle("Open the Review workspace").click();
  await expect(page).toHaveURL(/\/run$/);
  await expect(page.getByRole("heading", { name: "5. Review" })).toBeVisible({ timeout: 20000 });
  const adopts = countCalls(svc, "POST /pipeline/adopt");    // once, or twice under next dev's StrictMode
  expect(adopts).toBeGreaterThanOrEqual(1);
  expect(adopts).toBeLessThanOrEqual(2);

  await navButton(page, /^Studio Control Plane/).click();
  await expect(page.getByText("Rights & Deliver")).toBeVisible();
  const mark = svc.calls.length;
  await navButton(page, /^Pipeline/).click();
  await expectCall(svc, "GET /pipeline", mark);
  await expect(page.getByRole("heading", { name: "5. Review" })).toBeVisible();
  expect(countCalls(svc, "POST /pipeline/adopt")).toBe(adopts);
});

test("4c. a hand-off to a different project drops the held run while it adopts, and keeps the Opening hint", async ({ page }) => {
  // Run holds the fixture campaign (nh-s901-test) at stage 3. The console's selected project
  // is "NH-S901 fixture", a different id, so the stepper hand-off targets another project.
  await seedRun(page, 3);
  await page.goto("/studio/console/run");
  await expect(page.getByRole("heading", { name: "3. Storyboard" })).toBeVisible({ timeout: 20000 });
  await page.getByRole("navigation").first().getByRole("button", { name: /^Studio Control Plane/ }).click();
  await expect(page.getByText("Rights & Deliver")).toBeVisible();

  // Gate the adopt for the new project, so the in-between state can be looked at.
  let release: () => void = () => {};
  const gate = new Promise<void>((r) => { release = r; });
  let handoffAdopts = 0;
  await page.route((url) => url.origin === contract.default_origin && url.pathname === "/pipeline/adopt", async (route) => {
    if (route.request().method() === "OPTIONS") return route.fulfill({ status: 204, headers: { "access-control-allow-origin": "*", "access-control-allow-headers": "*", "access-control-allow-methods": "GET,POST,OPTIONS" } });
    handoffAdopts++;
    await gate;
    await route.fulfill({ status: 200, contentType: "application/json", headers: { "access-control-allow-origin": "*" }, body: JSON.stringify(adoptAt(5)) });
  });

  await page.getByTitle("Open the Review workspace").click();
  await expect(page).toHaveURL(/\/run$/);
  await expect.poll(() => handoffAdopts, { timeout: 15000 }).toBeGreaterThan(0);
  // While the new project is being adopted, the old project's workspace is neither shown
  // nor actionable (no stage heading, no stage panels), and the hint names the new project.
  await expect(page.getByText(/^Opening /)).toBeVisible();
  await expect(page.getByText(/^Opening NH-S901 fixture/)).toBeVisible();
  await expect(page.getByRole("heading", { name: /^\d+\. / })).toHaveCount(0);
  await expect(page.getByRole("button", { name: /^(Approve|Save|Run)/ })).toHaveCount(0);

  release();
  await expect(page.getByRole("heading", { name: "5. Review" })).toBeVisible({ timeout: 20000 });
  await expect(page.getByText(/^Opening /)).toHaveCount(0);
});

test("4d. Run's message banner is cleared when Run is shown again", async ({ page }) => {
  await mockPipelineService(page, { overrides: { "POST /pipeline/start": () => ({ status: 500, json: { error: "start failed on purpose" } }) } });
  await page.goto("/studio/console/run");
  await page.getByPlaceholder(/punchy 15s/).fill("a short test film");
  await page.getByRole("button", { name: "Spin up project" }).click();
  await expect(page.getByText("start failed on purpose")).toBeVisible();

  await navButton(page, /^Studio Control Plane/).click();
  await expect(page.getByText("Rights & Deliver")).toBeVisible();
  await navButton(page, /^Pipeline/).click();
  await expect(page.getByText("New project from a director prompt")).toBeVisible();
  await expect(page.getByText("start failed on purpose")).toHaveCount(0);
});

test("5. Alt+ArrowLeft is left to the browser, and history walks back through pages", async ({ page }) => {
  await seedRun(page, 5, { shots: true });
  await page.goto("/studio/console/run");
  await expect(reviewToolbar(page)).toBeVisible({ timeout: 20000 });   // review scope is live
  await page.evaluate(() => {
    (window as any).__prevented = [];
    window.addEventListener("keydown", (e) => { if (e.key.startsWith("Arrow")) (window as any).__prevented.push([e.key, e.altKey, e.defaultPrevented]); });
  });
  await blur(page);
  await page.keyboard.press("Alt+ArrowLeft");
  await page.keyboard.press("Alt+ArrowRight");
  expect(await page.evaluate(() => (window as any).__prevented)).toEqual([["ArrowLeft", true, false], ["ArrowRight", true, false]]);

  await navButton(page, /^Studio Control Plane/).click();
  await expect(page).toHaveURL(/\/analytics$/);
  await page.goBack();
  await expect(page).toHaveURL(/\/run$/);
  await expect(reviewToolbar(page)).toBeVisible();
  await page.goForward();
  await expect(page).toHaveURL(/\/analytics$/);
});

test("6. 'a' approves nothing unless the review stage is the visible surface", async ({ page }) => {
  const reviewPosts: string[] = [];
  let answer: "ok" | "forbidden" = "forbidden";
  await page.route("**/api/studio/review", async (route) => {
    reviewPosts.push(route.request().method());
    if (answer === "ok") return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ chain_ok: true }) });
    await route.fulfill({ status: 500, contentType: "application/json", body: JSON.stringify({ error: "must not be called" }) });
  });

  // Phase A, the dangerous state: Run on stage 5 with a take loaded, then leave Run.
  await seedRun(page, 5, { shots: true });
  await page.goto("/studio/console/run");
  await expect(reviewToolbar(page)).toBeVisible({ timeout: 20000 });
  await expect(page.locator("video[src*='take-001a']")).toBeAttached();
  await blur(page);
  // Positive control: here 'a' must produce exactly one review request, and it succeeds.
  answer = "ok";
  await page.keyboard.press("a");
  await expect(page.getByText("Approved — ledger updated")).toBeVisible({ timeout: 8000 });
  expect(reviewPosts, "positive control on the visible review stage").toEqual(["POST"]);

  // Leave Run through the palette. Run stays mounted (hidden) with the take still loaded.
  answer = "forbidden";
  await page.keyboard.press("Control+k");
  await page.getByPlaceholder("Type a command…").fill("library");
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/\/library$/);
  await expect(page.locator('[data-page="library"]')).toBeVisible();
  await expect(page.locator("video[src*='take-001a']")).toBeHidden();
  await blur(page);
  await page.keyboard.press("a");
  await page.waitForTimeout(500);
  expect(reviewPosts, "'a' on library after leaving review stage 5").toEqual(["POST"]);
  await page.keyboard.press("Control+k");
  await page.getByPlaceholder("Type a command…").fill("analytics");
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/\/analytics$/);
  await blur(page);
  await page.keyboard.press("a");
  await page.waitForTimeout(500);
  expect(reviewPosts, "'a' on a legacy page after leaving review stage 5").toEqual(["POST"]);
});

test("6b. 'a' approves nothing on stage 3, after leaving Run, or on a fresh deep link", async ({ page }) => {
  const reviewPosts: string[] = [];
  await page.route("**/api/studio/review", async (route) => {
    reviewPosts.push(route.request().method());
    await route.fulfill({ status: 500, contentType: "application/json", body: JSON.stringify({ error: "must not be called" }) });
  });
  const svc = await seedRun(page, 3, { shots: true });
  await page.goto("/studio/console/run");
  await expect(page.getByRole("heading", { name: "3. Storyboard" })).toBeVisible({ timeout: 20000 });
  await expectCall(svc, "GET /pipeline/{run_id}/shots");
  // The hidden review panel has rendered its takes: this is the state the old document
  // listener approved from.
  await expect(page.locator("video[src*='take-001a']")).toBeAttached();
  await blur(page);
  await page.keyboard.press("a");
  await page.waitForTimeout(500);
  expect(reviewPosts, "run stage 3").toEqual([]);

  await page.keyboard.press("Control+k");
  await page.getByPlaceholder("Type a command…").fill("library");
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/\/library$/);
  await expect(page.locator('[data-page="library"]')).toBeVisible();
  await blur(page);
  await page.keyboard.press("a");
  await page.waitForTimeout(500);
  expect(reviewPosts, "library after leaving run").toEqual([]);

  // And a fresh deep link: Run mounts hidden, with no session loaded.
  await page.goto("/studio/console/library");
  await expect(page.locator('[data-page="library"]')).toBeVisible();
  await page.keyboard.press("a");
  await page.waitForTimeout(500);
  expect(reviewPosts, "library deep link").toEqual([]);
});

test("7. Ctrl+K never pauses the video, and leaving Run pauses media", async ({ page }) => {
  await page.addInitScript(() => {
    (window as any).__pauses = 0;
    const orig = HTMLMediaElement.prototype.pause;
    HTMLMediaElement.prototype.pause = function (...a: []) { (window as any).__pauses++; return orig.apply(this, a); };
  });
  await seedRun(page, 5, { shots: true });
  await page.goto("/studio/console/run");
  await expect(reviewToolbar(page)).toBeVisible({ timeout: 20000 });
  await expect(page.locator("video[src*='take-001a']")).toBeAttached();
  await page.evaluate(() => { (window as any).__pauses = 0; });
  await blur(page);

  await page.keyboard.press("Control+k");
  await expect(page.getByPlaceholder("Type a command…")).toBeVisible();
  expect(await page.evaluate(() => (window as any).__pauses)).toBe(0);
  await page.keyboard.press("Escape");
  await expect(page.getByPlaceholder("Type a command…")).toBeHidden();

  await navButton(page, /^Studio Control Plane/).click();
  await expect(page.getByText("Rights & Deliver")).toBeVisible();
  expect(await page.evaluate(() => (window as any).__pauses)).toBeGreaterThan(0);
});

test("8. the cheat sheet is the registry: one overlay, every row live", async ({ page }) => {
  await seedRun(page, 5, { shots: true });
  await page.goto("/studio/console/run");
  await expect(reviewToolbar(page)).toBeVisible({ timeout: 20000 });
  await blur(page);

  await page.keyboard.press("?");
  const sheet = page.getByTestId("cheat-sheet");
  await expect(sheet).toHaveCount(1);
  const ids = await page.locator("[data-binding-id]").evaluateAll((els) => els.map((e) => e.getAttribute("data-binding-id")));
  expect(ids).toEqual(cheatSheetRows(BINDINGS).map((r) => r.id));
  const text = (await sheet.textContent()) ?? "";
  expect(text).not.toMatch(/jump to stage/i);
  expect(text).not.toMatch(/waveform/i);
  expect(text).toMatch(/Play at half speed/);
  // The review room's old second overlay is gone: still exactly one.
  await expect(page.getByText("slow reverse")).toHaveCount(0);

  await page.keyboard.press("?");
  await expect(sheet).toHaveCount(0);

  // With the palette open (palette scope) and the review stage visible (review scope), every
  // binding that has a key must have a registered handler. A row with no handler fails here.
  await page.keyboard.press("Control+k");
  await expect(page.getByPlaceholder("Type a command…")).toBeVisible();
  const dead = await page.evaluate((all: string[]) => all.filter((id) => !(window as any).__ilyriumKeys.has(id)), ids as string[]);
  expect(dead, "bindings with a key but no live handler").toEqual([]);
  await expect(page.getByRole("button", { name: "Go to Ideation & Scripting" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Go to Studio Control Plane" })).toBeVisible();
});

test("9. the Ctrl+K button opens the palette by click, and a command navigates", async ({ page }) => {
  await mockPipelineService(page);
  await page.goto("/studio/console/run");
  await page.getByTitle("Ctrl+K to open command palette").click();
  const input = page.getByPlaceholder("Type a command…");
  await expect(input).toBeVisible();
  await input.fill("library");
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/\/studio\/console\/library$/);
  await expect(page.locator('[data-page="library"]')).toBeVisible();
  await expect(input).toBeHidden();
});
