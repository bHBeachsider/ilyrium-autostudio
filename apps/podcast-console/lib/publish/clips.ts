import { execFile } from "node:child_process"
import { promisify } from "node:util"
import { writeFile, readFile, mkdtemp, rm } from "node:fs/promises"
import { tmpdir } from "node:os"
import { join } from "node:path"
import ffmpegPath from "ffmpeg-static"
import { generateText, Output } from "ai"
import * as z from "zod"
import type { EpisodeRow, Segment } from "@/lib/db"
import { blobReady, putObject } from "@/lib/blob"
import { getAudioDurationSeconds } from "@/lib/generation/video"
import { envFlag, type Publisher, type PublishResult } from "./types"

// Social clips publisher: a highlight agent picks 2-3 self-contained moments
// from the script, ffmpeg cuts them from the rendered episode video, and the
// results land on R2 with drafted post copy — status 'assets_ready' for manual
// posting (no X/social API wiring yet).

const execFileAsync = promisify(execFile)

const highlightSchema = z.object({
  clips: z
    .array(
      z.object({
        startSegmentIndex: z.number().int().describe("0-based index of the first transcript line of the clip"),
        endSegmentIndex: z.number().int().describe("0-based index of the last transcript line (inclusive)"),
        hook: z.string().describe("Why this moment works as a standalone clip, one sentence"),
        postCopy: z.string().describe("Ready-to-post social copy for this clip, <=240 chars, no hashtag spam"),
      }),
    )
    .min(1)
    .max(3)
    .describe("The strongest self-contained moments, best first"),
})

/** Estimate each segment's [start, end] seconds by prorating total duration over
 * character counts — the same heuristic the renderer uses for scene weights. */
export function segmentWindows(segments: Segment[], totalSeconds: number): { start: number; end: number }[] {
  const lens = segments.map((s) => Math.max(1, s.text.trim().length))
  const total = lens.reduce((a, b) => a + b, 0)
  const windows: { start: number; end: number }[] = []
  let t = 0
  for (const len of lens) {
    const dur = (len / total) * totalSeconds
    windows.push({ start: t, end: t + dur })
    t += dur
  }
  return windows
}

export const clipsPublisher: Publisher = {
  id: "clips",
  enabled() {
    return envFlag("PUBLISH_CLIPS_ENABLED") && blobReady()
  },
  disabledReason() {
    if (!envFlag("PUBLISH_CLIPS_ENABLED")) return "PUBLISH_CLIPS_ENABLED is not 'true'."
    return "R2 storage is not configured."
  },
  async publish(episode: EpisodeRow): Promise<PublishResult> {
    if (!episode.video_url) throw new Error("Episode has no video_url to clip.")
    if (!ffmpegPath) throw new Error("FFmpeg binary not available.")
    const segments = episode.segments
    if (!Array.isArray(segments) || segments.length === 0) throw new Error("Episode has no segments to pick from.")

    const { output } = await generateText({
      model: "openai/gpt-5-mini",
      output: Output.object({ schema: highlightSchema }),
      system:
        "You pick short, self-contained highlight moments from a two-host local-news podcast for social clips. " +
        "Each clip must make sense with zero context, ideally 15-45 seconds spoken (2-6 transcript lines).",
      messages: [
        {
          role: "user",
          content: `Episode: "${episode.title}"\nTranscript ([index] speaker: text):\n${segments
            .map((s, i) => `[${i}] ${s.speaker}: ${s.text}`)
            .join("\n")}`,
        },
      ],
    })

    const videoRes = await fetch(episode.video_url)
    if (!videoRes.ok) throw new Error(`Could not fetch episode video (${videoRes.status}).`)
    const video = Buffer.from(await videoRes.arrayBuffer())

    const workDir = await mkdtemp(join(tmpdir(), "pbcw-clips-"))
    try {
      const videoFile = join(workDir, "episode.mp4")
      await writeFile(videoFile, video)
      const totalSeconds = await getAudioDurationSeconds(videoFile)
      if (!totalSeconds) throw new Error("Could not determine episode duration.")
      const windows = segmentWindows(segments, totalSeconds)

      const clips: { url: string; hook: string; postCopy: string; startSeconds: number; durationSeconds: number }[] = []
      for (let c = 0; c < output.clips.length; c++) {
        const pick = output.clips[c]
        const startIdx = Math.min(Math.max(0, pick.startSegmentIndex), segments.length - 1)
        const endIdx = Math.min(Math.max(startIdx, pick.endSegmentIndex), segments.length - 1)
        const start = windows[startIdx].start
        // Clamp clip length to a social-friendly 8-60s window.
        const duration = Math.min(60, Math.max(8, windows[endIdx].end - start))
        const outFile = join(workDir, `clip-${c}.mp4`)
        await execFileAsync(
          ffmpegPath,
          [
            "-y",
            "-ss", start.toFixed(2),
            "-t", duration.toFixed(2),
            "-i", videoFile,
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "128k",
            "-movflags", "+faststart",
            outFile,
          ],
          { maxBuffer: 1024 * 1024 * 64 },
        )
        const key = `podcasts/${episode.guid ?? episode.id}/clips/clip-${c}.mp4`
        const url = await putObject(key, await readFile(outFile), "video/mp4")
        clips.push({
          url,
          hook: pick.hook,
          postCopy: pick.postCopy,
          startSeconds: Math.round(start),
          durationSeconds: Math.round(duration),
        })
      }

      return {
        status: "assets_ready",
        url: clips[0]?.url ?? null,
        detail: {
          note: "Clips + draft copy ready for manual posting (no social API connected).",
          clips,
        },
      }
    } finally {
      await rm(workDir, { recursive: true, force: true }).catch(() => {})
    }
  },
}
