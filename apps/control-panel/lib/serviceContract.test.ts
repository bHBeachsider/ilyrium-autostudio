// Drift guard for tests/fixtures/service/contract.json (ILY-206 Phase 0 task 9).
//
// The contract lists every pipeline-service request the console makes, with a fixture
// response. This test reads the console source and fails when:
//   - the console calls a service path that has no contract entry (a new fetch was
//     added without a fixture, so the browser tests would silently hit nothing), or
//   - a contract entry is no longer called from anywhere (a stale fixture), or
//   - an entry is malformed.
// It checks paths only, not methods or bodies. Whether a response matches the real
// service is a provider test, which cannot exist until the service is importable from
// git (spec decision D1).

import { describe, it, expect } from "vitest";
import { readdirSync, readFileSync } from "fs";
import { join, resolve } from "path";

const APP = resolve(__dirname, "..");
const CONSOLE_DIR = join(APP, "app", "studio", "console");
const contract = JSON.parse(
  readFileSync(join(APP, "tests", "fixtures", "service", "contract.json"), "utf8"),
) as { endpoints: Endpoint[] };

type Endpoint = {
  method: string; path: string; status: number; tracked: boolean;
  response?: unknown; text?: string; binary?: string;
  target_response?: unknown; target_binary?: string;
  callers: string[]; handler: string;
  /** Set when the console only reaches this path through a URL in another response. */
  via_response_of?: string;
};

const PLACEHOLDER = /\$\{[\w.]+\}/g; // `${runId}`, `${s.scene_number}`

// "/pipeline/{run_id}/shots" and "/pipeline/${runId}/shots" both become
// ["pipeline", "*", "shots"]. A placeholder only matches a placeholder and a literal only
// the same literal, so "/pipeline/jobs" in the console does not count as covered by
// "/pipeline/{run_id}" in the contract (the real route table makes exactly that mistake).
function segments(path: string): string[] {
  return path
    .split("?")[0]
    .split("/")
    .filter(Boolean)
    .map((s) => (s.includes("{") ? "*" : s));
}
function matches(a: string[], b: string[]): boolean {
  return a.length === b.length && a.every((s, i) => s === b[i]);
}

// Literal values a file passes for a dynamic last segment.
//   `.../${path}` -> the first argument of every post("...") call in the file
//   `.../${verb}` -> the members of the `verb: "a" | "b"` union in the file
function dynamicTailValues(src: string, name: string): string[] {
  if (name === "path") return [...src.matchAll(/\bpost\(\s*"([\w/]+)"/g)].map((m) => m[1]);
  const out: string[] = [];
  for (const m of src.matchAll(/\bverb:\s*((?:"\w+"\s*\|?\s*)+)/g)) {
    for (const v of m[1].matchAll(/"(\w+)"/g)) out.push(v[1]);
  }
  return out;
}

// Every service path written in the console source: template literals that start with
// the service base (`${PIPE}/...` or `${pipe}/...`) and the first argument of call(),
// the Pipeline helper that prefixes the base itself.
function consoleCalls(): { file: string; path: string }[] {
  const found: { file: string; path: string }[] = [];
  for (const file of readdirSync(CONSOLE_DIR).filter((f) => f.endsWith(".tsx"))) {
    const src = readFileSync(join(CONSOLE_DIR, file), "utf8");
    const patterns = [/`\$\{(?:PIPE|pipe)\}(\/[^`]*)`/g, /\bcall\(\s*[`"'](\/[^`"']*)[`"']/g];
    for (const re of patterns) {
      for (const m of src.matchAll(re)) {
        // Cut at the first interpolation that is not a plain variable (for example a
        // ternary that builds a query string).
        const cut = m[1].split(/\$\{(?![\w.]+\})/)[0];

        // A last segment built from a helper argument is expanded to the literal values
        // the file passes, so each needs its own contract entry and a wildcard can never
        // stand in for a real path.
        const tail = cut.match(/\/\$\{(path|verb)\}$/);
        if (tail) {
          const values = dynamicTailValues(src, tail[1]);
          if (values.length === 0) {
            throw new Error(`${file}: cannot resolve the values of ${tail[1]} in ${m[1]}`);
          }
          const base = cut.slice(0, tail.index).replace(PLACEHOLDER, "{}");
          for (const v of new Set(values)) found.push({ file, path: `${base}/${v}` });
          continue;
        }
        found.push({ file, path: cut.replace(PLACEHOLDER, "{}") });
      }
    }
  }
  return found;
}

describe("service contract fixtures", () => {
  const calls = consoleCalls();

  it("finds the console's service calls", () => {
    expect(calls.length).toBeGreaterThan(40);
    // No call may end in a bare placeholder that came from a helper argument.
    expect(calls.filter((c) => /\/\{\}$/.test(c.path) && /\/(box|jobs)\//.test(c.path))).toEqual([]);
  });

  it("every service path the console calls has a contract entry", () => {
    const missing = calls.filter(
      (c) => !contract.endpoints.some((e) => matches(segments(c.path), segments(e.path))),
    );
    expect(missing).toEqual([]);
  });

  it("every contract entry is called from the console", () => {
    const stale = contract.endpoints
      .filter((e) => !e.via_response_of)
      .filter((e) => !calls.some((c) => matches(segments(c.path), segments(e.path))))
      .map((e) => `${e.method} ${e.path}`);
    expect(stale).toEqual([]);
  });

  it("entries are well formed and unique", () => {
    const keys = contract.endpoints.map((e) => `${e.method} ${e.path}`);
    expect(new Set(keys).size).toBe(keys.length);
    for (const e of contract.endpoints) {
      const id = `${e.method} ${e.path}`;
      expect(["GET", "POST"], id).toContain(e.method);
      expect(e.path.startsWith("/"), id).toBe(true);
      expect(typeof e.tracked, id).toBe("boolean");
      expect(e.handler, id).toBeTruthy();
      expect(e.callers.length, id).toBeGreaterThan(0);
      const bodies = [e.response !== undefined, e.text !== undefined, e.binary !== undefined].filter(Boolean);
      expect(bodies.length, `${id} needs exactly one of response, text, binary`).toBe(1);
      if (e.tracked) {
        expect(e.status, id).toBe(200);
      } else {
        // The tracked service has no such route, so the fixture answers as it would.
        expect(e.status, id).toBe(404);
        expect(e.target_response !== undefined || e.target_binary !== undefined, `${id} needs a target shape`).toBe(true);
      }
    }
  });
});
