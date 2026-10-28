// Unit tests for the append-only JSONL ledger (lib/ledger.ts).
//
// Uses a temp directory per test so ilyrium-shots/ledger is never touched.
// Tests the chain invariant: every entry's hash re-derives from its content,
// and each entry's `prev` matches the preceding entry's `hash`.

import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { mkdtempSync, rmSync, readFileSync, writeFileSync } from "fs";
import { tmpdir } from "os";
import { join } from "path";
import { appendLedgerEntry, verifyChain, hashEntry } from "./ledger";

describe("hashEntry", () => {
  it("produces the same hash for the same input", () => {
    const base = {
      seq: 1,
      event: "take_registered",
      songId: "song-1",
      payload: { takeId: "t1" },
      ts: "2024-01-01T00:00:00.000Z",
      prev: null,
    };
    expect(hashEntry(base)).toBe(hashEntry(base));
  });

  it("produces different hashes for different payloads", () => {
    const a = { seq: 1, event: "take_registered", songId: "song-1", payload: { takeId: "t1" }, ts: "2024-01-01T00:00:00.000Z", prev: null };
    const b = { ...a, payload: { takeId: "t2" } };
    expect(hashEntry(a)).not.toBe(hashEntry(b));
  });

  it("includes prev in the hash", () => {
    const base = { seq: 2, event: "take_registered", songId: "song-1", payload: { takeId: "t2" }, ts: "2024-01-01T00:01:00.000Z", prev: null };
    const withPrev = { ...base, prev: "abc123" };
    expect(hashEntry(base)).not.toBe(hashEntry(withPrev));
  });
});

describe("appendLedgerEntry + verifyChain", () => {
  let dir: string;

  beforeEach(() => {
    dir = mkdtempSync(join(tmpdir(), "ilyrium-ledger-test-"));
  });

  afterEach(() => {
    rmSync(dir, { recursive: true, force: true });
  });

  it("appends the first entry with seq=1 and prev=null", () => {
    const entry = appendLedgerEntry("song-abc", "take_registered", { takeId: "t1" }, dir);
    expect(entry.seq).toBe(1);
    expect(entry.prev).toBeNull();
    expect(entry.hash).toHaveLength(64); // sha256 hex
  });

  it("chains sequential entries: each prev = previous hash", () => {
    const e1 = appendLedgerEntry("song-chain", "take_registered", { takeId: "t1" }, dir);
    const e2 = appendLedgerEntry("song-chain", "take_registered", { takeId: "t2" }, dir);
    const e3 = appendLedgerEntry("song-chain", "take_registered", { takeId: "t3" }, dir);

    expect(e2.prev).toBe(e1.hash);
    expect(e3.prev).toBe(e2.hash);
    expect(e2.seq).toBe(2);
    expect(e3.seq).toBe(3);
  });

  it("verifyChain returns true for a valid chain", () => {
    appendLedgerEntry("song-verify", "take_registered", { takeId: "t1" }, dir);
    appendLedgerEntry("song-verify", "take_registered", { takeId: "t2" }, dir);
    expect(verifyChain("song-verify", dir)).toBe(true);
  });

  it("verifyChain returns true for an empty / non-existent ledger", () => {
    expect(verifyChain("song-no-such", dir)).toBe(true);
  });

  it("chain_ok is true immediately after appendLedgerEntry", () => {
    const e = appendLedgerEntry("song-ok", "take_registered", { takeId: "t1" }, dir);
    expect(e.hash).toHaveLength(64);
    expect(verifyChain("song-ok", dir)).toBe(true);
  });

  it("verifyChain detects tampering (payload changed without re-hashing)", () => {
    appendLedgerEntry("song-tamper", "take_registered", { takeId: "t1" }, dir);

    const ledgerFile = join(dir, "song-tamper.jsonl");
    const lines = readFileSync(ledgerFile, "utf8").trim().split("\n");
    const parsed = JSON.parse(lines[0]);
    parsed.payload.takeId = "tampered";
    writeFileSync(ledgerFile, JSON.stringify(parsed) + "\n");

    expect(verifyChain("song-tamper", dir)).toBe(false);
  });

  it("verifyChain detects a broken prev pointer", () => {
    appendLedgerEntry("song-prev-break", "take_registered", { takeId: "t1" }, dir);
    appendLedgerEntry("song-prev-break", "take_registered", { takeId: "t2" }, dir);

    const ledgerFile = join(dir, "song-prev-break.jsonl");
    const lines = readFileSync(ledgerFile, "utf8").trim().split("\n");
    const second = JSON.parse(lines[1]);
    second.prev = "deadbeef".repeat(8); // wrong prev, hash not updated
    writeFileSync(ledgerFile, lines[0] + "\n" + JSON.stringify(second) + "\n");

    expect(verifyChain("song-prev-break", dir)).toBe(false);
  });

  it("fal write followed by takes write still passes verifyChain", () => {
    appendLedgerEntry("song-cross", "fal_asset_completed", { asset_url: "https://cdn.fal.ai/test.mp4", cost_cents: 200 }, dir);
    appendLedgerEntry("song-cross", "take_registered", { takeId: "t1" }, dir);
    expect(verifyChain("song-cross", dir)).toBe(true);
  });
});
