import { NextResponse } from "next/server"
import { DbNotConfiguredError, ensureSchema, requireSql, type ScriptRow, type ScriptStatus } from "@/lib/db"
import { isDecision } from "@/lib/ideas"

export const runtime = "nodejs"

// POST /api/scripts/:id/decision { decision, note?, reviewer? } — the second gate
// (two-gate mode): a drafted script must be approved before production.
export async function POST(req: Request, ctx: { params: Promise<{ id: string }> }) {
  try {
    const sql = requireSql()
    await ensureSchema()
    const { id } = await ctx.params
    const body = await req.json().catch(() => ({}))
    if (!isDecision(body.decision)) {
      return NextResponse.json({ error: "decision must be approved | rejected | needs_changes" }, { status: 400 })
    }
    const rows = (await sql`SELECT * FROM podcast_scripts WHERE id = ${id}`) as ScriptRow[]
    if (rows.length === 0) return NextResponse.json({ error: "Script not found." }, { status: 404 })
    const current: ScriptStatus = rows[0].status
    if (current !== "draft" && current !== "needs_changes") {
      return NextResponse.json(
        { error: `Script is '${current}' — cannot mark it '${body.decision}'.`, current },
        { status: 409 },
      )
    }
    const reviewer = (body.reviewer ?? "app").toString()
    const updated = (await sql`
      UPDATE podcast_scripts
      SET status = ${body.decision}, reviewer = ${reviewer}, review_note = ${body.note ?? null}, decided_at = now()
      WHERE id = ${id} AND status = ${current}
      RETURNING *
    `) as ScriptRow[]
    if (updated.length === 0) {
      return NextResponse.json({ error: "Script was decided concurrently." }, { status: 409 })
    }
    return NextResponse.json({ script: updated[0] })
  } catch (err) {
    if (err instanceof DbNotConfiguredError) {
      return NextResponse.json({ error: err.message, dbUnconfigured: true }, { status: 503 })
    }
    console.error("[api/scripts/decision]", err)
    return NextResponse.json({ error: "Decision failed." }, { status: 500 })
  }
}
