import { NextResponse } from "next/server"
import { ensureSchema, requireSql, DbNotConfiguredError, type IdeaRow } from "@/lib/db"
import { twoGateEnabled } from "@/lib/ideas"
import { notifyIdeaProposed, telegramEnabled } from "@/lib/telegram"

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
    let jobs: unknown[] = []
    if (rows.length > 0) {
      const ids = (rows as { id: string }[]).map((r) => r.id)
      if (twoGate) {
        scripts = await sql`
          SELECT DISTINCT ON (idea_id) * FROM podcast_scripts
          WHERE idea_id = ANY(${ids})
          ORDER BY idea_id, version DESC`
      }
      jobs = await sql`
        SELECT DISTINCT ON (idea_id) * FROM podcast_jobs
        WHERE idea_id = ANY(${ids})
        ORDER BY idea_id, created_at DESC`
    }
    return NextResponse.json({ ideas: rows, scripts, jobs, twoGate })
  } catch (err) {
    if (err instanceof DbNotConfiguredError) {
      return NextResponse.json({ error: err.message, dbUnconfigured: true }, { status: 503 })
    }
    console.error("[api/ideas]", err)
    return NextResponse.json({ error: "Database error." }, { status: 500 })
  }
}

// POST /api/ideas — manually propose an episode idea. Lands in the review queue
// as 'proposed' like agent output: the approval gate applies to everyone.
export async function POST(req: Request) {
  try {
    const sql = requireSql()
    await ensureSchema()
    const body = await req.json().catch(() => ({}))
    const title = (body.title ?? "").toString().trim()
    if (!title) return NextResponse.json({ error: "title is required" }, { status: 400 })
    const summary = body.summary ? body.summary.toString().trim() : null
    const angle = body.angle ? body.angle.toString().trim() : null
    const sourceRefs = Array.isArray(body.sourceRefs) ? body.sourceRefs.map(String).slice(0, 10) : []
    const rows = (await sql`
      INSERT INTO podcast_ideas (title, summary, angle, rationale, source_refs, status, created_by)
      VALUES (${title}, ${summary}, ${angle}, ${body.rationale ?? null},
              ${JSON.stringify(sourceRefs)}::jsonb, 'proposed', 'manual')
      RETURNING *`) as IdeaRow[]
    if (telegramEnabled()) await notifyIdeaProposed(rows[0]).catch(() => {})
    return NextResponse.json({ idea: rows[0] }, { status: 201 })
  } catch (err) {
    if (err instanceof DbNotConfiguredError) {
      return NextResponse.json({ error: err.message, dbUnconfigured: true }, { status: 503 })
    }
    console.error("[api/ideas POST]", err)
    return NextResponse.json({ error: "Failed to create idea." }, { status: 500 })
  }
}
