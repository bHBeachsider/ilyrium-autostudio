import { NextResponse } from "next/server"
import { ensureSchema, requireSql, DbNotConfiguredError } from "@/lib/db"
import { twoGateEnabled } from "@/lib/ideas"

export const runtime = "nodejs"

// GET /api/ideas[?status=proposed,needs_changes] -> ideas newest first (+ their
// draft scripts when two-gate review is on).
export async function GET(req: Request) {
  try {
    const sql = requireSql()
    await ensureSchema()
    const statusParam = new URL(req.url).searchParams.get("status")
    const statuses = statusParam
      ? statusParam.split(",").map((s) => s.trim()).filter(Boolean)
      : null
    const rows = statuses
      ? await sql`SELECT * FROM podcast_ideas WHERE status = ANY(${statuses}) ORDER BY created_at DESC LIMIT 100`
      : await sql`SELECT * FROM podcast_ideas ORDER BY created_at DESC LIMIT 100`
    const twoGate = twoGateEnabled()
    let scripts: unknown[] = []
    if (twoGate && rows.length > 0) {
      const ids = (rows as { id: string }[]).map((r) => r.id)
      scripts = await sql`
        SELECT DISTINCT ON (idea_id) * FROM podcast_scripts
        WHERE idea_id = ANY(${ids})
        ORDER BY idea_id, version DESC`
    }
    return NextResponse.json({ ideas: rows, scripts, twoGate })
  } catch (err) {
    if (err instanceof DbNotConfiguredError) {
      return NextResponse.json({ error: err.message, dbUnconfigured: true }, { status: 503 })
    }
    console.error("[api/ideas]", err)
    return NextResponse.json({ error: "Database error." }, { status: 500 })
  }
}
