import { NextResponse } from "next/server"
import { ensureSchema, requireSql, DbNotConfiguredError } from "@/lib/db"

export const runtime = "nodejs"

// GET /api/projects -> list projects with idea/episode counts (oldest first, matches UI).
export async function GET() {
  try {
    const sql = requireSql()
    await ensureSchema()
    const rows = await sql`
      SELECT p.id, p.name, p.created_at,
        (SELECT count(*) FROM podcast_episodes e WHERE e.project_id = p.id)::int AS episode_count,
        (SELECT count(*) FROM podcast_ideas i WHERE i.project_id = p.id)::int AS idea_count
      FROM podcast_projects p
      ORDER BY p.created_at ASC
    `
    return NextResponse.json({ projects: rows })
  } catch (err) {
    return handle(err)
  }
}

// POST /api/projects { name } -> create a project.
export async function POST(req: Request) {
  try {
    const sql = requireSql()
    await ensureSchema()
    const body = await req.json().catch(() => ({}))
    const name = (body.name ?? "").toString().trim() || "Untitled project"
    const rows = await sql`INSERT INTO podcast_projects (name) VALUES (${name}) RETURNING id, name, created_at`
    return NextResponse.json({ project: rows[0] }, { status: 201 })
  } catch (err) {
    return handle(err)
  }
}

function handle(err: unknown) {
  if (err instanceof DbNotConfiguredError) {
    return NextResponse.json({ error: err.message, dbUnconfigured: true }, { status: 503 })
  }
  console.error("[api/projects]", err)
  return NextResponse.json({ error: "Database error." }, { status: 500 })
}
