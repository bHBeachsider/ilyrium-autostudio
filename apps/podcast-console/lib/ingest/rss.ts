import Parser from "rss-parser"
import type { IngestSource, RawItem } from "./types"
import { parseDurationSeconds } from "./normalize"

// Ingest path C: any podcast RSS feed (e.g. the Transistor show feed site-box reads).
// Items without an audio enclosure are skipped — this importer exists to pull episodes.

type FeedItem = {
  guid?: string
  link?: string
  title?: string
  content?: string
  contentSnippet?: string
  isoDate?: string
  pubDate?: string
  enclosure?: { url?: string; type?: string }
  itunes?: { summary?: string; duration?: string; season?: string; episode?: string }
}

export function rssSource(feedUrl: string): IngestSource {
  return {
    kind: "rss",
    async list(): Promise<RawItem[]> {
      const parser: Parser<Record<string, never>, FeedItem> = new Parser()
      const feed = await parser.parseURL(feedUrl)
      const items: RawItem[] = []
      for (const item of feed.items ?? []) {
        const audioUrl = item.enclosure?.url
        if (!audioUrl || !item.title) continue
        items.push({
          guid: item.guid || item.link || audioUrl,
          title: item.title,
          description: item.contentSnippet || item.content || null,
          summary: item.itunes?.summary ?? null,
          weekOf: null,
          jurisdiction: null,
          episodeNumber: item.itunes?.episode ? Number(item.itunes.episode) || null : null,
          season: item.itunes?.season ? Number(item.itunes.season) || null : null,
          publishedAt: item.isoDate ?? item.pubDate ?? null,
          durationSeconds: parseDurationSeconds(item.itunes?.duration),
          showNotes: item.content ?? null,
          segments: [],
          audioRef: audioUrl,
        })
      }
      return items
    },
    async fetchAudio(item: RawItem): Promise<Buffer | null> {
      if (!item.audioRef) return null
      const res = await fetch(item.audioRef, { cache: "no-store" })
      if (!res.ok) return null
      return Buffer.from(await res.arrayBuffer())
    },
  }
}
