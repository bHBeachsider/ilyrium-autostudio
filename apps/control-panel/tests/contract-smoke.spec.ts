/**
 * Contract smoke test (ILY-206 Phase 0 task 9).
 *
 * Loads the console on fixtures only - the page props from fixtures/console.json and the
 * pipeline service from fixtures/service/contract.json - then walks every Pipeline stage
 * and every left-rail domain. It proves:
 *   1. the console renders with no Python service, no database and no GPU box;
 *   2. the requests each page makes when it mounts are served by contract fixtures:
 *      none falls through to the 501 "no fixture" answer and none leaves for another
 *      origin;
 *   3. nothing throws while the pages mount.
 * It does not exercise button actions; lib/serviceContract.test.ts is the guard that
 * every service path in the console source, mount-time or not, has a fixture.
 *
 * Uses fixtures only - never touches production Neon (Decision B).
 */
import { test, expect } from "@playwright/test";
import { mockPipelineService, contract, FIXTURE_IDS, type MockService } from "./helpers/mockService";

const STAGES = ["Brief", "Script", "Storyboard", "Asset Gen", "Review", "Assembly", "Rights/Release", "Delivery/Archive"];

// The adopt fixture mirrors the service and returns status "ready", which makes the
// console poll the run every 3 s and snap the visible stage back to the run's current
// stage. To walk the stages deterministically this spec adopts with a status that does
// not poll.
const adoptFixture = contract.endpoints.find((e) => e.method === "POST" && e.path === "/pipeline/adopt")!
  .response as { run_id: string; state: Record<string, unknown> };
const STABLE_ADOPT = { ...adoptFixture, state: { ...adoptFixture.state, status: "awaiting_approval" } };

/** Wait until the page has made the named service call (again, if `after` is given). */
async function expectCall(svc: MockService, key: string, after = 0) {
  await expect
    .poll(() => svc.calls.slice(after).includes(key), { message: `waiting for ${key}`, timeout: 15000 })
    .toBe(true);
}

test("every stage and domain renders on contract fixtures with no unmatched service call", async ({ page }) => {
  const pageErrors: string[] = [];
  page.on("pageerror", (e) => pageErrors.push(e.message));

  // Open the fixture project at stage 1, as a returning user would.
  await page.addInitScript((payload: string) => {
    try { localStorage.setItem("ilyrium.pipeline.session", payload); } catch {}
  }, JSON.stringify({ externalId: FIXTURE_IDS.campaign_id, view: 1 }));

  const svc = await mockPipelineService(page, { overrides: { "POST /pipeline/adopt": STABLE_ADOPT } });
  await page.goto("/studio/console");

  // The stage rail only renders once the run has been adopted from the service.
  const rail = (n: number) => page.getByRole("button", { name: `${n} ${STAGES[n - 1]}` });
  await expect(rail(1)).toBeVisible({ timeout: 20000 });
  await expectCall(svc, "POST /pipeline/adopt");
  await expectCall(svc, "GET /pipeline");

  for (let n = 1; n <= STAGES.length; n++) {
    await rail(n).click();
    await expect(page.getByRole("heading", { name: `${n}. ${STAGES[n - 1]}` })).toBeVisible();
  }
  // All stage panels mount with the run, so their load calls have gone out by now.
  for (const key of [
    "GET /pipeline/{run_id}", "GET /pipeline/{run_id}/shots", "GET /pipeline/{run_id}/cut",
    "GET /pipeline/{run_id}/script", "GET /pipeline/{run_id}/storyboard",
    "GET /pipeline/{run_id}/models", "GET /pipeline/{run_id}/conformance",
    "GET /stage/{project}/{stage}/checklist",
  ]) {
    await expectCall(svc, key);
  }

  // Each domain: click it, then wait for the call that proves it mounted and loaded.
  const nav = page.getByRole("navigation").first();
  const open = (label: RegExp) => nav.getByRole("button", { name: label }).click();

  await open(/^Review Room/);
  await expect(page.getByText("REVIEW ROOM").first()).toBeVisible();

  let mark = svc.calls.length;
  await open(/^Studio Chat/);
  await expectCall(svc, "GET /box/status", mark);

  await open(/^Ideation & Scripting/);
  await open(/^Asset Generation/);
  await open(/^Timeline & Assembly/);

  mark = svc.calls.length;
  await open(/^Studio Control Plane/);
  await expectCall(svc, "GET /pipeline/jobs", mark);
  await expect(page.getByText("Rights & Deliver")).toBeVisible();

  mark = svc.calls.length;
  await open(/^Pipeline/);
  await expectCall(svc, "GET /pipeline", mark);

  expect(svc.unmatched, "service requests with no contract fixture").toEqual([]);
  expect(svc.escaped, "requests to an origin that is neither the app nor the mock").toEqual([]);
  expect(pageErrors, "uncaught errors in the page").toEqual([]);
});

test("target shapes can be switched on per endpoint", async ({ page }) => {
  const svc = await mockPipelineService(page, { target: ["GET /pipeline/jobs"] });
  await page.goto("/studio/console");

  // The queue rail lives on the Control Plane. With the tracked service's 404 it shows
  // an idle queue; with the target shape it lists the fixture jobs.
  await page.getByRole("navigation").first().getByRole("button", { name: /^Studio Control Plane/ }).click();
  await expectCall(svc, "GET /pipeline/jobs");
  await expect(page.getByText(/Queue is idle/)).toHaveCount(0);
  await expect(page.getByText("render_shot").first()).toBeVisible({ timeout: 15000 });
  expect(svc.unmatched).toEqual([]);
  expect(svc.escaped).toEqual([]);
});

test("without the target shape the queue rail is idle, as with the real service today", async ({ page }) => {
  const svc = await mockPipelineService(page);
  await page.goto("/studio/console");
  await page.getByRole("navigation").first().getByRole("button", { name: /^Studio Control Plane/ }).click();
  await expectCall(svc, "GET /pipeline/jobs");
  await expect(page.getByText(/Queue is idle/)).toBeVisible({ timeout: 15000 });
});
