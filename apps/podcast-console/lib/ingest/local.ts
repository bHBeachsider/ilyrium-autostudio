import { promises as fs } from "fs"
import path from "path"
import type { IngestSource, RawItem } from "./types"
import { flattenProducerScript, scriptMeta } from "./normalize"

// Ingest path A: local producer output. PBC_PODCAST_DIR points at the producer's
// data/podcasts directory, containing <week_of>/{episode.mp3, script.json, manifest.json}
// (PermitHub-API LocalPublisher layout; typically a downloaded pbc-episode-<week> artifact).

type Manifest = {
  title?: string
  description?: string
  summary?: string
  audio_path?: string
  published_at?: string
  episode_number?: number
  season?: number
  guid?: string
}

async function readJson(file: string): Promise<unknown | null> {
  try {
    return JSON.parse(await fs.readFile(file, "utf8"))
  } catch {
    return null
  }
}

export function localSource(dir: string): IngestSource {
  return {
    kind: "local",
    async list(): Promise<RawItem[]> {
      const entries = await fs.readdir(dir, { withFileTypes: true })
      const items: RawItem[] = []
      for (const entry of entries) {
        if (!entry.isDirectory() || !/^\d{4}-\d{2}-\d{2}$/.test(entry.name)) continue
        const weekDir = path.join(dir, entry.name)
        const manifest = (await readJson(path.join(weekDir, "manifest.json"))) as Manifest | null
        if (!manifest?.guid || !manifest.title) continue
        const script = await readJson(path.join(weekDir, "script.json"))
        const meta = scriptMeta(script)
        const audioPath = path.join(weekDir, "episode.mp3")
        const hasAudio = await fs
          .stat(audioPath)
          .then((s) => s.isFile())
          .catch(() => false)
        items.push({
          guid: manifest.guid,
          title: manifest.title,
          description: manifest.description ?? null,
          summary: manifest.summary ?? null,
          weekOf: meta.weekOf ?? entry.name,
          jurisdiction: meta.jurisdiction,
          episodeNumber: manifest.episode_number ?? null,
          season: manifest.season ?? null,
          publishedAt: manifest.published_at ?? null,
          durationSeconds: null,
          showNotes: null,
          segments: flattenProducerScript(script),
          audioRef: hasAudio ? audioPath : null,
        })
      }
      return items
    },
    async fetchAudio(item: RawItem): Promise<Buffer | null> {
      if (!item.audioRef) return null
      try {
        return await fs.readFile(item.audioRef)
      } catch {
        return null
      }
    },
  }
}
