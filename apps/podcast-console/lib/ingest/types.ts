import type { Segment } from "@/lib/db"

/** A source-agnostic episode ready to be normalized into podcast_episodes. */
export type RawItem = {
  /** Idempotency key, e.g. the producer's "pbc-2026-06-08" or an RSS item guid. */
  guid: string
  title: string
  description: string | null
  summary: string | null
  weekOf: string | null
  jurisdiction: string | null
  episodeNumber: number | null
  season: number | null
  publishedAt: string | null
  durationSeconds: number | null
  showNotes: string | null
  /** Console-shape segments ({speaker: "Host A"|"Host B", text}); [] when the source has no script. */
  segments: Segment[]
  /** Where the audio lives before import: an absolute file path or an http(s) URL. */
  audioRef: string | null
}

export interface IngestSource {
  kind: "local" | "permithub_api" | "rss"
  list(): Promise<RawItem[]>
  fetchAudio(item: RawItem): Promise<Buffer | null>
}
