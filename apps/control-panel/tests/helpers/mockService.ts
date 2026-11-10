// Serves tests/fixtures/service/contract.json in place of the Python pipeline service,
// so browser tests need no service, database or GPU box (ILY-206 Phase 0 task 9).
//
//   const svc = await mockPipelineService(page, {
//     overrides: { "GET /pipeline/{run_id}/shots": shotsFixture },   // a body, or
//     target: ["GET /pipeline/jobs"],                                 // the target shape
//   });
//   ... drive the page ...
//   expect(svc.unmatched).toEqual([]);
//
// By default each endpoint answers the way the TRACKED service does, including 404 for
// routes the console calls but the service does not implement. `target` switches named
// endpoints to the shape the console expects instead. Any request to the service origin
// that no contract entry covers is answered 501 and recorded in `unmatched`, so a test
// can assert that nothing fell through.
//
// Nothing reaches a real service: every request to the mocked origin is fulfilled here,
// playwright.config.ts pins the console's service URL to that origin, and a request to
// any other origin is aborted and recorded in `escaped`.

import type { Page, Route } from "@playwright/test";
import * as fs from "fs";
import * as path from "path";

type Endpoint = {
  method: string; path: string; status: number; tracked: boolean;
  response?: unknown; text?: string; binary?: string;
  /** Alternative bodies selected by the request body's `op`; `response` is the fallback. */
  response_by_op?: Record<string, unknown>;
  target_response?: unknown; target_binary?: string;
};
type Contract = { default_origin: string; fixture_ids: { run_id: string; campaign_id: string }; endpoints: Endpoint[] };

export const contract: Contract = JSON.parse(
  fs.readFileSync(path.join(__dirname, "..", "fixtures", "service", "contract.json"), "utf8"),
);
export const FIXTURE_IDS = contract.fixture_ids;

/** A JSON body, or a function of the request that returns { status?, json }. */
export type Override =
  | unknown
  | ((req: { method: string; url: URL; body: unknown }) => { status?: number; json: unknown });

export type MockService = {
  /** "METHOD /path" of every request served, in order. */
  calls: string[];
  /** Requests to the service origin that no contract entry covers. Should stay empty. */
  unmatched: string[];
  /** Requests to any other origin (not the app, not the mock). Aborted. Should stay empty. */
  escaped: string[];
};

// Smallest bodies that browsers accept without erroring.
const TINY_MP4 = Buffer.from("0000001c667479706d703432000000006d7034326d703431000000086d646174", "hex");
const TINY_PNG = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==",
  "base64",
);

function binaryFor(url: URL): { contentType: string; body: Buffer } {
  const name = (url.searchParams.get("rel") ?? url.pathname).toLowerCase();
  if (/\.(mp4|mov|webm|mkv)$/.test(name)) return { contentType: "video/mp4", body: TINY_MP4 };
  if (/\.(mp3|wav|m4a|ogg)$/.test(name)) return { contentType: "audio/mpeg", body: Buffer.alloc(0) };
  return { contentType: "image/png", body: TINY_PNG };
}

function toSegments(p: string): string[] {
  return p.split("/").filter(Boolean);
}
function pathMatches(pattern: string, pathname: string): boolean {
  const a = toSegments(pattern);
  const b = toSegments(pathname);
  return a.length === b.length && a.every((s, i) => s.startsWith("{") || s === b[i]);
}
// Literal paths beat parameterised ones, so "/pipeline/jobs" is not swallowed by
// "/pipeline/{run_id}" (which is exactly what happens in the real route table; the
// contract entry for /pipeline/jobs records that by answering 404).
function specificity(e: Endpoint): number {
  return toSegments(e.path).filter((s) => !s.startsWith("{")).length;
}

const CORS = {
  "access-control-allow-origin": "*",
  "access-control-allow-headers": "*",
  "access-control-allow-methods": "GET,POST,OPTIONS",
};

