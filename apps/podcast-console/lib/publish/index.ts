import { ensureSchema, requireSql, type DistributionChannel, type DistributionRow, type EpisodeRow } from "@/lib/db"
import type { Publisher } from "./types"
import { transistorPublisher } from "./transistor"
import { siteboxPublisher } from "./sitebox"
import { youtubePublisher } from "./youtube"
import { clipsPublisher } from "./clips"

// Distribution orchestrator. Guards live here, in code: only episodes with
// durable media can distribute, each channel is independently env-gated, and
// every attempt's outcome (including failure) is recorded in
// podcast_distributions — unique per (episode, channel), re-runs update.

// Order matters: sitebox reads the transistor result within the same run.
const PUBLISHERS: Publisher[] = [transistorPublisher, siteboxPublisher, youtubePublisher, clipsPublisher]

export type DistributeOutcome = {
  channel: DistributionChannel
  skipped?: string
  distribution?: DistributionRow
  error?: string
}

export type DistributeResult =
  | { ok: true; episodeId: string; results: DistributeOutcome[] }
  | { ok: false; status: number; error: string }

export async function distributeEpisode(
  episodeId: string,
  channels?: DistributionChannel[],
): Promise<DistributeResult> {
  const sql = requireSql()
  await ensureSchema()

  const rows = (await sql`SELECT * FROM podcast_episodes WHERE id = ${episodeId}`) as EpisodeRow[]
  if (rows.length === 0) return { ok: false, status: 404, error: "Episode not found." }
  const episode = rows[0]
  if (!episode.audio_url && !episode.video_url) {
    return { ok: false, status: 409, error: "Episode has no durable media — produce (or import) it first." }
  }

  const wanted = PUBLISHERS.filter((p) => !channels || channels.includes(p.id))
  const results: DistributeOutcome[] = []
  for (const publisher of wanted) {
    if (!publisher.enabled()) {
      results.push({ channel: publisher.id, skipped: publisher.disabledReason() })
      continue
    }
    try {
      const r = await publisher.publish(episode)
      const saved = (await sql`
        INSERT INTO podcast_distributions (episode_id, channel, external_id, url, status, detail, error, published_at)
        VALUES (${episode.id}, ${publisher.id}, ${r.externalId ?? null}, ${r.url ?? null}, ${r.status},
                ${JSON.stringify(r.detail ?? {})}::jsonb, NULL,
                ${r.status === "published" ? new Date().toISOString() : null})
        ON CONFLICT (episode_id, channel) DO UPDATE SET
          external_id = EXCLUDED.external_id, url = EXCLUDED.url, status = EXCLUDED.status,
          detail = EXCLUDED.detail, error = NULL, published_at = EXCLUDED.published_at
        RETURNING *`) as DistributionRow[]
      results.push({ channel: publisher.id, distribution: saved[0] })
    } catch (err) {
      const message = err instanceof Error ? err.message.slice(0, 500) : "publish failed"
      const saved = (await sql`
        INSERT INTO podcast_distributions (episode_id, channel, status, error)
        VALUES (${episode.id}, ${publisher.id}, 'failed', ${message})
        ON CONFLICT (episode_id, channel) DO UPDATE SET status = 'failed', error = EXCLUDED.error
        RETURNING *`) as DistributionRow[]
      results.push({ channel: publisher.id, distribution: saved[0], error: message })
      console.error(`[publish] ${publisher.id} failed for ${episode.id}:`, message)
    }
  }

  // A live Transistor publish marks the idea's lifecycle as published.
  if (results.some((r) => r.distribution?.status === "published") && episode.idea_id) {
    await sql`UPDATE podcast_ideas SET status = 'published' WHERE id = ${episode.idea_id} AND status = 'produced'`
  }

  console.log(
    `[publish] episode=${episode.id}`,
    results.map((r) => `${r.channel}:${r.skipped ? "skipped" : (r.distribution?.status ?? "?")}`).join(" "),
  )
  return { ok: true, episodeId: episode.id, results }
}
