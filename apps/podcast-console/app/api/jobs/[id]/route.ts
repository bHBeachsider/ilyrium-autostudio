import { NextResponse } from "next/server"
import { DbNotConfiguredError, ensureSchema, requireSql } from "@/lib/db"

export const runtime = "nodejs"

// GET /api/jobs/:id — poll production progress.
export async function GET(_req: Request, ctx: { params: Promise<{ id: string }> }) {
  try {
    const sql = requireSql()
    await ensureSchema()
    const { id } = await ctx.params
    const rows = await sql`SELECT * FROM podcast_jobs WHERE id = ${id}`
    if (rows.length === 0) return NextResponse.json({ error: "Job not found." }, { status: 404 })
    return NextResponse.json({ job: rows[0] })
  } catch (err) {
    if (err instanceof DbNotConfiguredError) {
      return NextResponse.json({ error: err.message, dbUnconfigured: true }, { status: 503 })
    }
    console.error("[api/jobs]", err)
    return NextResponse.json({ error: "Database error." }, { status: 500 })
  }
}
