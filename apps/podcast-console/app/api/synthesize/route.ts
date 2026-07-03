import type { EpisodeSegment } from "@/lib/sandbox-types"
import { synthesizeSegments, ttsReady } from "@/lib/generation/tts"

export const runtime = "nodejs"
export const maxDuration = 300

// Real two-host TTS via ElevenLabs (see lib/generation/tts.ts). Contract unchanged:
//   in  -> { segments: EpisodeSegment[] }  (each { speaker: "Host A"|"Host B", text })
//   out -> audio/mpeg blob + X-Segments-Synthesized header
export async function POST(req: Request) {
  if (!ttsReady()) {
    return Response.json(
      { error: "ELEVENLABS_API_KEY is not set. Add it to apps/podcast-console/.env.local and restart dev." },
      { status: 500 },
    )
  }

  let body: { segments?: EpisodeSegment[] }
  try {
    body = await req.json()
  } catch {
    return Response.json({ error: "Invalid request body." }, { status: 400 })
  }

  const segments = (body.segments ?? []).filter((s) => s?.text?.trim())
  if (segments.length === 0) {
    return Response.json({ error: "No script segments to synthesize." }, { status: 400 })
  }

  try {
    const { audio, synthesized } = await synthesizeSegments(segments)
    return new Response(new Uint8Array(audio), {
      status: 200,
      headers: {
        "Content-Type": "audio/mpeg",
        "Content-Length": String(audio.length),
        "Cache-Control": "no-store",
        "X-Segments-Synthesized": String(synthesized),
      },
    })
  } catch (err) {
    return Response.json({ error: err instanceof Error ? err.message : "Synthesis failed." }, { status: 500 })
  }
}
