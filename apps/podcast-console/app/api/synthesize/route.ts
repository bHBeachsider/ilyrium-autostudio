import type { EpisodeSegment } from "@/lib/sandbox-types"

export const runtime = "nodejs"
export const maxDuration = 300

// Real two-host TTS via ElevenLabs. Same request/response contract as before:
//   in  -> { segments: EpisodeSegment[] }  (each { speaker: "Host A"|"Host B", text })
//   out -> audio/mpeg blob + X-Segments-Synthesized header
// One ElevenLabs call per host turn; buffers are concatenated (ffmpeg re-encodes
// downstream in /api/render-video, so naive MP3 concatenation is fine here).
//
// Config (apps/podcast-console/.env.local):
//   ELEVENLABS_API_KEY   (required)  -> https://elevenlabs.io/app/settings/api-keys
//   ELEVENLABS_VOICE_A   (optional)  -> voice id for Host A   (default: Rachel)
//   ELEVENLABS_VOICE_B   (optional)  -> voice id for Host B   (default: George, British)
//   ELEVENLABS_MODEL_ID  (optional)  -> default: eleven_multilingual_v2
// Grab voice ids from your ElevenLabs voice library (Voices -> ... -> Copy Voice ID).

const API_BASE = "https://api.elevenlabs.io/v1/text-to-speech"
const OUTPUT_FORMAT = "mp3_44100_128"

// Long-standing ElevenLabs default voices; override per your library via env.
const VOICE_A = process.env.ELEVENLABS_VOICE_A || "21m00Tcm4TlvDq8ikWAM" // Rachel (US, warm)
const VOICE_B = process.env.ELEVENLABS_VOICE_B || "JBFqnCBsd6RMkjVDRZzb" // George (UK, narration)
const MODEL_ID = process.env.ELEVENLABS_MODEL_ID || "eleven_multilingual_v2"

async function synthesizeSegment(text: string, voiceId: string, apiKey: string): Promise<Buffer> {
  const url = `${API_BASE}/${voiceId}?output_format=${OUTPUT_FORMAT}`
  const res = await fetch(url, {
    method: "POST",
    headers: {
      "xi-api-key": apiKey,
      "Content-Type": "application/json",
      Accept: "audio/mpeg",
    },
    body: JSON.stringify({
      text,
      model_id: MODEL_ID,
      voice_settings: {
        stability: 0.5,
        similarity_boost: 0.75,
        style: 0.0,
        use_speaker_boost: true,
      },
    }),
  })

  if (!res.ok) {
    // ElevenLabs returns a JSON error body on failure.
    const detail = await res.text().catch(() => "")
    throw new Error(`ElevenLabs TTS failed (${res.status}): ${detail.slice(0, 200)}`)
  }

  const arrayBuf = await res.arrayBuffer()
  return Buffer.from(arrayBuf)
}

export async function POST(req: Request) {
  const apiKey = process.env.ELEVENLABS_API_KEY
  if (!apiKey) {
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

  // Cap to keep synthesis within the route time budget.
  const capped = segments.slice(0, 40)

  try {
    const buffers: Buffer[] = []
    for (const seg of capped) {
      const voiceId = seg.speaker === "Host B" ? VOICE_B : VOICE_A
      const audio = await synthesizeSegment(seg.text.trim(), voiceId, apiKey)
      buffers.push(audio)
    }

    if (buffers.length === 0) {
      return Response.json({ error: "Nothing to synthesize." }, { status: 400 })
    }

    const combined = Buffer.concat(buffers)
    return new Response(new Uint8Array(combined), {
      status: 200,
      headers: {
        "Content-Type": "audio/mpeg",
        "Content-Length": String(combined.length),
        "Cache-Control": "no-store",
        "X-Segments-Synthesized": String(capped.length),
      },
    })
  } catch (err) {
    return Response.json(
      { error: err instanceof Error ? err.message : "Synthesis failed." },
      { status: 500 },
    )
  }
}
