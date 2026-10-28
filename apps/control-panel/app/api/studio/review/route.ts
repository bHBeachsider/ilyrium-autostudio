import { NextResponse } from "next/server";
import { createHash } from "crypto";
import { existsSync, readFileSync, appendFileSync, mkdirSync } from "fs";
import { resolve, dirname } from "path";
import studioDb from "../../../../lib/studio-db";

// Canonical JSON matching Python json.dumps(sort_keys=True, separators=(",",":"), ensure_ascii=False).
// MUST stay in sync with ilyrium-shots/provenance.py — do not modify without updating both.
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
  return "sha256:" + createHash("sha256").update(data, "utf8").digest("hex");
}

function snapshotHash(record: Record<string, unknown>): string {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const { chain: _chain, ...core } = record;
  return sha256(canonicalJSON(core));
}

function computeRecordHash(prevHash: string | null, record: Record<string, unknown>): string {
  return sha256((prevHash ?? "") + snapshotHash(record));
}

function verifyChain(ledgerPath: string): boolean {
  try {
    const lines = readFileSync(ledgerPath, "utf8").split("\n").filter(Boolean);
    let prev: string | null = null;
    for (const line of lines) {
      const rec = JSON.parse(line) as Record<string, unknown>;
      const chain = rec.chain as { prev_record_hash?: string | null; record_hash?: string } | undefined;
      const expected = computeRecordHash(prev, rec);
      if (chain?.record_hash !== expected) return false;
      prev = chain?.record_hash ?? null;
    }
    return true;
  } catch {
    return false;
  }
}

// POST /api/studio/review
// Body: { songId, shotId, decision: "approved"|"rejected", reviewer?, reason?, spawnRegen? }
// Appends a new ledger entry for the shot with the updated approval state, maintaining chain_ok.
// Writes are LOCAL to ilyrium-shots/ledger/ — this API is local dev only.
export async function POST(request: Request) {
  try {
    const body = await request.json() as Record<string, unknown>;
    const { songId, shotId, decision, reviewer, reason } = body as {
      songId?: string; shotId?: string; decision?: string; reviewer?: string; reason?: string;
    };

    if (!songId || !shotId || !decision) {
      return NextResponse.json({ error: "songId, shotId, and decision are required." }, { status: 400 });
    }
    if (!["approved", "rejected"].includes(decision)) {
      return NextResponse.json({ error: "decision must be approved or rejected." }, { status: 400 });
    }
    if (decision === "rejected" && !reason?.trim()) {
      return NextResponse.json({ error: "reason is required when rejecting." }, { status: 400 });
    }

    // Resolve ledger path relative to Next.js project root (apps/control-panel).
    const ledgerDir = resolve(process.cwd(), "../../ilyrium-shots/ledger");
    const ledgerPath = resolve(ledgerDir, `${songId}.jsonl`);

    let prevRecordHash: string | null = null;
    let sourceRecord: Record<string, unknown> | null = null;

    if (existsSync(ledgerPath)) {
      const lines = readFileSync(ledgerPath, "utf8").split("\n").filter(Boolean);
      // Find the most recent entry for this shotId.
      for (let i = lines.length - 1; i >= 0; i--) {
        try {
          const rec = JSON.parse(lines[i]) as Record<string, unknown>;
          const shot = rec.shot as { shot_id?: string } | undefined;
          if (shot?.shot_id === shotId) { sourceRecord = rec; break; }
        } catch { /* skip malformed lines */ }
      }
      // The overall prev hash is the last entry's record_hash.
      if (lines.length > 0) {
        try {
          const last = JSON.parse(lines[lines.length - 1]) as Record<string, unknown>;
          const chain = last.chain as { record_hash?: string } | undefined;
          prevRecordHash = chain?.record_hash ?? null;
        } catch { /* ignore */ }
      }
    }

    const now = new Date().toISOString().replace(/\.\d{3}Z$/, "Z");

    const newRecord: Record<string, unknown> = sourceRecord
      ? {
          ...sourceRecord,
          updated_at: now,
          status: decision,
          approval: { state: decision, reviewer: reviewer ?? null, decided_at: now, note: reason?.trim() ?? null },
        }
      : {
          schema_version: "1.0.0",
          record_id: `review-${Date.now()}`,
          created_at: now,
          updated_at: now,
          status: decision,
          attempt: 1,
          supersedes: null,
          shot: { song_id: songId, shot_id: shotId, scene_id: null, sequence_index: null },
          shot_spec: {},
          generation: {},
          models: [],
          engine: {},
          render: null,
          approval: { state: decision, reviewer: reviewer ?? null, decided_at: now, note: reason?.trim() ?? null },
          agent_version_id: null,
          content_hash: null,
        };

    // Remove chain before computing (must not be included in snapshot).
    delete newRecord.chain;
    const recordHash = computeRecordHash(prevRecordHash, newRecord);
    newRecord.chain = { prev_record_hash: prevRecordHash, record_hash: recordHash };

    // Append to ledger. Ensure directory exists (in case ledger dir was cleaned).
    if (!existsSync(ledgerDir)) mkdirSync(ledgerDir, { recursive: true });
    appendFileSync(ledgerPath, JSON.stringify(newRecord) + "\n", "utf8");

    const chainOk = verifyChain(ledgerPath);

    // Optional: record a gate_approvals/run row in Neon.
    let runId: string | undefined;
    try {
      const run = await studioDb.run.create({
        data: {
          agentName: "review-room",
          plane: "review",
          humanGateStatus: decision,
          completedAt: new Date(),
        },
      });
      runId = run.id;
    } catch { /* Neon write is best-effort */ }

    return NextResponse.json({ ok: true, chain_ok: chainOk, runId: runId ?? null });
  } catch (error) {
    console.error("studio/review error:", error);
    return NextResponse.json({ error: "Internal Server Error" }, { status: 500 });
  }
}
