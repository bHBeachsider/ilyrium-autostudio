import { dbReady, ensureSchema, requireSql } from "@/lib/db"
import { blobReady } from "@/lib/blob"

// Live data for the production dashboard. One loader, a handful of queries —
// the page is force-dynamic so every visit reflects the studio's real state.

export type DashboardData = {
  configured: boolean
  counts: {
    episodes: number
    published: number
    proposed: number
    approved: number
    producing: number
    rejectedByGate: number
  }
  pipeline: {
    ideaTitle: string
    step: string
    status: string
    error: string | null
    updatedAt: string
  }[]
  recentEpisodes: {
    id: string
    title: string
    source: string
    createdAt: string
    audioUrl: string | null
    videoUrl: string | null
    published: boolean
    claims: number | null
  }[]
  lastLoopRun: { finishedAt: string | null; counts: Record<string, unknown> } | null
  health: { name: string; ok: boolean; detail: string }[]
}

export async function loadDashboard(): Promise<DashboardData> {
  const health = [
    { name: "Database (Neon)", ok: dbReady(), detail: dbReady() ? "connected" : "DATABASE_URL unset" },
    { name: "Media storage (R2)", ok: blobReady(), detail: blobReady() ? "configured" : "R2_* unset" },
    { name: "Voices (ElevenLabs)", ok: !!process.env.ELEVENLABS_API_KEY, detail: "TTS for production" },
    { name: "Script/scenes (AI Gateway)", ok: !!process.env.AI_GATEWAY_API_KEY, detail: "gpt-5-mini + Imagen" },
    { name: "Research (Perplexity)", ok: !!process.env.PERPLEXITY_API_KEY, detail: "source retrieval + fact-check" },
    {
      name: "Publishing (Transistor)",
      ok: !!process.env.TRANSISTOR_API_KEY,
      detail: process.env.TRANSISTOR_PUBLISH === "true" ? "LIVE publishing enabled" : "drafts-only (safe default)",
    },
    {
      name: "Idea loop",
      ok: process.env.STUDIO_LOOP_ENABLED === "true",
      detail: process.env.STUDIO_LOOP_ENABLED === "true" ? "daily cron active" : "disabled",
    },
    {
      name: "Telegram mirror",
      ok: !!(process.env.TELEGRAM_BOT_TOKEN && process.env.TELEGRAM_CHAT_ID),
      detail: process.env.TELEGRAM_BOT_TOKEN ? "configured" : "off (optional)",
    },
  ]

  if (!dbReady()) {
    return {
      configured: false,
      counts: { episodes: 0, published: 0, proposed: 0, approved: 0, producing: 0, rejectedByGate: 0 },
      pipeline: [],
      recentEpisodes: [],
      lastLoopRun: null,
      health,
    }
  }

  const sql = requireSql()
  await ensureSchema()

  const [countRows, pipelineRows, episodeRows, loopRows] = await Promise.all([
    sql`SELECT
      (SELECT count(*)::int FROM podcast_episodes) AS episodes,
      (SELECT count(DISTINCT episode_id)::int FROM podcast_distributions WHERE channel='transistor' AND status='published') AS published,
      (SELECT count(*)::int FROM podcast_ideas WHERE status='proposed') AS proposed,
      (SELECT count(*)::int FROM podcast_ideas WHERE status='approved') AS approved,
      (SELECT count(*)::int FROM podcast_ideas WHERE status='producing') AS producing,
      (SELECT count(*)::int FROM podcast_jobs WHERE status='failed') AS rejected`,
    sql`SELECT j.step, j.status, j.error, j.updated_at, i.title
        FROM podcast_jobs j JOIN podcast_ideas i ON i.id = j.idea_id
        WHERE j.status != 'done'
        ORDER BY j.updated_at DESC LIMIT 8`,
    sql`SELECT e.id, e.title, e.source, e.created_at, e.audio_url, e.video_url,
        EXISTS(SELECT 1 FROM podcast_distributions d WHERE d.episode_id = e.id AND d.channel='transistor' AND d.status='published') AS published,
        (SELECT jsonb_array_length(j.artifacts->'verification'->'verdicts') FROM podcast_jobs j WHERE j.episode_id = e.id LIMIT 1) AS claims
        FROM podcast_episodes e ORDER BY e.created_at DESC LIMIT 6`,
    sql`SELECT finished_at, counts FROM podcast_agent_runs WHERE agent='loop_tick' ORDER BY started_at DESC LIMIT 1`,
  ])

  const c = countRows[0] as Record<string, number>
  return {
    configured: true,
    counts: {
      episodes: c.episodes,
      published: c.published,
      proposed: c.proposed,
      approved: c.approved,
      producing: c.producing,
      rejectedByGate: c.rejected,
    },
    pipeline: (pipelineRows as Record<string, unknown>[]).map((r) => ({
      ideaTitle: String(r.title),
      step: String(r.step),
      status: String(r.status),
      error: r.error ? String(r.error) : null,
      updatedAt: String(r.updated_at),
    })),
    recentEpisodes: (episodeRows as Record<string, unknown>[]).map((r) => ({
      id: String(r.id),
      title: String(r.title),
      source: String(r.source),
      createdAt: String(r.created_at),
      audioUrl: r.audio_url ? String(r.audio_url) : null,
      videoUrl: r.video_url ? String(r.video_url) : null,
      published: !!r.published,
      claims: r.claims == null ? null : Number(r.claims),
    })),
    lastLoopRun: loopRows[0]
      ? {
          finishedAt: loopRows[0].finished_at ? String(loopRows[0].finished_at) : null,
          counts: (loopRows[0].counts ?? {}) as Record<string, unknown>,
        }
      : null,
    health,
  }
}
