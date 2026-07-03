import { NextResponse } from "next/server"
import { DbNotConfiguredError, ensureSchema, requireSql } from "@/lib/db"

export const runtime = "nodejs"

const KINDS = ["local", "permithub_api", "rss", "manual"]

// GET /api/sources — list content sources the loop syncs.
export async function GET() {
  try {
    const sql = requireSql()
    await ensureSchema()
    const rows = await sql`SELECT * FROM podcast_content_sources ORDER BY created_at`
    return NextResponse.json({ sources: rows })
  } catch (err) {
    return handle(err)
  }
}

// POST /api/sources { kind, name, config?, enabled? } — register a source
// (e.g. { kind: 'rss', name: 'PBC construction news', config: { url } }).
export async function POST(req: Request) {
  try {
    const sql = requireSql()
    await ensureSchema()
    const body = await req.json().catch(() => ({}))
    const kind = (body.kind ?? "").toString()
    const name = (body.name ?? "").toString().trim()
    if (!KINDS.includes(kind)) return NextResponse.json({ error: `kind must be one of ${KINDS.join(", ")}` }, { status: 400 })
    if (!name) return NextResponse.json({ error: "name is required" }, { status: 400 })
    const config = body.config && typeof body.config === "object" ? body.config : {}
    const enabled = body.enabled !== false
    const rows = await sql`
      INSERT INTO podcast_content_sources (kind, name, config, enabled)
      VALUES (${kind}, ${name}, ${JSON.stringify(config)}::jsonb, ${enabled})
      RETURNING *`
    return NextResponse.json({ source: rows[0] }, { status: 201 })
  } catch (err) {
    return handle(err)
  }
}

function handle(err: unknown) {
  if (err instanceof DbNotConfiguredError) {
    return NextResponse.json({ error: err.message, dbUnconfigured: true }, { status: 503 })
  }
  console.error("[api/sources]", err)
  return NextResponse.json({ error: "Database error." }, { status: 500 })
}
