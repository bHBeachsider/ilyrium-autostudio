import { NextRequest } from "next/server"
import { execFile } from "node:child_process"
import { promisify } from "node:util"
import { writeFile, readFile, mkdtemp, rm } from "node:fs/promises"
import { tmpdir } from "node:os"
import { join } from "node:path"
import ffmpegPath from "ffmpeg-static"

export const runtime = "nodejs"
export const maxDuration = 300

const execFileAsync = promisify(execFile)

// Parse "Duration: HH:MM:SS.xx" out of ffmpeg's stderr to size the slideshow.
function parseDuration(stderr: string): number {
  const m = stderr.match(/Duration:\s*(\d+):(\d+):(\d+\.\d+)/)
  if (!m) return 0
  return Number(m[1]) * 3600 + Number(m[2]) * 60 + Number(m[3])
}

async function getAudioDuration(audioFile: string): Promise<number> {
  try {
    await execFileAsync(ffmpegPath as string, ["-i", audioFile])
    return 0
  } catch (err) {
    // ffmpeg exits non-zero when given no output target, but prints Duration to stderr.
    const stderr = (err as { stderr?: string }).stderr ?? ""
    return parseDuration(stderr)
  }
}

export async function POST(req: NextRequest) {
  if (!ffmpegPath) {
    return Response.json({ error: "FFmpeg binary not available." }, { status: 500 })
  }

  let audioBuffer: Buffer
  let imageBuffers: Buffer[] = []
  let weights: number[] = []
  try {
    const form = await req.formData()
    const audio = form.get("audio")
    if (!(audio instanceof Blob)) {
      return Response.json({ error: "No audio track provided." }, { status: 400 })
    }
    audioBuffer = Buffer.from(await audio.arrayBuffer())

    const images = form.getAll("images").filter((i) => i instanceof Blob) as Blob[]
    imageBuffers = await Promise.all(images.map(async (img) => Buffer.from(await img.arrayBuffer())))

    // Optional per-image narration weights, so each scene stays on screen while
    // its topic is being spoken instead of getting an equal slice.
    const rawWeights = form.get("weights")
    if (typeof rawWeights === "string") {
      try {
        const parsed = JSON.parse(rawWeights)
        if (Array.isArray(parsed)) weights = parsed.map((n) => Number(n)).filter((n) => Number.isFinite(n) && n > 0)
      } catch {
        // ignore malformed weights, fall back to equal slices
      }
    }
  } catch {
    return Response.json({ error: "Invalid request body." }, { status: 400 })
  }

  if (audioBuffer.length === 0) {
    return Response.json({ error: "Audio track is empty." }, { status: 400 })
  }

  const workDir = await mkdtemp(join(tmpdir(), "pbcw-video-"))
  const audioFile = join(workDir, "audio.mp3")
  const outFile = join(workDir, "episode.mp4")
  const fallbackBg = join(process.cwd(), "public", "episode-bg.png")

  try {
    await writeFile(audioFile, audioBuffer)

    // No images supplied -> fall back to the branded background + waveform.
    if (imageBuffers.length === 0) {
      const args = [
        "-y",
        "-loop", "1",
        "-i", fallbackBg,
        "-i", audioFile,
        "-filter_complex",
        "[1:a]showwaves=s=1280x240:mode=cline:rate=25:colors=0x34d399@0.9[wave];" +
          "[0:v]scale=1280:720,setsar=1[bg];" +
          "[bg][wave]overlay=(W-w)/2:H-h-70:shortest=1,format=yuv420p[v]",
        "-map", "[v]",
        "-map", "1:a",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-tune", "stillimage",
        "-c:a", "aac",
        "-b:a", "160k",
        "-shortest",
        "-movflags", "+faststart",
        outFile,
      ]
      await execFileAsync(ffmpegPath, args, { maxBuffer: 1024 * 1024 * 64 })
    } else {
      // Ken Burns slideshow: each scene image is held for a duration proportional
      // to how much narration covers its topic (so the image matches what is being
      // discussed), with a slow zoom, concatenated, then a synced waveform overlay.
      const fps = 25
      const duration = (await getAudioDuration(audioFile)) || imageBuffers.length * 6
      const n = imageBuffers.length

      // Build per-scene seconds. Use narration weights when they line up with the
      // images; otherwise fall back to equal slices.
      const minPer = 2.5
      let durations: number[]
      if (weights.length === n) {
        const total = weights.reduce((a, b) => a + b, 0)
        // Reserve the minimum for every scene, distribute the rest by weight.
        const reserved = minPer * n
        const flexible = Math.max(0, duration - reserved)
        durations = weights.map((w) => minPer + (flexible * w) / total)
      } else {
        durations = Array.from({ length: n }, () => Math.max(minPer, duration / n))
      }

      const inputArgs: string[] = []
      const imagePaths: string[] = []
      for (let i = 0; i < n; i++) {
        const p = join(workDir, `scene-${i}.png`)
        await writeFile(p, imageBuffers[i])
        imagePaths.push(p)
        // Feed each image as a single frame; zoompan generates the motion frames.
        // (Looping the still here would make zoompan emit d frames PER looped
        // frame, blowing the first scene up to fill the whole timeline.)
        inputArgs.push("-i", p)
      }
      // audio is the last input
      inputArgs.push("-i", audioFile)
      const audioIndex = n

      // Per-image: cover-crop to 1280x720, then a gentle alternating zoom held for
      // that scene's own frame count.
      const sceneFilters = imagePaths
        .map((_, i) => {
          const frames = Math.max(fps, Math.round(durations[i] * fps))
          const zoom = i % 2 === 0 ? "min(zoom+0.0008,1.18)" : "if(lte(zoom,1.0),1.18,max(1.0,zoom-0.0008))"
          return (
            `[${i}:v]scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,` +
            `zoompan=z='${zoom}':d=${frames}:s=1280x720:fps=${fps},setsar=1[s${i}]`
          )
        })
        .join(";")

      const concatInputs = imagePaths.map((_, i) => `[s${i}]`).join("")
      const filter =
        `${sceneFilters};` +
        `${concatInputs}concat=n=${imageBuffers.length}:v=1:a=0[slides];` +
        `[${audioIndex}:a]showwaves=s=1280x160:mode=cline:rate=${fps}:colors=0x34d399@0.85[wave];` +
        `[slides][wave]overlay=(W-w)/2:H-h-40:shortest=1,format=yuv420p[v]`

      const args = [
        "-y",
        ...inputArgs,
        "-filter_complex", filter,
        "-map", "[v]",
        "-map", `${audioIndex}:a`,
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "160k",
        "-shortest",
        "-movflags", "+faststart",
        outFile,
      ]
      await execFileAsync(ffmpegPath, args, { maxBuffer: 1024 * 1024 * 128 })
    }

    const video = await readFile(outFile)
    return new Response(new Uint8Array(video), {
      headers: {
        "Content-Type": "video/mp4",
        "Content-Disposition": 'inline; filename="episode.mp4"',
        "Cache-Control": "no-store",
      },
    })
  } catch (err) {
    const message = err instanceof Error ? err.message : "Video render failed."
    return Response.json({ error: message.slice(0, 500) }, { status: 500 })
  } finally {
    await rm(workDir, { recursive: true, force: true }).catch(() => {})
  }
}
