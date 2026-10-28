// Append-only JSONL ledger for studio events (takes, cuts, etc.).
//
// Each entry is signed with a SHA-256 hash that chains back to the previous entry,
// forming a tamper-evident log. verifyChain() checks the full chain in O(n).
//
// File location: <repoRoot>/ilyrium-shots/ledger/<songId>.jsonl
// Each line is a complete, self-contained JSON object.

import { createHash } from "crypto";
import { appendFileSync, existsSync, mkdirSync, readFileSync } from "fs";
import { resolve, dirname } from "path";

export interface LedgerEntry {
  seq: number;
  event: string;
  songId: string;
  payload: Record<string, unknown>;
  ts: string;
  prev: string | null;
  hash: string;
}

// Default ledger root: <repoRoot>/ilyrium-shots/ledger
// Override with LEDGER_DIR env var (for tests / CI).
function defaultLedgerDir(): string {
  if (process.env.LEDGER_DIR) return process.env.LEDGER_DIR;
  return resolve(process.cwd(), "../../ilyrium-shots/ledger");
}

function ledgerPath(songId: string, dir: string): string {
  return resolve(dir, `${songId}.jsonl`);
}

export function hashEntry(entry: Omit<LedgerEntry, "hash">): string {
  const content = `${entry.prev ?? ""}|${entry.seq}|${entry.event}|${entry.songId}|${JSON.stringify(entry.payload)}|${entry.ts}`;
  return createHash("sha256").update(content).digest("hex");
}

export function appendLedgerEntry(
  songId: string,
  event: string,
  payload: Record<string, unknown>,
  dir?: string,
): LedgerEntry {
  const ledgerDir = dir ?? defaultLedgerDir();
  if (!existsSync(ledgerDir)) mkdirSync(ledgerDir, { recursive: true });

  const path = ledgerPath(songId, ledgerDir);
  let seq = 1;
  let prev: string | null = null;

  if (existsSync(path)) {
    const lines = readFileSync(path, "utf8").trim().split("\n").filter(Boolean);
    if (lines.length > 0) {
      const last = JSON.parse(lines[lines.length - 1]) as LedgerEntry;
      seq = last.seq + 1;
      prev = last.hash;
    }
  }

  const ts = new Date().toISOString();
  const partial: Omit<LedgerEntry, "hash"> = { seq, event, songId, payload, ts, prev };
  const hash = hashEntry(partial);
  const entry: LedgerEntry = { ...partial, hash };

  appendFileSync(path, JSON.stringify(entry) + "\n", "utf8");
  return entry;
}

export function verifyChain(songId: string, dir?: string): boolean {
  const ledgerDir = dir ?? defaultLedgerDir();
  const path = ledgerPath(songId, ledgerDir);
  if (!existsSync(path)) return true;

  const lines = readFileSync(path, "utf8").trim().split("\n").filter(Boolean);
  let prevHash: string | null = null;

  for (const line of lines) {
    const entry = JSON.parse(line) as LedgerEntry;
    const { hash, ...rest } = entry;
    const expected = hashEntry(rest);
    if (hash !== expected) return false;
    if (entry.prev !== prevHash) return false;
    prevHash = hash;
  }
  return true;
}

export function readChain(songId: string, dir?: string): LedgerEntry[] {
  const ledgerDir = dir ?? defaultLedgerDir();
  const path = ledgerPath(songId, ledgerDir);
  if (!existsSync(path)) return [];
  return readFileSync(path, "utf8")
    .trim()
    .split("\n")
    .filter(Boolean)
    .map((l) => JSON.parse(l) as LedgerEntry);
}
