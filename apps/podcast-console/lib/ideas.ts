import { requireSql, ensureSchema, type IdeaRow, type IdeaStatus } from "@/lib/db"

// Single decision path for the approval queue. Both the in-app /review actions and
// the Telegram webhook go through applyIdeaDecision, so the DB is the one source of
// truth and transitions are enforced in code, not UI.

export type Decision = "approved" | "rejected" | "needs_changes"

const DECIDABLE: IdeaStatus[] = ["proposed", "needs_changes"]

/** Pure transition guard: which statuses may receive which reviewer decisions. */
export function canDecide(from: IdeaStatus, decision: Decision): boolean {
  if (!DECIDABLE.includes(from)) return false
  if (decision === "needs_changes") return from === "proposed"
  return true
}

export function isDecision(value: unknown): value is Decision {
  return value === "approved" || value === "rejected" || value === "needs_changes"
}

export type DecisionResult =
  | { ok: true; idea: IdeaRow }
  | { ok: false; status: number; error: string; current?: IdeaStatus }

export async function applyIdeaDecision(
  id: string,
  decision: Decision,
  reviewer: string,
  note?: string | null,
): Promise<DecisionResult> {
  const sql = requireSql()
  await ensureSchema()
  const rows = (await sql`SELECT * FROM podcast_ideas WHERE id = ${id}`) as IdeaRow[]
  if (rows.length === 0) return { ok: false, status: 404, error: "Idea not found." }
  const current = rows[0].status
  if (!canDecide(current, decision)) {
    return { ok: false, status: 409, error: `Idea is '${current}' — cannot mark it '${decision}'.`, current }
  }
  const updated = (await sql`
    UPDATE podcast_ideas
    SET status = ${decision}, reviewer = ${reviewer}, review_note = ${note ?? null}, decided_at = now()
    WHERE id = ${id} AND status = ${current}
    RETURNING *
  `) as IdeaRow[]
  if (updated.length === 0) {
    // Lost a race with another reviewer (in-app vs Telegram); re-read and report.
    const now = (await sql`SELECT status FROM podcast_ideas WHERE id = ${id}`) as { status: IdeaStatus }[]
    return { ok: false, status: 409, error: "Idea was decided concurrently.", current: now[0]?.status }
  }
  return { ok: true, idea: updated[0] }
}

/** Two-gate mode: ideas AND draft scripts require approval before production. */
export function twoGateEnabled(): boolean {
  return process.env.STUDIO_TWO_GATE === "true"
}
