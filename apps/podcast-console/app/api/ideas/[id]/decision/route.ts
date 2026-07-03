import { NextResponse } from "next/server"
import { DbNotConfiguredError, requireSql, type ScriptRow } from "@/lib/db"
import { applyIdeaDecision, isDecision, twoGateEnabled } from "@/lib/ideas"
import { generateScript } from "@/lib/generation/script"

export const runtime = "nodejs"
// Approval may draft a script inline in two-gate mode.
export const maxDuration = 120

// POST /api/ideas/:id/decision { decision: approved|rejected|needs_changes, note?, reviewer? }
// The in-app queue is the source of truth; the Telegram webhook applies the same function.
export async function POST(req: Request, ctx: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await ctx.params
    const body = await req.json().catch(() => ({}))
    if (!isDecision(body.decision)) {
      return NextResponse.json({ error: "decision must be approved | rejected | needs_changes" }, { status: 400 })
    }
    const reviewer = (body.reviewer ?? "app").toString()
    const result = await applyIdeaDecision(id, body.decision, reviewer, body.note)
    if (!result.ok) {
      return NextResponse.json({ error: result.error, current: result.current }, { status: result.status })
    }

    // Two-gate: approving the idea drafts a script for separate review. Draft failure
    // doesn't undo the approval — the review UI offers a retry.
    let script: ScriptRow | null = null
    if (body.decision === "approved" && twoGateEnabled()) {
      try {
        script = await draftScript(result.idea.id, result.idea.title, result.idea.summary)
      } catch (err) {
        console.error("[api/ideas/decision] script draft failed:", err)
      }
    }
    return NextResponse.json({ idea: result.idea, script })
  } catch (err) {
    if (err instanceof DbNotConfiguredError) {
      return NextResponse.json({ error: err.message, dbUnconfigured: true }, { status: 503 })
    }
    console.error("[api/ideas/decision]", err)
    return NextResponse.json({ error: "Decision failed." }, { status: 500 })
  }
}

async function draftScript(ideaId: string, title: string, summary: string | null): Promise<ScriptRow> {
  const sql = requireSql()
  const draft = await generateScript({ topic: title, summary: summary ?? undefined })
  const rows = (await sql`
    INSERT INTO podcast_scripts (idea_id, segments, title, description, estimated_minutes, status, version)
    VALUES (${ideaId}, ${JSON.stringify(draft.segments)}::jsonb, ${draft.title}, ${draft.description},
            ${Math.round(draft.estimatedMinutes)}, 'draft',
            COALESCE((SELECT MAX(version) FROM podcast_scripts WHERE idea_id = ${ideaId}), 0) + 1)
    RETURNING *
  `) as ScriptRow[]
  return rows[0]
}
