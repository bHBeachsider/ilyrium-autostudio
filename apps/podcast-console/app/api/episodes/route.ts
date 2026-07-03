import { NextResponse } from "next/server"
import { ensureSchema, requireSql, DbNotConfiguredError, type Segment } from "@/lib/db"

export const runtime = "nodejs"

// GET /api/episodes[?projectId=] -> episodes, newest first.
export async function GET(req: Request) {
  try {
    const sql = requireSql()
    await ensureSchema()
    const projectId = new URL(req.url).searchParams.get("projectId")
    const rows = projectId
      ? await sql`SELECT * FROM podcast_episodes WHERE project_id = ${projectId} ORDER BY created_at DESC`
      : await sql`SELECT * FROM podcast_episodes ORDER BY created_at DESC`
    return NextResponse.json({ episodes: rows })
  } catch (err) {
    return handle(err)
  }
}

// POST /api/episodes -> persist a generated episode's metadata + script. project_id/name are
// denormalized (projects are still session-side this increment), so episodes persist on their own.
export async function POST(req: Request) {
  try {
    const sql = requireSql()
    await ensureSchema()
    const body = await req.json().catch(() => ({}))
    const title = (body.title ?? "").toString().trim()
    if (!title) return NextResponse.json({ error: "title is required" }, { status: 400 })
    const projectId = body.projectId ?? null
    const projectName = body.projectName ?? null
    const segments: Segment[] = Array.isArray(body.segments) ? body.segments : []
    const description = body.description ?? null
    const estimatedMinutes = Number.isFinite(body.estimatedMinutes) ? Math.round(body.estimatedMinutes) : null
    const audioUrl = body.audioUrl ?? null
    const videoUrl = body.videoUrl ?? null
    const rows = await sql`
      INSERT INTO podcast_episodes
        (project_id, project_name, title, description, estimated_minutes, segments, status, audio_url, video_url)
      VALUES
        (${projectId}, ${projectName}, ${title}, ${description}, ${estimatedMinutes}, ${JSON.stringify(segments)}::jsonb, 'rendered', ${audioUrl}, ${videoUrl})
      RETURNING id, created_at
    `
    return NextResponse.json({ episode: rows[0] }, { status: 201 })
  } catch (err) {
    return handle(err)
  }
}

function handle(err: unknown) {
  if (err instanceof DbNotConfiguredError) {
    return NextResponse.json({ error: err.message, dbUnconfigured: true }, { status: 503 })
  }
  console.error("[api/episodes]", err)
  return NextResponse.json({ error: "Database error." }, { status: 500 })
}
