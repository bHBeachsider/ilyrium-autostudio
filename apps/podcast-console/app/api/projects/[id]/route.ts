import { NextResponse } from "next/server"
import { ensureSchema, requireSql, DbNotConfiguredError } from "@/lib/db"

export const runtime = "nodejs"

// PATCH /api/projects/:id { name } -> rename.
export async function PATCH(req: Request, { params }: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await params
    const sql = requireSql()
    await ensureSchema()
    const body = await req.json().catch(() => ({}))
    const name = (body.name ?? "").toString().trim()
    if (!name) return NextResponse.json({ error: "name is required" }, { status: 400 })
    const rows = await sql`UPDATE podcast_projects SET name = ${name} WHERE id = ${id} RETURNING id, name, created_at`
    if (rows.length === 0) return NextResponse.json({ error: "not found" }, { status: 404 })
    return NextResponse.json({ project: rows[0] })
  } catch (err) {
    return handle(err)
  }
}

// DELETE /api/projects/:id -> delete (episodes + ideas cascade).
export async function DELETE(_req: Request, { params }: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await params
    const sql = requireSql()
    await ensureSchema()
    await sql`DELETE FROM podcast_projects WHERE id = ${id}`
    return NextResponse.json({ ok: true })
  } catch (err) {
    return handle(err)
  }
}

function handle(err: unknown) {
  if (err instanceof DbNotConfiguredError) {
    return NextResponse.json({ error: err.message, dbUnconfigured: true }, { status: 503 })
  }
  console.error("[api/projects/:id]", err)
  return NextResponse.json({ error: "Database error." }, { status: 500 })
}
