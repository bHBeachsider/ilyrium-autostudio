import { NextResponse } from "next/server";

// POST /api/studio/archive — DEFERRED in Phase 1.
// The preservation package was an archive_packages table that does NOT exist in the real
// schema (and depended on the equally-absent provenance_records). Returns 501 so callers
// fail loudly rather than writing to a non-existent table.
export async function POST() {
  return NextResponse.json(
    { ok: false, error: "Not implemented in Phase 1: no archive_packages table (preservation packaging is deferred)." },
    { status: 501 },
  );
}
