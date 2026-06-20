import { NextResponse } from "next/server";

// POST /api/studio/c2pa — DEFERRED in Phase 1.
// The C2PA content-credentials manifest was stored on a provenance_records table that
// does NOT exist in the real schema. Provenance is normalized via assets.model_id /
// prompt_id; a content-credentials store is future work. Returns 501 so callers fail
// loudly rather than writing to a non-existent table.
export async function POST() {
  return NextResponse.json(
    { ok: false, error: "Not implemented in Phase 1: no provenance_records table (C2PA store is deferred)." },
    { status: 501 },
  );
}
