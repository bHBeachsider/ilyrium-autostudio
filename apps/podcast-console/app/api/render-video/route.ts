import { NextRequest } from "next/server"
import { renderEpisodeVideo } from "@/lib/generation/video"

export const runtime = "nodejs"
export const maxDuration = 300

// ffmpeg episode render (see lib/generation/video.ts). Contract unchanged:
// multipart {audio, images[], weights} -> video/mp4 body.
export async function POST(req: NextRequest) {
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

  try {
    const { video } = await renderEpisodeVideo({ audio: audioBuffer, images: imageBuffers, weights })
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
  }
}
