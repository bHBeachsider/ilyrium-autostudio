import type { IngestSource, RawItem } from "./types"
import { flattenProducerScript } from "./normalize"

// Ingest path B: PermitHub admin API. GET {PERMITHUB_BASE_URL}/api/admin/podcast/episodes
// with a JWT bearer (PERMITHUB_ADMIN_TOKEN). Best-effort by design: the backing
// intelligence.episodes table is seeded by a manual CLI step, so empty/stale/401
// responses are normal and reported as clear errors rather than thrown.

type ApiEpisode = {
  guid?: string
  title?: string
  description?: string | null
  summary?: string | null
  week_of?: string | null
  jurisdiction?: string | null
  episode_number?: number | null
  season?: number | null
  duration_seconds?: number | null
  audio_url?: string | null
  script_json?: unknown
  show_notes?: string | null
  produced_at?: string | null
}

export function permithubSource(baseUrl: string, token: string | undefined): IngestSource {
  return {
    kind: "permithub_api",
    async list(): Promise<RawItem[]> {
      const res = await fetch(`${baseUrl.replace(/\/+$/, "")}/api/admin/podcast/episodes`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        cache: "no-store",
      })
      if (res.status === 401) {
        throw new Error("PermitHub API returned 401 — PERMITHUB_ADMIN_TOKEN is missing, expired, or not a valid JWT.")
      }
      if (!res.ok) {
        throw new Error(`PermitHub API returned ${res.status} for /api/admin/podcast/episodes.`)
      }
      const body = (await res.json().catch(() => ({}))) as { episodes?: ApiEpisode[] }
      const episodes = Array.isArray(body.episodes) ? body.episodes : []
      return episodes
        .filter((ep) => ep.guid && ep.title)
        .map((ep) => ({
          guid: ep.guid!,
          title: ep.title!,
          description: ep.description ?? null,
          summary: ep.summary ?? null,
          weekOf: ep.week_of ?? null,
          jurisdiction: ep.jurisdiction ?? null,
          episodeNumber: ep.episode_number ?? null,
          season: ep.season ?? null,
          publishedAt: ep.produced_at ?? ep.week_of ?? null,
          durationSeconds: ep.duration_seconds ?? null,
          showNotes: ep.show_notes ?? null,
          segments: flattenProducerScript(ep.script_json),
          audioRef: ep.audio_url && /^https?:\/\//.test(ep.audio_url) ? ep.audio_url : null,
        }))
    },
    async fetchAudio(item: RawItem): Promise<Buffer | null> {
      if (!item.audioRef) return null
      const res = await fetch(item.audioRef, { cache: "no-store" })
      if (!res.ok) return null
      return Buffer.from(await res.arrayBuffer())
    },
  }
}
