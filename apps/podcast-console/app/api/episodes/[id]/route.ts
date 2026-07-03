import { NextResponse } from "next/server"
import { ensureSchema, requireSql, DbNotConfiguredError } from "@/lib/db"

export const runtime = "nodejs"

// DELETE /api/episodes/:id -> remove a persisted episode.
export async function DELETE(_req: Request, { params }: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await params
    const sql = requireSql()
    await ensureSchema()
    await sql`DELETE FROM podcast_episodes WHERE id = ${id}`
    return NextResponse.json({ ok: true })
  } catch (err) {
    if (err instanceof DbNotConfiguredError) {
      return NextResponse.json({ error: err.message, dbUnconfigured: true }, { status: 503 })
    }
    console.error("[api/episodes/:id]", err)
    return NextResponse.json({ error: "Database error." }, { status: 500 })
  }
}
