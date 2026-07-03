import { ensureSchema, requireSql, type DistributionRow, type EpisodeRow } from "@/lib/db"
import { envFlag, type Publisher, type PublishResult } from "./types"

// site-box publisher. site-box's /podcast page is a pure RSS consumer of
// PODCAST_RSS_URL (lib/podcast.ts in the site-box repo) — there is no podcast
// push endpoint. So "publishing to site-box" means: the episode must be LIVE on
// the Transistor feed, and site-box must point PODCAST_RSS_URL at that feed.
// This publisher verifies the chain and reports the feed URL to configure.

export const siteboxPublisher: Publisher = {
  id: "sitebox",
  enabled() {
    return envFlag("PUBLISH_SITEBOX_ENABLED")
  },
  disabledReason() {
    return "PUBLISH_SITEBOX_ENABLED is not 'true'."
  },
  async publish(episode: EpisodeRow): Promise<PublishResult> {
    const sql = requireSql()
    await ensureSchema()
    const rows = (await sql`
      SELECT * FROM podcast_distributions
      WHERE episode_id = ${episode.id} AND channel = 'transistor'`) as DistributionRow[]
    const transistor = rows[0]
    if (!transistor || transistor.status === "failed") {
      return {
        status: "pending",
        detail: { note: "Waiting on Transistor: site-box consumes the Transistor RSS feed (PODCAST_RSS_URL)." },
      }
    }
    const feedUrl = (transistor.detail?.feedUrl as string | undefined) ?? process.env.PODCAST_RSS_URL ?? null
    if (transistor.status === "draft") {
      return {
        status: "pending",
        url: feedUrl,
        detail: {
          feedUrl,
          note: "Transistor episode is a draft — site-box will pick it up from the feed once it is published.",
        },
      }
    }
    return {
      status: "published",
      url: feedUrl,
      detail: {
        feedUrl,
        note: feedUrl
          ? `Live on the feed. Ensure site-box has PODCAST_RSS_URL=${feedUrl} (ISR revalidates hourly).`
          : "Live on Transistor; set site-box PODCAST_RSS_URL to the show's feed URL.",
      },
    }
  },
}
