// Cross-format ledger test, TypeScript half (ILY-206 Phase 0 task 3).
//
// Two line formats can be written to ilyrium-shots/ledger/<song>.jsonl:
//   format 1 - ilyrium-shots/provenance.py: snapshot records with chain.record_hash
//   format 3 - this app's lib/ledger.ts:    {seq,event,songId,payload,ts,prev,hash}
// These tests pin down, by running the real code, what each side does with the
// other's lines. The Python half is tests/test_ledger_cross_format.py. Both read the
// same committed goldens in <repo>/tests/fixtures/ledger/.
//
// Every write goes to a temp dir. Nothing here touches ilyrium-shots/ledger.
//
// To regenerate the format-3 golden with the real writer:
//   UPDATE_LEDGER_GOLDEN=1 pnpm exec vitest run lib/ledger.crossformat.test.ts

import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { copyFileSync, existsSync, mkdtempSync, readFileSync, rmSync } from "fs";
import { tmpdir } from "os";
import { join, resolve } from "path";
import { appendLedgerEntry, verifyChain } from "./ledger";

const GOLDEN_DIR = resolve(__dirname, "../../../tests/fixtures/ledger");
const FORMAT1 = join(GOLDEN_DIR, "format1_provenance.jsonl");
const FORMAT3 = join(GOLDEN_DIR, "format3_events.jsonl");
const SONG = "TST-S001"; // fixture-only id

const lines = (path: string) => readFileSync(path, "utf8").split("\n").filter(Boolean);

let dir: string;
beforeEach(() => {
  dir = mkdtempSync(join(tmpdir(), "ilyrium-ledger-xfmt-"));
});
afterEach(() => {
  rmSync(dir, { recursive: true, force: true });
});

describe("format-3 golden (written by lib/ledger.ts)", () => {
  it.runIf(!!process.env.UPDATE_LEDGER_GOLDEN)("regenerates the golden with the real writer", () => {
    appendLedgerEntry(SONG, "take_registered", { takeId: "fixture-take-1", shotId: `${SONG}-SH001` }, dir);
    appendLedgerEntry(SONG, "fal_asset_completed", { requestId: "fixture-req-1", assetId: "fixture-asset-1" }, dir);
    appendLedgerEntry(SONG, "take_registered", { takeId: "fixture-take-2", shotId: `${SONG}-SH002` }, dir);
    copyFileSync(join(dir, `${SONG}.jsonl`), FORMAT3);
  });

  it("exists and verifies with the TypeScript verifier", () => {
    expect(existsSync(FORMAT3)).toBe(true);
    copyFileSync(FORMAT3, join(dir, `${SONG}.jsonl`));
    expect(lines(FORMAT3).length).toBe(3);
    expect(verifyChain(SONG, dir)).toBe(true);
  });
});

describe("format-1 file (written by provenance.py) seen from lib/ledger.ts", () => {
  beforeEach(() => {
    copyFileSync(FORMAT1, join(dir, `${SONG}.jsonl`));
  });

  it("golden really is provenance format", () => {
    const recs = lines(FORMAT1).map((l) => JSON.parse(l));
    expect(recs.length).toBe(3);
    for (const r of recs) {
      expect(r.chain?.record_hash).toMatch(/^sha256:[0-9a-f]{64}$/);
      expect(r.seq).toBeUndefined();
      expect(r.hash).toBeUndefined();
    }
  });

  it("the TypeScript verifier rejects a valid provenance ledger", () => {
    expect(verifyChain(SONG, dir)).toBe(false);
  });

  it("appending with lib/ledger.ts leaves the old lines intact but writes a broken entry", () => {
    const before = lines(join(dir, `${SONG}.jsonl`));
    const entry = appendLedgerEntry(SONG, "take_registered", { takeId: "fixture-take-9" }, dir);
    const after = lines(join(dir, `${SONG}.jsonl`));

    // Append-only holds: nothing already in the file was changed.
    expect(after.slice(0, before.length)).toEqual(before);
    expect(after.length).toBe(before.length + 1);

    // But the writer could not read a seq or hash off a provenance line, so the new
    // entry carries no usable position in either chain.
    expect(Number.isNaN(entry.seq)).toBe(true);
    expect(entry.prev).toBeUndefined();
    const written = JSON.parse(after[after.length - 1]);
    expect(written.seq).toBeNull(); // NaN serialises as null
    expect("prev" in written).toBe(false); // undefined is dropped
    expect(written.chain).toBeUndefined(); // not a provenance record

    expect(verifyChain(SONG, dir)).toBe(false);
  });
});
