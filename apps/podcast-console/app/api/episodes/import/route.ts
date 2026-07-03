import { NextResponse } from "next/server"
import { ensureSchema, requireSql, DbNotConfiguredError, type EpisodeSource } from "@/lib/db"
import { blobReady, putObject } from "@/lib/blob"
import { localSource } from "@/lib/ingest/local"
import { permithubSource } from "@/lib/ingest/permithub"
import { rssSource } from "@/lib/ingest/rss"
import type { IngestSource, RawItem } from "@/lib/ingest/types"

export const runtime = "nodejs"
export const maxDuration = 300

const SOURCE_COLUMN: Record<IngestSource["kind"], EpisodeSource> = {
  local: "imported_local",
  permithub_api: "imported_api",
  rss: "imported_rss",
}

function resolveSource(kind: string, url?: string): IngestSource | { error: string } {
  switch (kind) {
    case "local": {
      const dir = process.env.PBC_PODCAST_DIR
      if (!dir) return { error: "PBC_PODCAST_DIR is not set. Point it at the producer's data/podcasts directory." }
      return localSource(dir)
    }
    case "permithub_api": {
      const base = process.env.PERMITHUB_BASE_URL
      if (!base) return { error: "PERMITHUB_BASE_URL is not set." }
      return permithubSource(base, process.env.PERMITHUB_ADMIN_TOKEN)
    }
    case "rss": {
      const feed = url || process.env.PODCAST_RSS_URL
      if (!feed) return { error: "No feed URL. Pass { url } or set PODCAST_RSS_URL." }
      return rssSource(feed)
    }
    default:
      return { error: `Unknown source "${kind}". Expected local | permithub_api | rss.` }
  }
}

// POST /api/episodes/import { source, weekOf?, url?, limit? }
// Upserts by guid: existing episodes are skipped (or backfilled with audio if they
// were imported without it), so re-imports never duplicate.
export async function POST(req: Request) {
  try {
    const sql = requireSql()
    await ensureSchema()
    const body = await req.json().catch(() => ({}))
    const kind = (body.source ?? "").toString()
    const src = resolveSource(kind, body.url)
    if ("error" in src) return NextResponse.json({ error: src.error }, { status: 400 })

    const limit = Number.isFinite(body.limit) ? Math.max(1, Math.min(50, Math.round(body.limit))) : 10
    let items: RawItem[]
    try {
      items = await src.list()
    } catch (err) {
      return NextResponse.json({ error: err instanceof Error ? err.message : "Source listing failed." }, { status: 502 })
    }
    if (body.weekOf) items = items.filter((it) => it.weekOf === body.weekOf || it.guid.endsWith(body.weekOf))
    const scanned = items.length
    items = items.slice(0, limit)

    let imported = 0
    let updated = 0
    let skipped = 0
    const errors: { guid: string; message: string }[] = []

    for (const item of items) {
      try {
        const existing = (await sql`SELECT id, audio_url FROM podcast_episodes WHERE guid = ${item.guid}`) as {
          id: string
          audio_url: string | null
        }[]
        if (existing.length > 0 && existing[0].audio_url) {
          skipped++
          continue
        }
        const audioUrl = await persistAudio(src, item)
        if (existing.length > 0) {
          if (audioUrl) {
            await sql`UPDATE podcast_episodes SET audio_url = ${audioUrl} WHERE id = ${existing[0].id}`
            updated++
          } else {
            skipped++
          }
          continue
        }
        const estimatedMinutes = item.durationSeconds ? Math.max(1, Math.round(item.durationSeconds / 60)) : null
        await sql`
          INSERT INTO podcast_episodes
            (title, description, estimated_minutes, segments, status, audio_url, source, guid,
             week_of, jurisdiction, episode_number, season, duration_seconds, show_notes)
          VALUES
            (${item.title}, ${item.description}, ${estimatedMinutes}, ${JSON.stringify(item.segments)}::jsonb,
             'imported', ${audioUrl}, ${SOURCE_COLUMN[src.kind]}, ${item.guid}, ${item.weekOf},
             ${item.jurisdiction}, ${item.episodeNumber}, ${item.season}, ${item.durationSeconds}, ${item.showNotes})
        `
        imported++
      } catch (err) {
        errors.push({ guid: item.guid, message: err instanceof Error ? err.message : "import failed" })
      }
    }

    const summary = { source: kind, scanned, imported, updated, skipped, errors }
    console.log("[api/episodes/import]", JSON.stringify(summary))
    return NextResponse.json(summary)
  } catch (err) {
    if (err instanceof DbNotConfiguredError) {
      return NextResponse.json({ error: err.message, dbUnconfigured: true }, { status: 503 })
    }
    console.error("[api/episodes/import]", err)
    return NextResponse.json({ error: "Import failed." }, { status: 500 })
  }
}

/** Copy audio to R2 when configured; otherwise fall back to the source's own URL
 * (fine for RSS/API imports — local files have no public fallback). */
async function persistAudio(src: IngestSource, item: RawItem): Promise<string | null> {
  if (!item.audioRef) return null
  if (blobReady()) {
    const audio = await src.fetchAudio(item)
    if (audio) {
      const safeGuid = item.guid.replace(/[^a-zA-Z0-9._-]/g, "-")
      return putObject(`podcasts/${safeGuid}/episode.mp3`, audio, "audio/mpeg")
    }
    return null
  }
  if (/^https?:\/\//.test(item.audioRef)) {
    console.warn("[api/episodes/import] R2 not configured; storing remote audio URL for", item.guid)
    return item.audioRef
  }
  console.warn("[api/episodes/import] R2 not configured; imported metadata only for", item.guid)
  return null
}