export async function mockPipelineService(
  page: Page,
  opts: { overrides?: Record<string, Override>; target?: string[]; origin?: string } = {},
): Promise<MockService> {
  const origin = opts.origin ?? contract.default_origin;
  const overrides = opts.overrides ?? {};
  const target = new Set(opts.target ?? []);
  const known = new Set(contract.endpoints.map((e) => `${e.method} ${e.path}`));
  for (const key of [...Object.keys(overrides), ...target]) {
    if (!known.has(key)) throw new Error(`mockPipelineService: "${key}" is not in contract.json`);
  }
  const ordered = [...contract.endpoints].sort((a, b) => specificity(b) - specificity(a));
  const svc: MockService = { calls: [], unmatched: [], escaped: [] };

  // Guard, registered first so the service route below takes precedence: any http(s)
  // request that goes to neither the app nor the mocked service is aborted and recorded.
  // This is what makes "never reaches a real service" true even if the console was
  // built against a different service URL.
  const appOrigin = process.env.PW_APP_ORIGIN;
  if (!appOrigin) throw new Error("mockPipelineService: PW_APP_ORIGIN is not set - run via playwright.config.ts");
  await page.route(
    (url) => /^https?:$/.test(url.protocol) && url.origin !== appOrigin && url.origin !== origin,
    async (route: Route) => {
      svc.escaped.push(`${route.request().method()} ${route.request().url()}`);
      await route.abort("blockedbyclient");
    },
  );

  await page.route(
    (url) => url.origin === origin,
    async (route: Route) => {
      const req = route.request();
      const url = new URL(req.url());
      const method = req.method();
      if (method === "OPTIONS") return route.fulfill({ status: 204, headers: CORS });

      const ep = ordered.find((e) => e.method === method && pathMatches(e.path, url.pathname));
      if (!ep) {
        svc.unmatched.push(`${method} ${url.pathname}`);
        return route.fulfill({
          status: 501, headers: CORS, contentType: "application/json",
          body: JSON.stringify({ error: `no contract fixture for ${method} ${url.pathname}` }),
        });
      }
      const key = `${ep.method} ${ep.path}`;
      svc.calls.push(key);

      if (key in overrides) {
        const o = overrides[key];
        let body: unknown = null;
        try { body = req.postDataJSON(); } catch { /* not JSON */ }
        const out = typeof o === "function"
          ? (o as (r: { method: string; url: URL; body: unknown }) => { status?: number; json: unknown })({ method, url, body })
          : { json: o };
        return route.fulfill({
          status: out.status ?? 200, headers: CORS, contentType: "application/json",
          body: JSON.stringify(out.json),
        });
      }

      const useTarget = target.has(key);
      if ((useTarget && ep.target_binary) || (!useTarget && ep.binary)) {
        const bin = binaryFor(url);
        return route.fulfill({ status: 200, headers: CORS, contentType: bin.contentType, body: bin.body });
      }
      if (useTarget) {
        return route.fulfill({
          status: 200, headers: CORS, contentType: "application/json",
          body: JSON.stringify(ep.target_response),
        });
      }
      // One path, several response shapes keyed by the request body's `op`.
      if (ep.response_by_op) {
        let op: unknown;
        try { op = (req.postDataJSON() as { op?: unknown } | null)?.op; } catch { /* not JSON */ }
        if (typeof op === "string" && op in ep.response_by_op) {
          return route.fulfill({
            status: ep.status, headers: CORS, contentType: "application/json",
            body: JSON.stringify(ep.response_by_op[op]),
          });
        }
      }
      if (ep.text !== undefined) {
        return route.fulfill({ status: ep.status, headers: CORS, contentType: "text/plain", body: ep.text });
      }
      return route.fulfill({
        status: ep.status, headers: CORS, contentType: "application/json",
        body: JSON.stringify(ep.response),
      });
    },
  );
  return svc;
}
