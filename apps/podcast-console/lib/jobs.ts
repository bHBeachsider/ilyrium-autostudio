import {
  ensureSchema,
  requireSql,
  type IdeaRow,
  type JobArtifacts,
  type JobRow,
  type ScriptRow,
  type Segment,
} from "@/lib/db"
import { blobReady, getObject, putObject } from "@/lib/blob"
import { generateScript } from "@/lib/generation/script"
import { synthesizeSegments } from "@/lib/generation/tts"
import { generateEpisodeImages } from "@/lib/generation/images"
import { renderEpisodeVideo } from "@/lib/generation/video"
import { twoGateEnabled } from "@/lib/ideas"

// Production job engine. Approval is mandatory and enforced here, not in UI:
// createProductionJob refuses ideas that aren't 'approved' (plus an approved
// script in two-gate mode). Each advanceJobStep call runs exactly ONE bounded
// step — script -> audio -> images -> video -> finalize — persisting artifacts
// to R2 between requests, so no single request outgrows serverless limits and
// failed steps can be retried without redoing earlier work.

/** A running step that stops heartbeating for this long is considered crashed
 * and may be taken over by a retry. */
const STALE_RUNNING_MS = 10 * 60 * 1000

export type CreateJobResult =
  | { ok: true; job: JobRow; existing: boolean }
  | { ok: false; status: number; error: string }

export async function createProductionJob(ideaId: string): Promise<CreateJobResult> {
  const sql = requireSql()
  await ensureSchema()
  if (!blobReady()) {
    return { ok: false, status: 400, error: "Production requires R2 storage (R2_ENDPOINT/KEYS) for durable media." }
  }

  const ideas = (await sql`SELECT * FROM podcast_ideas WHERE id = ${ideaId}`) as IdeaRow[]
  if (ideas.length === 0) return { ok: false, status: 404, error: "Idea not found." }
  const idea = ideas[0]

  // Resume: an unfinished job for this idea is returned instead of duplicated.
  const activeJobs = (await sql`
    SELECT * FROM podcast_jobs WHERE idea_id = ${ideaId} AND status != 'done'
    ORDER BY created_at DESC LIMIT 1`) as JobRow[]
  if (activeJobs.length > 0) return { ok: true, job: activeJobs[0], existing: true }

  if (idea.status !== "approved") {
    return { ok: false, status: 409, error: `Idea is '${idea.status}' — only approved ideas can be produced.` }
  }
  if (twoGateEnabled()) {
    const scripts = (await sql`
      SELECT * FROM podcast_scripts WHERE idea_id = ${ideaId} ORDER BY version DESC LIMIT 1`) as ScriptRow[]
    if (scripts.length === 0 || scripts[0].status !== "approved") {
      return {
        ok: false,
        status: 409,
        error: `Two-gate mode: the idea's script must be approved first (current: ${scripts[0]?.status ?? "none"}).`,
      }
    }
  }

  const jobs = (await sql`
    INSERT INTO podcast_jobs (idea_id) VALUES (${ideaId}) RETURNING *`) as JobRow[]
  await sql`UPDATE podcast_ideas SET status = 'producing' WHERE id = ${ideaId} AND status = 'approved'`
  return { ok: true, job: jobs[0], existing: false }
}

export type StepResult =
  | { ok: true; job: JobRow }
  | { ok: false; status: number; error: string; job?: JobRow }

