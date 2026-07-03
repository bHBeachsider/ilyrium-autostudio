import type { DistributionChannel, DistributionStatus, EpisodeRow } from "@/lib/db"

// Common publisher interface (Phase 4). Every channel is independently
// enable-able via env; distribution only runs on produced episodes with media,
// and results — including failures — are recorded in podcast_distributions.

export type PublishResult = {
  status: DistributionStatus
  externalId?: string | null
  url?: string | null
  /** Channel-specific extras (feed URL, draft copy, clip URLs, …). */
  detail?: Record<string, unknown>
}

export interface Publisher {
  id: DistributionChannel
  /** false => channel skipped with a clear message (not an error). */
  enabled(): boolean
  /** Why the channel is disabled — surfaced to the caller. */
  disabledReason(): string
  publish(episode: EpisodeRow): Promise<PublishResult>
}

export function envFlag(name: string): boolean {
  return process.env[name] === "true"
}