export async function advanceJobStep(jobId: string): Promise<StepResult> {
  const sql = requireSql()
  await ensureSchema()

  // Claim the step (optimistic lock). A 'running' job younger than the staleness
  // window means another request is mid-step — don't double-run it.
  const claimed = (await sql`
    UPDATE podcast_jobs SET status = 'running', error = NULL, updated_at = now()
    WHERE id = ${jobId}
      AND status != 'done'
      AND (status != 'running' OR updated_at < now() - interval '10 minutes')
    RETURNING *`) as JobRow[]
  if (claimed.length === 0) {
    const rows = (await sql`SELECT * FROM podcast_jobs WHERE id = ${jobId}`) as JobRow[]
    if (rows.length === 0) return { ok: false, status: 404, error: "Job not found." }
    if (rows[0].status === "done") return { ok: true, job: rows[0] }
    return { ok: false, status: 409, error: "A step is already running for this job.", job: rows[0] }
  }
  const job = claimed[0]

  try {
    const artifacts = { ...job.artifacts }
    let nextStep = job.step

    switch (job.step) {
      case "script": {
        artifacts.script = await runScriptStep(job)
        nextStep = "audio"
        break
      }
      case "audio": {
        const script = requireScript(artifacts)
        const { audio } = await synthesizeSegments(script.segments)
        artifacts.audioKey = `podcasts/console-${job.id}/episode.mp3`
        artifacts.audioUrl = await putObject(artifacts.audioKey, audio, "audio/mpeg")
        nextStep = "images"
        break
      }
      case "images": {
        // Best-effort: a failed image plan/generation shouldn't kill the episode —
        // the video step falls back to the branded background + waveform.
        const script = requireScript(artifacts)
        try {
          const result = await generateEpisodeImages({
            title: script.title,
            description: script.description,
            segments: script.segments,
          })
          const keys: string[] = []
          for (let i = 0; i < result.images.length; i++) {
            const key = `podcasts/console-${job.id}/scene-${i}.png`
            await putObject(key, result.images[i].bytes, result.images[i].mediaType)
            keys.push(key)
          }
          artifacts.imageKeys = keys
          artifacts.weights = result.weights
        } catch (err) {
          artifacts.imagesSkipped = err instanceof Error ? err.message.slice(0, 300) : "image generation failed"
          console.warn(`[jobs] images step skipped for ${job.id}:`, artifacts.imagesSkipped)
        }
        nextStep = "video"
        break
      }
      case "video": {
        if (!artifacts.audioKey) throw new Error("Job has no audio artifact — audio step must run first.")
        const audio = await getObject(artifacts.audioKey)
        const images = await Promise.all((artifacts.imageKeys ?? []).map((k) => getObject(k)))
        const { video } = await renderEpisodeVideo({ audio, images, weights: artifacts.weights })
        artifacts.videoKey = `podcasts/console-${job.id}/episode.mp4`
        artifacts.videoUrl = await putObject(artifacts.videoKey, video, "video/mp4")
        nextStep = "finalize"
        break
      }
      case "finalize": {
        const episodeId = await finalize(job, artifacts)
        const rows = (await sql`
          UPDATE podcast_jobs
          SET step = 'done', status = 'done', episode_id = ${episodeId},
              artifacts = ${JSON.stringify(artifacts)}::jsonb, updated_at = now()
          WHERE id = ${job.id} RETURNING *`) as JobRow[]
        return { ok: true, job: rows[0] }
      }
      case "done":
        return { ok: true, job }
    }

    const rows = (await sql`
      UPDATE podcast_jobs
      SET step = ${nextStep}, status = 'queued', artifacts = ${JSON.stringify(artifacts)}::jsonb, updated_at = now()
      WHERE id = ${job.id} RETURNING *`) as JobRow[]
    return { ok: true, job: rows[0] }
  } catch (err) {
    const message = err instanceof Error ? err.message.slice(0, 500) : "Step failed."
    const rows = (await sql`
      UPDATE podcast_jobs SET status = 'failed', error = ${message}, updated_at = now()
      WHERE id = ${job.id} RETURNING *`) as JobRow[]
    console.error(`[jobs] step '${job.step}' failed for ${job.id}:`, message)
    return { ok: false, status: 500, error: message, job: rows[0] }
  }
}

function requireScript(artifacts: JobArtifacts): NonNullable<JobArtifacts["script"]> {
  if (!artifacts.script) throw new Error("Job has no script artifact — script step must run first.")
  return artifacts.script
}

async function runScriptStep(job: JobRow): Promise<NonNullable<JobArtifacts["script"]>> {
  const sql = requireSql()
  const ideas = (await sql`SELECT * FROM podcast_ideas WHERE id = ${job.idea_id}`) as IdeaRow[]
  if (ideas.length === 0) throw new Error("Idea vanished.")
  const idea = ideas[0]

  // Two-gate mode produced a human-approved script — use it verbatim.
  if (twoGateEnabled()) {
    const scripts = (await sql`
      SELECT * FROM podcast_scripts WHERE idea_id = ${job.idea_id} AND status = 'approved'
      ORDER BY version DESC LIMIT 1`) as ScriptRow[]
    if (scripts.length > 0) {
      const s = scripts[0]
      return {
        title: s.title ?? idea.title,
        description: s.description ?? idea.summary ?? "",
        estimatedMinutes: s.estimated_minutes ?? 5,
        segments: s.segments as Segment[],
      }
    }
  }
  const draft = await generateScript({ topic: idea.title, summary: idea.summary ?? undefined })
  return {
    title: draft.title,
    description: draft.description,
    estimatedMinutes: Math.round(draft.estimatedMinutes),
    segments: draft.segments,
  }
}

async function finalize(job: JobRow, artifacts: JobArtifacts): Promise<string> {
  const sql = requireSql()
  const script = requireScript(artifacts)
  const guid = `console-${job.id}`
  // Idempotent: a retried finalize updates the same guid row instead of duplicating.
  const rows = (await sql`
    INSERT INTO podcast_episodes
      (title, description, estimated_minutes, segments, status, audio_url, video_url, source, guid, idea_id)
    VALUES
      (${script.title}, ${script.description}, ${script.estimatedMinutes},
       ${JSON.stringify(script.segments)}::jsonb, 'produced', ${artifacts.audioUrl ?? null},
       ${artifacts.videoUrl ?? null}, 'generated', ${guid}, ${job.idea_id})
    ON CONFLICT (guid) WHERE guid IS NOT NULL
    DO UPDATE SET audio_url = EXCLUDED.audio_url, video_url = EXCLUDED.video_url, status = 'produced'
    RETURNING id`) as { id: string }[]
  const episodeId = rows[0].id
  await sql`
    UPDATE podcast_ideas SET status = 'produced', episode_id = ${episodeId}
    WHERE id = ${job.idea_id} AND status = 'producing'`
  return episodeId
}
